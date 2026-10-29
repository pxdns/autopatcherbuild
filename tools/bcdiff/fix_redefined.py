#!/usr/bin/env python3
"""For javac 'variable X is already defined in method ...': rename the declaration on the error line, and its uses up to the end of the
enclosing block, to X+'y'. (Inside a decompiled lambda the decompiler numbers the lambda's own locals independently of the enclosing
method, so they collide with the enclosing parameters.)  Records {file, line-statement hash, old, new} like the other fixers.
usage: fix_redefined.py <javac.log> <root> <strip-prefix> <fixes.jsonl>"""
import collections, hashlib, json, os, re, sys, bisect
log, root, strip, rec = sys.argv[1:5]
TOK = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_$][\w$]*|\d[\w.]*|[^\s\w]')
def mask(text):
    out, n, j = [], len(text), 0
    while j < n:
        if text.startswith("/*", j):
            k = text.find("*/", j + 2); k = n if k < 0 else k + 2
            out.append("".join(c if c == "\n" else " " for c in text[j:k])); j = k
        elif text.startswith("//", j):
            k = text.find("\n", j); k = n if k < 0 else k; out.append(" " * (k - j)); j = k
        else:
            out.append(text[j]); j += 1
    return "".join(out)
errs = collections.defaultdict(list)
for l in open(log, errors="replace"):
    m = re.match(r"^(\S+\.java):(\d+): error: variable (\S+) is already defined in", l)
    if m: errs[m.group(1)].append((int(m.group(2)), m.group(3)))
R = open(rec, "a"); n = files = 0
for f, items in errs.items():
    p = os.path.join(root, f[len(strip):] if f.startswith(strip) else f)
    if not os.path.exists(p): continue
    text = open(p, encoding="utf-8", errors="replace").read(); m_ = mask(text)
    starts = [0] + [m.end() for m in re.finditer("\n", m_)]
    toks = [(m.group(0), m.start(), m.end()) for m in TOK.finditer(m_)]
    line_of = lambda off: bisect.bisect_right(starts, off)
    edits = []  # (start, end, new)
    for ln, name in sorted(set(items)):
        # declaration token: first `name` on that line followed by = ; , ) :  and preceded by a type-ish token
        decl = None
        for i, (t, s, e) in enumerate(toks):
            if line_of(s) == ln and t == name and i + 1 < len(toks) and toks[i + 1][0] in ("=", ";", ",", ")", ":"):
                decl = i; break
        if decl is None: continue
        depth = 0; new = name + "y"
        for j in range(decl, len(toks)):
            t, s, e = toks[j]
            if t == "{": depth += 1
            elif t == "}":
                depth -= 1
                if depth < 0: break
            elif t == name: edits.append((s, e, new))
        R.write(json.dumps({"file": f[len(strip):] if f.startswith(strip) else f, "op": "rename-local-from-line-decl", "name": name, "new": new,
                            "h": hashlib.sha1(" ".join(t for t, s, e in toks if line_of(s) == ln).encode()).hexdigest()[:16]}, separators=(",", ":")) + "\n")
        n += 1
    if edits:
        for s, e, new in sorted(set(edits), reverse=True): text = text[:s] + new + text[e:]
        open(p, "w", encoding="utf-8").write(text); files += 1
R.close(); print("renamed", n, "clashing locals in", files, "files")
