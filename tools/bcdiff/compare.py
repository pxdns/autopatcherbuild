import collections,sys,random
def load(p):
    d={}
    for l in open(p,encoding="utf-8"):
        c,m,h=l.rstrip("\n").split("\t",2); d[(c,m)]=h
    return d
a=load("sig-van.txt");b=load("sig-ws.txt")
meth=lambda d:{k:v for k,v in d.items() if not k[1].startswith("#") and not k[1].startswith("lambda#") and not k[1].startswith("$values")}
am,bm=meth(a),meth(b)
diff=[k for k in am if k in bm and am[k].split()[-1]!=bm[k].split()[-1]]
strict=[k for k in am if k in bm and am[k].split()[2]!=bm[k].split()[2]]
print('strict-differ',len(strict),'bag-differ',len(diff))
same=len(am)-len(diff)-sum(1 for k in am if k not in bm)
onlyv=[k for k in am if k not in bm]; onlyw=[k for k in bm if k not in am]
print("van",len(am),"ws",len(bm),"identical",same,"differ",len(diff),"only-van",len(onlyv),"only-ws",len(onlyw))
cv={k[0] for k in a};cw={k[0] for k in b}
print("classes van",len(cv),"ws",len(cw),"common",len(cv&cw),"only-van",len(cv-cw),"only-ws",len(cw-cv))
bycls=collections.Counter(k[0] for k in diff)
print("classes with changed methods",len(bycls))
if len(sys.argv)>1:
    random.seed(int(sys.argv[1]))
    for k in random.sample(diff,15): print(k)
