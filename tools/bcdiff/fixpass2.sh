#!/bin/bash
# usage: fixpass2.sh 114 — from a freshly patched tree: assemble, compile, lambda capture repair (bytecode), import cleanup, local-name clashes,
# alignment name repair, replay of recorded manual edits. One line per stage.
cd "$(dirname "$0")"; J=/home/user/jdks/jdk-17.0.21+9/bin
LC='libs/tool-javaparser-core-3.26.4.jar:libs/tool-asm-9.7.jar:libs/tool-asm-tree-9.7.jar:libs/tool-asm-analysis-9.7.jar'
WSR=/home/user/eagler-versions/eaglercraft-1.14-workspace/src/main/java; ASM="$WSR,$WSR/../../lwjgl/java"; CPJ='libs/*'
VAN="net/minecraft/,com/mojang/blaze3d/,com/mojang/realmsclient/"; D=.; JAR=mc114-r2.jar
build() { rm -rf rtout && mkdir rtout && find rt -name '*.java' > rt.txt && $J/javac -J-Xmx3g -nowarn -proc:none -encoding UTF-8 --release 17 -XDstringConcat=inline -cp "$CPJ" -d rtout -Xmaxerrs 100000 @rt.txt > rtc.log 2>&1; echo "      javac errors: $(grep -c 'error:' rtc.log)"; }
echo "[a] assembling the compile tree from the freshly patched sources"; python3 -I mkrt.py "$ASM" patched rt "$VAN" ""
echo "[b] compiling (pristine)"; build; cp rtc.log pristine.log
echo "[L] repairing captured variables in lambdas from the bytecode"; $J/java -Xmx3g -cp "$LC:tool" LambdaCaptures $JAR rt pristine.log "rt/" lambda-report.txt 2>&1 | grep -v Picked | tail -1; build
echo "[c0] removing imports javac cannot resolve"; python3 -I fix_bad_imports.py rtc.log rt "rt/" 2>&1 | tail -1; build
for t in 1 2; do echo "[c1.$t] unique names for clashing locals"; python3 -I fix_redefined.py rtc.log rt "rt/" autos.jsonl 2>&1 | tail -1; build; done
for r in 1 2; do echo "[d$r] alignment name repair round $r"; python3 -I fix_by_alignment.py rtc.log rt "rt/" "$ASM" 2>&1 | tail -1; build; done
if [ -s manual.jsonl ]; then echo "[m] replaying recorded manual edits"; python3 -I applyfixes.py rt manual.jsonl | tail -3; build; fi
echo done
