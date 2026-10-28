# bcdiff: find what an Eaglercraft workspace changed in vanilla Minecraft

Text diffs against a fresh decompile are useless here: the workspaces were decompiled with another tool, so almost every
file differs in formatting, parameter names and lambdas. `bcdiff` compares **bytecode** instead.

1. Fetch the vanilla client jar at run time (never committed) and remap it to the workspace's MCP names
   (`mkmap.py` / `mkmap2.py` build the SRG->MCP mapping; `mkmap2.py` keeps the name each workspace class actually declares).
2. Compile the workspace sources with `javac --release 17 -XDstringConcat=inline`.
3. `BcSig` writes one line per member: `class<TAB>member<TAB>access size strictHash bagHash`. It drops line numbers,
   frames, checkcasts, local names and label numbers, treats invokespecial/invokevirtual/invokeinterface alike, collapses
   synthetic fields, and names lambdas by their body hash. `shims-<ver>.txt` maps Eaglercraft's JDK stand-ins
   (`net/lax1dude/eaglercraft/Random` and friends) back to the JDK class.
4. `compare.py` lists methods whose operand multiset (`bagHash`) differs, plus classes and members that exist on one side only.

`jd.py` shows the instruction-level difference for one method (for checking that a reported change is real).

Measured on the 1.14 workspace (2026-10-28): 35,148 vanilla methods, 28,755 identical, 2,927 changed, 3,466 vanilla-only,
1,831 workspace-only (before ignoring enum static initialisers). Not yet turned into a patch bundle.
