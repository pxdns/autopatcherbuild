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

## Round 2 (2026-10-28): renames, declared exceptions, OptiFine split, enum constants

What was added, and why (each fixed a measured problem):

- `mkrename.py`: the workspaces use older MCP name sets than the vanilla remap, so the same field or method had two names
  (`mcProfiler` vs `profiler`). It pairs members that only one side names, by type (fields) or identical bytecode (methods),
  writes an SRG-style rename map, and the vanilla jar is remapped again (two rounds). 1.12: 86 field and 163 method renames;
  the operation count fell from 3,066 to 1,803.
- `BcSig` now includes declared exceptions in the method hash. Without it, a removed `throws IOException` was invisible.
- `BundleExport`/`BundleApply`: enum constants (`enum-constants-replace`), imports are added without JavaParser's "redundant
  import" removal (it deleted the explicit import that settles a `MathHelper` clash), imports of deleted classes are removed.
- `mktsv.py`: drops a method delete when a method with the same name and parameters survives in the workspace (a bridge method
  with another return type made the delete remove the real method); same for fields.
- `filter_nonvanilla.py`: sets aside every operation that mentions OptiFine or shader classes (`net/minecraft/src`,
  `net/optifine`, `shadersmod`), so they never enter a bundle. 1.12: 189 operations set aside, mostly `Config` and `Reflector`.
- `mkrt.py` assembles the compile tree (patched vanilla + the workspace's own platform code); `errgroups.py` groups javac errors
  with one example each; `fix_dangling_var.py` repairs Vineflower's lambda-capture numbering from javac's own messages.
- `run112.sh` / `run114.sh` run the whole pipeline with one plain line per step. They contain scratch-folder paths: adjust before reuse.

Measured state:

| Version | Operations kept | Applied | Compile errors left |
| --- | --- | --- | --- |
| 1.12 (OptiFine and shaders left out) | 1,736 | 1,596, 0 failed | 170 |
| 1.14 | 4,313 | 4,006, 2 failed | 1,073 |

What the remaining errors are: decompiler damage in unchanged vanilla code, mainly captured variables in anonymous classes and
constructors written under the wrong names (`var6` where the enclosing method has another name), and wrong local types. These
need per-case rewrites recorded as scripted fixes (like the 26.3 `compile-fixes.json`); they cannot be copied from the
workspace because that would put game text into the bundle. Tried and rejected: Vineflower `-lac=1` (lambdas to anonymous
classes) raised 1.14 errors to 6,545 and broke 1,510 operations.

Not done: zero-error compile, then a bytecode comparison of the compiled patched tree against the workspace, a skeleton and a
build for either version, any browser test. The 1.12 workspace has no web build at all (its README says so).
