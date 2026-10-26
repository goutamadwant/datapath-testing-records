#!/usr/bin/env bash
# Runs inside the replay-clean container (started by run.sh). Clones the records repository at the
# requested commit, prepares a fresh copy of replay-2026-10-26 as its README describes (no Part A/B
# logs, no Part A/B setup records, no results.json; the historical Part C records are kept), runs
# replay.sh --part A --runs 5 and then replay.sh --part B, and copies every output to /out.
# Environment: RECORDS_URL, RECORDS_COMMIT, PARTS ("A B"), PART_A_TIMEOUT_S, PART_B_TIMEOUT_S.
set -u
OUT=/out
RECORDS_URL="${RECORDS_URL:-https://github.com/goutamadwant/datapath-testing-records.git}"
RECORDS_COMMIT="${RECORDS_COMMIT:?RECORDS_COMMIT is required}"
PARTS="${PARTS:-A B}"
PART_A_TIMEOUT_S="${PART_A_TIMEOUT_S:-5400}"
PART_B_TIMEOUT_S="${PART_B_TIMEOUT_S:-5400}"
SRC=/src/records
B="$SRC/replay-2026-10-26"
export REPLAY_WORK=/work REPLAY_MAVEN_REPO=/work/m2-partB
mkdir -p "$OUT/env" "$REPLAY_WORK"
CON="$OUT/container-console.txt"
log() { echo "# $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" | tee -a "$CON"; }

collect() {
  log "copying the bundle's logs and results.json to out/bundle"
  mkdir -p "$OUT/bundle"
  [ -d "$B/logs" ] && cp -a "$B/logs" "$OUT/bundle/"
  [ -f "$B/results.json" ] && cp -a "$B/results.json" "$OUT/bundle/results.json"
  { echo "# du -sh of work directories at the end"; du -sh "$REPLAY_WORK"/* 2>/dev/null; } > "$OUT/env/work-sizes.txt"
  log "container finished"
}
trap collect EXIT

log "container start; RECORDS_URL=$RECORDS_URL RECORDS_COMMIT=$RECORDS_COMMIT PARTS=$PARTS"
{
  echo "## uname -a"; uname -a
  echo "## /etc/os-release"; cat /etc/os-release
  echo "## nproc"; nproc
  echo "## memory (bytes)"; free -b
  echo "## user"; id
} > "$OUT/env/container-uname.txt" 2>&1
{
  echo "## JDK 8 ($JAVA8_HOME) from $JDK8_URL sha256 $JDK8_SHA256"
  "$JAVA8_HOME/bin/java" -version 2>&1; "$JAVA8_HOME/bin/javac" -version 2>&1
  file -L "$JAVA8_HOME/bin/java" | sed 's/.*: //'
  echo "## JDK 11 ($JAVA11_HOME) from $JDK11_URL sha256 $JDK11_SHA256"
  "$JAVA11_HOME/bin/java" -version 2>&1; "$JAVA11_HOME/bin/javac" -version 2>&1
  file -L "$JAVA11_HOME/bin/java" | sed 's/.*: //'
} > "$OUT/env/java-version.txt"
{
  python3 --version; git --version; curl --version | head -1; patch --version | head -1
  echo "bash $BASH_VERSION"; command -v wget >/dev/null && wget --version | head -1 || echo "wget not installed"
  echo "## dpkg-query -W"; dpkg-query -W -f '${Package} ${Version} ${Architecture}\n'
} > "$OUT/env/tools.txt" 2>&1

log "cloning $RECORDS_URL"
git clone -q "$RECORDS_URL" "$SRC" >> "$CON" 2>&1 || { log "FATAL: clone failed"; exit 4; }
git -C "$SRC" checkout -q --detach "$RECORDS_COMMIT" >> "$CON" 2>&1 || { log "FATAL: checkout $RECORDS_COMMIT failed"; exit 4; }
HEAD="$(git -C "$SRC" rev-parse HEAD)"
log "records repository at $HEAD"
case "$HEAD" in "$RECORDS_COMMIT"*) ;; *) log "FATAL: HEAD $HEAD is not $RECORDS_COMMIT"; exit 4 ;; esac
{
  echo "url=$RECORDS_URL"; echo "requested=$RECORDS_COMMIT"; echo "head=$HEAD"
  git -C "$SRC" log -1 --format='commit_date=%cI subject=%s'
  echo "## sha256 of the executed entry point and harness (as checked out)"
  (cd "$B" && sha256sum replay.sh harness/*.py harness/*.sh harness/*.patch harness/*.xml harness/java/*)
} > "$OUT/env/records-commit.txt"

# Fresh replay of Parts A and B, as replay-2026-10-26/README.md "Exact commands" describes.
log "fresh copy: removing logs/partA, logs/partB, the Part A/B files in logs/setup and results.json"
rm -rf "$B/logs/partA" "$B/logs/partB" "$B/results.json"
rm -f "$B"/logs/setup/*partA* "$B"/logs/setup/*partB*
git -C "$SRC" status --short > "$OUT/env/fresh-copy-git-status.txt"
log "removed $(grep -c . "$OUT/env/fresh-copy-git-status.txt") tracked files (list in env/fresh-copy-git-status.txt)"

cd "$B" || exit 2
RC_ALL=0
for P in $PARTS; do
  case "$P" in
    A) ARGS=(--part A --runs 5); TO="$PART_A_TIMEOUT_S" ;;
    B) ARGS=(--part B); TO="$PART_B_TIMEOUT_S" ;;
    *) log "unknown part $P"; exit 2 ;;
  esac
  log "start ./replay.sh ${ARGS[*]} (time box ${TO}s)"
  t0=$(date +%s)
  timeout --kill-after=60 "$TO" ./replay.sh "${ARGS[@]}" > "$OUT/console-part$P.txt" 2>&1
  rc=$?
  log "end ./replay.sh ${ARGS[*]} rc=$rc wall_seconds=$(( $(date +%s) - t0 ))$([ $rc = 124 ] && echo ' (time box reached; killed by timeout)')"
  [ $rc = 0 ] || RC_ALL=1
done
exit $RC_ALL
