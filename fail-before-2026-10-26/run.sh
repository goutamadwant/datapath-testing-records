#!/usr/bin/env bash
# Fail-before / pass-after runs for the regression tests named in the article.
#
# Usage: ./run.sh [case ...]
#   cases: df24193 df24917 df24917-diag df24917-budget st12038 st12038-shim st12038-factory st12360
#          st12472 st12481 st12481-shim df24917-budget-nohook
#   (default: all cases except st12481-shim and df24917-budget-nohook, in that order)
#
# For each case:
#   before = first parent of the pull request's merge commit, with ONLY the test change of the
#            pull request applied on top (whole test files, or the test-module hunks of a file that
#            also holds production code; see patches/)
#   after  = the pull request's merge commit, unmodified except for df24917-budget-nohook,
#            which adds a separate hook-free test function on both sides
# The same test command runs on both trees. Every run writes a full log under logs/<case>/ and
# appends one record to logs/runs.jsonl; logs are never overwritten (a repeated run gets a suffix).
# python3 make_results.py then derives the outcome of every run from its log and writes results.json.
#
# Completion: before any build, the requested cases and sides (before and after of every case) are
# appended to logs/requested.json under an invocation id; every record this invocation writes to
# logs/runs.jsonl carries that id. A side whose setup fails (clone, checkout, transplant or patch
# apply, missing JDK, refusal) gets a log and a record with "setup_error" naming the failed step;
# make_results.py reports it as SETUP_ERROR. At the end the script exits 1 if any requested side has
# no record from this invocation or only a setup-error record, and 2 for an unknown case name.
# A failing test is an outcome, not a runner error, and does not change the exit status.
#
# Environment (all optional):
#   FAILBEFORE_WORK   scratch directory for worktrees and the cargo target dir (default ./work)
#   DATAFUSION_REPO   existing local clone of apache/datafusion to add worktrees from
#                     (default: clone https://github.com/apache/datafusion.git into the work dir)
#   SEATUNNEL_REPO    existing local clone of apache/seatunnel (default: clone into the work dir)
#   JAVA8_HOME        JDK 8 used for every SeaTunnel run (default: /usr/libexec/java_home -v 1.8)
#   FAILBEFORE_DISPOSABLE=1 required for explicitly selected st12481-shim; see README Safety
set -u -o pipefail

cd "$(dirname "$0")"
HERE=$(pwd)
WORK=${FAILBEFORE_WORK:-$HERE/work}
LOGS=$HERE/logs
PATCHES=$HERE/patches
mkdir -p "$WORK/trees" "$LOGS"
INVOCATION=$(date -u '+%Y%m%dT%H%M%SZ')-$$
SETUP_OUT=$WORK/setup-$INVOCATION.out
DF_URL=https://github.com/apache/datafusion.git
ST_URL=https://github.com/apache/seatunnel.git

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

now() { python3 -c 'import time; print(time.time())'; }

# begin_side: start the setup of one side; step <description> <cmd...>: run one setup step, its
# output kept in $SETUP_OUT; on failure the step and its exit code are remembered for setup_error.
begin_side() {
    : > "$SETUP_OUT"
    SETUP_STEP=""
    SETUP_RC=0
    TREE=""
    SIDE_START=$(now)
    SIDE_START_DATE=$(date '+%Y-%m-%dT%H:%M:%S%z')
}
step() {
    local desc=$1 rc
    shift
    echo "\$ $desc" >> "$SETUP_OUT"
    "$@" >> "$SETUP_OUT" 2>&1
    rc=$?
    if [ "$rc" -ne 0 ]; then
        SETUP_STEP=$desc
        SETUP_RC=$rc
    fi
    return "$rc"
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
    if [ "$case" = st12481-shim ] && ! step "st12481-shim safety guard before execution" st12481_guard; then
        SETUP_ERROR_LOG=$log setup_error "$case" "$side" "$before" "$after" "$transplant" "$@"
        return 1
    fi
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
    append_record "$case" "$side" "$before" "$after" "$(git -C "$TREE" rev-parse HEAD)" \
        "$transplant" "$*" "$rc" "$start" "$end" "$rel" ""
    echo "[$case/$side] exit $rc in $(python3 -c "print(round($end-$start))") s -> $rel"
}

# setup_error <case> <side> <before_commit> <after_commit> <transplant text> <cmd...>
# Records a side whose setup failed: a log with the failed step and its output, and a record in
# logs/runs.jsonl with "setup_error" set. <cmd> is the test command that was not run.
setup_error() {
    local case=$1 side=$2 before=$3 after=$4 transplant=$5 log rel end head=""
    shift 5
    log=${SETUP_ERROR_LOG:-$(next_log "$case" "$side")}
    rel=${log#"$HERE"/}
    [ -n "$TREE" ] && head=$(git -C "$TREE" rev-parse HEAD 2>/dev/null)
    end=$(now)
    {
        echo "# case: $case"
        echo "# side: $side"
        echo "# before commit (first parent): $before"
        echo "# after commit (merge): $after"
        echo "# tree HEAD: ${head:-none}"
        echo "# transplant: $transplant"
        echo "# host: $(uname -srm)"
        echo "# command (not run): $*"
        echo "# start: $SIDE_START_DATE"
        echo "# setup error: step failed: $SETUP_STEP (exit $SETUP_RC)"
        echo "# setup output:"
        sed 's/^/#   /' "$SETUP_OUT"
        echo "# end: $(date '+%Y-%m-%dT%H:%M:%S%z')"
        echo "# exit code: $SETUP_RC"
    } > "$log"
    append_record "$case" "$side" "$before" "$after" "$head" "$transplant" "$*" "$SETUP_RC" \
        "$SIDE_START" "$end" "$rel" "$SETUP_STEP"
    echo "[$case/$side] SETUP_ERROR at '$SETUP_STEP' (exit $SETUP_RC) -> $rel"
}

# append_record <case> <side> <before> <after> <tree_head> <transplant> <command> <rc> <start> <end>
#               <log> <setup_error or empty>
append_record() {
    python3 - "$LOGS/runs.jsonl" "$INVOCATION" "$@" <<'EOF'
import json, sys
f, inv, case, side, before, after, head, transplant, cmd, rc, start, end, log, setup = sys.argv[1:]
rec = dict(case=case, side=side, before_commit=before, after_commit=after, tree_head=head,
           transplant=transplant, command=cmd, exit_code=int(rc),
           started_epoch=float(start), ended_epoch=float(end),
           duration_s=round(float(end) - float(start), 1), log=log, invocation=inv)
if setup:
    rec["setup_error"] = setup
with open(f, "a") as fh:
    fh.write(json.dumps(rec) + "\n")
EOF
}

# ---------------------------------------------------------------- DataFusion
df_tree() { # commit: clone if needed, then worktree "df" at <commit>
    step "clone $DF_URL" ensure_repo "$DF_URL" "$DF_REPO" &&
        step "check out $1" prep_tree "$DF_REPO" df "$1"
}

df_transplant() { # kind arg after_commit: apply the test change to $TREE
    if [ "$1" = patch ]; then
        step "apply patches/$2" git -C "$TREE" apply "$PATCHES/$2"
    else
        step "copy $2 from $3" git -C "$TREE" checkout "$3" -- "$2"
    fi
}

df_case() { # case before after test_cmd transplant_kind transplant_arg
    local case=$1 before=$2 after=$3 cmd=$4 kind=$5 arg=$6 text
    if [ "$kind" = patch ]; then
        text="patches/$arg applied (test-module hunks only)"
    else
        text="$arg copied from $after"
    fi
    df -h "$WORK" | tail -1
    begin_side
    if df_tree "$before" && df_transplant "$kind" "$arg" "$after"; then
        # shellcheck disable=SC2086
        run_one "$case" before "$before" "$after" "$text" - $cmd
    else
        # shellcheck disable=SC2086
        setup_error "$case" before "$before" "$after" "$text" $cmd
    fi
    begin_side
    if df_tree "$after"; then
        # shellcheck disable=SC2086
        run_one "$case" after "$before" "$after" "none (merge commit as is)" - $cmd
    else
        # shellcheck disable=SC2086
        setup_error "$case" after "$before" "$after" "none (merge commit as is)" $cmd
    fi
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
    local loop="rc=0; for i in 1 2 3; do $cmd || rc=1; done; exit \$rc"
    local text="$t copied from $after; then patches/$p applied"
    begin_side
    if df_tree "$before" && step "copy $t from $after" git -C "$TREE" checkout "$after" -- "$t" &&
        step "apply patches/$p" git -C "$TREE" apply "$PATCHES/$p"; then
        run_one df24917-diag before "$before" "$after" "$text" - sh -c "$loop"
    else
        setup_error df24917-diag before "$before" "$after" "$text" sh -c "$loop"
    fi
    begin_side
    if df_tree "$after" && step "apply patches/$p" git -C "$TREE" apply "$PATCHES/$p"; then
        run_one df24917-diag after "$before" "$after" "patches/$p applied" - sh -c "$loop"
    else
        setup_error df24917-diag after "$before" "$after" "patches/$p applied" sh -c "$loop"
    fi
}

# PR 24917 also added test_constant_regex_respects_planning_budget to the logical expression
# simplifier (datafusion-optimizer) and to the physical expression simplifier
# (datafusion-physical-expr). Both live in the files that hold the fix, so only the hunks that add
# these tests (and the imports of the physical test) are applied on the parent
# (patches/df24917-budget-tests-only.patch). --no-fail-fast: run both packages' tests even if one fails.
case_df24917-budget() {
    df_case df24917-budget 408527ae58b5b706f5c02df8c37e096122cd8c78 3dfa245d61dde362e2c077761783bc735931659c \
        "cargo test --locked --profile ci --no-fail-fast -p datafusion-optimizer -p datafusion-physical-expr --lib test_constant_regex_respects_planning_budget" \
        patch df24917-budget-tests-only.patch
}

# Apply a test patch on either side, including the merge commit.
df_patched_side() { # case side before after patch cmd...
    local case=$1 side=$2 before=$3 after=$4 patch=$5 commit text
    shift 5
    commit=$before
    [ "$side" = before ] || commit=$after
    text="patches/$patch applied (hook-free test-module hunks only)"
    begin_side
    if df_tree "$commit" && df_transplant patch "$patch" "$after"; then
        run_one "$case" "$side" "$before" "$after" "$text" - "$@"
    else
        setup_error "$case" "$side" "$before" "$after" "$text" "$@"
    fi
}

# Separate functions retain only the original regex assertions, without a UDF hook or column case.
case_df24917-budget-nohook() {
    local side
    for side in before after; do
        df_patched_side df24917-budget-nohook "$side" \
            408527ae58b5b706f5c02df8c37e096122cd8c78 3dfa245d61dde362e2c077761783bc735931659c \
            "df24917-budget-nohook-$side.patch" \
            cargo test --locked --profile ci --no-fail-fast -p datafusion-optimizer \
            -p datafusion-physical-expr --lib test_constant_regex_planning_budget_without_hook
    done
}

# ---------------------------------------------------------------- SeaTunnel
mvn_cmd() { # module test-selector
    # package, not test: upstream modules such as seatunnel-config-shade are only usable by the
    # reactor once their shaded jar exists (a first attempt with "clean test" failed there).
    echo "./mvnw -B -ntp -pl $1 -am -DskipUT=false -DskipIT=true -Dskip.spotless=true -Dspotless.check.skip=true -Dspotless.apply.skip=true -Dlicense.skipAddThirdParty=true -Dtest=$2 -DfailIfNoTests=false clean package"
}

# The parent-side teardown deletes this real host path even with mocked containers.
st12481_guard() {
    local hazard="st12481-shim host-deletion hazard: FileUtils.deleteFile(HOST_VOLUME_MOUNT_PATH) deletes $ST_REFUSE_IF_EXISTS on the real host filesystem even with mocked containers. Requires explicit st12481-shim selection and FAILBEFORE_DISPOSABLE=1 in a disposable filesystem environment without host-path mounts."
    echo "$hazard" >&2
    if [ "${EXPLICIT_CASES:-0}" -eq 0 ] || [ "${FAILBEFORE_DISPOSABLE:-}" != 1 ]; then
        return 1
    fi
    if [ -e "$ST_REFUSE_IF_EXISTS" ] || [ -L "$ST_REFUSE_IF_EXISTS" ]; then
        echo "refuse: $ST_REFUSE_IF_EXISTS exists; unfixed teardown would delete it" >&2
        return 1
    fi
}

# st_tree <tree> <commit>: safety guard, JDK 8 present, clone, worktree
st_tree() {
    { [ -z "${ST_REFUSE_IF_EXISTS:-}" ] ||
        step "st12481-shim safety guard before clone" st12481_guard; } &&
        step "find JDK 8 (JAVA8_HOME=$JAVA8_HOME)" test -n "$JAVA8_HOME" -a -x "$JAVA8_HOME/bin/javac" &&
        step "clone $ST_URL" ensure_repo "$ST_URL" "$ST_REPO" &&
        step "check out $2" prep_tree "$ST_REPO" "$1" "$2"
}

# st_case <case> <tree> <before> <after> <module> <selector> <sides> <patch or -> <test files...>
st_case() {
    local case=$1 tree=$2 before=$3 after=$4 module=$5 sel=$6 sides=$7 patch=$8 f text cmd
    shift 8
    export JAVA_HOME=$JAVA8_HOME
    cmd=$(mvn_cmd "$module" "$sel")
    if [[ $sides == *before* ]]; then
        text=""
        for f in "$@"; do
            text="$text$f copied from $after; "
        done
        if [ "$patch" != - ]; then
            text="${text}then patches/$patch applied"
        fi
        begin_side
        if st_tree "$tree" "$before" && st_copy "$after" "$@" &&
            { [ "$patch" = - ] || step "apply patches/$patch" git -C "$TREE" apply "$PATCHES/$patch"; }; then
            # shellcheck disable=SC2086
            run_one "$case" before "$before" "$after" "$text" "$module" $cmd
        else
            # shellcheck disable=SC2086
            setup_error "$case" before "$before" "$after" "$text" $cmd
        fi
    fi
    if [[ $sides == *after* ]]; then
        begin_side
        if st_tree "$tree" "$after"; then
            # shellcheck disable=SC2086
            run_one "$case" after "$before" "$after" "none (merge commit as is)" "$module" $cmd
        else
            # shellcheck disable=SC2086
            setup_error "$case" after "$before" "$after" "none (merge commit as is)" $cmd
        fi
    fi
}

st_copy() { # after_commit files...: copy the test files from the merge commit into $TREE
    local after=$1 f
    shift
    for f in "$@"; do
        step "copy $f from $after" git -C "$TREE" checkout "$after" -- "$f" || return 1
    done
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
# Unfixed tearDown() deletes /tmp/seatunnel_mnt on the host; explicit disposable runs only.
case_st12481-shim() {
    local ST_REFUSE_IF_EXISTS=/tmp/seatunnel_mnt
    echo "st12481-shim host-deletion hazard: teardown deletes $ST_REFUSE_IF_EXISTS on the real host filesystem; requires explicit selection and FAILBEFORE_DISPOSABLE=1 in a disposable filesystem environment without host-path mounts." >&2
    st_case st12481-shim st12481 7ba68325cb7ea1bf1a28f56c4f9c20695d221df3 0e4cf52896ee3604a8e7899d7736ffd914ee6ce7 \
        "$E2E" AbstractTestFlinkContainerTest before,after st12481-flink-test-drop-override.patch \
        "$E2E_T/flink/AbstractTestFlinkContainerTest.java"
}

ALL="df24193 df24917 df24917-diag df24917-budget st12038 st12038-shim st12038-factory st12360 st12472 st12481"
EXPLICIT_CASES=$#
CASES=${*:-$ALL}
for c in $CASES; do
    declare -F "case_$c" > /dev/null || { echo "unknown case: $c (cases: $ALL st12481-shim df24917-budget-nohook)" >&2; exit 2; }
done

# Requested cases and sides, written before any build.
# shellcheck disable=SC2086
python3 - "$LOGS/requested.json" "$INVOCATION" "$(date '+%Y-%m-%dT%H:%M:%S%z')" $CASES <<'EOF' || exit 1
import json, os, sys
f, inv, ts, *cases = sys.argv[1:]
hist = json.load(open(f)) if os.path.exists(f) else []
hist.append({"invocation": inv, "requested_at": ts, "cases": cases,
             "sides": [{"case": c, "side": s} for c in cases for s in ("before", "after")]})
with open(f + ".tmp", "w") as fh:
    fh.write(json.dumps(hist, indent=2) + "\n")
os.replace(f + ".tmp", f)
EOF
echo "invocation $INVOCATION: $CASES"

for c in $CASES; do
    "case_$c" || echo "[$c] case returned non-zero"
done
rm -f "$SETUP_OUT"

# Completion check: every requested side needs a record from this invocation that is not a setup error.
python3 - "$LOGS/requested.json" "$LOGS/runs.jsonl" "$INVOCATION" <<'EOF'
import json, os, sys
req_f, runs_f, inv = sys.argv[1:]
req = next(r for r in json.load(open(req_f)) if r["invocation"] == inv)
runs = [json.loads(l) for l in open(runs_f) if l.strip()] if os.path.exists(runs_f) else []
mine = {(r["case"], r["side"]): r for r in runs if r.get("invocation") == inv}
bad = 0
for s in req["sides"]:
    r = mine.get((s["case"], s["side"]))
    if r is None:
        print(f"INCOMPLETE {s['case']}/{s['side']}: no record from invocation {inv}")
        bad += 1
    elif r.get("setup_error"):
        print(f"INCOMPLETE {s['case']}/{s['side']}: setup error at {r['setup_error']!r} ({r['log']})")
        bad += 1
print(f"invocation {inv}: {len(req['sides']) - bad}/{len(req['sides'])} requested sides ran")
sys.exit(1 if bad else 0)
EOF
