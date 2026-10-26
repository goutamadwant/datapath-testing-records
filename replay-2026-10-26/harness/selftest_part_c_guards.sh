#!/usr/bin/env bash
# Self-test of the safety rules in harness/part_c.sh, with a simulated `docker`, `java`, `javac`
# and `git` on PATH (no Docker daemon is contacted and no experiment is executed). The simulated
# Docker keeps its containers in a state file; the simulated JVM prints the harness lines and
# creates containers as each scenario requires. Expected outcomes are checked per scenario.
# Two scenarios create the empty directory /tmp/seatunnel_mnt (the fixed path the guard checks)
# and remove it afterwards; they are skipped if that path already exists.
# Run: bash harness/selftest_part_c_guards.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
T="$(mktemp -d "${TMPDIR:-/tmp}/part-c-selftest.XXXXXX")"
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/bin" "$T/bundle/harness/java" "$T/bundle/logs/partC" "$T/jdk/bin"
cp "$HERE/part_c.sh" "$HERE/parse_part_c.py" "$T/bundle/harness/"
cp "$HERE/java/ReplayKillTeardownTest.java" "$HERE/java/RepeatMethod.java" "$T/bundle/harness/java/"
W="$T/work"; M="$W/wt-e2e/seatunnel-e2e/seatunnel-connector-v2-e2e/connector-fake-e2e"
mkdir -p "$M/target" "$W/partC/runner" "$W/partC/before-overrides/classes"
: > "$M/target/test-classpath.txt"; : > "$W/partC/runner/RepeatMethod.class"; : > "$W/partC/before-overrides/classes/.done"
STATE="$T/containers"   # one line per container: <64-hex id> <image> <created RFC 3339> <session label or ->
SPARK=tyrantlucifer/spark:3.3.0; FLINK=tyrantlucifer/flink:1.18.0-scala_2.12_hadoop27

cat > "$T/bin/docker" <<'D'
#!/usr/bin/env bash
S="$MOCK_STATE"; touch "$S"
[ "${MOCK_DOCKER_DOWN:-0}" = 1 ] && { echo "Cannot connect to the Docker daemon" >&2; exit 1; }
case "$1 $2" in
  "ps -a"|"ps -aq")
    if [ "$2" = -aq ]; then cut -d' ' -f1 "$S"; exit 0; fi
    args="$*"
    if [[ $args == *"--filter ancestor="* ]]; then img="${args#*ancestor=}"; img="${img%% *}"
      awk -v i="$img" '$2==i {print $1}' "$S"
    elif [[ $args == *"--filter id="* ]]; then id="${args#*id=}"; id="${id%% *}"
      awk -v i="$id" '$1==i {print substr($1,1,12)":Exited (137)"}' "$S"
    else awk '{print $1" "$2}' "$S"; fi ;;
  "network ls") echo net0 ;;
  "version --format") echo "0.0-sim linux/arm64" ;;
  "image inspect") echo "sha256:sim" ;;
  "inspect -f")
    fmt="$3"; id="$4"; line="$(awk -v i="$id" '$1==i' "$S")"; [ -n "$line" ] || exit 1
    set -- $line
    case "$fmt" in
      *Config.Image*) echo "$2" ;;
      *Created*) echo "$3" ;;
      *sessionId*) [ "$4" = - ] && echo "" || echo "$4" ;;
    esac ;;
  "rm -f") grep -v "^$3 " "$S" > "$S.tmp"; mv "$S.tmp" "$S"; echo "$3" ;;
  *) echo "sim docker: unsupported: $*" >&2; exit 1 ;;
esac
D
cat > "$T/bin/git" <<'G'
#!/usr/bin/env bash
echo 0e4cf52896ee3604a8e7899d7736ffd914ee6ce7
G
cat > "$T/jdk/bin/javac" <<'J'
#!/usr/bin/env bash
while [ $# -gt 0 ]; do [ "$1" = -d ] && { d="$2"; shift; }; shift; done
mkdir -p "$d/org/apache/seatunnel/e2e/connector/fake" && : > "$d/org/apache/seatunnel/e2e/connector/fake/ReplayKillTeardownTest.class"
J
cat > "$T/jdk/bin/java" <<'J'
#!/usr/bin/env bash
# simulated harness JVM: one spark3 run, then the scenario's side effects
S="$MOCK_STATE"; SESSION=11111111-2222-3333-4444-555555555555
now() { date -u +%Y-%m-%dT%H:%M:%S.123456789Z; }
new() { printf '%s %s %s %s\n' "$(printf '%012x%052d' "$1" 0)" "$2" "$3" "$4" >> "$S"; }
echo "RESULT testcontainers_session=$SESSION"
if [ "$MOCK_SCENARIO" = abort ]; then
  echo "ASSERT spark3 run=1 name=pre_run_no_engine_containers result=FAIL expected=none observed=[x]"
  echo "RESULT spark3 run=1 aborted: containers of tyrantlucifer/spark:3.3.0 exist before the run [x]"; exit 3
fi
for a in pre_run_no_engine_containers teardown_no_exception teardown_time_bound containers_absent_after_teardown \
         next_job_exit_zero next_job_time_bound post_run_no_leftover_containers; do
  echo "ASSERT spark3 run=1 name=$a result=PASS expected=x observed=x"
done
echo "RESULT spark3 run=1 done"
case "$MOCK_SCENARIO" in
  leftovers)
    new 101 tyrantlucifer/spark:3.3.0 "$(now)" "$SESSION"                     # this JVM's leftover: removed
    new 102 tyrantlucifer/spark:3.3.0 "$(now)" -                              # concurrent, no label: kept
    new 103 tyrantlucifer/spark:3.3.0 "$(now)" 99999999-0000-0000-0000-000000000000  # other session: kept
    new 104 tyrantlucifer/flink:1.18.0-scala_2.12_hadoop27 "$(now)" "$SESSION" # other engine image: kept
    new 105 tyrantlucifer/spark:3.3.0 "2000-01-01T00:00:00.000000000Z" "$SESSION" # created before start: kept
    new 106 postgres:16 "$(now)" - ;;                                         # not an engine image: not considered
  mount) mkdir /tmp/seatunnel_mnt ;;
esac
echo "ITER 1 PASS 1000"; echo "SUMMARY failed=0/1"
J
chmod +x "$T/bin/"* "$T/jdk/bin/"*

PASSED=0; FAILED=0
run() { # <scenario> -> sets RC, OUT
  OUT="$(PATH="$T/bin:$PATH" MOCK_STATE="$STATE" MOCK_SCENARIO="$1" REPLAY_BUNDLE="$T/bundle" REPLAY_WORK="$W" \
         JAVA8_HOME="$T/jdk" REV_C_BEFORE=7ba68325cb7ea1bf1a28f56c4f9c20695d221df3 \
         bash "$T/bundle/harness/part_c.sh" 1 spark-after 2>&1)"; RC=$?
}
expect() { # <name> <condition result 0/1> <detail>
  if [ "$2" = 0 ]; then PASSED=$((PASSED + 1)); echo "ok   $1"; else FAILED=$((FAILED + 1)); echo "FAIL $1 ($3)"; echo "$OUT" | sed 's/^/     /'; fi
}
lastlog() { ls -t "$T/bundle/logs/partC/"spark-after*.txt 2>/dev/null | head -1; }
id12() { printf '%012x' "$1"; }

# 1. pre-existing stopped engine container of another image (Flink) -> refuse before any cell
: > "$STATE"; printf '%012x%052d %s 2026-01-01T00:00:00Z -\n' 7 0 "$FLINK" >> "$STATE"
run plain; c=1; [ $RC = 2 ] && [[ $OUT == *"containers of the engine images already exist"* ]] && grep -q "^$(printf '%012x%052d' 7 0) " "$STATE" && c=0
expect "pre-existing stopped Flink container: refused (exit $RC), container untouched" $c "rc=$RC"
[ -z "$(lastlog)" ]; expect "  ... and no cell log written" $? ""

# 2. Docker cannot be listed -> refuse
: > "$STATE"; OUT="$(PATH="$T/bin:$PATH" MOCK_DOCKER_DOWN=1 MOCK_STATE="$STATE" REPLAY_BUNDLE="$T/bundle" REPLAY_WORK="$W" JAVA8_HOME="$T/jdk" bash "$T/bundle/harness/part_c.sh" 1 spark-after 2>&1)"; RC=$?
c=1; [ $RC = 2 ] && [[ $OUT == *"cannot list Docker containers"* ]] && c=0
expect "Docker daemon unreachable: refused (exit $RC)" $c "rc=$RC"

# 3. /tmp/seatunnel_mnt exists before the run -> refuse
if [ -e /tmp/seatunnel_mnt ]; then echo "skip /tmp/seatunnel_mnt scenarios: the path exists on this host"; else
  mkdir /tmp/seatunnel_mnt; : > "$STATE"; run plain; rmdir /tmp/seatunnel_mnt
  c=1; [ $RC = 2 ] && [[ $OUT == *"/tmp/seatunnel_mnt exists"* ]] && c=0
  expect "/tmp/seatunnel_mnt present before the run: refused (exit $RC)" $c "rc=$RC"
fi

# 4. clean cell -> PASS, exit 0
: > "$STATE"; run plain; L="$(lastlog)"
c=1; [ $RC = 0 ] && grep -q '^# cell_result=PASS' "$L" && c=0
expect "clean cell: exit $RC, cell_result=PASS" $c "rc=$RC"

# 5. leftovers: only the cell JVM's own container is removed; every candidate is logged
: > "$STATE"; run leftovers; L="$(lastlog)"
c=1
[ $RC = 1 ] && grep -q "CLEANUP spark-after id=$(id12 101) .*decision=remove result=removed" "$L" \
  && grep -q "CLEANUP spark-after id=$(id12 102) .*decision=keep reasons=session_label_mismatch" "$L" \
  && grep -q "CLEANUP spark-after id=$(id12 103) .*decision=keep reasons=session_label_mismatch" "$L" \
  && grep -q "CLEANUP spark-after id=$(id12 104) .*decision=keep reasons=not_cell_engine_image" "$L" \
  && grep -q "CLEANUP spark-after id=$(id12 105) .*decision=keep reasons=created_before_cell_start" "$L" \
  && ! grep -q "id=$(id12 106)" "$L" \
  && ! grep -q "^$(printf '%012x%052d' 101 0) " "$STATE" \
  && [ "$(grep -c . "$STATE")" = 5 ] \
  && grep -q '^# cell_result=FAIL failed_checks=no_engine_container_after_cell,no_engine_container_after_cleanup' "$L" && c=0
expect "leftovers: own container removed, 4 engine containers kept with reasons, postgres not considered, cell FAIL, exit $RC" $c "rc=$RC"

# 6. harness aborts on its pre-run check -> cell FAIL, exit 1
: > "$STATE"; run abort; L="$(lastlog)"
c=1; [ $RC = 1 ] && grep -q 'name=harness_jvm_completed result=FAIL expected=ITER_1_PASS observed=rc=3' "$L" && c=0
expect "harness abort (JVM exit 3): cell FAIL, exit $RC" $c "rc=$RC"

# 7. /tmp/seatunnel_mnt present after the run -> cell FAIL, exit 1
if [ ! -e /tmp/seatunnel_mnt ]; then
  : > "$STATE"; run mount; L="$(lastlog)"; rmdir /tmp/seatunnel_mnt 2>/dev/null
  c=1; [ $RC = 1 ] && grep -q 'name=host_tmp_seatunnel_mnt_absent result=FAIL' "$L" && c=0
  expect "/tmp/seatunnel_mnt present after the run: cell FAIL, exit $RC" $c "rc=$RC"
fi
echo "$PASSED checks as expected, $FAILED not"
[ "$FAILED" = 0 ]
