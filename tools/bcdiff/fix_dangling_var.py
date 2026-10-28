#!/usr/bin/env python3
"""Fixes Vineflower's 'dangling lambda capture': a lambda inside an instance method refers to varK where the enclosing method
declares var(K+1) (slot 0 is 'this' there). Uses javac's own 'cannot find symbol ... variable varK' errors, one line at a time.
usage: fix_dangling_var.py javac.log <root> [strip-prefix]      paths in the log are relative to cwd; <root> is where the files live"""
import re, sys, os, collections
log, root = sys.argv[1], sys.argv[2]; strip = sys.argv[3] if len(sys.argv) > 3 else ""
errs = collections.defaultdict(set)
L = open(log, errors="replace").read().split("\n")
for i, l in enumerate(L):
    m = re.match(r"^(\S+\.java):(\d+): error: cannot find symbol$", l)
    if not m: continue
    sym = next((x for x in L[i+1:i+5] if "symbol:" in x), "")
    v = re.search(r"variable var(\d+)\b", sym)
    if v: errs[m.group(1)].add((int(m.group(2)), int(v.group(1))))
fixed = skipped = 0
for f, items in errs.items():
    rel = f[len(strip):] if strip and f.startswith(strip) else f
    p = os.path.join(root, rel)
    if not os.path.exists(p): skipped += len(items); continue
    lines = open(p, encoding="utf-8").read().split("\n")
    for ln, k in sorted(items):
        want = f"var{k+1}"
        # the enclosing method must declare var(K+1) as a parameter somewhere above (signature, up to 60 lines up)
        decl = re.compile(r"[\w>\]]\s+" + want + r"\b\s*[,)]")
        ok = any(decl.search(lines[j]) and "(" in "".join(lines[max(0, j-3):j+1]) for j in range(ln - 1, max(ln - 61, -1), -1))
        if not ok: skipped += 1; continue
        new = re.sub(r"\bvar" + str(k) + r"\b", want, lines[ln - 1])
        if new != lines[ln - 1]: lines[ln - 1] = new; fixed += 1
    open(p, "w", encoding="utf-8").write("\n".join(lines))
print("lines fixed", fixed, "skipped", skipped)
