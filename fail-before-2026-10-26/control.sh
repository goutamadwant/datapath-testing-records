#!/usr/bin/env bash
# Runs the two guarded SeaTunnel Flink cases of the fail-before harness inside a disposable
# linux/arm64 container with no host-path mounts; outputs are copied out with docker cp afterwards.
set -u
NAME=failbefore-control-$(date -u +%Y%m%dT%H%M%SZ)
OUT=${1:?outdir}
mkdir -p "$OUT"
echo "container $NAME start $(date -u +%FT%TZ)" | tee "$OUT/host.txt"
docker run --platform linux/arm64 --name "$NAME" --entrypoint bash \
  -e FAILBEFORE_DISPOSABLE=1 -e JAVA8_HOME=/opt/jdk8 -e JAVA_HOME=/opt/jdk8 \
  -e FAILBEFORE_WORK=/work -e MAVEN_OPTS=-Dmaven.repo.local=/work/m2 -e TZ=UTC \
  replay-clean:arm64 -c '
set -u
echo "# $(date -u +%FT%TZ) uname: $(uname -srm)"; ls -la /tmp/seatunnel_mnt 2>&1 | head -1
git clone -q https://github.com/goutamadwant/datapath-testing-records.git /src/records && \
git -C /src/records checkout -q b9596a33327c07277bb803a0859835a5d40a0a02 && \
cd /src/records/fail-before-2026-10-26 || exit 3
echo "# records HEAD $(git rev-parse HEAD)"
mkdir -p /work
./run.sh st12481-shim st12481-shim-both; rc=$?
echo "# run.sh exit $rc $(date -u +%FT%TZ)"
python3 make_results.py; echo "# make_results exit $? $(date -u +%FT%TZ)"
ls -la /tmp/seatunnel_mnt 2>&1 | head -1
exit $rc
' > "$OUT/container-console.txt" 2>&1
RC=$?
echo "container exit $RC $(date -u +%FT%TZ)" | tee -a "$OUT/host.txt"
docker cp "$NAME":/src/records/fail-before-2026-10-26/logs "$OUT/logs"
docker cp "$NAME":/src/records/fail-before-2026-10-26/results.json "$OUT/results.json"
docker cp "$NAME":/work/setup-* "$OUT/" 2>/dev/null
docker rm "$NAME" >/dev/null
echo "copied $(date -u +%FT%TZ)" | tee -a "$OUT/host.txt"
