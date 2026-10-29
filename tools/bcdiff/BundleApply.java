import com.github.javaparser.*;
import com.github.javaparser.ast.*;
import com.github.javaparser.ast.body.*;
import com.github.javaparser.ast.expr.*;
import com.github.javaparser.printer.lexicalpreservation.LexicalPreservingPrinter;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.regex.*;
import java.util.stream.*;

/** Applies ops.jsonl to a decompiled vanilla source tree in place. Usage: BundleApply <treeRoot> <ops.jsonl> <report.txt> */
public class BundleApply {
    // tiny JSON-lines reader for the flat string/bool objects we emit
    static Map<String,String> parse(String line){
        Map<String,String> m=new LinkedHashMap<>(); int i=line.indexOf('{')+1;
        while(i<line.length()){
            while(i<line.length()&&(line.charAt(i)==' '||line.charAt(i)==',')) i++;
            if(i>=line.length()||line.charAt(i)=='}') break;
            int e=line.indexOf('"',i+1); String k=line.substring(i+1,e); i=e+2; // skip ":"
            String v;
            if(line.charAt(i)=='"'){ StringBuilder b=new StringBuilder(); i++; while(line.charAt(i)!='"'){ char c=line.charAt(i); if(c=='\\'){ i++; char d=line.charAt(i); switch(d){case 'n':b.append('\n');break;case 'r':b.append('\r');break;case 't':b.append('\t');break;case 'u':b.append((char)Integer.parseInt(line.substring(i+1,i+5),16));i+=4;break;default:b.append(d);} } else b.append(c); i++; } i++; v=b.toString(); }
            else { int e2=i; while(e2<line.length()&&line.charAt(e2)!=','&&line.charAt(e2)!='}') e2++; v=line.substring(i,e2); i=e2; }
            m.put(k,v);
        }
        return m;
    }
    static String simple(String full){ String s=full.substring(full.lastIndexOf('/')+1); return s.substring(s.lastIndexOf('$')+1); }
    static String srcType(Parameter p){ String t=p.getType().asString().replaceAll("<.*>",""); t=t.substring(t.lastIndexOf('.')+1); if(p.isVarArgs()) t+="[]"; return t; }
    static boolean paramsMatch(CallableDeclaration<?> c,String params,Set<String> tv,int skip){
        List<String> want=params.isEmpty()?List.of():Arrays.asList(params.split(","));
        List<Parameter> ps=c.getParameters();
        if(ps.size()!=want.size()-skip&&ps.size()!=want.size()) return false;
        int off=ps.size()==want.size()?0:skip;
        for(int i=0;i<ps.size();i++){ String s=srcType(ps.get(i)); if(tv.contains(s.replace("[]",""))) continue; if(!s.equals(want.get(i+off))) return false; }
        return true;
    }
    static Optional<TypeDeclaration<?>> findType(CompilationUnit cu,String top,String cls){
        String topName=top.substring(top.lastIndexOf('/')+1);
        Optional<TypeDeclaration<?>> td=cu.getTypes().stream().filter(t->t.getNameAsString().equals(topName)).findFirst().map(t->(TypeDeclaration<?>)t);
        String[] parts=cls.substring(top.length()).split("\\$");
        for(int i=1;i<parts.length&&td.isPresent();i++){ String nm=parts[i]; td=td.get().getMembers().stream().filter(m->m instanceof TypeDeclaration&&((TypeDeclaration<?>)m).getNameAsString().equals(nm)).findFirst().map(m->(TypeDeclaration<?>)m); }
        return td;
    }
    public static void main(String[] a) throws Exception {
        Path root=Paths.get(a[0]); PrintWriter rep=new PrintWriter(Files.newBufferedWriter(Paths.get(a[2]),StandardCharsets.UTF_8));
        List<Map<String,String>> ops=Files.readAllLines(Paths.get(a[1]),StandardCharsets.UTF_8).stream().filter(l->!l.isBlank()).map(BundleApply::parse).collect(Collectors.toList());
        Map<String,List<Map<String,String>>> byTop=new TreeMap<>();
        for(Map<String,String> o:ops){ String c=o.get("class"); String top=c.contains("$")?c.substring(0,c.indexOf('$')):c; byTop.computeIfAbsent(top,k->new ArrayList<>()).add(o); }
        JavaParser jp=new JavaParser(new ParserConfiguration().setLanguageLevel(ParserConfiguration.LanguageLevel.JAVA_17).setAttributeComments(true));
        int applied=0,failed=0,filesTouched=0;
        for(Map.Entry<String,List<Map<String,String>>> e:byTop.entrySet()){
            String top=e.getKey(); Path f=root.resolve(top+".java");
            for(Map<String,String> o:e.getValue()){
                if(o.get("op").equals("delete-class")&&o.get("class").equals(top)){ if(Files.deleteIfExists(f)){applied++;} else {rep.println("DEL-MISSING "+top);} }
                if(o.get("op").equals("add-file")||o.get("op").equals("replace-file")){ Files.createDirectories(f.getParent()); Files.writeString(f,o.get("text"),StandardCharsets.UTF_8); applied++; }
            }
            List<Map<String,String>> mem=e.getValue().stream().filter(o->!Set.of("delete-class","add-file","replace-file","whole-file-needed").contains(o.get("op"))||(o.get("op").equals("delete-class")&&!o.get("class").equals(top))).collect(Collectors.toList());
            if(mem.isEmpty()) continue;
            if(!Files.exists(f)){ rep.println("NOFILE "+top); failed+=mem.size(); continue; }
            if(e.getValue().stream().anyMatch(o->o.get("op").equals("replace-file")||o.get("op").equals("add-file"))) continue;
            ParseResult<CompilationUnit> pr=jp.parse(Files.readString(f,StandardCharsets.UTF_8));
            if(!pr.isSuccessful()||pr.getResult().isEmpty()){ rep.println("PARSEFAIL "+top+" "+pr.getProblems().stream().findFirst().map(Object::toString).orElse("")); failed+=mem.size(); continue; }
            CompilationUnit cu=pr.getResult().get(); LexicalPreservingPrinter.setup(cu);
            Set<String> tv=new HashSet<>(); cu.findAll(com.github.javaparser.ast.type.TypeParameter.class).forEach(t->tv.add(t.getNameAsString()));
            boolean changed=false;
            for(Map<String,String> o:mem){
                String op=o.get("op"),cls=o.get("class");
                if(op.equals("imports")){ for(String imp:o.get("imports").split("\n")){ imp=imp.trim(); if(imp.isEmpty()) continue; Matcher m=Pattern.compile("import\\s+(static\\s+)?([\\w.*]+);").matcher(imp); if(!m.matches()) continue; boolean st=m.group(1)!=null; String nm=m.group(2); boolean has=cu.getImports().stream().anyMatch(i2->i2.getNameAsString().equals(nm.replace(".*",""))&&i2.isStatic()==st&&i2.isAsterisk()==nm.endsWith(".*")); if(!has){ if(!st&&!nm.endsWith(".*")){ String sn=nm.substring(nm.lastIndexOf('.')+1); List<ImportDeclaration> clash=cu.getImports().stream().filter(i2->!i2.isStatic()&&!i2.isAsterisk()&&i2.getNameAsString().endsWith("."+sn)).collect(Collectors.toList()); for(ImportDeclaration c2:clash) c2.remove(); } cu.getImports().add(new ImportDeclaration(nm.replace(".*",""),st,nm.endsWith(".*"))); changed=true; } } continue; }
                if(op.equals("delete-class")){ Optional<TypeDeclaration<?>> td=findType(cu,top,cls); if(td.isPresent()){ td.get().remove(); applied++; changed=true; } else { rep.println("NOTYPE "+cls); failed++; } continue; }
                Optional<TypeDeclaration<?>> td=findType(cu,top,cls);
                if(td.isEmpty()){ rep.println("NOTYPE "+cls+" ("+op+")"); failed++; continue; }
                TypeDeclaration<?> t=td.get();
                try{
                switch(op){
                    case "field-add": { String name=o.get("name"); ParseResult<BodyDeclaration<?>> r=jp.parseBodyDeclaration(o.get("text")); if(!r.isSuccessful()){rep.println("PARSE-FIELD "+cls+" "+name);failed++;break;} Optional<FieldDeclaration> ex=t.getFields().stream().filter(x->x.getVariables().stream().anyMatch(v->v.getNameAsString().equals(name))).findFirst(); if(ex.isPresent()) ex.get().replace(r.getResult().get()); else t.addMember(r.getResult().get()); applied++; changed=true; break; }
                    case "enum-constants-replace": {
                        if(!(t instanceof EnumDeclaration)){ rep.println("NOT-ENUM "+cls); failed++; break; }
                        ParseResult<CompilationUnit> w=jp.parse("enum W {\n"+o.get("text")+";\n}"); if(!w.isSuccessful()){ rep.println("PARSE-ENUM "+cls); failed++; break; }
                        EnumDeclaration ed=(EnumDeclaration)t; EnumDeclaration nw=(EnumDeclaration)w.getResult().get().getType(0);
                        ed.getEntries().clear(); for(EnumConstantDeclaration en:nw.getEntries()) ed.getEntries().add(en.clone());
                        applied++; changed=true; break; }
                    case "type-add": {
                        ParseResult<BodyDeclaration<?>> r=jp.parseBodyDeclaration(o.get("text")); if(!r.isSuccessful()){ rep.println("PARSE-TYPE "+cls+" "+o.get("name")); failed++; break; }
                        final String tn=o.get("name"); t.getMembers().removeIf(m->m instanceof TypeDeclaration&&((TypeDeclaration<?>)m).getNameAsString().equals(tn));
                        t.addMember(r.getResult().get()); applied++; changed=true; break; }
                    case "field-delete": { String name=o.get("name"); Optional<FieldDeclaration> ex=t.getFields().stream().filter(x->x.getVariables().stream().anyMatch(v->v.getNameAsString().equals(name))).findFirst(); if(ex.isPresent()){ ex.get().remove(); applied++; changed=true; } else { rep.println("BENIGN-NOFIELD-DEL "+cls+" "+name); } break; }
                    case "method-delete": case "method-replace": case "method-add": {
                        String name=o.get("name"),params=o.get("params"); CallableDeclaration<?> found=null; int cnt=0;
                        if(name.equals("<init>")){ for(ConstructorDeclaration c:t.getConstructors()) if(paramsMatch(c,params,tv,t instanceof EnumDeclaration?2:1)){found=c;cnt++;} }
                        else for(MethodDeclaration m:t.getMethodsByName(name)) if(paramsMatch(m,params,tv,0)){found=m;cnt++;}
                        if(op.equals("method-delete")){ if(found!=null&&cnt==1){ found.remove(); applied++; changed=true; } else { rep.println("BENIGN-NOMETHOD-DEL "+cls+" "+name+"("+params+") cnt="+cnt); } break; }
                        ParseResult<BodyDeclaration<?>> r=jp.parseBodyDeclaration(o.get("text")); if(!r.isSuccessful()){ rep.println("PARSE-METHOD "+cls+" "+name+" "+r.getProblems().get(0)); failed++; break; }
                        if(found!=null&&cnt==1) found.replace(r.getResult().get()); else if(found==null) t.addMember(r.getResult().get()); else { rep.println("AMBIG-METHOD "+cls+" "+name+"("+params+")"); failed++; break; }
                        applied++; changed=true; break; }
                    case "initializers-replace": {
                        boolean st=Boolean.parseBoolean(o.get("static")); String text=o.get("text"); 
                        List<BodyDeclaration<?>> rem=new ArrayList<>();
                        for(BodyDeclaration<?> m:t.getMembers()){ if(m instanceof FieldDeclaration&&((FieldDeclaration)m).isStatic()==st&&((FieldDeclaration)m).getVariables().stream().anyMatch(v->v.getInitializer().isPresent())) rem.add(m); else if(m instanceof InitializerDeclaration&&((InitializerDeclaration)m).isStatic()==st) rem.add(m); }
                        if(t instanceof EnumDeclaration&&st){ rep.println("ENUM-INIT-MANUAL "+cls); failed++; break; }
                        ParseResult<ClassOrInterfaceDeclaration> wrap=null; 
                        ParseResult<CompilationUnit> w=jp.parse("class W {\n"+text+"\n}"); if(!w.isSuccessful()){ rep.println("PARSE-INIT "+cls); failed++; break; }
                        int pos=rem.isEmpty()?t.getMembers().size():t.getMembers().indexOf(rem.get(0));
                        for(BodyDeclaration<?> m:rem) m.remove();
                        List<BodyDeclaration<?>> add=new ArrayList<>(w.getResult().get().getType(0).getMembers());
                        for(int i=0;i<add.size();i++) t.getMembers().add(Math.min(pos+i,t.getMembers().size()),add.get(i).clone());
                        applied++; changed=true; break; }
                    default: rep.println("UNKNOWN-OP "+op); failed++;
                }
                } catch(Exception ex){ rep.println("EXC "+op+" "+cls+" "+ex); failed++; }
            }
            if(changed){ String outText; try{ outText=LexicalPreservingPrinter.print(cu); }catch(Exception px){ outText=cu.toString(); rep.println("PLAINPRINT "+top); } Files.writeString(f,outText,StandardCharsets.UTF_8); filesTouched++; }
        }
        // imports of deleted top-level classes would no longer resolve: drop them everywhere
        Set<String> gone=new HashSet<>(); for(Map<String,String> o:ops) if(o.get("op").equals("delete-class")&&!o.get("class").contains("$")) gone.add("import "+o.get("class").replace('/','.')+";");
        int cleaned=0;
        if(!gone.isEmpty()){ try(Stream<Path> w=Files.walk(root)){ for(Path pth:(Iterable<Path>)w.filter(x->x.toString().endsWith(".java"))::iterator){ List<String> ls=Files.readAllLines(pth,StandardCharsets.UTF_8); List<String> kept=ls.stream().filter(l->!gone.contains(l.trim())).collect(Collectors.toList()); if(kept.size()!=ls.size()){ Files.write(pth,kept,StandardCharsets.UTF_8); cleaned++; } } } }
        rep.close();
        System.out.println("importsCleanedFiles="+cleaned+" applied="+applied+" failed="+failed+" filesTouched="+filesTouched);
    }
}
