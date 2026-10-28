#!/usr/bin/env python3
"""Splits ops.jsonl into ops that are Mojang-vs-Eagler changes and ops that depend on third-party code (OptiFine, shader mod).

usage: filter_nonvanilla.py <workspace-java-root> <ops.jsonl> <out-clean.jsonl> <out-excluded.jsonl> <dir> [<dir> ...]
Each <dir> (relative to the workspace root, e.g. net/minecraft/src) holds third-party classes; an op whose text mentions
one of their class names is excluded. Import lines naming those packages are dropped from 'imports' ops.
"""
import json, os, re, sys, collections
ws, src, clean, excl = sys.argv[1:5]
dirs = sys.argv[5:]
names = set()
for d in dirs:
    for r, _, fs in os.walk(os.path.join(ws, d)):
        for f in fs:
            if f.endswith(".java"): names.add(f[:-5])
# plain JDK/Java names must not count as third-party even if a class of that name exists there
names -= {"Function", "Consumer", "Supplier", "Predicate", "List", "Map", "Set", "Optional", "Arrays", "Objects"}
names = {n for n in names if len(n) >= 4}
rx = re.compile(r"\b(" + "|".join(sorted(map(re.escape, names), key=len, reverse=True)) + r")\b")
pk = tuple(d.replace("/", ".") + "." for d in dirs)
kept = ex = 0; why = collections.Counter()
with open(src) as fi, open(clean, "w") as fc, open(excl, "w") as fe:
    for line in fi:
        o = json.loads(line)
        if o["op"] == "imports":
            keep = [l for l in o["imports"].split("\n") if not any(p in l for p in pk)]
            o["imports"] = "\n".join(keep); fc.write(json.dumps(o, separators=(",", ":")) + "\n"); continue
        t = o.get("text", "")
        m = rx.search(t) if t else None
        if m:
            ex += 1; why[m.group(1)] += 1
            fe.write(json.dumps({"op": o["op"], "class": o["class"], "name": o.get("name", ""), "mentions": m.group(1)}, separators=(",", ":")) + "\n")
        else:
            kept += 1; fc.write(json.dumps(o, separators=(",", ":")) + "\n")
print("kept", kept, "excluded", ex, "top reasons", why.most_common(6))
