#!/usr/bin/env bash
# Part C driver (bundle 2026-10-26): kill an engine container, call tearDown(), start a new
# container of the same engine and run fake_to_assert.conf (harness: java/ReplayKillTeardownTest).
# "after" = PR 12481 merge as built in work/wt-e2e; "before" = the same build with the four
# teardown classes of the parent compiled and placed first on the classpath.
# Called by ../replay.sh (exports REPLAY_BUNDLE, REPLAY_WORK, JAVA8_HOME, REV_C_BEFORE).
# usage: part_c.sh <runs> [cell ...]
#   cells: flink-before flink-after spark-before spark-after
# Per cell: one JVM runs <runs> kill/teardown/next-job cycles; the harness prints one ASSERT line
# per check; this script adds cell-level checks and appends one JSON record per run to
# logs/partC/runs.jsonl.
#
# This is not a sandbox. It talks to the host's Docker daemon and the SeaTunnel teardown under
# test deletes the contents of the host path /tmp/seatunnel_mnt. Run it only on a host with no
# other SeaTunnel, Flink, Spark or Zeta containers. Safety rules enforced here:
#   - before every cell: refuse to start (exit 2) if /tmp/seatunnel_mnt exists, if Docker cannot
#     be listed, or if ANY container (running or stopped) of the engine images exists;
#   - after every cell: /tmp/seatunnel_mnt must be absent and no engine container may be left,
#     otherwise the cell FAILS and the script stops (exit 1) without starting further cells;
#   - cleanup removes a container only if it (i) did not exist before the cell, (ii) was created
#     at or after the cell's start time (docker inspect .Created), (iii) runs the cell's engine
#     image, and (iv) carries the Testcontainers session label of the cell's JVM (printed by the
#     harness). Every container considered and the decision are written to the cell log
#     (CLEANUP lines).
set -u
B="$REPLAY_BUNDLE"; W="$REPLAY_WORK"
LOGS="$B/logs/partC"
WT="$W/wt-e2e"
MODDIR="$WT/seatunnel-e2e/seatunnel-connector-v2-e2e/connector-fake-e2e"
LAUNCHER="$W/lib/junit-platform-launcher-1.9.0.jar"
RUNS="${1:-5}"; shift
case "$RUNS" in ''|*[!0-9]*|0) echo "part_c.sh: runs must be a positive integer (got '$RUNS')" >&2; exit 2 ;; esac
CELLS="$*"; [ -z "$CELLS" ] && CELLS="flink-before flink-after spark-before spark-after"
FLINK_IMAGE=tyrantlucifer/flink:1.18.0-scala_2.12_hadoop27
SPARK_IMAGE=tyrantlucifer/spark:3.3.0
ZETA_IMAGE=seatunnelhub/openjdk:8u342
ENGINE_IMAGES="$FLINK_IMAGE $SPARK_IMAGE $ZETA_IMAGE"
MNT=/tmp/seatunnel_mnt
JOB_TIMEOUT_SEC=150
TEARDOWN_BOUND_SEC=60

refuse() { echo "part_c.sh: refusing to start${CELL:+ cell $CELL}: $*" >&2; exit 2; }

# Full ids of all containers (any state) of the engine images, one per line. Matches both the
# ancestor filter (image present locally) and the image name the container was created from.
# Returns non-zero if Docker cannot be listed.
engine_containers() {
  local img out all
  out=""
  for img in $ENGINE_IMAGES; do
    all="$(docker ps -a --no-trunc --filter "ancestor=$img" --format '{{.ID}}')" || return 1
    out="$out$all"$'\n'
  done
  all="$(docker ps -a --no-trunc --format '{{.ID}} {{.Image}}')" || return 1
  while read -r id im; do
    [ -n "$id" ] || continue
    case " $ENGINE_IMAGES " in *" $im "*) out="$out$id"$'\n' ;; esac
  done <<< "$all"
  printf '%s' "$out" | sed '/^$/d' | sort -u
}

# epoch seconds of a Docker RFC 3339 timestamp, or nothing if it cannot be parsed
to_epoch() {
  python3 -I -c '
import datetime, re, sys
m = re.match(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(\.\d+)?(Z|[+-]\d\d:\d\d)$", sys.argv[1])
if m:
    t = datetime.datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S")
    off = datetime.timedelta(0)
    if m.group(3) != "Z":
        sign = 1 if m.group(3)[0] == "+" else -1
        off = sign * datetime.timedelta(hours=int(m.group(3)[1:3]), minutes=int(m.group(3)[4:6]))
    print(int((t - off).replace(tzinfo=datetime.timezone.utc).timestamp()))
' "$1"
}

# pre-start guard, run before the build steps and again before every cell
guard() {
  [ -e "$MNT" ] && refuse "$MNT exists on this host; the SeaTunnel teardown deletes its contents. Remove or rename it first."
  local existing
  existing="$(engine_containers)" || refuse "cannot list Docker containers (is the daemon reachable?)"
  if [ -n "$existing" ]; then
    refuse "containers of the engine images already exist (running or stopped): $(echo "$existing" | cut -c1-12 | tr '\n' ' ')
This replay must run on a host with no other SeaTunnel/Flink/Spark/Zeta containers, so that nothing
it inspects or removes can belong to someone else. Remove those containers or use another host."
  fi
}
CELL=""
guard

mkdir -p "$LOGS" "$W/partC"
CP="$MODDIR/target/test-classes:$MODDIR/target/classes:$(cat "$MODDIR/target/test-classpath.txt"):$LAUNCHER"

# RepeatMethod runner (shared with Part B)
RUNNER="$W/partC/runner"
if [ ! -f "$RUNNER/RepeatMethod.class" ]; then
  mkdir -p "$RUNNER"
  "$JAVA8_HOME/bin/javac" -nowarn -cp "$CP" -d "$RUNNER" "$B/harness/java/RepeatMethod.java" \
    > "$LOGS/compile-runner.txt" 2>&1
  [ -f "$RUNNER/RepeatMethod.class" ] || { echo "runner compile failed"; exit 2; }
fi
# "before" overrides: the four teardown classes from the PR 12481 parent
OV="$W/partC/before-overrides"
if [ ! -f "$OV/classes/.done" ]; then
  rm -rf "$OV"; mkdir -p "$OV/src" "$OV/classes"
  C=seatunnel-e2e/seatunnel-e2e-common/src/test/java/org/apache/seatunnel/e2e/common/container
  for f in AbstractTestContainer.java flink/AbstractTestFlinkContainer.java \
           spark/AbstractTestSparkContainer.java seatunnel/SeaTunnelContainer.java; do
    git -C "$WT" show "$REV_C_BEFORE:$C/$f" > "$OV/src/$(basename "$f")"
  done
  { echo "# javac (JDK 8) four teardown classes from $REV_C_BEFORE -> <work>/partC/before-overrides/classes"
    "$JAVA8_HOME/bin/javac" -nowarn -source 8 -target 8 -cp "$CP" -d "$OV/classes" "$OV"/src/*.java
    echo "# exit=$?"; } > "$LOGS/compile-before-overrides.txt" 2>&1
  grep -q '^# exit=0' "$LOGS/compile-before-overrides.txt" || { echo "override compile failed"; exit 3; }
  touch "$OV/classes/.done"
fi
# The harness is compiled from harness/java (the copy placed in the module only had to build)
HC="$W/partC/harness-classes"; rm -rf "$HC"; mkdir -p "$HC"
{ echo "# javac (JDK 8) harness/java/ReplayKillTeardownTest.java sha256=$(shasum -a 256 "$B/harness/java/ReplayKillTeardownTest.java" | cut -d' ' -f1)"
  "$JAVA8_HOME/bin/javac" -nowarn -source 8 -target 8 -cp "$CP" -d "$HC" "$B/harness/java/ReplayKillTeardownTest.java"
  echo "# exit=$?"; } > "$LOGS/compile-harness.txt" 2>&1
[ -f "$HC/org/apache/seatunnel/e2e/connector/fake/ReplayKillTeardownTest.class" ] || { echo "harness compile failed"; exit 4; }

for cell in $CELLS; do
  case "$cell" in
    flink-before|flink-after) METHOD=flink118TaskManagerKilled; IMAGE=$FLINK_IMAGE ;;
    spark-before|spark-after) METHOD=spark3MasterKilled; IMAGE=$SPARK_IMAGE ;;
    *) echo "unknown cell $cell"; exit 1 ;;
  esac
  CELL="$cell"
  guard
  REV=${cell#*-}
  CCP="$RUNNER:$HC:$CP"; [ "$REV" = before ] && CCP="$RUNNER:$HC:$OV/classes:$CP"
  # a repeated invocation writes <cell>-2.txt, <cell>-3.txt, ...; earlier logs are kept
  LOG="$LOGS/$cell.txt"; k=1
  while [ -e "$LOG" ]; do k=$((k + 1)); LOG="$LOGS/$cell-$k.txt"; done
  START_EPOCH=$(date +%s)
  START="$(date -r "$START_EPOCH" '+%Y-%m-%dT%H:%M:%S%z' 2>/dev/null || date -d "@$START_EPOCH" '+%Y-%m-%dT%H:%M:%S%z')"
  CONTAINERS_BEFORE=" $(docker ps -aq --no-trunc | tr '\n' ' ')"
  NETS_BEFORE="$(docker network ls -q | sort | tr '\n' ' ')"
  {
    echo "# cell=$cell start=$START build_rev=$(git -C "$WT" rev-parse HEAD) runs=$RUNS"
    [ "$REV" = before ] && echo "# teardown classes from parent $REV_C_BEFORE first on the classpath"
    echo "# JAVA_HOME=$JAVA8_HOME cwd=<work>/wt-e2e/seatunnel-e2e/seatunnel-connector-v2-e2e/connector-fake-e2e"
    echo "# harness sha256: $(shasum -a 256 "$B/harness/java/ReplayKillTeardownTest.java" | cut -d' ' -f1)"
    echo "# driver sha256: $(shasum -a 256 "$B/harness/part_c.sh" | cut -d' ' -f1)"
    echo "# docker: $(docker version --format '{{.Server.Version}} {{.Server.Os}}/{{.Server.Arch}}') image=$IMAGE id=$(docker image inspect --format '{{.Id}}' "$IMAGE")"
    echo "# pre-cell guard: $MNT absent; no container of $ENGINE_IMAGES; containers present before the cell: $(echo $CONTAINERS_BEFORE | wc -w | tr -d ' ') (start epoch $START_EPOCH)"
    echo "# load_before: $(uptime)"
    echo "# command: \$JAVA_HOME/bin/java -Dreplay.runs=$RUNS -Dreplay.jobTimeoutSec=$JOB_TIMEOUT_SEC -Dreplay.teardownBoundSec=$TEARDOWN_BOUND_SEC -cp <runner, harness classes, (before only) parent teardown classes, module test-classes/classes/test-classpath.txt, launcher> RepeatMethod org.apache.seatunnel.e2e.connector.fake.ReplayKillTeardownTest $METHOD 1"
  } > "$LOG"
  T0=$(date +%s)
  (cd "$MODDIR" && "$JAVA8_HOME/bin/java" -Dreplay.runs="$RUNS" -Dreplay.jobTimeoutSec=$JOB_TIMEOUT_SEC \
     -Dreplay.teardownBoundSec=$TEARDOWN_BOUND_SEC -cp "$CCP" RepeatMethod \
     org.apache.seatunnel.e2e.connector.fake.ReplayKillTeardownTest "$METHOD" 1) >> "$LOG" 2>&1
  RC=$?; WALL=$(( $(date +%s) - T0 ))
  echo "# exit=$RC wall_seconds=$WALL end=$(date '+%Y-%m-%dT%H:%M:%S%z')" >> "$LOG"
  # cell-level checks, executed by this script after the JVM has exited
  FAILED=""
  chk() {
    echo "ASSERT-CELL $cell name=$1 result=$2 expected=$3 observed=$4" >> "$LOG"
    [ "$2" = PASS ] || FAILED="$FAILED$1,"
  }
  if [ "$RC" = 0 ] && [ "$(grep -c '^ITER 1 PASS' "$LOG")" = 1 ]; then
    chk harness_jvm_completed PASS ITER_1_PASS "rc=$RC"
  else
    chk harness_jvm_completed FAIL ITER_1_PASS "rc=$RC"
  fi
  if LEFT_IDS="$(engine_containers)"; then
    LEFT="$(for id in $LEFT_IDS; do docker ps -a --filter "id=$id" --format '{{.ID}}:{{.Status}}'; done | tr '\n' ',')"
  else
    LEFT="docker-list-error"
  fi
  [ -z "$LEFT" ] && chk no_engine_container_after_cell PASS none none \
    || chk no_engine_container_after_cell FAIL none "$LEFT"
  sleep 15   # let the Testcontainers reaper remove its networks after the JVM exit
  NEW_NETS=""
  for n in $(docker network ls -q); do case " $NETS_BEFORE " in *" $n "*) ;; *) NEW_NETS="$NEW_NETS$n," ;; esac; done
  [ -z "$NEW_NETS" ] && chk no_new_docker_network_after_cell PASS none none \
    || chk no_new_docker_network_after_cell FAIL none "$NEW_NETS"
  BOUND=$(( RUNS * 600 ))
  [ "$WALL" -le "$BOUND" ] && chk cell_time_bound PASS "<=${BOUND}s" "${WALL}s" || chk cell_time_bound FAIL "<=${BOUND}s" "${WALL}s"
  [ -e "$MNT" ] && chk host_tmp_seatunnel_mnt_absent FAIL absent present \
    || chk host_tmp_seatunnel_mnt_absent PASS absent absent

  # cleanup: consider every container of the engine images; remove only those positively
  # attributable to this cell (rules i-iv in the header); log each decision
  SESSION="$(sed -n 's/^RESULT testcontainers_session=\([0-9a-fA-F-]*\)$/\1/p' "$LOG" | tail -1)"
  echo "# cleanup: start_epoch=$START_EPOCH image=$IMAGE session=${SESSION:-none}" >> "$LOG"
  if CANDIDATES="$(engine_containers)"; then
    for id in $CANDIDATES; do
      img="$(docker inspect -f '{{.Config.Image}}' "$id" 2>/dev/null)"
      created="$(docker inspect -f '{{.Created}}' "$id" 2>/dev/null)"
      label="$(docker inspect -f '{{index .Config.Labels "org.testcontainers.sessionId"}}' "$id" 2>/dev/null)"
      cep="$(to_epoch "$created")"
      why=""
      case "$CONTAINERS_BEFORE" in *" $id "*) why="${why}existed_before_cell," ;; esac
      if [ -z "$cep" ]; then why="${why}created_unparsable,"; elif [ "$cep" -lt "$START_EPOCH" ]; then why="${why}created_before_cell_start,"; fi
      [ "$img" = "$IMAGE" ] || why="${why}not_cell_engine_image,"
      { [ -n "$SESSION" ] && [ "$label" = "$SESSION" ]; } || why="${why}session_label_mismatch,"
      if [ -z "$why" ]; then
        if out="$(docker rm -f "$id" 2>&1)"; then res=removed; else res="remove_failed:$(echo "$out" | tr ' \n' '__' | cut -c1-200)"; fi
        echo "CLEANUP $cell id=${id:0:12} image=$img created=$created session=$label decision=remove result=$res" >> "$LOG"
      else
        echo "CLEANUP $cell id=${id:0:12} image=$img created=$created session=${label:-none} decision=keep reasons=${why%,}" >> "$LOG"
      fi
    done
    REMAIN="$(engine_containers | cut -c1-12 | tr '\n' ',')"
  else
    echo "CLEANUP $cell docker-list-error: nothing removed" >> "$LOG"
    REMAIN="docker-list-error"
  fi
  [ -z "$REMAIN" ] && chk no_engine_container_after_cleanup PASS none none \
    || chk no_engine_container_after_cleanup FAIL none "$REMAIN"

  if [ -z "$FAILED" ]; then echo "# cell_result=PASS" >> "$LOG"; else echo "# cell_result=FAIL failed_checks=${FAILED%,}" >> "$LOG"; fi
  python3 "$B/harness/parse_part_c.py" "$LOG" "$cell" "$B" >> "$LOGS/runs.jsonl" \
    || FAILED="${FAILED}records_incomplete,"
  echo "$cell: $(grep -c '^ASSERT .*result=PASS' "$LOG") PASS, $(grep -c '^ASSERT .*result=FAIL' "$LOG") FAIL assertions; wall ${WALL}s"
  if [ -n "$FAILED" ]; then
    echo "part_c.sh: cell $cell FAILED (${FAILED%,}); not starting further cells. See ${LOG#$B/}" >&2
    exit 1
  fi
done
