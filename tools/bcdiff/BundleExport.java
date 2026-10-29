import com.github.javaparser.*;
import com.github.javaparser.ast.*;
import com.github.javaparser.ast.body.*;
import com.github.javaparser.ast.type.*;
import com.github.javaparser.ast.expr.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;

/** Turns delta.tsv + the workspace sources into member-level ops (JSON lines). Usage: BundleExport <wsRoot> <delta.tsv> <out.jsonl> <report.txt> */
public class BundleExport {
    static String esc(String s){ StringBuilder b=new StringBuilder("\""); for(char c:s.toCharArray()){ switch(c){case '"':b.append("\\\"");break;case '\\':b.append("\\\\");break;case '\n':b.append("\\n");break;case '\r':b.append("\\r");break;case '\t':b.append("\\t");break;default: if(c<0x20) b.append(String.format("\\u%04x",(int)c)); else b.append(c);} } return b.append('"').toString(); }
    /** JVM descriptor params -> simple type names */
    static List<String> descParams(String desc){
        List<String> r=new ArrayList<>(); int i=desc.indexOf('(')+1;
        while(desc.charAt(i)!=')'){
            int dims=0; while(desc.charAt(i)=='['){dims++;i++;}
            String t;
            char c=desc.charAt(i);
            if(c=='L'){ int e=desc.indexOf(';',i); String full=desc.substring(i+1,e); t=simple(full); i=e+1; }
            else { t=switch(c){case 'Z'->"boolean";case 'B'->"byte";case 'C'->"char";case 'S'->"short";case 'I'->"int";case 'J'->"long";case 'F'->"float";case 'D'->"double";default->"?";}; i++; }
            r.add(t+"[]".repeat(dims));
        }
        return r;
    }
    static String simple(String full){ String s=full.substring(full.lastIndexOf('/')+1); return s.substring(s.lastIndexOf('$')+1); }
    static String srcType(Parameter p){
        String t=p.getType().asString(); t=t.replaceAll("<.*>",""); t=t.substring(t.lastIndexOf('.')+1);
        if(p.isVarArgs()) t+="[]";
        return t;
    }
    static boolean sameParams(List<String> d,CallableDeclaration<?> c,Set<String> tvars){
        List<Parameter> ps=c.getParameters(); if(ps.size()!=d.size()) return false;
        for(int i=0;i<d.size();i++){ String s=srcType(ps.get(i)); String base=s.replace("[]",""); if(tvars.contains(base)) continue; if(!s.equals(d.get(i))) return false; }
        return true;
    }

    static boolean isAnon(ObjectCreationExpr o){ return o.getAnonymousClassBody().isPresent(); }
    /** n-th (1-based) anonymous class created directly in the scope's body (not inside another anonymous body or nested named type). */
    static Optional<ObjectCreationExpr> nthAnon(Node scope,int n){
        List<ObjectCreationExpr> l=new ArrayList<>();
        for(ObjectCreationExpr o:scope.findAll(ObjectCreationExpr.class)){
            if(!isAnon(o)) continue;
            Node p=o.getParentNode().orElse(null); boolean direct=true;
            while(p!=null&&p!=scope){ if((p instanceof ObjectCreationExpr&&isAnon((ObjectCreationExpr)p)&&((ObjectCreationExpr)p).getAnonymousClassBody().isPresent()&&p!=o)||(p instanceof TypeDeclaration)){ if(!(p==o)){ direct=false; break; } } p=p.getParentNode().orElse(null); }
            if(direct) l.add(o);
        }
        return n>=1&&n<=l.size()?Optional.of(l.get(n-1)):Optional.empty();
    }
    static Optional<BodyDeclaration<?>> enclosingMember(Node n){
        Node p=n.getParentNode().orElse(null);
        while(p!=null){ if(p instanceof MethodDeclaration||p instanceof ConstructorDeclaration||p instanceof FieldDeclaration||p instanceof InitializerDeclaration) return Optional.of((BodyDeclaration<?>)p); p=p.getParentNode().orElse(null); }
        return Optional.empty();
    }
    static void emitInit(PrintWriter out,TypeDeclaration<?> t,String cls,boolean isStatic){
        StringBuilder sb=new StringBuilder();
        for(BodyDeclaration<?> m:t.getMembers()){
            if(m instanceof FieldDeclaration){ FieldDeclaration f=(FieldDeclaration)m; if(f.isStatic()==isStatic&&f.getVariables().stream().anyMatch(v->v.getInitializer().isPresent())) sb.append(f).append("\n"); }
            else if(m instanceof InitializerDeclaration){ InitializerDeclaration i=(InitializerDeclaration)m; if(i.isStatic()==isStatic) sb.append(i).append("\n"); }
        }
        if(t instanceof EnumDeclaration&&isStatic) sb.insert(0,((EnumDeclaration)t).getEntries().stream().map(Object::toString).collect(Collectors.joining(",\n"))+";\n");
        out.println("{\"op\":\"initializers-replace\",\"class\":"+esc(cls)+",\"static\":"+isStatic+",\"text\":"+esc(sb.toString())+"}");
    }
    public static void main(String[] a) throws Exception {
        Path ws=Paths.get(a[0]);
        List<String[]> rows=Files.readAllLines(Paths.get(a[1])).stream().map(l->l.split("\t",-1)).collect(Collectors.toList());
        PrintWriter out=new PrintWriter(Files.newBufferedWriter(Paths.get(a[2]),StandardCharsets.UTF_8));
        PrintWriter rep=new PrintWriter(Files.newBufferedWriter(Paths.get(a[3]),StandardCharsets.UTF_8));
        Map<String,List<String[]>> byFile=new TreeMap<>();
        for(String[] r:rows){ String cls=r[0]; String top=cls.contains("$")?cls.substring(0,cls.indexOf('$')):cls; byFile.computeIfAbsent(top,k->new ArrayList<>()).add(r); }
        JavaParser jp=new JavaParser(new ParserConfiguration().setLanguageLevel(ParserConfiguration.LanguageLevel.JAVA_17).setAttributeComments(true));
        int ops=0,whole=0,unres=0; Set<String> enumDone=new HashSet<>();
        for(Map.Entry<String,List<String[]>> e:byFile.entrySet()){
            String top=e.getKey(); List<String[]> rs=e.getValue();
            // class-level ops
            for(String[] r:rs) if(r[1].equals("delete-class")) { out.println("{\"op\":\"delete-class\",\"class\":"+esc(r[0])+"}"); ops++; }
            boolean anyAdd=rs.stream().anyMatch(r->r[1].equals("add-class"));
            List<String[]> mem=rs.stream().filter(r->!r[1].endsWith("-class")&&!r[1].equals("replace-file")).collect(Collectors.toList());
            if(rs.stream().allMatch(r->r[1].equals("delete-class")) ) continue;
            Path f=ws.resolve(top+".java");
            if(!Files.exists(f)){ rep.println("NOFILE "+top); unres++; continue; }
            String src=Files.readString(f,StandardCharsets.UTF_8);
            ParseResult<CompilationUnit> pr=jp.parse(src);
            if(!pr.isSuccessful()||pr.getResult().isEmpty()){ rep.println("PARSEFAIL "+top); unres++; continue; }
            CompilationUnit cu=pr.getResult().get();
            boolean topAdded=rs.stream().anyMatch(r->(r[1].equals("add-class")||r[1].equals("replace-file"))&&r[0].equals(top));
            boolean replace=rs.stream().anyMatch(r->r[1].equals("replace-file"));
            List<String> imports=cu.getImports().stream().map(i->i.toString().trim()).collect(Collectors.toList());
            // named nested classes that exist only in the workspace: carry the whole type
            Set<String> addedNames=rs.stream().filter(r->r[1].equals("add-class")).map(r->r[0]).collect(Collectors.toSet());
            for(String ac:addedNames){
                if(ac.equals(top)||ac.matches(".*\\$\\d.*")) continue;
                String parentCls=ac.substring(0,ac.lastIndexOf('$'));
                if(addedNames.contains(parentCls)) continue; // the parent's text already contains it
                String[] ps=ac.substring(top.length()).split("\\$");
                String topNm=top.substring(top.lastIndexOf('/')+1);
                Optional<TypeDeclaration<?>> cur=cu.getTypes().stream().filter(t->t.getNameAsString().equals(topNm)).findFirst().map(t->(TypeDeclaration<?>)t);
                for(int i=1;i<ps.length&&cur.isPresent();i++){ String nm=ps[i]; cur=cur.get().getMembers().stream().filter(m->m instanceof TypeDeclaration&&((TypeDeclaration<?>)m).getNameAsString().equals(nm)).findFirst().map(m->(TypeDeclaration<?>)m); }
                if(cur.isEmpty()){ rep.println("NOTYPE-ADD "+ac); unres++; continue; }
                out.println("{\"op\":\"type-add\",\"class\":"+esc(parentCls)+",\"name\":"+esc(ps[ps.length-1])+",\"text\":"+esc(cur.get().toString())+"}"); ops++;
            }
            if(topAdded){ out.println("{\"op\":\""+(replace?"replace-file":"add-file")+"\",\"class\":"+esc(top)+",\"text\":"+esc(src)+"}"); ops++; whole++; continue; }
            // collect type vars across the file (class/method level) as wildcards
            Set<String> tv=new HashSet<>(); cu.findAll(TypeParameter.class).forEach(t->tv.add(t.getNameAsString()));
            for(String[] r:mem){
                String cls=r[0]; String kind=r[1]; String key=r[2];
                if(cls.matches(".*\\$\\d.*")){
                    // map an anonymous class (Outer$Inner$3 or $3$1) to the member of its nearest named class that creates it
                    String[] seg=cls.substring(top.length()).split("\\$");
                    String topName2=top.substring(top.lastIndexOf('/')+1);
                    Node scope=cu.getTypes().stream().filter(t2->t2.getNameAsString().equals(topName2)).findFirst().orElse(null);
                    Node lastNamedScope=scope; ObjectCreationExpr firstAnon=null;
                    for(int i=1;i<seg.length&&scope!=null;i++){
                        if(seg[i].matches("\\d+")){
                            Optional<ObjectCreationExpr> oc=nthAnon(scope,Integer.parseInt(seg[i]));
                            if(oc.isEmpty()){ scope=null; break; }
                            if(firstAnon==null) firstAnon=oc.get();
                            scope=oc.get();
                        } else { final String nm=seg[i]; scope=((TypeDeclaration<?>)scope).getMembers().stream().filter(m->m instanceof TypeDeclaration&&((TypeDeclaration<?>)m).getNameAsString().equals(nm)).findFirst().orElse(null); if(scope==null) break; lastNamedScope=scope; }
                    }
                    Optional<BodyDeclaration<?>> em=firstAnon==null?Optional.empty():enclosingMember(firstAnon);
                    if(scope==null||em.isEmpty()){ out.println("{\"op\":\"whole-file-needed\",\"class\":"+esc(top)+",\"why\":"+esc("anonymous class not located "+cls+" "+kind+" "+key)+"}"); rep.println("ANON "+cls+" "+kind+" "+key); unres++; continue; }
                    BodyDeclaration<?> b=em.get();
                    String ownerCls=cls.replaceAll("(\\$\\d+)+$","");
                    ownerCls=ownerCls.replaceAll("\\$\\d+.*$","");
                    if(b instanceof MethodDeclaration||b instanceof ConstructorDeclaration){
                        CallableDeclaration<?> cd=(CallableDeclaration<?>)b; String nm2=b instanceof ConstructorDeclaration?"<init>":cd.getNameAsString();
                        List<String> ps=new ArrayList<>(); for(Parameter p:cd.getParameters()) ps.add(srcType(p));
                        out.println("{\"op\":\"method-replace\",\"class\":"+esc(ownerCls)+",\"name\":"+esc(nm2)+",\"params\":"+esc(String.join(",",ps))+",\"via\":"+esc("anon "+cls)+",\"text\":"+esc(cd.toString())+"}"); ops++;
                    } else if(b instanceof FieldDeclaration){
                        FieldDeclaration fd=(FieldDeclaration)b; out.println("{\"op\":\"field-add\",\"class\":"+esc(ownerCls)+",\"name\":"+esc(fd.getVariable(0).getNameAsString())+",\"via\":"+esc("anon "+cls)+",\"text\":"+esc(fd.toString())+"}"); ops++;
                    } else { out.println("{\"op\":\"whole-file-needed\",\"class\":"+esc(top)+",\"why\":"+esc("anonymous class in initializer block "+cls)+"}"); rep.println("ANONINIT "+cls); unres++; }
                    continue;
                }
                String[] parts=cls.substring(top.length()).split("\\$"); // "", Inner, Inner2
                String topName=top.substring(top.lastIndexOf('/')+1);
                Optional<TypeDeclaration<?>> td=cu.getTypes().stream().filter(t->t.getNameAsString().equals(topName)).findFirst().map(t->(TypeDeclaration<?>)t);
                for(int i=1;i<parts.length&&td.isPresent();i++){ String nm=parts[i]; td=td.get().getMembers().stream().filter(m->m instanceof TypeDeclaration&&((TypeDeclaration<?>)m).getNameAsString().equals(nm)).findFirst().map(m->(TypeDeclaration<?>)m); }
                if(td.isEmpty()){ rep.println("NOTYPE "+cls); unres++; continue; }
                TypeDeclaration<?> t=td.get();
                if(kind.startsWith("field-")){
                    String fname=key.substring(0,key.indexOf(':'));
                    if(t instanceof EnumDeclaration && ((EnumDeclaration)t).getEntries().stream().anyMatch(en->en.getNameAsString().equals(fname))){
                        if(enumDone.add(cls)){ String txt=((EnumDeclaration)t).getEntries().stream().map(Object::toString).collect(Collectors.joining(",\n")); out.println("{\"op\":\"enum-constants-replace\",\"class\":"+esc(cls)+",\"text\":"+esc(txt)+"}"); ops++; }
                        continue;
                    }
                    Optional<FieldDeclaration> fd=t.getFields().stream().filter(x->x.getVariables().stream().anyMatch(v->v.getNameAsString().equals(fname))).findFirst();
                    if(kind.equals("field-add")){ if(fd.isPresent()){ out.println("{\"op\":\"field-add\",\"class\":"+esc(cls)+",\"name\":"+esc(fname)+",\"text\":"+esc(fd.get().toString())+"}"); ops++; } else { rep.println("NOFIELD "+cls+" "+fname); unres++; } }
                    else { out.println("{\"op\":\"field-delete\",\"class\":"+esc(cls)+",\"name\":"+esc(fname)+"}"); ops++; }
                    continue;
                }
                String mname=key.substring(0,key.indexOf('('));
                List<String> dp=descParams(key.substring(key.indexOf('(')));
                if(mname.equals("<clinit>")){ emitInit(out,t,cls,true); ops++; continue; }
                if(kind.equals("method-delete")){ out.println("{\"op\":\"method-delete\",\"class\":"+esc(cls)+",\"name\":"+esc(mname)+",\"params\":"+esc(String.join(",",dp))+"}"); ops++; continue; }
                CallableDeclaration<?> found=null; int cnt=0;
                if(mname.equals("<init>")){
                    // inner (non-static) classes get the outer instance as first descriptor param; try both
                    List<ConstructorDeclaration> cs=t.getConstructors();
                    for(ConstructorDeclaration c:cs){ if(sameParams(dp,c,tv)||(dp.size()==c.getParameters().size()+1&&sameParams(dp.subList(1,dp.size()),c,tv))||(dp.size()>=2&&dp.size()==c.getParameters().size()+2&&t instanceof EnumDeclaration&&sameParams(dp.subList(2,dp.size()),c,tv))){found=c;cnt++;} }
                    if(found==null&&cs.isEmpty()&&(dp.isEmpty()||t instanceof EnumDeclaration)){ emitInit(out,t,cls,false); ops++; continue; }
                } else {
                    for(MethodDeclaration m:t.getMethodsByName(mname)){ if(sameParams(dp,m,tv)){found=m;cnt++;} }
                }
                if(found==null||cnt!=1){ rep.println((cnt>1?"AMBIG ":"NOMETHOD ")+cls+" "+mname+" "+dp); unres++; out.println("{\"op\":\"whole-file-needed\",\"class\":"+esc(top)+",\"why\":"+esc("unresolved "+cls+" "+mname+dp)+"}"); continue; }
                out.println("{\"op\":\""+(kind.equals("method-add")?"method-add":"method-replace")+"\",\"class\":"+esc(cls)+",\"name\":"+esc(mname)+",\"params\":"+esc(String.join(",",dp))+",\"text\":"+esc(found.toString())+"}"); ops++;
            }
            out.println("{\"op\":\"imports\",\"class\":"+esc(top)+",\"imports\":"+esc(String.join("\n",imports))+"}");
        }
        // imports for every other file that exists on both sides (shim imports such as Random change without any member changing)
        if(a.length>4){ Set<String> done=new HashSet<>(byFile.keySet());
            for(String top:Files.readAllLines(Paths.get(a[4]))){ if(top.isBlank()||done.contains(top)) continue; Path f=ws.resolve(top+".java"); if(!Files.exists(f)) continue;
                ParseResult<CompilationUnit> pr=jp.parse(Files.readString(f,StandardCharsets.UTF_8)); if(!pr.isSuccessful()||pr.getResult().isEmpty()) continue;
                List<String> imps=pr.getResult().get().getImports().stream().map(i->i.toString().trim()).collect(Collectors.toList());
                out.println("{\"op\":\"imports\",\"class\":"+esc(top)+",\"imports\":"+esc(String.join("\n",imps))+"}"); } }
        out.close(); rep.close();
        System.out.println("ops="+ops+" wholeFileAdds="+whole+" unresolved="+unres);
    }
}
