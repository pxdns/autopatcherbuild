import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import java.util.zip.*;

/** Per-method canonical bytecode signatures: class \t member \t hash. Line numbers, frames, local names, labels are normalised away. */
public class BcSig {
    static String hex(byte[] b){StringBuilder s=new StringBuilder();for(int i=0;i<8;i++)s.append(String.format("%02x",b[i]));return s.toString();}
    static String norm(String s){ return s; }

    static Set<String> SYNF=new HashSet<>();
    static String fk(String owner,String name,String desc,List<String[]> ren){ return rn(owner+"."+(SYNF.contains(owner+"."+name)?"SYN":name)+desc,ren); }
    static String rn(String x,List<String[]> ren){ if(x==null) return null; for(String[] kv:ren) x=x.replace(kv[0],kv[1]); return x; }

    static String bag(MethodNode mn,Map<String,String> bodyHash,List<String[]> ren){
        List<String> t=new ArrayList<>();
        for(AbstractInsnNode n=mn.instructions.getFirst();n!=null;n=n.getNext()){
            if(n instanceof FieldInsnNode){FieldInsnNode x=(FieldInsnNode)n; t.add("F"+(x.getOpcode()==178||x.getOpcode()==180?"r":"w")+fk(x.owner,x.name,x.desc,ren));}
            else if(n instanceof MethodInsnNode){MethodInsnNode x=(MethodInsnNode)n; t.add("M"+rn(x.owner+"."+x.name+x.desc,ren));}
            else if(n instanceof InvokeDynamicInsnNode){InvokeDynamicInsnNode x=(InvokeDynamicInsnNode)n; StringBuilder sb=new StringBuilder("D"+rn(x.name+x.desc,ren)); for(Object o:x.bsmArgs){ if(o instanceof Handle){Handle h=(Handle)o; String k=h.getOwner()+"."+h.getName()+h.getDesc(); String bh=bodyHash==null?null:bodyHash.get(k); sb.append(bh!=null?"lam"+bh:rn(k,ren));} else sb.append(rn(String.valueOf(o),ren)); } t.add(sb.toString());}
            else if(n instanceof TypeInsnNode && n.getOpcode()!=192) t.add("T"+n.getOpcode()+rn(((TypeInsnNode)n).desc,ren));
            else if(n instanceof LdcInsnNode) t.add("C"+((LdcInsnNode)n).cst.getClass().getSimpleName()+":"+((LdcInsnNode)n).cst);
            else if(n instanceof IntInsnNode && n.getOpcode()!=188) t.add("I"+((IntInsnNode)n).operand);
            else if(n.getOpcode()>=2&&n.getOpcode()<=15) t.add("K"+n.getOpcode());
        }
        Collections.sort(t); return String.join("|",t);
    }
    static String body(MethodNode mn,Map<String,String> bodyHash,List<String[]> ren){
        StringBuilder sb=new StringBuilder();
        Map<LabelNode,Integer> lab=new HashMap<>(); int[] c={0};
        for(AbstractInsnNode in2=mn.instructions.getFirst();in2!=null;in2=in2.getNext()) if(in2 instanceof LabelNode) lab.put((LabelNode)in2,c[0]++);
        for(AbstractInsnNode n=mn.instructions.getFirst();n!=null;n=n.getNext()){
            if(n instanceof LineNumberNode||n instanceof FrameNode) continue;
            if(n instanceof LabelNode){ sb.append("L").append(lab.get(n)).append(';'); continue;}
            int op=n.getOpcode(); if(op==183||op==185) op=182; sb.append(op).append(' ');
            if(n instanceof FieldInsnNode){FieldInsnNode x=(FieldInsnNode)n; sb.append(fk(x.owner,x.name,x.desc,ren));}
            else if(n instanceof MethodInsnNode){MethodInsnNode x=(MethodInsnNode)n; sb.append(rn(x.owner+"."+x.name+x.desc,ren));}
            else if(n instanceof InvokeDynamicInsnNode){InvokeDynamicInsnNode x=(InvokeDynamicInsnNode)n; sb.append(rn(x.name+x.desc,ren)).append(x.bsm.getName());
                for(Object o:x.bsmArgs){ if(o instanceof Handle){ Handle h=(Handle)o; String k=h.getOwner()+"."+h.getName()+h.getDesc(); String bh=bodyHash==null?null:bodyHash.get(k); sb.append("H:").append(bh!=null?"lam"+bh:rn(k,ren)); } else if(o instanceof Type) sb.append(rn(o.toString(),ren)); else sb.append(o); } }
            else if(n instanceof TypeInsnNode){ if(n.getOpcode()==192){ int l=sb.lastIndexOf("192 "); sb.setLength(l); continue;} sb.append(rn(((TypeInsnNode)n).desc,ren)); }
            else if(n instanceof IntInsnNode) sb.append(((IntInsnNode)n).operand);
            else if(n instanceof VarInsnNode) sb.append(((VarInsnNode)n).var);
            else if(n instanceof IincInsnNode) sb.append(((IincInsnNode)n).var).append(' ').append(((IincInsnNode)n).incr);
            else if(n instanceof LdcInsnNode) sb.append(((LdcInsnNode)n).cst.getClass().getSimpleName()).append(':').append(((LdcInsnNode)n).cst);
            else if(n instanceof JumpInsnNode) sb.append("L").append(lab.get(((JumpInsnNode)n).label));
            else if(n instanceof TableSwitchInsnNode){TableSwitchInsnNode x=(TableSwitchInsnNode)n; sb.append(x.min).append(' ').append(x.max).append(" d").append(lab.get(x.dflt)); for(LabelNode l:x.labels) sb.append(' ').append(lab.get(l));}
            else if(n instanceof LookupSwitchInsnNode){LookupSwitchInsnNode x=(LookupSwitchInsnNode)n; sb.append("d").append(lab.get(x.dflt)); for(int i=0;i<x.keys.size();i++) sb.append(' ').append(x.keys.get(i)).append('>').append(lab.get(x.labels.get(i)));}
            else if(n instanceof MultiANewArrayInsnNode) sb.append(rn(((MultiANewArrayInsnNode)n).desc,ren)).append(((MultiANewArrayInsnNode)n).dims);
            sb.append(';');
        }
        for(TryCatchBlockNode t:mn.tryCatchBlocks) sb.append("T").append(lab.get(t.start)).append(lab.get(t.end)).append(lab.get(t.handler)).append(rn(t.type,ren)).append(';');
        return sb.toString();
    }
    public static void main(String[] a) throws Exception {
        // args: input (jar or dir) output prefixes...
        String in=a[0]; PrintWriter out=new PrintWriter(new BufferedWriter(new OutputStreamWriter(new FileOutputStream(a[1]),StandardCharsets.UTF_8)));
        List<String> prefixes=new ArrayList<>(); for(int i=2;i<a.length;i++) prefixes.add(a[i]);
        Map<String,byte[]> classes=new TreeMap<>();
        File f=new File(in);
        if(f.isDirectory()){
            java.nio.file.Files.walk(f.toPath()).filter(p->p.toString().endsWith(".class")).forEach(p->{
                try{ String n=f.toPath().relativize(p).toString().replace(File.separatorChar,'/'); classes.put(n.substring(0,n.length()-6),java.nio.file.Files.readAllBytes(p)); }catch(IOException e){throw new RuntimeException(e);} });
        } else try(ZipFile z=new ZipFile(f)){
            for(Enumeration<? extends ZipEntry> e=z.entries();e.hasMoreElements();){ZipEntry ze=e.nextElement(); if(ze.getName().endsWith(".class")){ try(InputStream is=z.getInputStream(ze)){classes.put(ze.getName().substring(0,ze.getName().length()-6),is.readAllBytes());}}}
        }
        List<String[]> ren=new ArrayList<>();
        if(System.getProperty("ren")!=null) for(String l:java.nio.file.Files.readAllLines(new File(System.getProperty("ren")).toPath())){ if(l.isBlank()||l.startsWith("#")) continue; String[] kv=l.split("\t"); ren.add(kv); }
        // pass 1: body hash of every method (lambda handle names blanked), keyed owner.name+desc
        Map<String,String> bodyHash=new HashMap<>();
        for(Map.Entry<String,byte[]> e:classes.entrySet()){
            ClassNode cn=new ClassNode(); new ClassReader(e.getValue()).accept(cn,ClassReader.SKIP_FRAMES|ClassReader.SKIP_DEBUG);
            for(FieldNode fn:cn.fields) if((fn.access&Opcodes.ACC_SYNTHETIC)!=0) SYNF.add(cn.name+"."+fn.name);
            for(MethodNode mn:cn.methods) if((mn.access&Opcodes.ACC_SYNTHETIC)!=0 && (mn.name.startsWith("lambda$")||mn.name.startsWith("func_")||true)) bodyHash.put(cn.name+"."+mn.name+mn.desc, hex(MessageDigest.getInstance("SHA-1").digest(body(mn,null,ren).getBytes(StandardCharsets.UTF_8))));
        }
        for(Map.Entry<String,byte[]> e:classes.entrySet()){
            boolean ok=prefixes.isEmpty(); for(String p:prefixes) if(e.getKey().startsWith(p)) ok=true; if(!ok) continue;
            ClassNode cn=new ClassNode(); new ClassReader(e.getValue()).accept(cn,ClassReader.SKIP_FRAMES|ClassReader.SKIP_DEBUG);
            List<String> ifs=new ArrayList<>(cn.interfaces); Collections.sort(ifs); out.println(cn.name+"\t#class\t"+rn((cn.superName==null?"":cn.superName)+" "+String.join(",",ifs),ren)+" "+(cn.access&~Opcodes.ACC_SUPER&~Opcodes.ACC_SYNTHETIC&~Opcodes.ACC_FINAL));
            List<String> fs=new ArrayList<>(); for(FieldNode fn:cn.fields) if((fn.access&Opcodes.ACC_SYNTHETIC)==0) fs.add(fn.name+":"+fn.desc+":"+(fn.access&~Opcodes.ACC_SYNTHETIC)+":"+fn.value);
            for(String s:fs) out.println(cn.name+"\t#field\t"+s);
            for(MethodNode mn:cn.methods){
                if((mn.access&Opcodes.ACC_BRIDGE)!=0||mn.name.startsWith("access$")) continue;
                String sbs=body(mn,bodyHash,ren);
                int acc=mn.access&~Opcodes.ACC_SYNTHETIC&~Opcodes.ACC_BRIDGE&~Opcodes.ACC_VARARGS;
                String h=hex(MessageDigest.getInstance("SHA-1").digest(sbs.getBytes(StandardCharsets.UTF_8)));
                boolean syn=(mn.access&Opcodes.ACC_SYNTHETIC)!=0 && bodyHash.containsKey(cn.name+"."+mn.name+mn.desc) && (mn.name.startsWith("lambda$")||mn.name.startsWith("func_"));
                String bg=hex(MessageDigest.getInstance("SHA-1").digest(bag(mn,bodyHash,ren).getBytes(StandardCharsets.UTF_8)));
                out.println(cn.name+"\t"+(syn?"lambda#"+bodyHash.get(cn.name+"."+mn.name+mn.desc)+rn(mn.desc,ren):rn(mn.name+mn.desc,ren))+"\t"+acc+" "+mn.instructions.size()+" "+h+" "+bg);
            }
        }
        out.close();
    }
}
