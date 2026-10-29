#!/bin/bash
# usage: sh.sh <root> <rel-file-under-net/minecraft> <from> <to>
awk -v a=$3 -v b=$4 'NR>=a && NR<=b {gsub(/\/\* \$VF was: [^*]*\*\//,""); printf "%d: %s\n", NR, $0}' $1/net/minecraft/$2 | cut -c1-190
