#!/bin/bash
# usage: fixpass.sh 112|114 — from a freshly patched tree: assemble, compile, run the fixers, compile again; one line per stage.
cd "$(dirname "$0")"; J=/home/user/jdks/jdk-17.0.21+9/bin
if [ "$1" = 112 ]; then
  W=/home/user/devevolperplus/eaglercraft-1.12-source; WSR="$W/src/main/java"; D=r112; PATCHED=r112/patched; VAN="net/minecraft/"; EXC="net/optifine/,shadersmod/"; CPJ=$(find $W/lib -name '*.jar' | tr '\n' ':')
  ASM="$WSR"
else
  WSR=/home/user/eagler-versions/eaglercraft-1.14-workspace/src/main/java; D=.; PATCHED=patched; VAN="net/minecraft/,com/mojang/blaze3d/,com/mojang/realmsclient/"; EXC=""; CPJ='libs/*'
  ASM="$WSR,$WSR/../../lwjgl/java"
fi
build() { (cd $D && rm -rf rtout && mkdir rtout && find rt -name '*.java' > rt.txt && $J/javac -J-Xmx3g -nowarn -proc:none -encoding UTF-8 --release 17 -XDstringConcat=inline -cp "$CPJ" -d rtout -Xmaxerrs 100000 @rt.txt > rtc.log 2>&1; echo "      javac errors: $(grep -c 'error:' rtc.log)"); }
echo "[a] assembling the compile tree from the freshly patched sources"
python3 -I mkrt.py "$ASM" $PATCHED $D/rt "$VAN" "$EXC"
echo "[b] compiling"; build
echo "[c0] removing imports javac cannot resolve"; python3 -I fix_bad_imports.py $D/rtc.log $D/rt "rt/" 2>&1 | tail -1; build
echo "[c] lambda-capture shift fixer (var0 -> var1 style)"; python3 -I fix_dangling_var.py $D/rtc.log $D/rt "rt/" 2>&1 | tail -1 ; build
for r in 1 2 3; do
  echo "[d$r] alignment fixer round $r (names only, from the workspace source)"; python3 -I fix_by_alignment.py $D/rtc.log $D/rt "rt/" "$ASM" 2>&1 | tail -2; build
done
echo "done"
