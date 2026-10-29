#!/usr/bin/env python3
"""Prints ed.py batch lines that rename every whole-token occurrence of <old> to <new> in lines [a,b] of <file> (under <root>).
usage: edgen.py <root> <relfile> <a> <b> <old> <new> [skip-line,...]   (skip lines are left alone)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stmtlib import *
root, rel, a, b, old, new = sys.argv[1:7]; a, b = int(a), int(b)
skip = {int(x) for x in sys.argv[7].split(",")} if len(sys.argv) > 7 and sys.argv[7] else set()
toks = tokenize(open(os.path.join(root, rel), encoding="utf-8").read())
for t in toks:
    if t[0] == old and a <= t[1] <= b and t[1] not in skip:
        print("%s:%d | %s => %s" % (rel, t[1], old, new))
