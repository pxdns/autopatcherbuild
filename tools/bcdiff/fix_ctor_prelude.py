#!/usr/bin/env python3
"""javac: 'call to this/super must be first statement in constructor' -> inline the hoisted temporaries into the call (see stmtlib.inline_prelude).
Records {file, h, op: inline-prelude}: a statement hash only, no game text.
usage: fix_ctor_prelude.py <javac.log> <root> <strip-prefix> <fixes.jsonl>"""
import os, re, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stmtlib import *
log, root, strip, rec = sys.argv[1:5]
todo = {}
for l in open(log, errors="replace"):
    m = re.match(r"^(\S+\.java):(\d+): error: call to (this|super) must be first statement", l)
    if m: todo.setdefault(m.group(1), set()).add(int(m.group(2)))
R = open(rec, "a"); n = 0
for f, lines in todo.items():
    rel = f[len(strip):] if f.startswith(strip) else f
    p = os.path.join(root, rel); text = open(p, encoding="utf-8").read()
    for ln in sorted(lines, reverse=True):
        toks = tokenize(text); sts = statements(toks)
        st = next((st for st in sts if toks[st[0]][1] <= ln <= toks[st[1]][1] and toks[st[0]][0] in ("this", "super")), None)
        if st is None: print("NO CALL", rel, ln); continue
        h = shash(toks, st); occ = [i for i, s2 in enumerate(sts) if shash(toks, s2) == h].index(sts.index(st)); text, c = inline_prelude(text, h, occ)
        if c: R.write(json.dumps({"file": rel, "h": h, "op": "inline-prelude", "o": occ}, separators=(",", ":")) + "\n"); n += c
    open(p, "w", encoding="utf-8").write(text)
print("inlined", n, "temporaries")
