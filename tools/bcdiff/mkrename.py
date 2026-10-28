#!/usr/bin/env python3
"""Pairs members the vanilla jar and the workspace name differently, and writes an SRG-style rename map (vanilla name -> workspace name).
usage: mkrename.py sig-van.txt sig-ws.txt out.srg
Fields: same class, same descriptor, exactly one unmatched candidate on each side.
Methods: same class, same descriptor and identical operand bag, exactly one unmatched candidate on each side."""
import sys, collections
van, ws, out = sys.argv[1:4]
def load(p):
    F = collections.defaultdict(list); M = collections.defaultdict(list); C = set()
    for l in open(p, encoding="utf-8"):
        t = l.rstrip("\n").split("\t", 2)
        if len(t) != 3: continue
        c, m, h = t; C.add(c)
        if m == "#field":
            n, d = h.split(":")[0], h.split(":")[1]; F[c].append((n, d))
        elif not m.startswith("#") and not m.startswith("lambda#") and not m.startswith("$values") and not m.startswith("<"):
            i = m.index("("); M[c].append((m[:i], m[i:], h.split()[-1]))
    return F, M, C
vf, vm, vc = load(van); wf, wm, wc = load(ws)
lines = []; nf = nm = 0
for c in sorted(vc & wc):
    vn = {n for n, _ in vf[c]}; wn = {n for n, _ in wf[c]}
    uv = [(n, d) for n, d in vf[c] if n not in wn]; uw = [(n, d) for n, d in wf[c] if n not in vn]
    byd_v = collections.defaultdict(list); byd_w = collections.defaultdict(list)
    for n, d in uv: byd_v[d].append(n)
    for n, d in uw: byd_w[d].append(n)
    for d, vs in byd_v.items():
        ws_ = byd_w.get(d, [])
        if len(vs) == 1 and len(ws_) == 1: lines.append(f"FD: {c}/{vs[0]} {c}/{ws_[0]}"); nf += 1
    vk = {(n, d) for n, d, _ in vm[c]}; wk = {(n, d) for n, d, _ in wm[c]}
    uvm = [(n, d, b) for n, d, b in vm[c] if (n, d) not in wk]; uwm = [(n, d, b) for n, d, b in wm[c] if (n, d) not in vk]
    byk_v = collections.defaultdict(list); byk_w = collections.defaultdict(list)
    for n, d, b in uvm: byk_v[(d, b)].append(n)
    for n, d, b in uwm: byk_w[(d, b)].append(n)
    for k, vs in byk_v.items():
        ws_ = byk_w.get(k, [])
        if len(vs) == 1 and len(ws_) == 1: lines.append(f"MD: {c}/{vs[0]} {k[0]} {c}/{ws_[0]} {k[0]}"); nm += 1
open(out, "w").write("\n".join(lines) + "\n")
print("field renames", nf, "method renames", nm)
