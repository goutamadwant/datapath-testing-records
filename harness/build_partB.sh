#!/bin/bash
# Part B build (reconstruction, 2026-10-25): build only the edge-agent connector module and the
# modules it needs, compile its tests, and write each module's test classpath to
# target/test-classpath.txt. Uses `package` (not install) so the user's ~/.m2 is not overwritten.
# usage: build_partB.sh <worktree> <java_home> <log>
set -u
WT="$1"; export JAVA_HOME="$2"; LOG="$3"
cd "$WT" || exit 2
CMD=(./mvnw -B -T 1 -pl seatunnel-edge-agent/seatunnel-edge-agent-connector -am package
     dependency:build-classpath -DskipUT=true -DskipTests -Dspotless.check.skip=true
     -Dspotless.apply.skip=true -Dlicense.skipAddThirdParty=true
     -Dmdep.outputFile=target/test-classpath.txt -Dmdep.includeScope=test --no-snapshot-updates)
{
  echo "# $(date '+%Y-%m-%dT%H:%M:%S%z') cwd=$PWD JAVA_HOME=$JAVA_HOME rev=$(git rev-parse HEAD)"
  echo "# command: ${CMD[*]}"
  "${CMD[@]}"
  echo "# exit=$?"
} > "$LOG" 2>&1
tail -5 "$LOG"
