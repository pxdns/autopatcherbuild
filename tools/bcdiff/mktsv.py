import json,collections,re
d=json.load(open("delta.json"))
def load(p):
    r=collections.defaultdict(int)
    for l in open(p,encoding="utf-8"):
        c,m,h=l.rstrip("\n").split("\t",2)
        if not m.startswith("#") and not m.startswith("lambda#") and not m.startswith("$values"): r[c.split("$")[0]]+=1
    return r
van=load("sig-van.txt")
lib=("com/mojang/brigadier","com/mojang/authlib","com/mojang/datafixers","com/mojang/bridge")
chg=collections.Counter()
for c,v in d["modified"].items(): chg[c.split("$")[0]]+=len(v["methods_changed"])+len(v["methods_removed"])
whole=set(t for t,n in chg.items() if van.get(t,0)>=5 and n/van[t]>0.5)
whole|={c.split("$")[0] for c,v in d["modified"].items() if v["class_header"] and not re.search(r"\$\d",c)}
removed=set(d["removed_classes"])
with open("delta.tsv","w") as f:
    for c in d["removed_classes"]:
        if re.search(r"\$\d",c): continue
        if c.split("$")[0] in removed and "$" in c: continue
        f.write(f"{c}\tdelete-class\t\n")
    for c in d["added_classes"]:
        if not c.startswith(lib): f.write(f"{c}\tadd-class\t\n")
    for t in sorted(whole): f.write(f"{t}\treplace-file\t\n")
    for c,v in d["modified"].items():
        if c.split("$")[0] in whole: continue
        addf={x.split(":")[0] for x in v["fields_added"]}
        for k,m in (("method-replace","methods_changed"),("method-add","methods_added"),("method-delete","methods_removed"),("field-add","fields_added"),("field-delete","fields_removed")):
            for x in v[m]:
                if k=="field-delete" and x.split(":")[0] in addf: continue
                if k=="method-delete" and (re.search(r"[(,]1[,)]",x) or "$" in x.split("(")[0]): continue
                f.write(f"{c}\t{k}\t{x}\n")
print("replace-file",len(whole))
