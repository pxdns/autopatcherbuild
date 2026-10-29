#!/usr/bin/env python3
"""Deletes import lines that javac reports as unresolved (the workspace dropped the library together with the code that used it).
usage: fix_bad_imports.py <javac.log> <root> <strip-prefix>"""
import re, sys, os, collections
log, root, strip = sys.argv[1:4]
L = open(log, errors="replace").read().split("\n")
bad = collections.defaultdict(set)
for i, l in enumerate(L):
    m = re.match(r"^(\S+\.java):(\d+): error: (package .* does not exist|cannot find symbol)$", l)
    if m and i + 1 < len(L) and re.match(r"^\s*import\s", L[i + 1]):
        bad[m.group(1)].add(int(m.group(2)))
n = 0
for f, lines_ in bad.items():
    p = os.path.join(root, f[len(strip):] if f.startswith(strip) else f)
    if not os.path.exists(p): continue
    src = open(p, encoding="utf-8").read().split("\n")
    for ln in sorted(lines_, reverse=True):
        if src[ln - 1].lstrip().startswith("import "):
            del src[ln - 1]; n += 1
    open(p, "w", encoding="utf-8").write("\n".join(src))
print("removed", n, "unresolved import lines in", len(bad), "files")
