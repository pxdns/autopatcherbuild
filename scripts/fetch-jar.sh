#!/bin/bash
# Downloads the official Minecraft client jar for a version from Mojang and checks its SHA-1.
# Usage: scripts/fetch-jar.sh [version]   (default 26.3)   Output: build-inputs/minecraft-<version>-client.jar
# The jar is Mojang's and is never committed (build-inputs/ is in .gitignore).
set -euo pipefail
VERSION="${1:-26.3}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/build-inputs/minecraft-$VERSION-client.jar"
mkdir -p "$ROOT/build-inputs"
read -r URL SHA1 < <(python3 -I - "$VERSION" <<'PY'
import json, sys, urllib.request
v = sys.argv[1]
get = lambda u: json.load(urllib.request.urlopen(u, timeout=60))
manifest = get("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
entry = next((e for e in manifest["versions"] if e["id"] == v), None)
if entry is None:
    sys.exit("version %s is not in Mojang's manifest (latest release: %s, latest snapshot: %s)" % (v, manifest["latest"]["release"], manifest["latest"]["snapshot"]))
client = get(entry["url"])["downloads"]["client"]
print(client["url"], client["sha1"])
PY
)
if [ -f "$OUT" ] && [ "$(sha1sum "$OUT" | cut -d' ' -f1)" = "$SHA1" ]; then
  echo "already have $OUT"; exit 0
fi
curl -fsSL --retry 3 -o "$OUT.part" "$URL"
GOT="$(sha1sum "$OUT.part" | cut -d' ' -f1)"
[ "$GOT" = "$SHA1" ] || { echo "SHA-1 mismatch: expected $SHA1, got $GOT" >&2; rm -f "$OUT.part"; exit 1; }
mv "$OUT.part" "$OUT"
echo "ok $OUT ($SHA1)"
