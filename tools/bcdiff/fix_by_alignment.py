#!/usr/bin/env python3
"""Repairs decompiler variable names by aligning each file with the workspace source of the same class (names only, no text is copied).

For every javac error line that uses a local named varK which has NO declaration nearby (it is dangling):
  1. tokenise the decompiled file and the workspace file and align them (difflib), local-looking identifiers wildcarded;
  2. the workspace identifier W aligned with that varK is the variable's real name;
  3. the decompiled identifier aligned with W at a declaration (typed declaration, parameter, for-each/catch variable or lambda
     parameter) nearest above the error is the name the enclosing code really uses; varK is rewritten to it on that line.
A varK that is declared within SCOPE_LINES lines above is considered fine and is left alone.

usage: fix_by_alignment.py <javac.log> <compile-root> <strip-prefix> <ws-root>[,<ws-root>...]
"""
import difflib, os, re, sys, collections

log, root, strip, wsroots = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
SCOPE_LINES = 80
TOK = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_$][\w$]*|\d[\w.]*|[^\s\w]')
VARRX = re.compile(r"^var\d+[a-z]*$")
IDRX = re.compile(r"^[A-Za-z_$][\w$]*$")
KEYWORDS = set("abstract assert boolean break byte case catch char class const continue default do double else enum extends final finally float for goto if implements import instanceof int interface long native new package private protected public return short static strictfp super switch synchronized this throw throws transient try void volatile while true false null var".split())
NOT_TYPES = {"return", "new", "else", "case", "throw", "instanceof", "yield", "assert"}


def tokens(text):
    """[(token, line_number)] with comments removed (line numbers kept)."""
    n, j, cleaned = len(text), 0, []
    while j < n:
        if text.startswith("/*", j):
            k = text.find("*/", j + 2); k = n if k < 0 else k + 2
            cleaned.append("\n" * text.count("\n", j, k)); j = k
        elif text.startswith("//", j):
            k = text.find("\n", j); j = n if k < 0 else k
        else:
            cleaned.append(text[j]); j += 1
    text = "".join(cleaned)
    starts = [0]
    for m in re.finditer("\n", text):
        starts.append(m.end())
    import bisect
    return [(m.group(0), bisect.bisect_right(starts, m.start())) for m in TOK.finditer(text)]


def declarations(dt):
    """token index -> True for every token that declares a varK name."""
    decl = set()
    n = len(dt)
    for i, (t, _) in enumerate(dt):
        if not VARRX.match(t) or i == 0 or i + 1 >= n:
            continue
        prev, nxt = dt[i - 1][0], dt[i + 1][0]
        typed = (IDRX.match(prev) and prev not in NOT_TYPES) or prev in (">", "]")
        if typed and nxt in (",", ")", "=", ";", ":"):
            decl.add(i)
        elif nxt == "-" and i + 2 < n and dt[i + 2][0] == ">" and prev in ("(", ",", ";", "{", "=", "return"):
            decl.add(i)  # lambda: var ->
    # lambda: ( a , b , c ) ->  : every varK directly inside the parentheses is a parameter
    for i, (t, _) in enumerate(dt):
        if t != "(":
            continue
        depth, j, members = 1, i + 1, []
        while j < n and depth:
            tj = dt[j][0]
            if tj == "(":
                depth += 1
            elif tj == ")":
                depth -= 1
            elif depth == 1 and VARRX.match(tj):
                members.append(j)
            elif depth == 1 and tj not in (",",) and not VARRX.match(tj):
                members = []; break  # not a bare parameter list
            j += 1
            if j - i > 40:
                members = []; break
        if members and j + 1 < n and dt[j][0] == "-" and dt[j + 1][0] == ">":
            decl.update(members)
    return decl


def find_ws(rel):
    for r in wsroots:
        p = os.path.join(r, rel)
        if os.path.exists(p):
            return p
    return None


errs = collections.defaultdict(lambda: collections.defaultdict(set))
L = open(log, errors="replace").read().split("\n")
for i, l in enumerate(L):
    m = re.match(r"^(\S+\.java):(\d+): error: (.*)$", l)
    if not m:
        continue
    ks = set(re.findall(r"\b(var\d+[a-z]*)\b", L[i + 1] if i + 1 < len(L) else ""))
    if ks:
        errs[m.group(1)][int(m.group(2))] |= ks

fixed = files = 0
why = collections.Counter()
for f, lines_map in sorted(errs.items()):
    rel = f[len(strip):] if f.startswith(strip) else f
    dec_path = os.path.join(root, rel)
    ws_path = find_ws(rel)
    if not os.path.exists(dec_path) or ws_path is None:
        why["no workspace file"] += 1; continue
    dec_text = open(dec_path, encoding="utf-8", errors="replace").read()
    ws_text = open(ws_path, encoding="utf-8", errors="replace").read()
    dt, wt = tokens(dec_text), tokens(ws_text)
    decl = declarations(dt)
    decl_lines = collections.defaultdict(list)
    for i in decl:
        decl_lines[dt[i][0]].append(dt[i][1])
    dec_ids = {t for t, _ in dt if not VARRX.match(t)}
    dkey = ["L" if VARRX.match(t) else t for t, _ in dt]
    wkey = ["L" if (IDRX.match(t) and t not in KEYWORDS and t not in dec_ids) else t for t, _ in wt]
    sm = difflib.SequenceMatcher(a=dkey, b=wkey, autojunk=False)
    align = {}
    for a0, b0, size in sm.get_matching_blocks():
        for k in range(size):
            align[a0 + k] = b0 + k
    aligned_idx = sorted(align)
    import bisect as _bs

    def local_align(i):
        """Aligns just the stretch between the nearest aligned tokens around i; returns the workspace token index or None."""
        p = _bs.bisect_left(aligned_idx, i)
        if p == 0 or p >= len(aligned_idx):
            return None
        a, b = aligned_idx[p - 1], aligned_idx[p]
        wa, wb = align[a], align[b]
        if not (0 < b - a <= 600 and 0 < wb - wa <= 600):
            return None
        m2 = difflib.SequenceMatcher(a=dkey[a + 1:b], b=wkey[wa + 1:wb], autojunk=False)
        for x0, y0, size in m2.get_matching_blocks():
            if x0 <= i - a - 1 < x0 + size:
                return wa + 1 + y0 + (i - a - 1 - x0)
        return None

    by_w = collections.defaultdict(list)  # workspace identifier -> [(line, decompiled name)] at declarations
    for i in decl:
        if i in align:
            by_w[wt[align[i]][0]].append((dt[i][1], dt[i][0]))
    lines = dec_text.split("\n")
    changed = False
    for ln, ks in sorted(lines_map.items()):
        for k in sorted(ks):
            cands = [i for i, (t, l2) in enumerate(dt) if l2 == ln and t == k and i in align]
            if cands:
                W = wt[align[cands[0]]][0]
            else:
                raw = [i for i, (t, l2) in enumerate(dt) if l2 == ln and t == k]
                wi = local_align(raw[0]) if raw else None
                if wi is None:
                    why["token not aligned"] += 1; continue
                W = wt[wi][0]; why["aligned locally"] += 1
            # nearest declaration of K above this line (token index), if any
            near = [i for i in decl if dt[i][0] == k and ln - SCOPE_LINES <= dt[i][1] <= ln]
            if near:
                d = max(near, key=lambda i: dt[i][1])
                Wd = wt[align[d]][0] if d in align else None
                if Wd is None or Wd == W:
                    why["declared nearby and consistent (left alone)"] += 1; continue
                why["declared nearby but bound to the wrong variable"] += 1
            sites = [(l2, name) for (l2, name) in by_w.get(W, []) if l2 < ln and name != k]
            if not sites:
                why["no declaration for the aligned name"] += 1; continue
            target = max(sites)[1]
            new = re.sub(r"\b" + re.escape(k) + r"\b", target, lines[ln - 1])
            if new != lines[ln - 1]:
                lines[ln - 1] = new; changed = True; fixed += 1
    if changed:
        open(dec_path, "w", encoding="utf-8").write("\n".join(lines)); files += 1
print(dict(why))
print("renamed on %d error lines in %d files" % (fixed, files))
