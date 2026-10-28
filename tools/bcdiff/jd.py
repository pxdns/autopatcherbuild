import subprocess,re,sys,difflib
J="/home/user/jdks/jdk-17.0.21+9/bin/javap"
def dump(root,cls,meth):
    out=subprocess.run([J,"-c","-p","-cp",root,cls.replace("/",".")],capture_output=True,text=True).stdout
    # slice the method
    name=meth.split("(")[0]
    lines=out.split("\n");res=[];on=False
    for l in lines:
        if re.match(r"  \S.*\b"+re.escape(name)+r"\(",l): on=True;res=[];continue
        if on:
            if l.strip()=="" : break
            m=re.match(r"\s+\d+: (.*)",l)
            if m:
                t=re.sub(r"#\d+(, *\d+)?","",m.group(1)); t=re.sub(r"\s+"," ",t); t=re.sub(r"^(\w+) +//","\\1 //",t)
                res.append(t)
    return res
for cls,meth in [a.split("::") for a in sys.argv[1:]]:
    A=dump("vx",cls,meth);B=dump("ws17",cls,meth)
    print("=====",cls,meth)
    for l in difflib.unified_diff(A,B,"van","ws",lineterm="",n=0):
        if not l.startswith(("---","+++","@@")): print(l[:170])
