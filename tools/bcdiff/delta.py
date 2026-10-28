import json,re,collections,sys
def load(p):
    d={}
    for l in open(p,encoding="utf-8"):
        c,m,h=l.rstrip("\n").split("\t",2); d[(c,m)]=h
    return d
a=load("sig-van.txt");b=load("sig-ws.txt")
skip=lambda m:m.startswith("lambda#") or m.startswith("$values")
cv={k[0] for k in a};cw={k[0] for k in b}
isanon=lambda c:re.search(r"\$\d",c) is not None
enum={c for (c,m),h in a.items() if m=="#class" and int(h.split()[-1])&0x4000}
out={"removed_classes":sorted(cv-cw),"added_classes":sorted(cw-cv),"modified":{}}
mod=collections.defaultdict(lambda:{"methods_changed":[],"methods_added":[],"methods_removed":[],"fields_added":[],"fields_removed":[],"fields_changed":[],"class_header":False})
for k,v in a.items():
    c,m=k
    if c not in cw: continue
    if m=="#class":
        if k in b and b[k]!=v: mod[c]["class_header"]=True
    elif m=="#field":
        pass
    elif skip(m): continue
    elif k in b:
        if v.split()[-1]!=b[k].split()[-1] and not (m.startswith("<clinit>") and c in enum): mod[c]["methods_changed"].append(m)
    else: mod[c]["methods_removed"].append(m)
for k,v in b.items():
    c,m=k
    if c not in cv: continue
    if m in ("#class","#field") or skip(m): continue
    if k not in a: mod[c]["methods_added"].append(m)
# fields: lines are keyed (class,#field) duplicates; recompute
def fields(p):
    d=collections.defaultdict(set)
    for l in open(p,encoding="utf-8"):
        c,m,h=l.rstrip("\n").split("\t",2)
        if m=="#field": d[c].add(h)
    return d
fa,fb=fields("sig-van.txt"),fields("sig-ws.txt")
for c in cv&cw:
    ra,rb=fa[c],fb[c]
    for f in sorted(rb-ra): mod[c]["fields_added"].append(f)
    for f in sorted(ra-rb): mod[c]["fields_removed"].append(f)
out["modified"]={c:v for c,v in mod.items() if any(v.values())}
json.dump(out,open("delta.json","w"),indent=1)
M=out["modified"]
print("removed classes",len(out["removed_classes"]),"added classes",len(out["added_classes"]),"modified classes",len(M))
print("methods changed",sum(len(v["methods_changed"]) for v in M.values()),"added",sum(len(v["methods_added"]) for v in M.values()),"removed",sum(len(v["methods_removed"]) for v in M.values()),"fields +",sum(len(v["fields_added"]) for v in M.values()),"-",sum(len(v["fields_removed"]) for v in M.values()))
print("modified classes anonymous/local:",sum(1 for c in M if isanon(c)),"named:",sum(1 for c in M if not isanon(c)))
print("added classes by area:",collections.Counter("/".join(c.split("/")[:3]) for c in out["added_classes"]).most_common(6))
print("removed by area:",collections.Counter("/".join(c.split("/")[:3]) for c in out["removed_classes"]).most_common(6))
