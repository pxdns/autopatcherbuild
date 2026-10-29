import com.github.javaparser.*;
import com.github.javaparser.ast.*;
import com.github.javaparser.ast.body.*;
import com.github.javaparser.ast.expr.*;
import com.github.javaparser.ast.stmt.*;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.objectweb.asm.tree.analysis.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.regex.*;
import java.util.stream.*;
import java.util.zip.*;

/**
 * Repairs the names of captured variables inside decompiled lambdas.
 * The decompiler numbers a lambda's variables inside the lambda's own synthetic method: captured values first (var0, var1, ...), then
 * parameters, then locals. The enclosing method calls the same variables by their own numbers. The bytecode says which enclosing local
 * feeds each captured argument, so the correct names are known exactly.
 * Only lambdas that contain a javac error line (from the log of the pristine tree) are changed.
 * Usage: LambdaCaptures <vanilla-jar> <treeRoot> <javac.log> <strip-prefix> <report.txt>
 */
public class LambdaCaptures {
    static class Site { int ord; int[] slots; Type[] capTypes; String implOwner, implName, implDesc; }
    static class MInfo { String owner, name, desc; List<String> simpleParams; }
    static final Map<String, List<Site>> SITES = new HashMap<>();
    static final Map<String, List<MInfo>> BY_CLASS = new HashMap<>();
    static final Pattern IDENT = Pattern.compile("[A-Za-z_$][A-Za-z0-9_$]*");

    static String simple(String full) { String s = full.substring(full.lastIndexOf('/') + 1); return s.substring(s.lastIndexOf('$') + 1); }
    static List<String> descParams(String desc) {
        List<String> r = new ArrayList<>();
        for (Type t : Type.getArgumentTypes(desc)) {
            String n = t.getSort() == Type.ARRAY ? simple(t.getElementType().getClassName().replace('.', '/')) + "[]".repeat(t.getDimensions())
                    : t.getSort() == Type.OBJECT ? simple(t.getInternalName()) : t.getClassName();
            r.add(n);
        }
        return r;
    }
    static int size(Type t) { return t.getSize(); }

    static void loadJar(String path) throws Exception {
        try (ZipFile z = new ZipFile(path)) {
            for (Enumeration<? extends ZipEntry> e = z.entries(); e.hasMoreElements(); ) {
                ZipEntry ze = e.nextElement();
                if (!ze.getName().endsWith(".class")) continue;
                ClassNode cn = new ClassNode();
                try (InputStream is = z.getInputStream(ze)) { new ClassReader(is).accept(cn, ClassReader.SKIP_FRAMES | ClassReader.SKIP_DEBUG); }
                for (MethodNode mn : cn.methods) {
                    List<Site> sites = null;
                    Frame<SourceValue>[] frames = null;
                    int ord = 0;
                    for (int i = 0; i < mn.instructions.size(); i++) {
                        AbstractInsnNode in = mn.instructions.get(i);
                        if (!(in instanceof InvokeDynamicInsnNode)) continue;
                        InvokeDynamicInsnNode idn = (InvokeDynamicInsnNode) in;
                        if (!idn.bsm.getOwner().equals("java/lang/invoke/LambdaMetafactory")) continue;
                        if (frames == null) {
                            try { frames = new Analyzer<>(new SourceInterpreter()).analyze(cn.name, mn); } catch (AnalyzerException ex) { frames = new Frame[0]; }
                        }
                        if (frames.length == 0 || frames[i] == null) { ord++; continue; }
                        Type[] args = Type.getArgumentTypes(idn.desc);
                        Frame<SourceValue> f = frames[i];
                        int sp = f.getStackSize();
                        Site s = new Site(); s.ord = ord++; s.slots = new int[args.length]; s.capTypes = args;
                        for (int j = 0; j < args.length; j++) {
                            SourceValue sv = f.getStack(sp - args.length + j);
                            s.slots[j] = -1;
                            if (sv.insns.size() == 1) { AbstractInsnNode p = sv.insns.iterator().next(); if (p instanceof VarInsnNode && p.getOpcode() >= Opcodes.ILOAD && p.getOpcode() <= Opcodes.ALOAD) s.slots[j] = ((VarInsnNode) p).var; }
                        }
                        Handle impl = (Handle) idn.bsmArgs[1];
                        s.implOwner = impl.getOwner(); s.implName = impl.getName(); s.implDesc = impl.getDesc();
                        if (sites == null) sites = new ArrayList<>();
                        sites.add(s);
                    }
                    if (sites != null) {
                        SITES.put(cn.name + "." + mn.name + mn.desc, sites);
                        if (!mn.name.startsWith("lambda$")) {
                            MInfo mi = new MInfo(); mi.owner = cn.name; mi.name = mn.name; mi.desc = mn.desc; mi.simpleParams = descParams(mn.desc);
                            BY_CLASS.computeIfAbsent(cn.name, k -> new ArrayList<>()).add(mi);
                        }
                    }
                }
            }
        }
    }

    // ---- AST helpers
    static boolean sameParams(List<String> d, CallableDeclaration<?> c, int skip) {
        List<Parameter> ps = c.getParameters();
        if (ps.size() + skip != d.size()) return false;
        for (int i = 0; i < ps.size(); i++) {
            String t = ps.get(i).getType().asString().replaceAll("<.*>", ""); t = t.substring(t.lastIndexOf('.') + 1);
            if (ps.get(i).isVarArgs()) t += "[]";
            String base = t.replace("[]", "");
            if (base.length() == 1 && Character.isUpperCase(base.charAt(0))) continue; // type variable
            if (!t.equals(d.get(i + skip))) return false;
        }
        return true;
    }
    static void collect(Node n, List<Node> out) {
        List<Node> kids = new ArrayList<>(n.getChildNodes());
        kids.sort(Comparator.comparing(k -> k.getRange().map(r -> r.begin).orElse(new com.github.javaparser.Position(0, 0))));
        for (Node c : kids) {
            if (c instanceof LambdaExpr || c instanceof MethodReferenceExpr) { out.add(c); continue; }
            if (c instanceof ObjectCreationExpr && ((ObjectCreationExpr) c).getAnonymousClassBody().isPresent()) {
                ObjectCreationExpr o = (ObjectCreationExpr) c;
                for (Expression a : o.getArguments()) { if (a instanceof LambdaExpr || a instanceof MethodReferenceExpr) out.add(a); else collect(a, out); }
                continue;
            }
            if (c instanceof ClassOrInterfaceDeclaration || c instanceof LocalClassDeclarationStmt || c instanceof LocalRecordDeclarationStmt) continue;
            collect(c, out);
        }
    }
    static int[] lineStarts(String text) {
        List<Integer> st = new ArrayList<>(); st.add(0);
        for (int i = 0; i < text.length(); i++) if (text.charAt(i) == '\n') st.add(i + 1);
        return st.stream().mapToInt(x -> x).toArray();
    }
    static int off(int[] ls, com.github.javaparser.Position p) { return ls[p.line - 1] + p.column - 1; }

    /** Everything needed to name variables in one lambda body. */
    static class Rule {
        int begin, end;                 // text offsets of the lambda expression
        Map<String, String> cap = new HashMap<>();   // var-name inside the lambda -> enclosing name
        Set<String> own = new HashSet<>();           // names declared inside the lambda: renamed +y
        Function2 slotName;             // slot inside this lambda's synthetic method -> final name (or null)
    }
    interface Function2 { String get(int slot); }

    static Set<String> declaredNames(Node body) {
        Set<String> d = new HashSet<>();
        body.findAll(VariableDeclarator.class).forEach(v -> d.add(v.getNameAsString()));
        body.findAll(Parameter.class).forEach(p -> d.add(p.getNameAsString()));
        return d;
    }

    static int stats_flagged, stats_done, stats_unmatched, stats_unresolved;
    static PrintWriter REP;

    /** names of variables visible as locals of `scopeBody` before offset `before` whose decompiler name ends in the given slot number */
    static String localBySlot(Node scopeBody, int slot, int[] ls, int before, int skipBegin, int skipEnd) {
        String best = null; int bestAt = -1;
        Pattern p = Pattern.compile("^var" + slot + "[a-z]*$");
        for (VariableDeclarator v : scopeBody.findAll(VariableDeclarator.class)) {
            if (!p.matcher(v.getNameAsString()).matches()) continue;
            int at = off(ls, v.getRange().get().begin);
            if (at < before && at > bestAt) { best = v.getNameAsString(); bestAt = at; }
        }
        // for-each / catch parameters are Parameter nodes
        for (Parameter v : scopeBody.findAll(Parameter.class)) {
            if (!p.matcher(v.getNameAsString()).matches()) continue;
            int at = off(ls, v.getRange().get().begin);
            if (at < before && at > bestAt) { best = v.getNameAsString(); bestAt = at; }
        }
        return best;
    }

    static void buildRules(List<Node> nodes, List<Site> sites, Function2 outerSlotName, Node scopeBody, int[] ls, Set<Integer> flaggedLines,
                           List<Rule> rules, boolean outerIsMethod) {
        for (int i = 0; i < nodes.size() && i < sites.size(); i++) {
            Node n = nodes.get(i); Site s = sites.get(i);
            if (!(n instanceof LambdaExpr)) continue;
            LambdaExpr L = (LambdaExpr) n;
            Type[] implArgsChk = Type.getArgumentTypes(s.implDesc);
            if (implArgsChk.length != s.capTypes.length + L.getParameters().size()) {
                if (REP != null) REP.println("SITE MISMATCH at line " + L.getRange().get().begin.line + " impl=" + s.implName + " implArgs=" + implArgsChk.length + " captured=" + s.capTypes.length + " lambdaParams=" + L.getParameters().size());
                stats_unmatched++; continue;
            }
            int bl = L.getRange().get().begin.line, el = L.getRange().get().end.line;
            boolean flagged = false;
            for (int ln : flaggedLines) if (ln >= bl && ln <= el) { flagged = true; break; }
            if (!flagged) {
                if (!outerIsMethod) { Rule sh = new Rule(); sh.begin = off(ls, L.getRange().get().begin); sh.end = off(ls, L.getRange().get().end) + 1; rules.add(sh); }
                continue;
            }
            stats_flagged++;
            Rule r = new Rule();
            r.begin = off(ls, L.getRange().get().begin); r.end = off(ls, L.getRange().get().end) + 1;
            // slots inside the lambda's synthetic method
            Type[] implArgs = Type.getArgumentTypes(s.implDesc);
            int[] slotAt = new int[implArgs.length]; int acc = 0;
            for (int k = 0; k < implArgs.length; k++) { slotAt[k] = acc; acc += implArgs[k].getSize(); }
            int c = s.capTypes.length;
            boolean complete = true;
            for (int k = 0; k < c; k++) {
                String inner = "var" + slotAt[k];
                String target = s.slots[k] < 0 ? null : outerSlotName.get(s.slots[k]);
                if (target == null) { complete = false; continue; }
                r.cap.put(inner, target);
            }
            if (!complete) { stats_unresolved++; if (REP != null) REP.println("UNRESOLVED captured slots in lambda at line " + bl); }
            r.own = declaredNames(L.getBody());
            for (Parameter p : L.getParameters()) r.own.add(p.getNameAsString());
            // lambda parameters: slots after the captured ones
            final List<Parameter> lps = L.getParameters();
            final int[] sa = slotAt; final int cc = c; final Rule rf = r; final Node body = L.getBody(); final int bb = r.begin;
            r.slotName = slot -> {
                for (int k = 0; k < cc; k++) if (sa[k] == slot) return rf.cap.get("var" + sa[k]);
                for (int j = 0; j < lps.size() && cc + j < sa.length; j++) if (sa[cc + j] == slot) return lps.get(j).getNameAsString() + "y";
                String lv = localBySlot(body, slot, ls, Integer.MAX_VALUE, 0, 0);
                return lv == null ? null : lv + "y";
            };
            rules.add(r);
            // nested lambdas
            List<Site> inner = SITES.get(s.implOwner + "." + s.implName + s.implDesc);
            if (inner != null) {
                List<Node> kids = new ArrayList<>(); collect(L.getBody(), kids);
                buildRules(kids, inner, r.slotName, L.getBody(), ls, flaggedLines, rules, false);
            }
        }
    }

    public static void main(String[] a) throws Exception {
        loadJar(a[0]);
        Path root = Paths.get(a[1]);
        Map<String, Set<Integer>> flagged = new TreeMap<>();
        for (String l : Files.readAllLines(Paths.get(a[2]), StandardCharsets.UTF_8)) {
            Matcher m = Pattern.compile("^(\\S+\\.java):(\\d+): error: ").matcher(l);
            if (m.find()) { String f = m.group(1); if (f.startsWith(a[3])) f = f.substring(a[3].length()); flagged.computeIfAbsent(f, k -> new TreeSet<>()).add(Integer.parseInt(m.group(2))); }
        }
        REP = new PrintWriter(Files.newBufferedWriter(Paths.get(a[4]), StandardCharsets.UTF_8));
        JavaParser jp = new JavaParser(new ParserConfiguration().setLanguageLevel(ParserConfiguration.LanguageLevel.JAVA_17));
        int files = 0;
        for (Map.Entry<String, Set<Integer>> e : flagged.entrySet()) {
            Path p = root.resolve(e.getKey());
            if (!Files.exists(p)) continue;
            String text = Files.readString(p, StandardCharsets.UTF_8);
            ParseResult<CompilationUnit> pr = jp.parse(text);
            if (!pr.isSuccessful() || pr.getResult().isEmpty()) continue;
            CompilationUnit cu = pr.getResult().get();
            int[] ls = lineStarts(text);
            String top = e.getKey().substring(0, e.getKey().length() - 5);
            List<Rule> rules = new ArrayList<>();
            // walk named types
            Deque<Object[]> work = new ArrayDeque<>();
            for (TypeDeclaration<?> t : cu.getTypes()) work.add(new Object[]{t, top});
            while (!work.isEmpty()) {
                Object[] w = work.poll(); TypeDeclaration<?> t = (TypeDeclaration<?>) w[0]; String internal = (String) w[1];
                for (BodyDeclaration<?> m : t.getMembers()) if (m instanceof TypeDeclaration) work.add(new Object[]{m, internal + "$" + ((TypeDeclaration<?>) m).getNameAsString()});
                List<MInfo> infos = BY_CLASS.getOrDefault(internal, List.of());
                for (BodyDeclaration<?> m : t.getMembers()) {
                    if (!(m instanceof MethodDeclaration)) continue;
                    MethodDeclaration md = (MethodDeclaration) m;
                    if (md.getBody().isEmpty()) continue;
                    MInfo match = null; int cnt = 0;
                    for (MInfo mi : infos) if (mi.name.equals(md.getNameAsString()) && sameParams(mi.simpleParams, md, 0)) { match = mi; cnt++; }
                    if (cnt != 1) continue;
                    List<Site> sites = SITES.get(match.owner + "." + match.name + match.desc);
                    List<Node> nodes = new ArrayList<>(); collect(md.getBody().get(), nodes);
                    if (nodes.size() != sites.size()) { stats_unmatched++; if (REP != null) REP.println("COUNT MISMATCH " + internal + "." + md.getNameAsString() + " ast=" + nodes.size() + " bytecode=" + sites.size()); continue; }
                    // slot -> name in the enclosing method: parameters, then locals
                    final MethodDeclaration fmd = md; final boolean isStatic = md.isStatic();
                    final Type[] pt = Type.getArgumentTypes(match.desc);
                    Function2 slotName = slot -> {
                        int acc = isStatic ? 0 : 1;
                        if (!isStatic && slot == 0) return null; // this
                        for (int j = 0; j < pt.length; j++) { if (acc == slot) return fmd.getParameter(j).getNameAsString(); acc += pt[j].getSize(); }
                        return localBySlot(fmd.getBody().get(), slot, ls, Integer.MAX_VALUE, 0, 0);
                    };
                    buildRules(nodes, sites, slotName, md.getBody().get(), ls, e.getValue(), rules, true);
                }
            }
            if (rules.isEmpty()) continue;
            // single pass over identifier tokens; innermost rule that contains the token wins
            StringBuilder out = new StringBuilder(); Matcher im = IDENT.matcher(text); int last = 0; int changed = 0;
            while (im.find()) {
                int s0 = im.start();
                String id = im.group();
                Rule best = null;
                for (Rule r : rules) if (s0 >= r.begin && s0 < r.end && (best == null || (r.end - r.begin) < (best.end - best.begin))) best = r;
                if (best == null) continue;
                String repl = null;
                if (best.cap.containsKey(id)) repl = best.cap.get(id);
                else if (best.own.contains(id) && id.startsWith("var")) repl = id + "y";
                if (repl != null && !repl.equals(id)) { out.append(text, last, s0).append(repl); last = im.end(); changed++; }
            }
            out.append(text.substring(last));
            if (changed > 0) { Files.writeString(p, out.toString(), StandardCharsets.UTF_8); files++; stats_done += rules.size(); }
        }
        REP.close();
        System.out.println("flagged lambdas=" + stats_flagged + " rewritten rule sets=" + stats_done + " unresolved captures=" + stats_unresolved + " count-mismatch methods=" + stats_unmatched + " files changed=" + files);
    }
}
