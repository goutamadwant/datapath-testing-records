#!/usr/bin/env bash
# Clean-environment replay of replay-2026-10-26 (Parts A and B) in a disposable linux/arm64 container.
#
#   replay-clean/run.sh [<records commit>]        default commit: d059baf95c8a21850a0b5d9d08ef07128d636ed2
#
# Builds the image from replay-clean/Dockerfile, starts one fresh container (removed afterwards) that
# clones this repository from GitHub at the commit, and runs, in order,
#   ./replay.sh --part A --runs 5
#   ./replay.sh --part B
# in a fresh copy of replay-2026-10-26 (see in_container.sh). Everything is written to replay-clean/out/:
#   out/host.txt              host, Docker version, image id and base digest, command, start/end
#   out/image-build.txt       docker build output
#   out/env/                  container uname, java -version of both JDKs, tool and package versions,
#                             records commit and sha256 of the executed scripts, work sizes
#   out/console-part{A,B}.txt replay.sh consoles; out/container-console.txt the container's own log
#   out/bundle/               the replay's logs/ and the regenerated results.json
# Environment: PARTS ("A B"), PART_A_TIMEOUT_S, PART_B_TIMEOUT_S (default 5400 each),
#              RECORDS_URL (default https://github.com/goutamadwant/datapath-testing-records.git).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
COMMIT="${1:-d059baf95c8a21850a0b5d9d08ef07128d636ed2}"
OUT="$HERE/out"
IMAGE=replay-clean:arm64
NAME="replay-clean-$(date +%Y%m%dT%H%M%S)"
[ -e "$OUT" ] && { echo "$OUT exists; move it away first (outputs are never overwritten)" >&2; exit 2; }
mkdir -p "$OUT"
H="$OUT/host.txt"
stamp() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
{
  echo "# run.sh start $(stamp) commit=$COMMIT container=$NAME"
  echo "## host uname -a"; uname -a
  (sysctl -n machdep.cpu.brand_string hw.ncpu hw.memsize 2>/dev/null || nproc) | tr '\n' ' '; echo
  sw_vers 2>/dev/null || true
  echo "## docker"; docker version --format 'client {{.Client.Version}} server {{.Server.Version}} {{.Server.Os}}/{{.Server.Arch}}'
  docker info --format 'ncpu={{.NCPU}} mem_bytes={{.MemTotal}} os={{.OperatingSystem}} kernel={{.KernelVersion}}'
  echo "## sha256 of the files that define the image and the run"
  (cd "$HERE" && shasum -a 256 Dockerfile in_container.sh run.sh)
} > "$H" 2>&1

echo "# docker build start $(stamp)" > "$OUT/image-build.txt"
docker build --platform linux/arm64 --progress plain --pull -t "$IMAGE" "$HERE" >> "$OUT/image-build.txt" 2>&1 \
  || { echo "image build failed (out/image-build.txt)" | tee -a "$H"; exit 3; }
echo "# docker build end $(stamp)" >> "$OUT/image-build.txt"
{
  echo "## image"
  docker image inspect "$IMAGE" --format 'image_id={{.Id}} os={{.Os}} arch={{.Architecture}} created={{.Created}}'
  echo "base=$(sed -n 's/^FROM .* \(ubuntu:[^ ]*\)$/\1/p' "$HERE/Dockerfile")"
} >> "$H"

echo "## docker run start $(stamp)" >> "$H"
echo "+ docker run --rm --platform linux/arm64 --name $NAME -v <replay-clean>/out:/out -e RECORDS_COMMIT=$COMMIT -e PARTS -e PART_A_TIMEOUT_S -e PART_B_TIMEOUT_S -e RECORDS_URL $IMAGE" >> "$H"
docker run --rm --platform linux/arm64 --name "$NAME" -v "$OUT:/out" \
  -e RECORDS_COMMIT="$COMMIT" -e PARTS="${PARTS:-A B}" \
  -e PART_A_TIMEOUT_S="${PART_A_TIMEOUT_S:-5400}" -e PART_B_TIMEOUT_S="${PART_B_TIMEOUT_S:-5400}" \
  -e RECORDS_URL="${RECORDS_URL:-https://github.com/goutamadwant/datapath-testing-records.git}" \
  "$IMAGE"
RC=$?
echo "## docker run end $(stamp) exit=$RC" >> "$H"
exit $RC
