#!/usr/bin/env bash
# Part B driver (bundle 2026-10-26): PR 12472 stall injection on
# FileCollectReaderBehaviorTest.rediscoversFileAfterInactiveCursorClosed.
# Called by ../replay.sh after the two worktrees are built (exports REPLAY_BUNDLE, REPLAY_WORK,
# JAVA8_HOME, JAVA11_HOME).
# usage: part_b.sh <loops> [cell ...]
#   cells: dev-hook-jdk8 dev-hook-jdk11 patch-hook-jdk8 patch-hook-jdk11
#          dev-hook-lead45|55|65-jdk8|jdk11      (sensitivity sweep: stall <= NN ms before idleDeadlineMs)
#          dev-nohook-contention-jdk8 dev-nohook-contention-jdk11
# Each cell is one JVM running the method 20 times (50 for the contention cells) through the JUnit
# Platform launcher; <loops> repeats that per cell. One JSON record per loop -> logs/partB/runs.jsonl.
set -u
B="$REPLAY_BUNDLE"; W="$REPLAY_WORK"
LOGS="$B/logs/partB"
MOD=seatunnel-edge-agent/seatunnel-edge-agent-connector
T=src/test/java/org/apache/seatunnel/edge/agent/connector/file/FileCollectReaderBehaviorTest.java
CLS=org.apache.seatunnel.edge.agent.connector.file.FileCollectReaderBehaviorTest
METHOD=rediscoversFileAfterInactiveCursorClosed
LAUNCHER="$W/lib/junit-platform-launcher-1.9.0.jar"
LOOPS="${1:-1}"; shift
CELLS="$*"
[ -z "$CELLS" ] && CELLS="dev-hook-jdk8 dev-hook-jdk11 patch-hook-jdk8 patch-hook-jdk11 dev-hook-lead45-jdk8 dev-hook-lead45-jdk11 dev-hook-lead55-jdk8 dev-hook-lead55-jdk11 dev-hook-lead65-jdk8 dev-hook-lead65-jdk11 dev-nohook-contention-jdk8 dev-nohook-contention-jdk11"
mkdir -p "$LOGS" "$W/partB/runner" "$W/partB/classes"
relp() { echo "${1#$B/}"; }

modcp() { # <worktree>
  echo "$1/$MOD/target/test-classes:$1/$MOD/target/classes:$(cat "$1/$MOD/target/test-classpath.txt"):$LAUNCHER"
}

# Runner, compiled once with JDK 8 (log: logs/partB/compile-runner.txt)
if [ ! -f "$W/partB/runner/RepeatMethod.class" ]; then
  { echo "# javac (JDK 8) -cp <wt-dev test classpath> -d <work>/partB/runner harness/java/RepeatMethod.java"
    "$JAVA8_HOME/bin/javac" -cp "$(modcp "$W/wt-dev")" -d "$W/partB/runner" "$B/harness/java/RepeatMethod.java"
    echo "# exit=$?"; } > "$LOGS/compile-runner.txt" 2>&1
  [ -f "$W/partB/runner/RepeatMethod.class" ] || { echo "runner compile failed"; exit 2; }
fi

hooked_classes() { # <worktree> <patch> <name>: apply the hook to a copy of the test, compile it
  local wt="$1" patch="$2" name="$3" out="$W/partB/classes/$3"
  rm -rf "$out" "$out.src"; mkdir -p "$out" "$out.src"
  cp "$wt/$MOD/$T" "$out.src/FileCollectReaderBehaviorTest.java"
  {
    echo "# hook $(basename "$patch") applied to work/$(basename "$wt")/$MOD/$T (copy), compiled with JDK 8"
    (cd "$out.src" && patch FileCollectReaderBehaviorTest.java < "$patch")
    "$JAVA8_HOME/bin/javac" -nowarn -source 8 -target 8 -cp "$(modcp "$wt")" -d "$out" \
        "$out.src/FileCollectReaderBehaviorTest.java"
    echo "# exit=$?"
  } > "$LOGS/compile-$name.txt" 2>&1
  [ -f "$out/org/apache/seatunnel/edge/agent/connector/file/FileCollectReaderBehaviorTest.class" ] || exit 4
}

run_cell() { # <cell> <loop> <worktree> <extra-classes-or-empty> <jdk> <iterations> <busy loops> [jvm props]
  local cell="$1" loop="$2" wt="$3" extra="$4" jdk="$5" n="$6" busy="$7"; shift 7
  local cp; cp="$W/partB/runner:$(modcp "$wt")"
  [ -n "$extra" ] && cp="$extra:$cp"
  mkdir -p "$LOGS/$cell"
  local log="$LOGS/$cell/loop$loop.txt"
  [ -e "$log" ] && mv "$log" "$log.interrupted-$(date +%s)"
  local pids=() start; start="$(date '+%Y-%m-%dT%H:%M:%S%z')"
  {
    echo "# cell=$cell loop=$loop start=$start rev=$(git -C "$wt" rev-parse HEAD)"
    echo "# JAVA_HOME=$jdk iterations=$n busy_loops=$busy jvm_props=$*"
    if [ -n "$extra" ]; then echo "# hooked_test_classes=<work>/partB/classes/$(basename "$extra")"; else echo "# hooked_test_classes=none"; fi
    echo "# load_before: $(uptime)"
    echo "# command: \$JAVA_HOME/bin/java $* -cp <classpath: hooked classes, runner, module test-classes, classes, test-classpath.txt, launcher> RepeatMethod $CLS $METHOD $n"
  } > "$log"
  if [ "$busy" -gt 0 ]; then
    for i in $(seq 1 "$busy"); do ( while :; do :; done ) & pids+=($!); done
    sleep 2
    echo "# load_with_busy_loops: $(uptime)" >> "$log"
  fi
  local t0; t0=$(date +%s)
  "$jdk/bin/java" "$@" -cp "$cp" RepeatMethod "$CLS" "$METHOD" "$n" >> "$log" 2>&1
  local rc=$? wall=$(( $(date +%s) - t0 ))
  if [ "$busy" -gt 0 ]; then kill "${pids[@]}" 2>/dev/null; wait "${pids[@]}" 2>/dev/null; fi
  echo "# exit=$rc wall_seconds=$wall end=$(date '+%Y-%m-%dT%H:%M:%S%z')" >> "$log"
  python3 - "$log" "$cell" "$loop" "$rc" "$wall" "$start" "$(git -C "$wt" rev-parse HEAD)" "$B" <<'EOF' >> "$LOGS/runs.jsonl"
import json, os, re, sys
log, cell, loop, rc, wall, start, rev, bundle = sys.argv[1:]
iters, hooks = [], []
for line in open(log, errors="replace"):
    m = re.match(r"ITER (\d+) (PASS|FAIL|ERROR) (\d+)(?: (.*))?", line)
    if m:
        iters.append({"i": int(m.group(1)), "outcome": m.group(2), "ms": int(m.group(3)),
                      "message": (m.group(4) or "")[:300]})
    m = re.search(r"REPLAY-HOOK stall45 at deadline(-?\d+)ms, woke at deadline(-?\d+)ms", line)
    if m:
        hooks.append({"stall_at_ms": int(m.group(1)), "woke_at_ms": int(m.group(2))})
lead = re.search(r"lead(\d+)", cell)
print(json.dumps({
    "part": "B", "cell": cell, "loop": int(loop), "start": start, "revision": rev,
    "jdk": "jdk11" if cell.endswith("jdk11") else "jdk8",
    "hook": "none" if "nohook" in cell else ("patch-stalls" if cell.startswith("patch") else "dev-stall45"),
    "stall_lead_ms": int(lead.group(1)) if lead else (35 if cell.startswith("dev-hook") else None),
    "iterations": len(iters), "failed": sum(1 for i in iters if i["outcome"] != "PASS"),
    "passed": sum(1 for i in iters if i["outcome"] == "PASS"),
    "exit_code": int(rc), "wall_seconds": int(wall), "log": os.path.relpath(log, bundle),
    "iteration_results": iters, "hook_positions": hooks}))
EOF
  echo "$cell loop $loop: $(grep '^SUMMARY' "$log")"
}

for rep in $(seq 1 "$LOOPS"); do
  for cell in $CELLS; do
    # loop number = loops already logged for this cell + 1 (earlier loops are never overwritten)
    loop=$(( $(ls "$LOGS/$cell" 2>/dev/null | grep -c '^loop[0-9]*\.txt$') + 1 ))
    jdk=$JAVA8_HOME; [[ $cell == *jdk11 ]] && jdk=$JAVA11_HOME
    case "$cell" in
      dev-hook-jdk8|dev-hook-jdk11|dev-hook-lead[0-9]*-jdk8|dev-hook-lead[0-9]*-jdk11)
        [ -d "$W/partB/classes/dev-hook" ] || hooked_classes "$W/wt-dev" "$B/harness/hook-dev-deb16a3c3-stall45.patch" dev-hook
        props=""; [[ $cell =~ lead([0-9]+) ]] && props="-Dreplay.stall.lead.ms=${BASH_REMATCH[1]}"
        run_cell "$cell" "$loop" "$W/wt-dev" "$W/partB/classes/dev-hook" "$jdk" 20 0 $props ;;
      patch-hook-jdk8|patch-hook-jdk11)
        [ -d "$W/partB/classes/patch-hook" ] || hooked_classes "$W/wt-patch" "$B/harness/hook-patch-87ed0afe0-stalls.patch" patch-hook
        run_cell "$cell" "$loop" "$W/wt-patch" "$W/partB/classes/patch-hook" "$jdk" 20 0 ;;
      dev-nohook-contention-jdk8|dev-nohook-contention-jdk11)
        run_cell "$cell" "$loop" "$W/wt-dev" "" "$jdk" 50 20 ;;
      *) echo "unknown cell $cell"; exit 1 ;;
    esac
  done
done
