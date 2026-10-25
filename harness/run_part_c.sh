#!/bin/bash
# Part C runner (reconstruction, 2026-10-25): kill an engine container, call tearDown(), start a
# new container of the same engine and run fake_to_assert.conf (harness: ReplayKillTeardownTest).
# "after" = PR 12481 merge 0e4cf5289 as built; "before" = the same build with the four
# teardown classes of the parent 7ba68325c compiled and placed first on the classpath.
# usage: run_part_c.sh <before|after> <flink118TaskManagerKilled|spark3MasterKilled> <runs>
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
LOGS="$HERE/../logs/partC"
RT=<repo>/runtime/replay
WT=$RT/wt-e2e
JDK8=/Library/Java/JavaVirtualMachines/jdk1.8.0_172.jdk/Contents/Home
MODDIR=$WT/seatunnel-e2e/seatunnel-connector-v2-e2e/connector-fake-e2e
LAUNCHER=$HOME/.m2/repository/org/junit/platform/junit-platform-launcher/1.9.0/junit-platform-launcher-1.9.0.jar
PARENT=7ba68325cb7ea1bf1a28f56c4f9c20695d221df3
REV="$1"; METHOD="$2"; RUNS="$3"
CP="$MODDIR/target/test-classes:$MODDIR/target/classes:$(cat "$MODDIR/target/test-classpath.txt"):$LAUNCHER"
if [ "$REV" = before ]; then
  OV=$RT/partC/before-overrides
  if [ ! -d "$OV/classes" ]; then
    mkdir -p "$OV/src" "$OV/classes"
    C=seatunnel-e2e/seatunnel-e2e-common/src/test/java/org/apache/seatunnel/e2e/common/container
    for f in AbstractTestContainer.java flink/AbstractTestFlinkContainer.java \
             spark/AbstractTestSparkContainer.java seatunnel/SeaTunnelContainer.java; do
      git -C "$WT" show "$PARENT:$C/$f" > "$OV/src/$(basename "$f")"
    done
    "$JDK8/bin/javac" -nowarn -source 8 -target 8 -cp "$CP" -d "$OV/classes" "$OV"/src/*.java || exit 3
  fi
  CP="$OV/classes:$CP"
fi
# Compile the current harness source (harness/java/ReplayKillTeardownTest.java) ahead of the copy
# that build_partC.sh placed in the module, so harness edits do not need a full rebuild.
HC=$RT/partC/harness-classes; rm -rf "$HC"; mkdir -p "$HC"
"$JDK8/bin/javac" -nowarn -source 8 -target 8 -cp "$CP" -d "$HC" "$HERE/java/ReplayKillTeardownTest.java" 2>&1 | grep -v "bootstrap classpath"
[ -f "$HC/org/apache/seatunnel/e2e/connector/fake/ReplayKillTeardownTest.class" ] || exit 4
CP="$RT/partB/runner:$HC:$CP"
LOG="$LOGS/$METHOD-$REV.txt"
[ -e "$LOG" ] && LOG="$LOGS/$METHOD-$REV-$(date +%H%M%S).txt"
{
  echo "# start=$(date '+%Y-%m-%dT%H:%M:%S%z') rev_label=$REV build_rev=$(git -C "$WT" rev-parse HEAD) runs=$RUNS"
  [ "$REV" = before ] && echo "# teardown classes from parent $PARENT compiled into $RT/partC/before-overrides/classes (first on classpath)"
  echo "# JAVA_HOME=$JDK8 cwd=$MODDIR"
  echo "# harness sha256: $(shasum -a 256 "$HERE/java/ReplayKillTeardownTest.java" | cut -d' ' -f1)"
  echo "# docker: $(docker version --format '{{.Server.Version}} {{.Server.Os}}/{{.Server.Arch}}')"
  echo "# command: java -Dreplay.runs=$RUNS -cp <cp> RepeatMethod org.apache.seatunnel.e2e.connector.fake.ReplayKillTeardownTest $METHOD 1"
} > "$LOG"
cd "$MODDIR" && "$JDK8/bin/java" -Dreplay.runs="$RUNS" -cp "$CP" RepeatMethod \
  org.apache.seatunnel.e2e.connector.fake.ReplayKillTeardownTest "$METHOD" 1 >> "$LOG" 2>&1
echo "# exit=$? end=$(date '+%Y-%m-%dT%H:%M:%S%z')" >> "$LOG"
grep -E "^RESULT|^ITER|^SUMMARY" "$LOG"
