#!/bin/bash
# delta -> ops -> apply to a copy of the vanilla decompile -> compile with the workspace's platform code -> bytecode-diff again
set -e
cd "$(dirname "$0")"; J=/home/user/jdks/jdk-17.0.21+9/bin; JP=libs/tool-javaparser-core-3.26.4.jar
python3 -I delta.py >/dev/null; python3 -I mktsv.py
$J/java -cp "$JP:tool" BundleExport /home/user/eagler-versions/eaglercraft-1.14-workspace/src/main/java delta.tsv ops.jsonl report.txt tops.txt 2>&1 | grep -v Picked
rm -rf patched rt rtout; mkdir patched rt rtout; cp -r dec2/net dec2/com patched/
$J/java -Xmx3g -cp "$JP:tool" BundleApply patched ops.jsonl apply-report.txt 2>&1 | grep -v Picked
cp -r patched/net patched/com rt/
W=/home/user/eagler-versions/eaglercraft-1.14-workspace/src; R=$PWD/rt
for d in $W/main/java $W/lwjgl/java; do (cd $d; find . -name '*.java' | grep -v -E '^\./(net/minecraft|com/mojang)/' | while read f; do mkdir -p "$R/$(dirname $f)"; cp "$f" "$R/$f"; done
  for p in com/mojang/brigadier com/mojang/authlib com/mojang/datafixers com/mojang/bridge; do [ -d $p ] && find $p -name '*.java' | while read f; do mkdir -p "$R/$(dirname $f)"; cp "$f" "$R/$f"; done; done; true); done
find rt -name '*.java' | grep -v PlatformWebRTC > rt.txt
# PlatformWebRTC needs webrtc-java which is on the classpath; keep it
find rt -name '*.java' > rt.txt
$J/javac -nowarn -proc:none -encoding UTF-8 --release 17 -XDstringConcat=inline -cp 'libs/*' -d rtout -Xmaxerrs 100000 @rt.txt > rtc.log 2>&1 || true
echo "compile errors: $(grep -c 'error:' rtc.log)"
