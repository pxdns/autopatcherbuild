#!/bin/bash
# Rebuilds the 1.14 manual-edit record from scratch: fresh pipeline (no manual replay), then the edit batches in order.
cd "$(dirname "$0")"
mv manual.jsonl manual.prev.jsonl 2>/dev/null; : > manual.jsonl
./run114b.sh > run114h.log 2>&1; tail -3 run114h.log
for b in b1 b2; do python3 -I ed.py rt manual.jsonl $b.txt | tail -3; done
./build.sh
python3 -I fix_ctor_prelude.py rtc.log rt "rt/" manual.jsonl
for b in b3 b4 b5 b6; do python3 -I ed.py rt manual.jsonl $b.txt | tail -3; done
./build.sh; wc -l manual.jsonl
