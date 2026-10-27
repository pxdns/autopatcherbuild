"""Fails if a patch bundle contains text copied from the game's decompiled source.

The bundle (eaglercraft-java-source-patch-bundle v1) stores new files in full and changed files as byte-span
deltas whose only text is the inserted bytes (removed bytes are hashes). This tool pulls out every piece of text the
bundle would publish and compares it with the base tree, which only ever exists on the machine running the check.

A "window" is WINDOW consecutive significant lines (blank lines, lines of only braces/punctuation, and import/package lines are skipped,
whitespace is normalised). Any window of the bundle's text that also occurs in the base tree is a leak and fails the
check. Single lines of LONG_LINE characters or more that also occur in the base tree are listed as warnings, since a
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
LONG_LINE = 60
SKIP = re.compile(r"^([\s{}()\[\];,]*|(import|package)\s.*)$")


def sig_lines(text):
    out = []
    for raw in text.splitlines():
        line = " ".join(raw.split())
        if not SKIP.match(line):
            out.append(line)
    return out


def windows(lines):
    for i in range(len(lines) - WINDOW + 1):
        yield "\n".join(lines[i:i + WINDOW])


def h(s):
    return hashlib.sha1(s.encode("utf-8", "replace")).digest()[:12]


def bundle_texts(bundle):
    ops = json.load(open(os.path.join(bundle, "operations.json")))["operations"]
    for op in ops:
        if op["op"] == "delete":
            continue
        path = os.path.join(bundle, op["payload"])
        if op["op"] == "add":
            yield op["path"], open(path, "rb").read().decode("utf-8", "replace")
        else:
            delta = json.load(open(path))
            for hunk in delta["hunks"]:
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
