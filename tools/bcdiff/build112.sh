#!/bin/bash
cd "$(dirname "$0")/r112"; J=/home/user/jdks/jdk-17.0.21+9/bin; W=/home/user/devevolperplus/eaglercraft-1.12-source; CPJ=$(find $W/lib -name '*.jar' | tr '\n' ':')
rm -rf rtout && mkdir rtout && find rt -name '*.java' > rt.txt && $J/javac -J-Xmx3g -nowarn -proc:none -encoding UTF-8 --release 17 -XDstringConcat=inline -cp "$CPJ" -d rtout -Xmaxerrs 100000 @rt.txt > rtc.log 2>&1; echo "javac errors: $(grep -c 'error:' rtc.log)"
