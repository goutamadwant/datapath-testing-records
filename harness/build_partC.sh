#!/bin/bash
# Part C build (reconstruction, 2026-10-25). Packages (no install) the Flink 1.15+ and Spark 3
# starters, the fake/assert connectors, transforms-v2 and connector-fake-e2e (with
# seatunnel-e2e-common via -am), after copying the local-only harness test into
# connector-fake-e2e. Writes connector-fake-e2e's test classpath to target/test-classpath.txt
# (-De2e.dependency.skip=false: the e2e parent pom skips maven-dependency-plugin by default; the
# first build ran without this flag, see logs/partC/build-after-0e4cf5289-jdk8.full.txt).
# usage: build_partC.sh <worktree> <java_home> <log>
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
WT="$1"; export JAVA_HOME="$2"; LOG="$3"
cd "$WT" || exit 2
cp "$HERE/java/ReplayKillTeardownTest.java" \
   seatunnel-e2e/seatunnel-connector-v2-e2e/connector-fake-e2e/src/test/java/org/apache/seatunnel/e2e/connector/fake/
MODS=seatunnel-core/seatunnel-flink-starter/seatunnel-flink-15-starter,seatunnel-core/seatunnel-spark-starter/seatunnel-spark-3-starter,seatunnel-connectors-v2/connector-fake,seatunnel-connectors-v2/connector-assert,seatunnel-transforms-v2,seatunnel-e2e/seatunnel-connector-v2-e2e/connector-fake-e2e
CMD=(./mvnw -B -T 1C -pl "$MODS" -am package dependency:build-classpath -DskipUT=true -DskipIT=true
     -DskipTests -Dspotless.check.skip=true -Dspotless.apply.skip=true -Dlicense.skipAddThirdParty=true
     -De2e.dependency.skip=false -Dmdep.outputFile=target/test-classpath.txt -Dmdep.includeScope=test
     --no-snapshot-updates)
{
  echo "# $(date '+%Y-%m-%dT%H:%M:%S%z') cwd=$PWD JAVA_HOME=$JAVA_HOME rev=$(git rev-parse HEAD)"
  echo "# git status (local-only changes):"; git status --short
  echo "# command: ${CMD[*]}"
  "${CMD[@]}"
  echo "# exit=$?"
} > "$LOG" 2>&1
tail -5 "$LOG"
