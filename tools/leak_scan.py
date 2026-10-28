"""Fails if a patch bundle contains text copied from the game's decompiled source.

The bundle (eaglercraft-java-source-patch-bundle v1 or v2) stores new files in full and changed files as byte-span
deltas whose only text is the inserted bytes (removed bytes are hashes). This tool pulls out every piece of text the
bundle would publish and compares it with the base tree, which only ever exists on the machine running the check.

A "window" is WINDOW consecutive significant lines (blank lines, lines of only braces/punctuation, import/package lines, annotation-only lines such as @Override and
method signatures are skipped,
whitespace is normalised). Any window (of at least MIN_WINDOW_CHARS characters in total) of the bundle's text that also occurs in the base tree is a leak and fails the
check. Single lines of LONG_LINE characters or more that also occur in the base tree are listed as warnings (method
signatures are not counted: an override has to repeat the signature it overrides), since a
long copied line is a likely sign of copied code even when its neighbours differ.

    python3 -I tools/leak_scan.py --base <decompiled java tree> --bundle <bundle dir> [--report report.json]

Exit status: 0 clean, 1 leaks found, 2 bad input. The report names files and line counts, never the copied text.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import sys

WINDOW = 3
MIN_WINDOW_CHARS = 100
LONG_LINE = 60
SIGNATURE = re.compile(r"^(@\w+\s+)*((public|protected|private|static|final|abstract|synchronized|default)\s+)*[\w<>\[\],.? ]+\s+\w+\([^)]*\)\s*(throws [\w, .]+)?\s*\{$")
SKIP = re.compile(r"^([\s{}()\[\];,]*|(import|package)\s.*|@\w+(\(.*\))?)$")


def sig_lines(text, keep_signatures=False):
    out = []
    for raw in text.splitlines():
        line = " ".join(raw.split())
        if SKIP.match(line):
            continue
        if not keep_signatures and SIGNATURE.match(line):
            continue   # an override has to repeat the signature it overrides
        out.append(line)
    return out


def windows(lines):
    """Yield each run of WINDOW lines that is long enough to carry expression.

    A run whose lines total fewer than MIN_WINDOW_CHARS characters is a sequence of idioms such as
    "return true;" / "break;" / "default:" and is not counted.
    """
    for i in range(len(lines) - WINDOW + 1):
        run = lines[i:i + WINDOW]
        if sum(len(x) for x in run) >= MIN_WINDOW_CHARS:
            yield "\n".join(run)


def h(s):
    return hashlib.sha1(s.encode("utf-8", "replace")).digest()[:12]


def bundle_texts(bundle):
    ops = json.load(open(os.path.join(bundle, "operations.json")))["operations"]
    for op in ops:
        if op["op"] == "delete":
            continue
        path = os.path.join(bundle, op["payload"])
        if op["op"] == "add" and op.get("payload_kind") == "parts-v2":
            # v2: a reference to base bytes is not text the bundle publishes; every text part is scanned on its own
            for part in json.load(open(path))["parts"]:
                if part["t"] == "b64":
                    yield op["path"], base64.b64decode(part["d"]).decode("utf-8", "replace")
        elif op["op"] == "add":
            yield op["path"], open(path, "rb").read().decode("utf-8", "replace")
        else:
            delta = json.load(open(path))
            for hunk in delta["hunks"]:
                if "insert_parts" in hunk:
                    for part in hunk["insert_parts"]:
                        if part["t"] == "b64":
                            yield op["path"], base64.b64decode(part["d"]).decode("utf-8", "replace")
                else:
                    yield op["path"], base64.b64decode(hunk["insert_b64"]).decode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--report")
    a = ap.parse_args()
    if not os.path.isdir(a.base) or not os.path.isfile(os.path.join(a.bundle, "operations.json")):
        print("bad --base or --bundle", file=sys.stderr)
        return 2
    base_windows, base_lines = set(), set()
    for root, _, files in os.walk(a.base):
        for f in files:
            if f.endswith(".java"):
                lines = sig_lines(open(os.path.join(root, f), encoding="utf-8", errors="replace").read())
                base_windows.update(h(w) for w in windows(lines))
                base_lines.update(h(l) for l in lines if len(l) >= LONG_LINE)
    leaks, warns, scanned = {}, {}, 0
    for path, text in bundle_texts(a.bundle):
        scanned += 1
        lines = sig_lines(text)
        n = sum(1 for w in windows(lines) if h(w) in base_windows)
        if n:
            leaks[path] = leaks.get(path, 0) + n
        m = sum(1 for l in lines if len(l) >= LONG_LINE and h(l) in base_lines)
        if m:
            warns[path] = warns.get(path, 0) + m
    rep = {"text_pieces_scanned": scanned, "window_lines": WINDOW,
           "leaking_files": len(leaks), "leaking_windows": sum(leaks.values()),
           "long_line_warnings": len(warns), "leaks": leaks, "warnings": warns}
    if a.report:
        json.dump(rep, open(a.report, "w"), indent=1, sort_keys=True)
    print("scanned %d text pieces: %d files with copied %d-line windows (%d windows), %d files with copied long lines"
          % (scanned, len(leaks), WINDOW, sum(leaks.values()), len(warns)))
    return 1 if leaks else 0


if __name__ == "__main__":
    sys.exit(main())
