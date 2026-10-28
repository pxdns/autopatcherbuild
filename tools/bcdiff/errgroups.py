#!/usr/bin/env python3
"""usage: errgroups.py javac.log [N]  — groups javac errors by message (and missing symbol) and shows one example each."""
import re, sys, collections
L = open(sys.argv[1], errors="replace").read().split("\n"); N = int(sys.argv[2]) if len(sys.argv) > 2 else 10
kinds = collections.OrderedDict()
for i, l in enumerate(L):
    m = re.match(r"^(\S+\.java):(\d+): error: (.*)$", l)
    if not m: continue
    msg = re.sub(r"'[^']*'", "X", m.group(3))[:75]
    if msg == "cannot find symbol":
        sym = next((x.strip() for x in L[i+2:i+6] if "symbol:" in x), ""); msg += " | " + re.sub(r"\s+", " ", sym)[:45]
    kinds.setdefault(msg, []).append((re.sub(r"^\w+/", "", m.group(1)), m.group(2), L[i+1].strip()[:100]))
print("total", sum(len(v) for v in kinds.values()))
for msg, v in sorted(kinds.items(), key=lambda x: -len(x[1]))[:N]:
    f, ln, src = v[0]; print(f"{len(v):3d}  {msg}\n       e.g. {f}:{ln}  {src}")
