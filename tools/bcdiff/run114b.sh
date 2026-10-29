#!/bin/bash
# 1.14: rows -> operations -> apply -> fix pass. One plain line per step.
cd "$(dirname "$0")"; J=/home/user/jdks/jdk-17.0.21+9/bin; JP=libs/tool-javaparser-core-3.26.4.jar
WS=/home/user/eagler-versions/eaglercraft-1.14-workspace/src/main/java
echo "[1] finding what the workspace changed (current rules)"; python3 -I delta.py | head -2; python3 -I mktsv.py
echo "[2] turning the differences into patch operations (now incl. added nested classes)"
$J/java -Xmx2g -cp "$JP:tool" BundleExport $WS delta.tsv ops.jsonl report.txt tops.txt 2>&1 | grep -v Picked
echo "[3] applying them to the fresh decompile"
rm -rf patched && mkdir patched && cp -r dec2/net dec2/com patched/
$J/java -Xmx3g -cp "$JP:tool" BundleApply patched ops.jsonl apply-report.txt 2>&1 | grep -v Picked | tail -1
echo "[4] assemble, compile, run the fixers"
./fixpass.sh 114
