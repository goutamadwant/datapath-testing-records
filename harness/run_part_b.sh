#!/bin/bash
# Part B driver (reconstruction, 2026-10-25): PR 12472 stall injection on
# FileCollectReaderBehaviorTest.rediscoversFileAfterInactiveCursorClosed.
# Requires build_partB.sh to have run in both worktrees.
# usage: run_part_b.sh <cell> [<cell> ...]
#   cells: dev-hook-jdk8 dev-hook-jdk11 patch-hook-jdk8 patch-hook-jdk11
#          dev-nohook-contention-jdk8 dev-nohook-contention-jdk11
#          dev-hook-leadNN-jdk8 dev-hook-leadNN-jdk11   (sensitivity: stall NN ms before idleDeadlineMs)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
LOGS="$HERE/../logs/partB"
RT=<repo>/runtime/replay
JDK8=/Library/Java/JavaVirtualMachines/jdk1.8.0_172.jdk/Contents/Home
JDK11=<home>
MOD=seatunnel-edge-agent/seatunnel-edge-agent-connector
T=src/test/java/org/apache/seatunnel/edge/agent/connector/file/FileCollectReaderBehaviorTest.java
CLS=org.apache.seatunnel.edge.agent.connector.file.FileCollectReaderBehaviorTest
METHOD=rediscoversFileAfterInactiveCursorClosed
LAUNCHER=$HOME/.m2/repository/org/junit/platform/junit-platform-launcher/1.9.0/junit-platform-launcher-1.9.0.jar
mkdir -p "$LOGS" "$RT/partB/runner" "$RT/partB/classes"

modcp() { # <worktree>
  echo "$1/$MOD/target/test-classes:$1/$MOD/target/classes:$(cat "$1/$MOD/target/test-classpath.txt"):$LAUNCHER"
}

# Runner, compiled once with JDK 8.
if [ ! -f "$RT/partB/runner/RepeatMethod.class" ]; then
  "$JDK8/bin/javac" -cp "$(modcp "$RT/wt-dev")" -d "$RT/partB/runner" "$HERE/java/RepeatMethod.java" || exit 2
fi

hooked_classes() { # <worktree> <patch> <outdir>: apply the hook to a copy of the test, compile it
  local wt="$1" patch="$2" out="$3"
  rm -rf "$out" "$out.src"; mkdir -p "$out" "$out.src"
  cp "$wt/$MOD/$T" "$out.src/FileCollectReaderBehaviorTest.java"
  (cd "$out.src" && patch -s FileCollectReaderBehaviorTest.java < "$patch") || exit 3
  "$JDK8/bin/javac" -nowarn -source 8 -target 8 -cp "$(modcp "$wt")" -d "$out" \
      "$out.src/FileCollectReaderBehaviorTest.java" 2>&1 | grep -v "bootstrap classpath" || true
  [ -f "$out/org/apache/seatunnel/edge/agent/connector/file/FileCollectReaderBehaviorTest.class" ] || exit 4
}

run_cell() { # <cell> <worktree> <extra-classes-or-empty> <jdk> <iterations> <contention 0|N> [jvm props]
  local cell="$1" wt="$2" extra="$3" jdk="$4" n="$5" busy="$6"; shift 6
  local cp; cp="$RT/partB/runner:$(modcp "$wt")"
  [ -n "$extra" ] && cp="$extra:$cp"
  local log="$LOGS/$cell.txt"
  local pids=()
  {
    echo "# cell=$cell start=$(date '+%Y-%m-%dT%H:%M:%S%z') rev=$(git -C "$wt" rev-parse HEAD)"
    echo "# JAVA_HOME=$jdk iterations=$n busy_loops=$busy jvm_props=$*"
    echo "# hooked_test_classes=${extra:-none}"
    echo "# load_before: $(uptime)"
    echo "# command: $jdk/bin/java $* -cp <classpath below> RepeatMethod $CLS $METHOD $n"
    echo "# classpath: $cp"
  } > "$log"
  if [ "$busy" -gt 0 ]; then
    for i in $(seq 1 "$busy"); do ( while :; do :; done ) & pids+=($!); done
    echo "# busy-loop pids: ${pids[*]}" >> "$log"
    sleep 2
    echo "# load_with_busy_loops: $(uptime)" >> "$log"
  fi
  local t0=$(date +%s)
  "$jdk/bin/java" "$@" -cp "$cp" RepeatMethod "$CLS" "$METHOD" "$n" >> "$log" 2>&1
  local rc=$?
  [ "$busy" -gt 0 ] && kill "${pids[@]}" 2>/dev/null; wait 2>/dev/null
  echo "# exit=$rc wall_seconds=$(( $(date +%s) - t0 )) end=$(date '+%Y-%m-%dT%H:%M:%S%z')" >> "$log"
  echo "$cell: $(grep '^SUMMARY' "$log")"
}

for cell in "$@"; do
  case "$cell" in
    dev-hook-jdk8|dev-hook-jdk11|dev-hook-lead[0-9]*-jdk8|dev-hook-lead[0-9]*-jdk11)
      [ -d "$RT/partB/classes/dev-hook" ] || hooked_classes "$RT/wt-dev" "$HERE/hook-dev-deb16a3c3-stall45.patch" "$RT/partB/classes/dev-hook"
      jdk=$JDK8; [[ $cell == *jdk11 ]] && jdk=$JDK11
      props=""; [[ $cell =~ lead([0-9]+) ]] && props="-Dreplay.stall.lead.ms=${BASH_REMATCH[1]}"
      run_cell "$cell" "$RT/wt-dev" "$RT/partB/classes/dev-hook" "$jdk" 20 0 $props ;;
    patch-hook-jdk8|patch-hook-jdk11)
      [ -d "$RT/partB/classes/patch-hook" ] || hooked_classes "$RT/wt-patch" "$HERE/hook-patch-87ed0afe0-stalls.patch" "$RT/partB/classes/patch-hook"
      jdk=$JDK8; [[ $cell == *jdk11 ]] && jdk=$JDK11
      run_cell "$cell" "$RT/wt-patch" "$RT/partB/classes/patch-hook" "$jdk" 20 0 ;;
    dev-nohook-contention-jdk8|dev-nohook-contention-jdk11)
      jdk=$JDK8; [[ $cell == *jdk11 ]] && jdk=$JDK11
      run_cell "$cell" "$RT/wt-dev" "" "$jdk" 50 20 ;;
    *) echo "unknown cell $cell"; exit 1 ;;
  esac
done
