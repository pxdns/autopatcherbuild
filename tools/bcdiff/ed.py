#!/usr/bin/env python3
"""Applies token edits and records them (statement hash + token index + old/new tokens: no game text).
Batch file lines:  <relpath>:<line> | <old tokens> => <new tokens> [| nth]
 - tokens are matched as a whole-token sequence inside the statement that contains <line>; 'nth' (1-based) picks the occurrence.
 - <new tokens> may be empty (delete) or several tokens (insert a cast, a type...).
usage: ed.py <root> <fixes.jsonl> <batch.txt>"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stmtlib import *
root, rec, batch = sys.argv[1:4]
R = open(rec, "a"); done = bad = 0
by_file = {}
for line in open(batch, encoding="utf-8"):
    line = line.rstrip("\n")
    if not line.strip() or line.startswith("#"): continue
    parts = [p.strip() for p in line.split("|")]
    loc, edit = parts[0], parts[1]; nth = int(parts[2]) if len(parts) > 2 else 1
    rel, ln = loc.rsplit(":", 1)
    old, new = [x.strip() for x in edit.split("=>")]
    by_file.setdefault(rel, []).append((int(ln), old.split(), new.split(), nth, line))
for rel, items in by_file.items():
    p = os.path.join(root, rel); text = open(p, encoding="utf-8").read()
    # apply from the bottom of the file upwards so line numbers stay valid
    for ln, old, new, nth, raw in sorted(items, key=lambda x: -x[0]):
        toks = tokenize(text); sts = statements(toks)
        cand = [i for i, (a, b) in enumerate(sts) if any(toks[k][1] == ln for k in range(a, b + 1))]
        if not cand: print("NO STATEMENT", raw); bad += 1; continue
        pick = None
        for si in cand:
            a, b = sts[si]; seq = [toks[k][0] for k in range(a, b + 1)]
            hits = [k for k in range(len(seq) - len(old) + 1) if seq[k:k + len(old)] == old] if old else [0]
            if len(hits) >= nth: pick = si; break
        if pick is None:
            a, b = sts[cand[0]]; print("NOT FOUND", raw, "| statement:", " ".join(toks[k][0] for k in range(a, b + 1))[:150]); bad += 1; continue
        a, b = sts[pick]
        k = hits[nth - 1]; s0 = toks[a + k][2]; e0 = toks[a + k + len(old) - 1][3] if old else toks[a + k][2]
        h = shash(toks, (a, b))
        occ = [i for i, st in enumerate(sts) if shash(toks, st) == h].index(pick)
        text = text[:s0] + join_tokens(new) + text[e0:]
        R.write(json.dumps({"file": rel, "h": h, "i": k, "old": old, "new": new, "nth": nth, "o": occ}, separators=(",", ":")) + "\n"); done += 1
    open(p, "w", encoding="utf-8").write(text)
R.close(); print("applied", done, "failed", bad)
