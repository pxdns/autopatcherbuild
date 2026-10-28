import csv,sys,re
cfg,mcpdir,out=sys.argv[1:4]
names={}
for f in ("fields.csv","methods.csv"):
    for r in csv.DictReader(open(f"{mcpdir}/{f}",encoding="utf-8")):
        names[r["searge"]]=r["name"]
n=0
with open(cfg,encoding="utf-8") as fi, open(out,"w",encoding="utf-8") as fo:
    for line in fi:
        def sub(m):
            global n
            k=m.group(0)
            if k in names: n+=1; return names[k]
            return k
        fo.write(re.sub(r"\b(?:func|field)_\d+_\w+",sub,line))
print("renamed",n)
