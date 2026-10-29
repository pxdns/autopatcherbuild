#!/usr/bin/env python3
"""Replays recorded token edits (see ed.py) on a tree. Each record: {file, h: hash of the statement's tokens, i: index of the first old
token inside the statement, old: [tokens], new: [tokens], nth}. Records are applied in file order; a record whose statement is not found
is reported (the tree no longer matches).
usage: applyfixes.py <root> <fixes.jsonl>"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stmtlib import *
root, rec = sys.argv[1:3]
ok = miss = 0
recs = [json.loads(l) for l in open(rec) if l.strip()]
byf = {}
for r in recs: byf.setdefault(r["file"], []).append(r)
for rel, items in byf.items():
    p = os.path.join(root, rel)
    if not os.path.exists(p): miss += len(items); continue
    text = open(p, encoding="utf-8").read()
    for r in items:
        if r.get("op") == "inline-prelude":
            text, c = inline_prelude(text, r["h"], r.get("o", 0)); ok += c; miss += 0 if c else 1; continue
        toks = tokenize(text); sts = statements(toks)
        same = [st for st in sts if shash(toks, st) == r["h"]]; o = r.get("o", 0)
        hit = same[o] if o < len(same) else None
        if hit is None: miss += 1; print("MISSING", rel, r["old"], "=>", r["new"]); continue
        a, b = hit; old = r["old"] if isinstance(r["old"], list) else [r["old"]]; new = r["new"] if isinstance(r["new"], list) else [r["new"]]
        k = r["i"]
        if [toks[a + k + j][0] for j in range(len(old))] != old: miss += 1; print("MISMATCH", rel, old); continue
        s0 = toks[a + k][2]; e0 = toks[a + k + len(old) - 1][3] if old else s0
        text = text[:s0] + join_tokens(new) + text[e0:]; ok += 1
    open(p, "w", encoding="utf-8").write(text)
print("replayed", ok, "missing", miss)
