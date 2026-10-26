#!/usr/bin/env bash
# Fail-before / pass-after runs for the regression tests named in the article.
#
# Usage: ./run.sh [case ...]
#   cases: df24193 df24917 df24917-diag st12038 st12038-shim st12038-factory st12360 st12472 st12481 st12481-shim
#   (default: all cases, in that order)
#
# For each case:
#   before = first parent of the pull request's merge commit, with ONLY the test change of the
#            pull request applied on top (whole test files, or the test-module hunks of a file that
#            also holds production code; see patches/)
#   after  = the pull request's merge commit, unmodified
# The same test command runs on both trees. Every run writes a full log under logs/<case>/ and
# appends one record to logs/runs.jsonl; logs are never overwritten (a repeated run gets a suffix).
# python3 make_results.py then derives the outcome of every run from its log and writes results.json.
#
# Environment (all optional):
#   FAILBEFORE_WORK   scratch directory for worktrees and the cargo target dir (default ./work)
#   DATAFUSION_REPO   existing local clone of apache/datafusion to add worktrees from
#                     (default: clone https://github.com/apache/datafusion.git into the work dir)
#   SEATUNNEL_REPO    existing local clone of apache/seatunnel (default: clone into the work dir)
#   JAVA8_HOME        JDK 8 used for every SeaTunnel run (default: /usr/libexec/java_home -v 1.8)
set -u -o pipefail

cd "$(dirname "$0")"
HERE=$(pwd)
WORK=${FAILBEFORE_WORK:-$HERE/work}
LOGS=$HERE/logs
PATCHES=$HERE/patches
mkdir -p "$WORK/trees" "$LOGS"

DF_REPO=${DATAFUSION_REPO:-$WORK/datafusion.git}
ST_REPO=${SEATUNNEL_REPO:-$WORK/seatunnel.git}
JAVA8_HOME=${JAVA8_HOME:-$(/usr/libexec/java_home -v 1.8 2>/dev/null || true)}
export CARGO_TARGET_DIR=$WORK/df-target

ensure_repo() { # url dir
    [ -d "$2" ] || git clone --filter=blob:none --no-checkout "$1" "$2"
}

# prep_tree <repo> <name> <commit>: worktree <name> at <commit>, no local changes, no untracked files
prep_tree() {
    local repo=$1 name=$2 commit=$3 dir=$WORK/trees/$2
    git -C "$repo" cat-file -e "$commit^{commit}" 2>/dev/null || git -C "$repo" fetch -q origin "$commit"
    if [ ! -e "$dir/.git" ]; then
        git -C "$repo" worktree add -q --detach "$dir" "$commit" || return 1
    fi
    git -C "$dir" reset -q --hard || return 1
    git -C "$dir" checkout -q --detach --force "$commit" || return 1
    git -C "$dir" clean -q -fdx || return 1
    TREE=$dir
}

next_log() { # case side -> unused log path
    local base=$LOGS/$1/$2 n=2
    mkdir -p "$LOGS/$1"
    if [ ! -e "$base.log" ]; then echo "$base.log"; return; fi
    while [ -e "$base-$n.log" ]; do n=$((n + 1)); done
    echo "$base-$n.log"
}

# run_one <case> <side> <before_commit> <after_commit> <transplant text> <module or -> <cmd...>
# Runs <cmd> in $TREE, logs everything, appends a record to logs/runs.jsonl.
run_one() {
    local case=$1 side=$2 before=$3 after=$4 transplant=$5 module=$6
    shift 6
    local log rel start end rc
    log=$(next_log "$case" "$side")
    rel=${log#"$HERE"/}
    {
        echo "# case: $case"
        echo "# side: $side"
        echo "# before commit (first parent): $before"
        echo "# after commit (merge): $after"
        echo "# tree HEAD: $(git -C "$TREE" rev-parse HEAD)"
        echo "# transplant: $transplant"
        echo "# git status --porcelain:"
        git -C "$TREE" status --porcelain | sed 's/^/#   /'
        echo "# git diff --stat HEAD:"
        git -C "$TREE" diff --stat HEAD | sed 's/^/#   /'
        echo "# host: $(uname -srm)"
        if [ "$module" = "-" ]; then
            echo "# toolchain: $(cd "$TREE" && rustc --version) / $(cd "$TREE" && cargo --version)"
        else
            echo "# toolchain: $("$JAVA_HOME/bin/java" -version 2>&1 | head -1)"
        fi
        echo "# command: $*"
        echo "# start: $(date '+%Y-%m-%dT%H:%M:%S%z')"
    } > "$log"
    start=$(python3 -c 'import time; print(time.time())')
    (cd "$TREE" && "$@") >> "$log" 2>&1
    rc=$?
    end=$(python3 -c 'import time; print(time.time())')
    {
        echo "# end: $(date '+%Y-%m-%dT%H:%M:%S%z')"
        echo "# exit code: $rc"
    } >> "$log"
    if [ "$module" != "-" ] && [ -d "$TREE/$module/target/surefire-reports" ]; then
        mkdir -p "${log%.log}.surefire"
        cp "$TREE/$module"/target/surefire-reports/TEST-*.xml "${log%.log}.surefire/" 2>/dev/null || true
    fi
    python3 - "$LOGS/runs.jsonl" "$case" "$side" "$before" "$after" "$(git -C "$TREE" rev-parse HEAD)" \
        "$transplant" "$*" "$rc" "$start" "$end" "$rel" <<'EOF'
import json, sys
f, case, side, before, after, head, transplant, cmd, rc, start, end, log = sys.argv[1:]
rec = dict(case=case, side=side, before_commit=before, after_commit=after, tree_head=head,
           transplant=transplant, command=cmd, exit_code=int(rc),
           started_epoch=float(start), ended_epoch=float(end),
           duration_s=round(float(end) - float(start), 1), log=log)
with open(f, "a") as fh:
    fh.write(json.dumps(rec) + "\n")
EOF
    echo "[$case/$side] exit $rc in $(python3 -c "print(round($end-$start))") s -> $rel"
}

# ---------------------------------------------------------------- DataFusion
df_case() { # case before after test_cmd transplant_kind transplant_arg
    local case=$1 before=$2 after=$3 cmd=$4 kind=$5 arg=$6 text
    ensure_repo https://github.com/apache/datafusion.git "$DF_REPO"
    df -h "$WORK" | tail -1
    prep_tree "$DF_REPO" df "$before" || return 1
    if [ "$kind" = patch ]; then
        git -C "$TREE" apply "$PATCHES/$arg" || return 1
        text="patches/$arg applied (test-module hunks only)"
    else
        git -C "$TREE" checkout "$after" -- "$arg" || return 1
        text="$arg copied from $after"
    fi
    # shellcheck disable=SC2086
    run_one "$case" before "$before" "$after" "$text" - $cmd
    prep_tree "$DF_REPO" df "$after" || return 1
    # shellcheck disable=SC2086
    run_one "$case" after "$before" "$after" "none (merge commit as is)" - $cmd
}

case_df24193() {
    df_case df24193 d5868e683435042aa5fa72465a8a2d667d8cc468 047f531488f6617e88c76769baf2e2d6ac8e1c0e \
        "cargo test --locked --profile ci -p datafusion-physical-plan --lib unbounded_input_emits_before_batch_size" \
        patch df24193-tests-only.patch
}

case_df24917() {
    df_case df24917 408527ae58b5b706f5c02df8c37e096122cd8c78 3dfa245d61dde362e2c077761783bc735931659c \
        "cargo test --locked --profile ci -p datafusion --test core_integration expensive_regexp_like_is_deferred_to_execution" \
        file datafusion/core/tests/optimizer/mod.rs
}

# Diagnostic, not a fail-before run: the same test with the logical plans and the planning time of
# the literal query printed (patches/df24917-diagnostic-print-plan.patch), three runs per tree, to
# show what the plan looks like on each tree.
case_df24917-diag() {
    local before=408527ae58b5b706f5c02df8c37e096122cd8c78 after=3dfa245d61dde362e2c077761783bc735931659c
    local t=datafusion/core/tests/optimizer/mod.rs p=df24917-diagnostic-print-plan.patch
    local cmd="cargo test --locked --profile ci -p datafusion --test core_integration expensive_regexp_like_is_deferred_to_execution -- --nocapture"
    ensure_repo https://github.com/apache/datafusion.git "$DF_REPO"
    prep_tree "$DF_REPO" df "$before" || return 1
    git -C "$TREE" checkout "$after" -- "$t" && git -C "$TREE" apply "$PATCHES/$p" || return 1
    run_one df24917-diag before "$before" "$after" "$t copied from $after; then patches/$p applied" - \
        sh -c "rc=0; for i in 1 2 3; do $cmd || rc=1; done; exit \$rc"
    prep_tree "$DF_REPO" df "$after" || return 1
    git -C "$TREE" apply "$PATCHES/$p" || return 1
    run_one df24917-diag after "$before" "$after" "patches/$p applied" - \
        sh -c "rc=0; for i in 1 2 3; do $cmd || rc=1; done; exit \$rc"
}

# ---------------------------------------------------------------- SeaTunnel
mvn_cmd() { # module test-selector
    # package, not test: upstream modules such as seatunnel-config-shade are only usable by the
    # reactor once their shaded jar exists (a first attempt with "clean test" failed there).
    echo "./mvnw -B -ntp -pl $1 -am -DskipUT=false -DskipIT=true -Dskip.spotless=true -Dspotless.check.skip=true -Dspotless.apply.skip=true -Dlicense.skipAddThirdParty=true -Dtest=$2 -DfailIfNoTests=false clean package"
}

# st_case <case> <tree> <before> <after> <module> <selector> <sides> <patch or -> <test files...>
st_case() {
    local case=$1 tree=$2 before=$3 after=$4 module=$5 sel=$6 sides=$7 patch=$8 f text
    shift 8
    [ -n "$JAVA8_HOME" ] && [ -x "$JAVA8_HOME/bin/javac" ] || { echo "JDK 8 not found (JAVA8_HOME)"; return 1; }
    export JAVA_HOME=$JAVA8_HOME
    ensure_repo https://github.com/apache/seatunnel.git "$ST_REPO"
    if [[ $sides == *before* ]]; then
        prep_tree "$ST_REPO" "$tree" "$before" || return 1
        text=""
        for f in "$@"; do
            git -C "$TREE" checkout "$after" -- "$f" || return 1
            text="$text$f copied from $after; "
        done
        if [ "$patch" != - ]; then
            git -C "$TREE" apply "$PATCHES/$patch" || return 1
            text="${text}then patches/$patch applied"
        fi
        # shellcheck disable=SC2046
        run_one "$case" before "$before" "$after" "$text" "$module" $(mvn_cmd "$module" "$sel")
    fi
    if [[ $sides == *after* ]]; then
        prep_tree "$ST_REPO" "$tree" "$after" || return 1
        # shellcheck disable=SC2046
        run_one "$case" after "$before" "$after" "none (merge commit as is)" "$module" $(mvn_cmd "$module" "$sel")
    fi
}

SQS=seatunnel-connectors-v2/connector-amazonsqs
SQS_T=$SQS/src/test/java/org/apache/seatunnel/connectors/seatunnel/amazonsqs
case_st12038() {
    st_case st12038 st12038 9ebb27e8f92059dee76d71029adbfbaa1c099285 1e450e11f7c8e3ef78d186b0a407148d5faed939 \
        "$SQS" AmazonSqsSourceReaderTest before,after - "$SQS_T/source/AmazonSqsSourceReaderTest.java"
}
# One-line shim: the reader test builds AmazonSqsSourceConfig through its all-arguments
# constructor, which the pull request extended with ignoreParseErrors; dropping that argument
# lets the test compile against the unfixed code. The three tests that ask for
# ignoreParseErrors=true then run with the unfixed reader, which has no such option.
case_st12038-shim() {
    st_case st12038-shim st12038 9ebb27e8f92059dee76d71029adbfbaa1c099285 1e450e11f7c8e3ef78d186b0a407148d5faed939 \
        "$SQS" AmazonSqsSourceReaderTest before,after st12038-reader-test-drop-ignore-arg.patch \
        "$SQS_T/source/AmazonSqsSourceReaderTest.java"
}
# The pull request also extended AmazonSqsSourceFactoryTest; transplanting it as well checks
# whether that part compiles against the unfixed code.
case_st12038-factory() {
    st_case st12038-factory st12038 9ebb27e8f92059dee76d71029adbfbaa1c099285 1e450e11f7c8e3ef78d186b0a407148d5faed939 \
        "$SQS" AmazonSqsSourceFactoryTest before,after - \
        "$SQS_T/source/AmazonSqsSourceReaderTest.java" "$SQS_T/AmazonSqsSourceFactoryTest.java"
}

case_st12360() {
    st_case st12360 st12360 4648c9956ec88dec560a4af27cbd610568f47a60 eb76f81c823af25c9f4d75ba41b986bc8a0dab57 \
        seatunnel-connectors-v2/connector-cdc/connector-cdc-base IncrementalSourceReaderTest before,after - \
        seatunnel-connectors-v2/connector-cdc/connector-cdc-base/src/test/java/org/apache/seatunnel/connectors/cdc/base/source/reader/IncrementalSourceReaderTest.java
}

case_st12472() {
    st_case st12472 st12472 e1a7e64b6733d2b2cd4682190c753a81fac93bc2 87ed0afe0f783eda1b1f3ac6f0ac9fadedcb4f98 \
        seatunnel-edge-agent/seatunnel-edge-agent-connector \
        'FileCollectReaderBehaviorTest#rediscoversFileAfterInactiveCursorClosed' before,after - \
        seatunnel-edge-agent/seatunnel-edge-agent-connector/src/test/java/org/apache/seatunnel/edge/agent/connector/file/FileCollectReaderBehaviorTest.java
}

E2E=seatunnel-e2e/seatunnel-e2e-common
E2E_T=$E2E/src/test/java/org/apache/seatunnel/e2e/common/container
case_st12481() {
    st_case st12481 st12481 7ba68325cb7ea1bf1a28f56c4f9c20695d221df3 0e4cf52896ee3604a8e7899d7736ffd914ee6ce7 \
        "$E2E" 'AbstractTestContainerTest,AbstractTestFlinkContainerTest' before,after - \
        "$E2E_T/AbstractTestContainerTest.java" "$E2E_T/flink/AbstractTestFlinkContainerTest.java"
}
# One-line shim: the Flink test's helper overrides deleteHostVolumeMountPath(), a method the pull
# request added; dropping the @Override annotation lets the test compile against the unfixed code.
# Unfixed tearDown() then deletes the host path /tmp/seatunnel_mnt itself, so the run refuses to
# start while that path exists.
case_st12481-shim() {
    if [ -e /tmp/seatunnel_mnt ]; then
        echo "refusing st12481-shim: /tmp/seatunnel_mnt exists and unfixed teardown would delete it"
        return 1
    fi
    st_case st12481-shim st12481 7ba68325cb7ea1bf1a28f56c4f9c20695d221df3 0e4cf52896ee3604a8e7899d7736ffd914ee6ce7 \
        "$E2E" AbstractTestFlinkContainerTest before,after st12481-flink-test-drop-override.patch \
        "$E2E_T/flink/AbstractTestFlinkContainerTest.java"
}

ALL="df24193 df24917 df24917-diag st12038 st12038-shim st12038-factory st12360 st12472 st12481 st12481-shim"
for c in ${@:-$ALL}; do
    "case_$c" || echo "[$c] setup failed"
done
