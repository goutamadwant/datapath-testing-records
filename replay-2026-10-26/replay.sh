#!/usr/bin/env bash
# Replay entry point for the datapath-testing reconstruction records (bundle 2026-10-26).
#
#   ./replay.sh --part A|B|all [--runs N] [--prepare-only] [--cells "<cell> ..."]
#               [--require-toolchain <toolchain.json>]
#
#   --part A   PR 12468 Maven retry under injected faults (Table 1 rows 1-5)
#   --part B   PR 12472 stall injection (FileCollectReaderBehaviorTest)
#   --part all Parts A and B.
#   --part C   not run. Part C (PR 12481 killed-container teardown, Table 1 rows 6-7) executed
#              SeaTunnel's real end-to-end teardown against the host's Docker daemon, and that
#              teardown deletes the host path /tmp/seatunnel_mnt. Its recorded runs are kept as
#              historical records (logs/partC, results.json); its scripts are kept for inspection
#              in harness/historical-part-c/ and are not run by this script. --part C prints this
#              and exits 0; --part all prints it and runs Parts A and B only.
#   --runs N   A: runs per cell (default 5). B: repetitions of each 20-iteration
#              (50 for the contention cells) loop (default 1).
#   --prepare-only   toolchain check, clone, worktrees and builds only; no runs.
#   --cells    restrict a part to the named cells (see harness/part_a.py, harness/part_b.sh).
#   --require-toolchain <file>   optional: stop (exit 3) unless the toolchain equals the manifest
#              (e.g. ../replay-clean/toolchain.json; a relative path is taken from the directory
#              replay.sh was invoked from). Compared exactly, before anything is run: the full
#              `java -version` output of both JDKs, `python3 --version`, the six pinned commits, the
#              Maven wrapper distributionUrl at the Part A and B revisions, and (after the downloads)
#              the maven-wrapper jar sha1 and the Maven distribution zip sha256.
#
# Everything is created under ./work (override with REPLAY_WORK); logs go to ./logs and
# ./results.json is regenerated from the per-run records after every invocation. The
# regeneration validates the requested matrix first (harness/make_results.py): a missing or
# unparsable log, or fewer valid runs than requested, makes this script exit 1 and leaves
# results.json unchanged.
# Environment (all optional):
#   JAVA8_HOME, JAVA11_HOME  JDK homes (default: discovered with /usr/libexec/java_home or
#                            /usr/lib/jvm; a JDK must contain bin/javac)
#   REPLAY_WORK              work directory (default ./work, relative to this script)
#   REPLAY_SEATUNNEL_URL     apache/seatunnel clone URL (default https://github.com/apache/seatunnel.git)
#   REPLAY_MAVEN_REPO        local Maven repository for the Part B build (default: Maven's own)
set -u
INVOKE_DIR="$(pwd)"
cd "$(dirname "$0")" || exit 2
BUNDLE="$(pwd)"
export REPLAY_BUNDLE="$BUNDLE"
export REPLAY_WORK="${REPLAY_WORK:-$BUNDLE/work}"
PART=""; RUNS=""; PREPARE_ONLY=0; CELLS=""; REQUIRE_TC=""
while [ $# -gt 0 ]; do
  case "$1" in
    --part) PART="$2"; shift 2 ;;
    --runs) RUNS="$2"; shift 2 ;;
    --prepare-only) PREPARE_ONLY=1; shift ;;
    --cells) CELLS="$2"; shift 2 ;;
    --require-toolchain) REQUIRE_TC="$2"; shift 2
      case "$REQUIRE_TC" in /*) ;; *) REQUIRE_TC="$INVOKE_DIR/$REQUIRE_TC" ;; esac
      [ -f "$REQUIRE_TC" ] || { echo "--require-toolchain: $REQUIRE_TC not found" >&2; exit 2; } ;;
    -h|--help) sed -n '2,37p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
case "$PART" in A|B|C|all) ;; *) echo "usage: $0 --part A|B|all [--runs N]" >&2; exit 2 ;; esac
case "$RUNS" in '') ;; *[!0-9]*|0*) echo "--runs must be a positive integer (got '$RUNS')" >&2; exit 2 ;; esac

# Part C is not run (checked before anything is created, cloned, built or contacted).
part_c_notice() {
  cat >&2 <<'MSG'
replay.sh: Part C is not run by this script.
  Part C (PR 12481 killed-container teardown, Table 1 rows 6-7) executed SeaTunnel's real
  end-to-end teardown against the host's Docker daemon, not inside a sandbox, and that teardown
  deletes the host path /tmp/seatunnel_mnt. Its 20 recorded runs are historical records: their
  logs are in logs/partC and their sha256 values in results.json. The scripts that ran them are
  kept for inspection, not for execution, in harness/historical-part-c/ (see its README.md).
MSG
}
if [ "$PART" = C ]; then
  part_c_notice; echo "replay.sh: nothing run for --part C." >&2; exit 0
fi
if [ "$PART" = all ]; then
  part_c_notice; echo "replay.sh: --part all runs Parts A and B only." >&2
fi

STAMP="$(date +%Y%m%dT%H%M%S)"
mkdir -p logs/setup "$REPLAY_WORK"
SETUP_LOG="logs/setup/setup-part$PART-$STAMP.txt"
log() { echo "# $(date '+%Y-%m-%dT%H:%M:%S%z') $*" | tee -a "$SETUP_LOG"; }

# Pinned revisions (apache/seatunnel)
REV_A_BEFORE=a1084015eeb390a6c7f53d3ce7391217e427e4d9   # PR 12468 parent
REV_A_AFTER=ae7c919bcb78f03446dbd2b754a2b9882602946a    # PR 12468 merge
REV_B_DEV=deb16a3c3152f0349a587a504dccc997a131a9d7      # PR 12472 unchanged dev
REV_B_PATCH=87ed0afe0f783eda1b1f3ac6f0ac9fadedcb4f98    # PR 12472 merge
REV_C_BEFORE=7ba68325cb7ea1bf1a28f56c4f9c20695d221df3   # PR 12481 parent
REV_C_AFTER=0e4cf52896ee3604a8e7899d7736ffd914ee6ce7    # PR 12481 merge
export REV_A_BEFORE REV_A_AFTER REV_B_DEV REV_B_PATCH REV_C_BEFORE REV_C_AFTER

# Artifacts fetched from Maven Central, verified against Central's published .sha1
CENTRAL=https://repo.maven.apache.org/maven2
WRAPPER_JAR_PATH=org/apache/maven/wrapper/maven-wrapper/3.1.0/maven-wrapper-3.1.0.jar
LAUNCHER_JAR_PATH=org/junit/platform/junit-platform-launcher/1.9.0/junit-platform-launcher-1.9.0.jar

# ---------------------------------------------------------------- toolchain
jdk_version_ok() { # <home> <8|11>
  [ -x "$1/bin/java" ] && [ -x "$1/bin/javac" ] || return 1
  local v; v="$("$1/bin/java" -version 2>&1 | head -1)"
  case "$2" in
    8) [[ "$v" == *'"1.8.'* ]] ;;
    11) [[ "$v" == *'"11.'* ]] ;;
  esac
}
find_jdk() { # <8|11> -> prints a JDK home
  local want="$1" var cand
  var="JAVA${want}_HOME"
  if [ -n "${!var:-}" ]; then
    jdk_version_ok "${!var}" "$want" && { echo "${!var}"; return 0; }
    echo "$var=${!var} is not a JDK $want with javac" >&2; return 1
  fi
  if [ -x /usr/libexec/java_home ]; then
    local v="$want"; [ "$want" = 8 ] && v=1.8
    cand="$(/usr/libexec/java_home -v "$v" 2>/dev/null)"
    if [ -n "$cand" ] && jdk_version_ok "$cand" "$want"; then echo "$cand"; return 0; fi
    # java_home -v may return a JRE without javac; try every listed JVM
    while IFS= read -r cand; do
      jdk_version_ok "$cand" "$want" && { echo "$cand"; return 0; }
    done < <(/usr/libexec/java_home -V 2>&1 | grep '" /' | sed 's/.*" //')
  fi
  for cand in /usr/lib/jvm/*; do
    jdk_version_ok "$cand" "$want" && { echo "$cand"; return 0; }
  done
  return 1
}

toolchain() {
  local t="logs/setup/toolchain-part$PART-$STAMP.txt"
  JAVA8_HOME="$(find_jdk 8)" || { log "FATAL: no JDK 8 with javac found (set JAVA8_HOME)"; exit 3; }
  JAVA11_HOME="$(find_jdk 11)" || { log "FATAL: no JDK 11 with javac found (set JAVA11_HOME)"; exit 3; }
  export JAVA8_HOME JAVA11_HOME
  for tool in git curl python3 patch shasum; do
    command -v "$tool" >/dev/null || { log "FATAL: $tool not found"; exit 3; }
  done
  {
    echo "# toolchain record $(date '+%Y-%m-%dT%H:%M:%S%z') part=$PART"
    echo "## host"; uname -a
    (sysctl -n machdep.cpu.brand_string hw.ncpu hw.memsize 2>/dev/null || nproc) | tr '\n' ' '; echo
    sw_vers 2>/dev/null || cat /etc/os-release 2>/dev/null | head -3
    echo "## load"; uptime
    echo "## JDK 8 ($JAVA8_HOME)"; "$JAVA8_HOME/bin/java" -version 2>&1
    file "$JAVA8_HOME/bin/java" 2>/dev/null | sed 's/.*: //'
    echo "## JDK 11 ($JAVA11_HOME)"; "$JAVA11_HOME/bin/java" -version 2>&1
    file "$JAVA11_HOME/bin/java" 2>/dev/null | sed 's/.*: //'
    echo "## python"; python3 --version 2>&1
    echo "## git"; git --version
    echo "## curl"; curl --version | head -1
    echo "## wget"; command -v wget >/dev/null && wget --version | head -1 || echo "wget not installed"
    echo "## bash"; echo "$BASH_VERSION"
  } > "$t" 2>&1
  log "toolchain ok: JDK8=$JAVA8_HOME JDK11=$JAVA11_HOME record=$t"
}

# ---------------------------------------------------------------- optional toolchain manifest
# tc_check <key> <observed value>: with --require-toolchain, the value must equal manifest.enforce[key].
tc_check() {
  [ -n "$REQUIRE_TC" ] || return 0
  local msg
  msg="$(python3 -I -c '
import json, sys
m, key, got = sys.argv[1], sys.argv[2], sys.argv[3]
want = json.load(open(m)).get("enforce", {}).get(key)
if want is None:
    print("FATAL: toolchain manifest has no enforce.%s" % key); sys.exit(1)
if got != want:
    print("FATAL: toolchain mismatch for %s: observed %r, manifest %r" % (key, got, want)); sys.exit(1)
print("toolchain manifest: %s matches" % key)
' "$REQUIRE_TC" "$1" "$2")"
  local rc=$?
  log "$msg"
  [ $rc = 0 ] || exit 3
}
tc_check_pre() {
  [ -n "$REQUIRE_TC" ] || return 0
  log "checking the toolchain against ${REQUIRE_TC} (sha256 $(shasum -a 256 "$REQUIRE_TC" | cut -d' ' -f1))"
  tc_check jdk8_java_version "$("$JAVA8_HOME/bin/java" -version 2>&1)"
  tc_check jdk11_java_version "$("$JAVA11_HOME/bin/java" -version 2>&1)"
  tc_check python_version "$(python3 --version 2>&1)"
  tc_check seatunnel_commits "$REV_A_BEFORE $REV_A_AFTER $REV_B_DEV $REV_B_PATCH $REV_C_BEFORE $REV_C_AFTER"
}
tc_check_wrapper_props() {
  [ -n "$REQUIRE_TC" ] || return 0
  local r
  for r in $REV_A_BEFORE $REV_A_AFTER $REV_B_DEV $REV_B_PATCH; do
    tc_check maven_distribution_url "$(git -C "$REPLAY_WORK/seatunnel" show "$r:.mvn/wrapper/maven-wrapper.properties" \
      | sed -n 's/^distributionUrl=//p' | tr -d '\r')"
  done
}

# ---------------------------------------------------------------- sources
clone_seatunnel() {
  local url="${REPLAY_SEATUNNEL_URL:-https://github.com/apache/seatunnel.git}"
  local repo="$REPLAY_WORK/seatunnel"
  if [ ! -d "$repo/.git" ]; then
    log "cloning $url (blobless) into work/seatunnel"
    git clone --filter=blob:none --no-checkout "$url" "$repo" >> "$SETUP_LOG" 2>&1 \
      || { log "FATAL: clone failed"; exit 4; }
  fi
  local r
  for r in $REV_A_BEFORE $REV_A_AFTER $REV_B_DEV $REV_B_PATCH $REV_C_BEFORE $REV_C_AFTER; do
    if ! git -C "$repo" cat-file -e "$r^{commit}" 2>/dev/null; then
      log "fetching $r"; git -C "$repo" fetch -q origin "$r" >> "$SETUP_LOG" 2>&1 \
        || { log "FATAL: commit $r not reachable"; exit 4; }
    fi
  done
  log "all six pinned commits present in work/seatunnel"
}

worktree() { # <name> <rev>
  local repo="$REPLAY_WORK/seatunnel" wt="$REPLAY_WORK/$1"
  if [ ! -d "$wt" ]; then
    log "worktree work/$1 at $2"
    git -C "$repo" worktree add --detach "$wt" "$2" >> "$SETUP_LOG" 2>&1 || { log "FATAL: worktree $1"; exit 4; }
  fi
  [ "$(git -C "$wt" rev-parse HEAD)" = "$2" ] || { log "FATAL: work/$1 is not at $2"; exit 4; }
}

fetch_central() { # <repo-relative path> <dest file>
  local dest="$2"
  [ -f "$dest" ] && return 0
  mkdir -p "$(dirname "$dest")"
  curl -fsSL "$CENTRAL/$1" -o "$dest.tmp" && curl -fsSL "$CENTRAL/$1.sha1" -o "$dest.sha1" \
    || { log "FATAL: download $1"; exit 5; }
  local want got
  want="$(cut -c1-40 < "$dest.sha1")"; got="$(shasum -a 1 "$dest.tmp" | cut -d' ' -f1)"
  [ "$want" = "$got" ] || { log "FATAL: sha1 mismatch for $1 ($got != $want)"; exit 5; }
  mv "$dest.tmp" "$dest"
  log "fetched $1 sha1=$got (matches Central)"
}

# ---------------------------------------------------------------- Part A setup
prepare_a() {
  local warm="$REPLAY_WORK/partA/warm-repo" wd="$REPLAY_WORK/partA/warmdir"
  export MAVEN_USER_HOME="$REPLAY_WORK/mvn-home"   # wrapper distribution cache, isolated
  fetch_central "$WRAPPER_JAR_PATH" "$warm/$WRAPPER_JAR_PATH"
  fetch_central "${WRAPPER_JAR_PATH%.jar}.pom" "$warm/${WRAPPER_JAR_PATH%.jar}.pom"
  if [ ! -f "$REPLAY_WORK/partA/warm.done" ]; then
    mkdir -p "$wd/.mvn/wrapper"
    git -C "$REPLAY_WORK/seatunnel" show "$REV_A_AFTER:mvnw" > "$wd/mvnw"; chmod +x "$wd/mvnw"
    git -C "$REPLAY_WORK/seatunnel" show "$REV_A_AFTER:.mvn/wrapper/maven-wrapper.properties" \
      > "$wd/.mvn/wrapper/maven-wrapper.properties"
    cp "$warm/$WRAPPER_JAR_PATH" "$wd/.mvn/wrapper/maven-wrapper.jar"
    cp harness/tiny-pom.xml "$wd/pom.xml"
    local wl="logs/partA/warm-repo-build.txt" j
    mkdir -p logs/partA
    : > "$wl"
    for j in "$JAVA11_HOME" "$JAVA8_HOME"; do
      echo "== JAVA_HOME=$j MAVEN_USER_HOME=work/mvn-home" >> "$wl"
      echo "+ ./mvnw -B -s <bundle>/harness/settings-empty.xml -Dmaven.repo.local=<work>/partA/warm-repo -f pom.xml dependency:resolve" >> "$wl"
      (cd "$wd" && JAVA_HOME="$j" MAVEN_OPTS="" ./mvnw -B -s "$BUNDLE/harness/settings-empty.xml" \
        -Dmaven.repo.local="$warm" -f pom.xml dependency:resolve) >> "$wl" 2>&1 \
        || { log "FATAL: warming the mirror repository failed (see $wl)"; exit 6; }
    done
    touch "$REPLAY_WORK/partA/warm.done"
    log "warm repository built from Maven Central (log $wl)"
  fi
  if [ ! -f logs/partA/maven-version.txt ]; then
    {
      echo "# ./mvnw -v (wrapper from $REV_A_AFTER, MAVEN_USER_HOME=work/mvn-home)"
      (cd "$wd" && JAVA_HOME="$JAVA8_HOME" ./mvnw -v) 2>&1
      echo "# transport and resolver jars in the wrapper distribution:"
      find "$MAVEN_USER_HOME/wrapper/dists" -path '*/lib/*' \( -name 'wagon-*.jar' -o -name 'maven-resolver-*.jar' \) \
        -exec basename {} \; | sort
      echo "# sha256 of the distribution zip:"
      find "$MAVEN_USER_HOME/wrapper/dists" -name '*.zip' -exec shasum -a 256 {} \; | sed "s#$REPLAY_WORK#<work>#"
    } > logs/partA/maven-version.txt
  fi
  if [ -n "$REQUIRE_TC" ]; then
    tc_check maven_wrapper_jar_sha1 "$(shasum -a 1 "$warm/$WRAPPER_JAR_PATH" | cut -d' ' -f1)"
    tc_check maven_distribution_sha256 "$(find "$MAVEN_USER_HOME/wrapper/dists" -name 'apache-maven-*-bin.zip' \
      -exec shasum -a 256 {} \; | cut -d' ' -f1 | sort -u | tr '\n' ' ' | sed 's/ $//')"
  fi
}

# ---------------------------------------------------------------- Part B setup
fetch_launcher() { fetch_central "$LAUNCHER_JAR_PATH" "$REPLAY_WORK/lib/junit-platform-launcher-1.9.0.jar"; }

mvn_repo_flag() { [ -n "${REPLAY_MAVEN_REPO:-}" ] && echo "-Dmaven.repo.local=$REPLAY_MAVEN_REPO"; }

build_module() { # <worktree name> <log> <maven args...>
  local wt="$REPLAY_WORK/$1" lg="$BUNDLE/$2"; shift 2
  [ -f "$wt/.replay-built" ] && { log "work/$(basename "$wt") already built"; return 0; }
  log "building work/$(basename "$wt") (log ${lg#$BUNDLE/})"
  (
    cd "$wt" || exit 2
    echo "# $(date '+%Y-%m-%dT%H:%M:%S%z') worktree=work/$(basename "$wt") JAVA_HOME=$JAVA8_HOME rev=$(git rev-parse HEAD)"
    echo "# git status (local-only changes):"; git status --short
    echo "# command: ./mvnw $* $(mvn_repo_flag)"
    JAVA_HOME="$JAVA8_HOME" ./mvnw "$@" $(mvn_repo_flag)
    rc=$?; echo "# exit=$rc end=$(date '+%Y-%m-%dT%H:%M:%S%z')"; exit $rc
  ) > "$lg" 2>&1 || { log "FATAL: build failed, see ${lg#$BUNDLE/}"; exit 7; }
  touch "$wt/.replay-built"
}

prepare_b() {
  fetch_launcher
  mkdir -p logs/partB
  worktree wt-dev "$REV_B_DEV"; worktree wt-patch "$REV_B_PATCH"
  local args=(-B -T 1 -pl seatunnel-edge-agent/seatunnel-edge-agent-connector -am package
    dependency:build-classpath -DskipUT=true -DskipTests -Dspotless.check.skip=true
    -Dspotless.apply.skip=true -Dlicense.skipAddThirdParty=true
    -Dmdep.outputFile=target/test-classpath.txt -Dmdep.includeScope=test --no-snapshot-updates)
  build_module wt-dev logs/partB/build-dev-deb16a3c3-jdk8.txt "${args[@]}"
  build_module wt-patch logs/partB/build-patch-87ed0afe0-jdk8.txt "${args[@]}"
  if [ -n "$REQUIRE_TC" ]; then
    tc_check maven_distribution_sha256 "$(find "${MAVEN_USER_HOME:-$HOME/.m2}/wrapper/dists" \
      -name 'apache-maven-*-bin.zip' -exec shasum -a 256 {} \; | cut -d' ' -f1 | sort -u | tr '\n' ' ' | sed 's/ $//')"
  fi
}

# ---------------------------------------------------------------- main
log "replay.sh --part $PART runs=${RUNS:-default} prepare_only=$PREPARE_ONLY cells=${CELLS:-all} work=${REPLAY_WORK#$BUNDLE/}"
toolchain
tc_check_pre
clone_seatunnel
tc_check_wrapper_props
RC=0
if [ "$PART" = A ] || [ "$PART" = all ]; then
  prepare_a
  if [ "$PREPARE_ONLY" = 0 ]; then
    MAVEN_USER_HOME="$REPLAY_WORK/mvn-home" python3 harness/part_a.py --runs "${RUNS:-5}" $CELLS || RC=1
  fi
fi
if [ "$PART" = B ] || [ "$PART" = all ]; then
  prepare_b
  [ "$PREPARE_ONLY" = 0 ] && { bash harness/part_b.sh "${RUNS:-1}" $CELLS || RC=1; }
fi
if ! python3 harness/make_results.py; then
  log "validation failed: results.json not regenerated (the problems are listed above)"
  RC=1
fi
log "done rc=$RC"
exit $RC
