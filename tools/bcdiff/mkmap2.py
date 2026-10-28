import csv,sys,re,collections
# usage: mkmap2.py joined.tsrg mcpdir sig-ws.txt out.tsrg
cfg,mcpdir,sig,out=sys.argv[1:5]
ids={}
for f in ("fields.csv","methods.csv"):
    for r in csv.DictReader(open(f"{mcpdir}/{f}",encoding="utf-8")): ids[r["searge"]]=r["name"]
decl=collections.defaultdict(set)
for l in open(sig,encoding="utf-8"):
    c,m,h=l.rstrip("\n").split("\t",2)
    if m=="#field": decl[c].add(h.split(":")[0])
    elif not m.startswith("#"): decl[c].add(m.split("(")[0])
stats=collections.Counter()
cur=None
with open(cfg,encoding="utf-8") as fi, open(out,"w",encoding="utf-8") as fo:
    for line in fi:
        if not line.startswith("\t"):
            cur=line.split()[1] if len(line.split())>1 else None
            fo.write(line);continue
        def sub(m):
            k=m.group(0); v=ids.get(k)
            if v is None: return k
            d=decl.get(cur,set())
            if v in d: stats["mcp"]+=1; return v
            if k in d: stats["srg"]+=1; return k
            stats["undeclared"]+=1; return v
        fo.write(re.sub(r"\b(?:func|field)_\d+_\w+",sub,line))
print(dict(stats))
