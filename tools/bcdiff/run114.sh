#!/bin/bash
# Full 1.14 pipeline, one plain-English line per step.
cd "$(dirname "$0")"; J=/home/user/jdks/jdk-17.0.21+9/bin; JP=libs/tool-javaparser-core-3.26.4.jar
CP='libs/tool-asm-9.7.jar:libs/tool-asm-tree-9.7.jar:tool'
WS=/home/user/eagler-versions/eaglercraft-1.14-workspace/src/main/java
echo "[1/9] reading the workspace's compiled classes (bytecode signatures incl. declared exceptions)"
$J/java -Xmx1g -Dren=ren.txt -cp "$CP" BcSig ws17 sig-ws.txt net/minecraft/ com/mojang/ 2>&1 | grep -v Picked
echo "[2/9] reading the vanilla 1.14.4 jar (name set already matched per class)"
$J/java -Xmx1g -Dren=ren.txt -cp "$CP" BcSig mc114-adj.jar sig-van.txt net/minecraft/ com/mojang/ 2>&1 | grep -v Picked
echo "[3/9] pairing members the two sides name differently, then renaming them in the vanilla jar (two rounds)"
python3 -I mkrename.py sig-van.txt sig-ws.txt rename114a.srg
$J/java -Xmx1g -jar ss.jar --in-jar mc114-adj.jar --out-jar mc114-r1.jar --srg-in rename114a.srg --kill-source 2>&1 | tail -1
$J/java -Xmx1g -Dren=ren.txt -cp "$CP" BcSig mc114-r1.jar sig-van.txt net/minecraft/ com/mojang/ 2>&1 | grep -v Picked
python3 -I mkrename.py sig-van.txt sig-ws.txt rename114b.srg
$J/java -Xmx1g -jar ss.jar --in-jar mc114-r1.jar --out-jar mc114-r2.jar --srg-in rename114b.srg --kill-source 2>&1 | tail -1
$J/java -Xmx1g -Dren=ren.txt -cp "$CP" BcSig mc114-r2.jar sig-van.txt net/minecraft/ com/mojang/ 2>&1 | grep -v Picked
echo "[4/9] decompiling the renamed vanilla jar (Vineflower)"
rm -rf dec2 && mkdir dec2 && $J/java -Xmx3g -jar /home/user/26.3/build-inputs/vineflower-1.12.0.jar -dgs=1 -asc=1 -rsy=1 -hdc=0 mc114-r2.jar dec2 > dec2.log 2>&1
echo "      $(find dec2 -name '*.java' | wc -l) source files"
echo "[5/9] finding what the workspace changed"
python3 -I delta.py | tail -4; python3 -I mktsv.py
echo "[6/9] turning the differences into patch operations"
$J/java -Xmx2g -cp "$JP:tool" BundleExport $WS delta.tsv ops.jsonl report.txt tops.txt 2>&1 | grep -v Picked
echo "[7/9] applying the operations to the fresh decompile"
rm -rf patched && mkdir patched && cp -r dec2/net dec2/com patched/
$J/java -Xmx3g -cp "$JP:tool" BundleApply patched ops.jsonl apply-report.txt 2>&1 | grep -v Picked | tail -1
echo "[8/9] assembling the compile tree (patched vanilla + workspace platform code)"
python3 -I mkrt.py $WS,$WS/../../lwjgl/java patched rt "net/minecraft/,com/mojang/blaze3d/,com/mojang/realmsclient/" ""
echo "[9/9] compiling with javac"
rm -rf rtout && mkdir rtout && find rt -name '*.java' > rt.txt
$J/javac -J-Xmx3g -nowarn -proc:none -encoding UTF-8 --release 17 -XDstringConcat=inline -cp 'libs/*' -d rtout -Xmaxerrs 100000 @rt.txt > rtc.log 2>&1
echo "      javac errors: $(grep -c 'error:' rtc.log)"
