#!/usr/bin/env python3
"""usage: mkrt.py <workspace-java-root[,more roots]> <patched-vanilla-dir> <out-dir> <vanilla-prefix,...> <excluded-prefix,...>
out-dir = patched vanilla tree + every other workspace source file that is not under an excluded prefix."""
import os, shutil, sys
wsroots, patched, out, vanilla, excluded = sys.argv[1:6]
wsroots = wsroots.split(",")
vanilla = vanilla.split(","); excluded = [e for e in excluded.split(",") if e]
shutil.rmtree(out, ignore_errors=True)
n = 0
for d, _, fs in os.walk(patched):
    for f in fs:
        if f.endswith(".java"):
            r = os.path.relpath(os.path.join(d, f), patched)
            os.makedirs(os.path.dirname(os.path.join(out, r)), exist_ok=True); shutil.copyfile(os.path.join(d, f), os.path.join(out, r)); n += 1
m = 0
for ws in wsroots:
  for d, _, fs in os.walk(ws):
    for f in fs:
        if not f.endswith(".java"): continue
        r = os.path.relpath(os.path.join(d, f), ws).replace(os.sep, "/")
        if any(r.startswith(v) for v in vanilla) or any(r.startswith(e) for e in excluded): continue
        t = os.path.join(out, r); os.makedirs(os.path.dirname(t), exist_ok=True); shutil.copyfile(os.path.join(d, f), t); m += 1
print("patched vanilla files", n, "+ workspace platform files", m)
