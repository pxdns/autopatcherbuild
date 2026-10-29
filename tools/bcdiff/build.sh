#!/bin/bash
# usage: build.sh  — compile rt/ and print the error count (1.14)
cd "$(dirname "$0")"; J=/home/user/jdks/jdk-17.0.21+9/bin
rm -rf rtout && mkdir rtout && find rt -name '*.java' > rt.txt && $J/javac -J-Xmx3g -nowarn -proc:none -encoding UTF-8 --release 17 -XDstringConcat=inline -cp 'libs/*' -d rtout -Xmaxerrs 100000 @rt.txt > rtc.log 2>&1; echo "javac errors: $(grep -c 'error:' rtc.log)"
