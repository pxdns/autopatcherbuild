"""Shared helpers: comment-masked tokenising, statements, aligned twin lookup."""
import bisect, difflib, hashlib, os, re
TOK = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_$][\w$]*|\d[\w.]*|[^\s\w]')
VARRX = re.compile(r"^var\d+[a-z]*$"); IDRX = re.compile(r"^[A-Za-z_$][\w$]*$")
KEYWORDS = set("abstract assert boolean break byte case catch char class const continue default do double else enum extends final finally float for goto if implements import instanceof int interface long native new package private protected public return short static strictfp super switch synchronized this throw throws transient try void volatile while true false null var".split())
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
    masked = mask_comments(text); starts = [0] + [m.end() for m in re.finditer("\n", masked)]
    return [(m.group(0), bisect.bisect_right(starts, m.start()), m.start(), m.end()) for m in TOK.finditer(masked)]
def statements(toks):
    out, a = [], 0
    for i, t in enumerate(toks):
        if t[0] in (";", "{", "}"): out.append((a, i)); a = i + 1
    if a < len(toks): out.append((a, len(toks) - 1))
    return out
def shash(toks, rng):
    return hashlib.sha1(" ".join(toks[i][0] for i in range(rng[0], rng[1] + 1)).encode()).hexdigest()[:16]
def find_ws(roots, rel):
    for r in roots:
        p = os.path.join(r, rel)
        if os.path.exists(p): return p
class Twin:
    def __init__(self, dec_text, ws_text):
        self.dt, self.wt = tokenize(dec_text), tokenize(ws_text)
        self.ds, self.ws = statements(self.dt), statements(self.wt)
        dec_ids = {t[0] for t in self.dt if not VARRX.match(t[0])}
        self.dk = [tuple("L" if VARRX.match(self.dt[i][0]) else self.dt[i][0] for i in range(a, b + 1)) for a, b in self.ds]
        self.wk = [tuple("L" if (IDRX.match(self.wt[i][0]) and self.wt[i][0] not in KEYWORDS and self.wt[i][0] not in dec_ids) else self.wt[i][0] for i in range(a, b + 1)) for a, b in self.ws]
        sm = difflib.SequenceMatcher(a=self.dk, b=self.wk, autojunk=False)
        self.pair = {}
        for a0, b0, size in sm.get_matching_blocks():
            for k in range(size): self.pair[a0 + k] = b0 + k
        self.sorted = sorted(self.pair)
    def twin(self, si):
        if si in self.pair: return self.pair[si]
        p = bisect.bisect_left(self.sorted, si)
        if p == 0 or p >= len(self.sorted): return None
        lo, hi = self.pair[self.sorted[p - 1]], self.pair[self.sorted[p]]
        best, br = None, 0.0
        for wi in range(lo + 1, hi):
            if abs(len(self.wk[wi]) - len(self.dk[si])) > 8: continue
            r = difflib.SequenceMatcher(a=self.dk[si], b=self.wk[wi], autojunk=False).ratio()
            if r > br: best, br = wi, r
        return best if br >= 0.5 else None
    def stmt_of_line(self, ln):
        for si, (a, b) in enumerate(self.ds):
            if any(self.dt[i][1] == ln for i in range(a, b + 1)): return si
    def text(self, toks, rng): return " ".join(toks[i][0] for i in range(rng[0], rng[1] + 1))


def inline_prelude(text, call_hash, occ=0):
    """Vineflower hoists argument temporaries above this(...)/super(...). For the statement whose token hash is call_hash, inline the
    directly preceding `Type name = expr;` declarations into the call's arguments and drop them. Returns (new_text, number_inlined)."""
    toks = tokenize(text); sts = statements(toks)
    same = [i for i, st in enumerate(sts) if shash(toks, st) == call_hash]
    ci = same[occ] if occ < len(same) else None
    if ci is None: return text, 0
    a, b = sts[ci]
    if toks[a][0] not in ("this", "super") or toks[a + 1][0] != "(": return text, 0
    decls = []  # (name, expr tokens) nearest first
    j, first = ci - 1, None
    while j >= 0:
        sa, sb = sts[j]
        seq = [toks[k][0] for k in range(sa, sb + 1)]
        if seq[-1] != ";" or "=" not in seq: break
        e = seq.index("=")
        if e < 2 or not IDRX.match(seq[e - 1]): break
        decls.append((seq[e - 1], seq[e + 1:-1])); first = sa; j -= 1
    if not decls: return text, 0
    decls.reverse()  # source order
    exprs = {}
    for name, ex in decls:
        out = []
        for t in ex:
            out.append(exprs[t] if t in exprs else t)
        exprs[name] = "(" + " ".join(out) + ")" if len(out) > 1 else out[0]
    call = [exprs[toks[k][0]] if toks[k][0] in exprs else toks[k][0] for k in range(a, b + 1)]
    new = " ".join(call).replace("( (", "((").replace(") )", "))")
    return text[:toks[first][2]] + new + text[toks[b][3]:], len(decls)


_GLUE = [("- >", "->"), ("< =", "<="), ("> =", ">="), ("! =", "!="), ("= =", "=="), ("& &", "&&"), ("| |", "||"), (": :", "::")]
def join_tokens(new):
    s = " ".join(new)
    for a, b in _GLUE: s = s.replace(a, b)
    return s
