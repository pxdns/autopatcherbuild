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

## Turning the diff into patch operations (2026-10-28, 1.14)

- `delta.py` lists changed, added and removed classes and members. `mktsv.py` turns that into rows and decides when a whole
  file is replaced (more than half its methods changed, or its class header changed).
- `BundleExport` (JavaParser) reads the changed members' source from the workspace and writes `ops.jsonl`: `method-replace`,
  `method-add`, `method-delete`, `field-add`, `field-delete`, `initializers-replace`, `imports`, `replace-file`, `add-file`,
  `delete-class`. Members of anonymous classes are mapped to the member that creates them. 65 spots were not resolved
  (anonymous classes it could not locate, ambiguous overloads) and are listed in `report.txt`.
- `BundleApply` applies the operations to a fresh decompile of the vanilla jar.
- `run-pipeline.sh` runs all of it and compiles the patched tree together with the workspace's platform code.

State: 4,493 operations; 4,192 apply cleanly. The patched tree still has about 1,576 compile errors, mostly decompiler
leftovers (variable names, ambiguous imports, UUID/`EaglercraftUUID` call sites), so the patched tree has not yet been
compiled and compared against the workspace. The operations carry method bodies that contain vanilla code, so the
bundle stays private and goes through the leak scan before anything is published.
