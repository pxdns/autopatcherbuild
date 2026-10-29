#!/bin/bash
# Rebuilds the 1.12 manual-edit record from scratch: fresh pipeline (no manual replay), then the edit batches in order.
cd "$(dirname "$0")"
mv r112/manual.jsonl r112/manual.prev.jsonl 2>/dev/null; : > r112/manual.jsonl
./run112b.sh > run112d.log 2>&1; tail -3 run112d.log
for b in c1 c2 c3 c4 c6 c7 c8 c9 c10 c11 c12 c13 c14 c15; do echo "$b: $(python3 -I ed.py r112/rt r112/manual.jsonl $b.txt 2>&1 | tail -1)"; done
./build112.sh; wc -l r112/manual.jsonl
