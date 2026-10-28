#!/bin/bash
# Full 1.12 pipeline, one plain-English line per step.
cd "$(dirname "$0")"; J=/home/user/jdks/jdk-17.0.21+9/bin; JP=libs/tool-javaparser-core-3.26.4.jar
W=/home/user/devevolperplus/eaglercraft-1.12-source; WS=$W/src/main/java
echo "[1/7] decompiling the renamed vanilla 1.12.2 jar (Vineflower)"
rm -rf dec12 && mkdir dec12 && $J/java -Xmx3g -jar /home/user/26.3/build-inputs/vineflower-1.12.0.jar --log-level=warn -dgs=1 -rsy=1 mc112-adj2.jar dec12 > dec12.log 2>&1
echo "      $(find dec12 -name '*.java' | wc -l) source files"
echo "[2/7] finding what the workspace changed (bytecode comparison results already in sig12-*.txt)"
cp sig12-van3.txt r112/sig-van.txt; cp sig12-ws.txt r112/sig-ws.txt
(cd r112 && python3 -I delta.py | tail -4 && python3 -I mktsv.py && python3 - <<'P'
rows=open("delta.tsv").read().splitlines()
keep=[l for l in rows if not l.split("\t")[0].startswith("net/minecraft/src/")]
open("delta.tsv","w").write("\n".join(keep)+"\n")
tops=sorted({l.split("\t",1)[0] for l in open("sig-van.txt",encoding="utf-8") if "$" not in l.split("\t",1)[0]})
open("tops.txt","w").write("\n".join(tops)+"\n")
P
)
echo "[3/7] turning the differences into patch operations (JavaParser reads the workspace sources)"
$J/java -Xmx2g -cp "$JP:tool" BundleExport $WS r112/delta.tsv r112/ops.jsonl r112/report.txt r112/tops.txt 2>&1 | grep -v Picked
echo "[4/7] setting aside operations that depend on OptiFine / shader code"
python3 -I filter_nonvanilla.py $WS r112/ops.jsonl r112/ops-clean.jsonl r112/ops-excluded.jsonl net/minecraft/src net/optifine shadersmod
echo "[5/7] applying the operations to the fresh decompile"
rm -rf r112/patched && mkdir r112/patched && cp -r dec12/net r112/patched/
$J/java -Xmx3g -cp "$JP:tool" BundleApply r112/patched r112/ops-clean.jsonl r112/apply-report.txt 2>&1 | grep -v Picked | tail -1
echo "[6/7] assembling the compile tree (patched vanilla + workspace platform code, no OptiFine/shaders)"
python3 -I mkrt.py $WS r112/patched r112/rt "net/minecraft/" "net/optifine/,shadersmod/"
echo "[7/7] compiling with javac"
cd r112 && rm -rf rtout && mkdir rtout && find rt -name '*.java' > rt.txt && CPJ=$(find $W/lib -name '*.jar' | tr '\n' ':')
$J/javac -J-Xmx3g -nowarn -proc:none -encoding UTF-8 --release 17 -XDstringConcat=inline -cp "$CPJ" -d rtout -Xmaxerrs 100000 @rt.txt > rtc.log 2>&1
echo "      javac errors: $(grep -c 'error:' rtc.log)"
