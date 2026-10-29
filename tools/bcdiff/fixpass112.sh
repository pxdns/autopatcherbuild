#!/bin/bash
# 1.12: same fixers as fixpass2.sh, run against r112/ (patched tree from run112.sh steps 1-5).
cd "$(dirname "$0")"; B=$PWD; J=/home/user/jdks/jdk-17.0.21+9/bin
LC="$B/libs/tool-javaparser-core-3.26.4.jar:$B/libs/tool-asm-9.7.jar:$B/libs/tool-asm-tree-9.7.jar:$B/libs/tool-asm-analysis-9.7.jar"
W=/home/user/devevolperplus/eaglercraft-1.12-source; WSR=$W/src/main/java; CPJ=$(find $W/lib -name '*.jar' | tr '\n' ':')
JAR=$B/mc112-adj2.jar
cd r112
build() { rm -rf rtout && mkdir rtout && find rt -name '*.java' > rt.txt && $J/javac -J-Xmx3g -nowarn -proc:none -encoding UTF-8 --release 17 -XDstringConcat=inline -cp "$CPJ" -d rtout -Xmaxerrs 100000 @rt.txt > rtc.log 2>&1; echo "      javac errors: $(grep -c 'error:' rtc.log)"; }
echo "[a] assembling"; python3 -I ../mkrt.py $WSR patched rt "net/minecraft/" "net/optifine/,shadersmod/"
echo "[b] compiling (pristine)"; build; cp rtc.log pristine.log
echo "[L] lambda captures from bytecode"; $J/java -Xmx3g -cp "$LC:$B/tool" LambdaCaptures $JAR rt pristine.log "rt/" lambda-report.txt 2>&1 | grep -v Picked | tail -1; build
echo "[c0] bad imports"; python3 -I ../fix_bad_imports.py rtc.log rt "rt/" 2>&1 | tail -1; build
for t in 1 2; do echo "[c1.$t] clashing locals"; python3 -I ../fix_redefined.py rtc.log rt "rt/" autos.jsonl 2>&1 | tail -1; build; done
for r in 1 2; do echo "[d$r] alignment round $r"; python3 -I ../fix_by_alignment.py rtc.log rt "rt/" "$WSR" 2>&1 | tail -1; build; done
if [ -s manual.jsonl ]; then echo "[m] manual replay"; python3 -I ../applyfixes.py rt manual.jsonl | tail -3; build; fi
echo done
