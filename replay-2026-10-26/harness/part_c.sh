#!/usr/bin/env bash
# Part C driver (bundle 2026-10-26): kill an engine container, call tearDown(), start a new
# container of the same engine and run fake_to_assert.conf (harness: java/ReplayKillTeardownTest).
# "after" = PR 12481 merge as built in work/wt-e2e; "before" = the same build with the four
# teardown classes of the parent compiled and placed first on the classpath.
# Called by ../replay.sh (exports REPLAY_BUNDLE, REPLAY_WORK, JAVA8_HOME, REV_C_BEFORE).
# usage: part_c.sh <runs> [cell ...]
#   cells: flink-before flink-after spark-before spark-after
# Per cell: one JVM runs <runs> kill/teardown/next-job cycles; the harness prints one ASSERT line
# per check; this script adds cell-level checks (JVM exit, no engine container left, time bound)
# and appends one JSON record per run to logs/partC/runs.jsonl.
set -u
B="$REPLAY_BUNDLE"; W="$REPLAY_WORK"
LOGS="$B/logs/partC"
WT="$W/wt-e2e"
MODDIR="$WT/seatunnel-e2e/seatunnel-connector-v2-e2e/connector-fake-e2e"
LAUNCHER="$W/lib/junit-platform-launcher-1.9.0.jar"
RUNS="${1:-5}"; shift
CELLS="$*"; [ -z "$CELLS" ] && CELLS="flink-before flink-after spark-before spark-after"
JOB_TIMEOUT_SEC=150
TEARDOWN_BOUND_SEC=60
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
    flink-before|flink-after) METHOD=flink118TaskManagerKilled; IMAGE=tyrantlucifer/flink:1.18.0-scala_2.12_hadoop27 ;;
    spark-before|spark-after) METHOD=spark3MasterKilled; IMAGE=tyrantlucifer/spark:3.3.0 ;;
    *) echo "unknown cell $cell"; exit 1 ;;
  esac
  REV=${cell#*-}
  CCP="$RUNNER:$HC:$CP"; [ "$REV" = before ] && CCP="$RUNNER:$HC:$OV/classes:$CP"
  # a repeated invocation writes <cell>-2.txt, <cell>-3.txt, ...; earlier logs are kept
  LOG="$LOGS/$cell.txt"; k=1
  while [ -e "$LOG" ]; do k=$((k + 1)); LOG="$LOGS/$cell-$k.txt"; done
  START="$(date '+%Y-%m-%dT%H:%M:%S%z')"
  {
    echo "# cell=$cell start=$START build_rev=$(git -C "$WT" rev-parse HEAD) runs=$RUNS"
    [ "$REV" = before ] && echo "# teardown classes from parent $REV_C_BEFORE first on the classpath"
    echo "# JAVA_HOME=$JAVA8_HOME cwd=<work>/wt-e2e/seatunnel-e2e/seatunnel-connector-v2-e2e/connector-fake-e2e"
    echo "# harness sha256: $(shasum -a 256 "$B/harness/java/ReplayKillTeardownTest.java" | cut -d' ' -f1)"
    echo "# docker: $(docker version --format '{{.Server.Version}} {{.Server.Os}}/{{.Server.Arch}}') image=$IMAGE id=$(docker image inspect --format '{{.Id}}' "$IMAGE")"
    echo "# load_before: $(uptime)"
    echo "# command: \$JAVA_HOME/bin/java -Dreplay.runs=$RUNS -Dreplay.jobTimeoutSec=$JOB_TIMEOUT_SEC -Dreplay.teardownBoundSec=$TEARDOWN_BOUND_SEC -cp <runner, harness classes, (before only) parent teardown classes, module test-classes/classes/test-classpath.txt, launcher> RepeatMethod org.apache.seatunnel.e2e.connector.fake.ReplayKillTeardownTest $METHOD 1"
  } > "$LOG"
  NETS_BEFORE="$(docker network ls -q | sort | tr '\n' ' ')"
  T0=$(date +%s)
  (cd "$MODDIR" && "$JAVA8_HOME/bin/java" -Dreplay.runs="$RUNS" -Dreplay.jobTimeoutSec=$JOB_TIMEOUT_SEC \
     -Dreplay.teardownBoundSec=$TEARDOWN_BOUND_SEC -cp "$CCP" RepeatMethod \
     org.apache.seatunnel.e2e.connector.fake.ReplayKillTeardownTest "$METHOD" 1) >> "$LOG" 2>&1
  RC=$?; WALL=$(( $(date +%s) - T0 ))
  echo "# exit=$RC wall_seconds=$WALL end=$(date '+%Y-%m-%dT%H:%M:%S%z')" >> "$LOG"
  # cell-level checks, executed by this script after the JVM has exited
  LEFT="$(docker ps -a --filter "ancestor=$IMAGE" --format '{{.ID}}:{{.Status}}' | tr '\n' ',')"
  chk() { echo "ASSERT-CELL $cell name=$1 result=$2 expected=$3 observed=$4" >> "$LOG"; }
  [ "$(grep -c '^ITER 1 PASS' "$LOG")" = 1 ] && chk harness_jvm_completed PASS ITER_1_PASS "rc=$RC" \
    || chk harness_jvm_completed FAIL ITER_1_PASS "rc=$RC"
  [ -z "$LEFT" ] && chk no_engine_container_after_cell PASS none none \
    || chk no_engine_container_after_cell FAIL none "$LEFT"
  sleep 15   # let the Testcontainers reaper remove its networks after the JVM exit
  NEW_NETS=""
  for n in $(docker network ls -q); do case " $NETS_BEFORE " in *" $n "*) ;; *) NEW_NETS="$NEW_NETS$n," ;; esac; done
  [ -z "$NEW_NETS" ] && chk no_new_docker_network_after_cell PASS none none \
    || chk no_new_docker_network_after_cell FAIL none "$NEW_NETS"
  BOUND=$(( RUNS * 600 ))
  [ "$WALL" -le "$BOUND" ] && chk cell_time_bound PASS "<=${BOUND}s" "${WALL}s" || chk cell_time_bound FAIL "<=${BOUND}s" "${WALL}s"
  [ -e /tmp/seatunnel_mnt ] && chk host_tmp_seatunnel_mnt_absent FAIL absent present \
    || chk host_tmp_seatunnel_mnt_absent PASS absent absent
  python3 "$B/harness/parse_part_c.py" "$LOG" "$cell" "$B" >> "$LOGS/runs.jsonl"
  echo "$cell: $(grep -c '^ASSERT .*result=PASS' "$LOG") PASS, $(grep -c '^ASSERT .*result=FAIL' "$LOG") FAIL assertions; wall ${WALL}s"
  # independence between cells: remove anything of this engine left behind
  for id in $(docker ps -aq --filter "ancestor=$IMAGE"); do docker rm -f "$id" >> "$LOG.cleanup.txt" 2>&1; done
done
