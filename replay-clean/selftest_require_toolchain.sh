#!/usr/bin/env bash
# Exercises replay.sh --require-toolchain in the replay-clean image (run after run.sh built it).
#
#   replay-clean/selftest_require_toolchain.sh
#
# Copies this checkout (mounted read-only) into a fresh container and runs, in a fresh copy of
# replay-2026-10-26 each time:
#   1. ./replay.sh --part A --prepare-only --require-toolchain ../replay-clean/toolchain.json
#      expected: every check matches, exit 0 (clones apache/seatunnel, downloads the Maven wrapper
#      distribution; no runs)
#   2. the same with a copy of toolchain.json whose enforce.jdk8_java_version names the JDK of the
#      published runs (Oracle 1.8.0_172); expected: exit 3 before anything is cloned
#   3. ./replay.sh --part B --prepare-only --require-toolchain ../replay-clean/toolchain.json is not
#      run here (it builds the module; the full replay in out/ covers the build)
# Output: replay-clean/out-selftest/ (consoles, the setup and toolchain records each case wrote, exit codes).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
OUT="$HERE/out-selftest"
[ -e "$OUT" ] && { echo "$OUT exists; move it away first" >&2; exit 2; }
mkdir -p "$OUT"
docker run --rm --platform linux/arm64 -v "$ROOT:/ro:ro" -v "$OUT:/out" --entrypoint bash replay-clean:arm64 -c '
set -u
log() { echo "# $(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a /out/selftest.txt; }
fresh() { rm -rf /src; mkdir -p /src; cp -a /ro/replay-2026-10-26 /ro/replay-clean /src/;
          rm -rf /src/replay-2026-10-26/work /src/replay-clean/out /src/replay-clean/out-selftest; }
log "replay.sh sha256 $(sha256sum /ro/replay-2026-10-26/replay.sh | cut -d" " -f1)"
log "toolchain.json sha256 $(sha256sum /ro/replay-clean/toolchain.json | cut -d" " -f1)"
fresh; cd /src/replay-2026-10-26
touch /src/.mark; sleep 1
log "case 1: matching manifest"
./replay.sh --part A --prepare-only --require-toolchain ../replay-clean/toolchain.json > /out/case1-console.txt 2>&1
log "case 1 exit=$? (expected 0)"
mkdir -p /out/case1-setup; find logs/setup -type f -newer /src/.mark -exec cp -a {} /out/case1-setup/ \; ; ls /out/case1-setup | sed "s/^/  case 1 wrote logs\/setup\//" >> /out/selftest.txt
fresh; cd /src/replay-2026-10-26
python3 - <<PY
import json
m = json.load(open("/src/replay-clean/toolchain.json"))
m["enforce"]["jdk8_java_version"] = "java version \"1.8.0_172\"\nJava(TM) SE Runtime Environment (build 1.8.0_172-b11)\nJava HotSpot(TM) 64-Bit Server VM (build 25.172-b11, mixed mode)"
json.dump(m, open("/src/toolchain-mismatch.json", "w"), indent=1)
PY
touch /src/.mark; sleep 1
log "case 2: manifest naming the JDK 8 of the published runs"
./replay.sh --part A --prepare-only --require-toolchain /src/toolchain-mismatch.json > /out/case2-console.txt 2>&1
log "case 2 exit=$? (expected 3); work/seatunnel cloned: $([ -d work/seatunnel ] && echo yes || echo no)"
mkdir -p /out/case2-setup; find logs/setup -type f -newer /src/.mark -exec cp -a {} /out/case2-setup/ \; ; ls /out/case2-setup | sed "s/^/  case 2 wrote logs\/setup\//" >> /out/selftest.txt
'
