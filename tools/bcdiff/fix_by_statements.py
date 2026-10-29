#!/usr/bin/env python3
"""Statement-level repair of decompiler damage, using the workspace source of the same class as an oracle for NAMES ONLY.

Both files are split into statements (cut at ; { }), the statements are aligned by shape (difflib on shape keys), and for every
statement javac complains about:
  * an aligned statement (same shape): each decompiler local varK is renamed to the declaration that the workspace identifier at
    the same position resolves to (the declaration must come in an EARLIER statement);
  * an unaligned statement with exactly the same token count as its best workspace twin: identifiers (types, methods) that differ
    are replaced by the workspace identifier at that position; varK is handled as above.
Every edit is recorded as {statement-hash, token-index, old, new}: no game text, only identifiers and a hash.

usage: fix_by_statements.py <javac.log> <root> <strip-prefix> <ws-root[,ws-root]> <fixes.jsonl>
"""
import bisect, collections, difflib, hashlib, json, os, re, sys

log, root, strip, wsroots, rec_path = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(","), sys.argv[5]
TOK = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_$][\w$]*|\d[\w.]*|[^\s\w]')
VARRX = re.compile(r"^var\d+[a-z]*$")
IDRX = re.compile(r"^[A-Za-z_$][\w$]*$")
KEYWORDS = set("abstract assert boolean break byte case catch char class const continue default do double else enum extends final finally float for goto if implements import instanceof int interface long native new package private protected public return short static strictfp super switch synchronized this throw throws transient try void volatile while true false null var".split())
NOT_TYPES = {"return", "new", "else", "case", "throw", "instanceof", "yield", "assert"}


def mask_comments(text):
    out, n, j = [], len(text), 0
    while j < n:
        c = text[j]
        if c == '"' or c == "'":
            k = j + 1
            while k < n and text[k] != c and text[k] != "\n":
                k += 2 if text[k] == "\\" else 1
            out.append(text[j:k + 1]); j = k + 1
        elif text.startswith("/*", j):
            k = text.find("*/", j + 2); k = n if k < 0 else k + 2
            out.append("".join(ch if ch == "\n" else " " for ch in text[j:k])); j = k
        elif text.startswith("//", j):
            k = text.find("\n", j); k = n if k < 0 else k; out.append(" " * (k - j)); j = k
        else:
            out.append(c); j += 1
    return "".join(out)


def tokenize(text):
    masked = mask_comments(text)
    starts = [0] + [m.end() for m in re.finditer("\n", masked)]
    return [(m.group(0), bisect.bisect_right(starts, m.start()), m.start(), m.end()) for m in TOK.finditer(masked)]


def statements(toks):
    """[(first, last)] token index ranges, each ending at a ; { or } token."""
    out, a = [], 0
    for i, t in enumerate(toks):
        if t[0] in (";", "{", "}"):
            out.append((a, i)); a = i + 1
    if a < len(toks):
        out.append((a, len(toks) - 1))
    return out


def find_ws(rel):
    for r in wsroots:
        p = os.path.join(r, rel)
        if os.path.exists(p):
            return p
    return None


def declaration_positions(toks, rng):
    """indices (inside the statement range) of tokens that declare a varK name."""
    a, b = rng
    found = []
    for i in range(a, b + 1):
        t = toks[i][0]
        if not VARRX.match(t) or i == 0 or i + 1 >= len(toks):
            continue
        prev, nxt = toks[i - 1][0], toks[i + 1][0]
        typed = (IDRX.match(prev) and prev not in NOT_TYPES) or prev in (">", "]")
        if typed and nxt in (",", ")", "=", ";", ":"):
            found.append(i)
        elif nxt == "-" and i + 2 < len(toks) and toks[i + 2][0] == ">" and prev in ("(", ",", ";", "{", "=", "return"):
            found.append(i)
    # lambda ( a , b ) ->
    for i in range(a, b + 1):
        if toks[i][0] != "(":
            continue
        j, depth, mem = i + 1, 1, []
        while j < len(toks) and depth and j - i < 40:
            tj = toks[j][0]
            if tj == "(":
                depth += 1
            elif tj == ")":
                depth -= 1
            elif depth == 1 and VARRX.match(tj):
                mem.append(j)
            elif depth == 1 and tj != ",":
                mem = []; break
            j += 1
        if mem and j + 1 < len(toks) and toks[j][0] == "-" and toks[j + 1][0] == ">":
            found.extend(m for m in mem if a <= m <= b)
    return sorted(set(found))


# ---- errors
errs = collections.defaultdict(set)
L = open(log, errors="replace").read().split("\n")
for i, l in enumerate(L):
    m = re.match(r"^(\S+\.java):(\d+): error: ", l)
    if m:
        errs[m.group(1)].add(int(m.group(2)))

records = open(rec_path, "a")
edits_total = files_changed = 0
why = collections.Counter()
for f, err_lines in sorted(errs.items()):
    rel = f[len(strip):] if f.startswith(strip) else f
    dec_path = os.path.join(root, rel); ws_path = find_ws(rel)
    if not os.path.exists(dec_path) or ws_path is None:
        why["no workspace file"] += 1; continue
    dec_text = open(dec_path, encoding="utf-8", errors="replace").read()
    ws_text = open(ws_path, encoding="utf-8", errors="replace").read()
    dt, wt = tokenize(dec_text), tokenize(ws_text)
    ds, ws_ = statements(dt), statements(wt)
    dec_ids = {t[0] for t in dt if not VARRX.match(t[0])}

    def dkey(r): return tuple("L" if VARRX.match(dt[i][0]) else dt[i][0] for i in range(r[0], r[1] + 1))
    def wkey(r): return tuple("L" if (IDRX.match(wt[i][0]) and wt[i][0] not in KEYWORDS and wt[i][0] not in dec_ids) else wt[i][0] for i in range(r[0], r[1] + 1))
    dk = [dkey(r) for r in ds]; wk = [wkey(r) for r in ws_]
    sm = difflib.SequenceMatcher(a=dk, b=wk, autojunk=False)
    pair = {}  # dec statement index -> ws statement index
    for a0, b0, size in sm.get_matching_blocks():
        for k in range(size):
            pair[a0 + k] = b0 + k
    paired_sorted = sorted(pair)

    def ws_twin(si):
        """(workspace statement index, how): exact shape match, else the most similar statement between the aligned neighbours."""
        if si in pair:
            return pair[si], "aligned"
        p = bisect.bisect_left(paired_sorted, si)
        if p == 0 or p >= len(paired_sorted):
            return None, "no neighbours"
        lo, hi = pair[paired_sorted[p - 1]], pair[paired_sorted[p]]
        best, best_r = None, 0.0
        for wi in range(lo + 1, hi):
            if abs(len(wk[wi]) - len(dk[si])) > 6:
                continue
            r = difflib.SequenceMatcher(a=dk[si], b=wk[wi], autojunk=False).ratio()
            if r > best_r:
                best, best_r = wi, r
        if best is not None and best_r >= 0.6:
            return best, "twin"
        return None, "no twin"

    def tpairs(si, wi):
        """dec token index -> ws token index for tokens whose keys agree; plus 1:1 replacements (dec, ws) of unequal tokens."""
        d_r, w_r = ds[si], ws_[wi]
        m2 = difflib.SequenceMatcher(a=dk[si], b=wk[wi], autojunk=False)
        eq, rep = {}, []
        for tag, i1, i2, j1, j2 in m2.get_opcodes():
            if tag == "equal":
                for k in range(i2 - i1):
                    eq[d_r[0] + i1 + k] = w_r[0] + j1 + k
            elif tag == "replace" and (i2 - i1) == (j2 - j1):
                for k in range(i2 - i1):
                    rep.append((d_r[0] + i1 + k, w_r[0] + j1 + k))
        return eq, rep

    twins = {}
    def twin_cached(si):
        if si not in twins:
            wi, how = ws_twin(si)
            twins[si] = (wi, how, tpairs(si, wi) if wi is not None else ({}, []))
        return twins[si]

    # declaration table: workspace identifier -> [(statement index, decompiler name)]
    by_w = collections.defaultdict(list)
    for si in range(len(ds)):
        decls = declaration_positions(dt, ds[si])
        if not decls:
            continue
        wi, how, (eq, rep) = twin_cached(si)
        if wi is None:
            continue
        for ti in decls:
            if ti in eq:
                by_w[wt[eq[ti]][0]].append((si, dt[ti][0]))

    stmt_of = {}
    for si, (a_, b_) in enumerate(ds):
        for ti in range(a_, b_ + 1):
            stmt_of[ti] = si
    edits = {}
    err_stmts = sorted({stmt_of[ti] for ti, tk in enumerate(dt) if tk[1] in err_lines and ti in stmt_of})
    for si in err_stmts:
        wi, how, (eq, rep) = twin_cached(si)
        if wi is None:
            why["statement: " + how] += 1; continue
        decl_here = set(declaration_positions(dt, ds[si]))
        for ti, wj in sorted(list(eq.items()) + rep):
            d, w = dt[ti][0], wt[wj][0]
            if d == w or ti in decl_here:
                continue
            if VARRX.match(d) and IDRX.match(w) and w not in KEYWORDS:
                cands = [(s2, name) for (s2, name) in by_w.get(w, []) if s2 < si and name != d]
                if cands:
                    edits[ti] = max(cands)[1]; why["renamed local"] += 1
                else:
                    why["no earlier declaration"] += 1
            elif (ti, wj) in rep and IDRX.match(d) and IDRX.match(w) and not VARRX.match(d) and d not in KEYWORDS and w not in KEYWORDS and w in dec_ids:
                edits[ti] = w; why["replaced identifier"] += 1
    if not edits:
        continue
    # record + apply (right to left so offsets stay valid)
    out = dec_text
    for ti in sorted(edits, reverse=True):
        si = stmt_of[ti]; a, b = ds[si]
        norm = " ".join(dt[i][0] for i in range(a, b + 1))
        rec = {"file": rel, "h": hashlib.sha1(norm.encode()).hexdigest()[:16], "i": ti - a, "old": dt[ti][0], "new": edits[ti]}
        records.write(json.dumps(rec, separators=(",", ":")) + "\n")
        out = out[:dt[ti][2]] + edits[ti] + out[dt[ti][3]:]
    open(dec_path, "w", encoding="utf-8").write(out)
    files_changed += 1; edits_total += len(edits)
records.close()
print(dict(why))
print("edited %d tokens in %d files" % (edits_total, files_changed))
