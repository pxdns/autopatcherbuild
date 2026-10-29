#!/usr/bin/env python3
"""usage: ctx.py <javac.log> <root> <strip> <ws-roots> <start> <count> — shows errors with the decompiled statement and its workspace twin."""
import re, sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stmtlib import *
log, root, strip, wsroots, start, count = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(","), int(sys.argv[5]), int(sys.argv[6])
L = open(log, errors="replace").read().split("\n"); errs = []
for i, l in enumerate(L):
    m = re.match(r"^(\S+\.java):(\d+): error: (.*)$", l)
    if m: errs.append((m.group(1), int(m.group(2)), m.group(3)[:110], " ".join(x.strip() for x in L[i + 2:i + 4] if "symbol" in x or "location" in x)[:100]))
errs.sort()
cache = {}; seen = set(); shown = 0
for f, ln, msg, extra in errs:
    if shown >= start + count: break
    rel = f[len(strip):] if f.startswith(strip) else f
    if rel not in cache:
        p = os.path.join(root, rel); w = find_ws(wsroots, rel)
        cache[rel] = Twin(open(p, encoding="utf-8", errors="replace").read(), open(w, encoding="utf-8", errors="replace").read()) if w else None
    T = cache[rel]
    key = (rel, T.stmt_of_line(ln) if T else ln)
    if key in seen: continue
    seen.add(key); shown += 1
    if shown <= start: continue
    print(f"=== {rel.split('/')[-1]}:{ln}  {msg} {extra}")
    if T is None: print("   (no workspace file)"); continue
    si = T.stmt_of_line(ln)
    if si is None: continue
    print("   DEC:", T.text(T.dt, T.ds[si])[:260])
    wi = T.twin(si)
    print("   WS :", T.text(T.wt, T.ws[wi])[:260] if wi is not None else "(no twin)")
