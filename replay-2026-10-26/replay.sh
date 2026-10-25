#!/usr/bin/env bash
# Replay entry point for the datapath-testing reconstruction records (bundle 2026-10-26).
#
#   ./replay.sh --part A|B|C|all [--runs N] [--prepare-only] [--cells "<cell> ..."]
#
#   --part A   PR 12468 Maven retry under injected faults (Table 1 rows 1-5)
#   --part B   PR 12472 stall injection (FileCollectReaderBehaviorTest)
#   --part C   PR 12481 killed-container teardown (Table 1 rows 6-7, Docker)
#   --runs N   A and C: runs per cell (default 5). B: repetitions of each 20-iteration
#              (50 for the contention cells) loop (default 1).
#   --prepare-only   toolchain check, clone, worktrees and builds only; no runs.
#   --cells    restrict a part to the named cells (see harness/part_*.{py,sh} for names).
#
# Everything is created under ./work (override with REPLAY_WORK); logs go to ./logs and
# ./results.json is regenerated from the per-run records after every invocation.
# Environment (all optional):
#   JAVA8_HOME, JAVA11_HOME  JDK homes (default: discovered with /usr/libexec/java_home or
#                            /usr/lib/jvm; a JDK must contain bin/javac)
#   REPLAY_WORK              work directory (default ./work, relative to this script)
#   REPLAY_SEATUNNEL_URL     apache/seatunnel clone URL (default https://github.com/apache/seatunnel.git)
#   REPLAY_MAVEN_REPO        local Maven repository for the Part B/C builds (default: Maven's own)
#   REPLAY_PULL_ZETA=1       pull seatunnelhub/openjdk:8u342 (Zeta cell; not run by default)
set -u
cd "$(dirname "$0")" || exit 2
BUNDLE="$(pwd)"
export REPLAY_BUNDLE="$BUNDLE"
export REPLAY_WORK="${REPLAY_WORK:-$BUNDLE/work}"
PART=""; RUNS=""; PREPARE_ONLY=0; CELLS=""
while [ $# -gt 0 ]; do
  case "$1" in
    --part) PART="$2"; shift 2 ;;
    --runs) RUNS="$2"; shift 2 ;;
    --prepare-only) PREPARE_ONLY=1; shift ;;
    --cells) CELLS="$2"; shift 2 ;;
    -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
case "$PART" in A|B|C|all) ;; *) echo "usage: $0 --part A|B|C|all [--runs N]" >&2; exit 2 ;; esac

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
  local need_docker="$1" t="logs/setup/toolchain-part$PART-$STAMP.txt"
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
    echo "## docker"
    if command -v docker >/dev/null; then
      docker version --format 'client {{.Client.Version}} server {{.Server.Version}} {{.Server.Os}}/{{.Server.Arch}}' 2>&1
    else echo "docker not installed"; fi
  } > "$t" 2>&1
  if [ "$need_docker" = 1 ] && ! docker info >/dev/null 2>&1; then
    log "FATAL: docker daemon not reachable (Part C needs it)"; exit 3
  fi
  log "toolchain ok: JDK8=$JAVA8_HOME JDK11=$JAVA11_HOME record=$t"
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
}

# ---------------------------------------------------------------- Part B/C setup
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
}

prepare_c() {
  fetch_launcher
  mkdir -p logs/partC
  worktree wt-e2e "$REV_C_AFTER"
  local img
  for img in tyrantlucifer/flink:1.18.0-scala_2.12_hadoop27 tyrantlucifer/spark:3.3.0; do
    if ! docker image inspect "$img" >/dev/null 2>&1; then
      log "pulling $img"; docker pull "$img" >> "$SETUP_LOG" 2>&1 || { log "FATAL: pull $img"; exit 8; }
    fi
    log "image $img id=$(docker image inspect --format '{{.Id}}' "$img")"
  done
  if [ "${REPLAY_PULL_ZETA:-0}" = 1 ]; then docker pull seatunnelhub/openjdk:8u342 >> "$SETUP_LOG" 2>&1; fi
  if docker image inspect seatunnelhub/openjdk:8u342 >/dev/null 2>&1; then
    log "Zeta image seatunnelhub/openjdk:8u342 is cached (the Zeta cell is still not part of this harness)"
  else
    log "Zeta image seatunnelhub/openjdk:8u342 not cached: Zeta cell not re-run"
  fi
  # the local-only harness test is placed into connector-fake-e2e before the build
  cp harness/java/ReplayKillTeardownTest.java \
    "$REPLAY_WORK/wt-e2e/seatunnel-e2e/seatunnel-connector-v2-e2e/connector-fake-e2e/src/test/java/org/apache/seatunnel/e2e/connector/fake/"
  local mods=seatunnel-core/seatunnel-flink-starter/seatunnel-flink-15-starter,seatunnel-core/seatunnel-spark-starter/seatunnel-spark-3-starter,seatunnel-connectors-v2/connector-fake,seatunnel-connectors-v2/connector-assert,seatunnel-transforms-v2,seatunnel-e2e/seatunnel-connector-v2-e2e/connector-fake-e2e
  build_module wt-e2e logs/partC/build-after-0e4cf5289-jdk8.txt -B -T 1C -pl "$mods" -am package \
    dependency:build-classpath -DskipUT=true -DskipIT=true -DskipTests -Dspotless.check.skip=true \
    -Dspotless.apply.skip=true -Dlicense.skipAddThirdParty=true -De2e.dependency.skip=false \
    -Dmdep.outputFile=target/test-classpath.txt -Dmdep.includeScope=test --no-snapshot-updates
}

# ---------------------------------------------------------------- main
NEED_DOCKER=0; { [ "$PART" = C ] || [ "$PART" = all ]; } && NEED_DOCKER=1
log "replay.sh --part $PART runs=${RUNS:-default} prepare_only=$PREPARE_ONLY cells=${CELLS:-all} work=${REPLAY_WORK#$BUNDLE/}"
toolchain "$NEED_DOCKER"
clone_seatunnel
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
if [ "$PART" = C ] || [ "$PART" = all ]; then
  prepare_c
  [ "$PREPARE_ONLY" = 0 ] && { bash harness/part_c.sh "${RUNS:-5}" $CELLS || RC=1; }
fi
python3 harness/make_results.py || RC=1
log "done rc=$RC"
exit $RC
