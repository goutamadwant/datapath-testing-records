#!/bin/sh
# Model-written regexp_like queries vs DataFusion planning time, before and after PR 24917.
#
#   ./run.sh build      clone apache/datafusion at the two pinned commits into $RUN_WORK and
#                       build with the pinned toolchain and verified lockfiles (--locked)
#   ./run.sh resolve-locks  resolve from each checkout's Cargo.lock and save the resolved
#                       harness lockfiles and lockfiles.sha256 (release profile, shared target)
#   ./run.sh generate   generate queries with both generators into queries/ (needs an
#                       OpenAI-compatible endpoint for G1 and the `claude` client for G2)
#   ./run.sh measure    classify patterns and time planning of every query and control
#   ./run.sh results    rebuild the selected set's results and tables
#   ./run.sh compare SET  compare results.json with results-SET.json in COMPARISON-SET.md
#   ./run.sh all        build, measure, results (uses the queries already in queries/)
#   ./run.sh explore    exploratory (not pre-registered): also build at the last main commit
#                       before issue 22185 was filed and time the controls and a nesting
#                       series at all three commits (logs/exploratory/)
#
# Environment (all optional):
#   RUN_WORK         work directory (default ./work, relative to this script)
#   MEASURE_SET      measurement log directory name (default measure); named sets write
#                    results-<set>.json and logs/<set>/tables.md
#   DATAFUSION_URL   clone URL (default https://github.com/apache/datafusion.git)
#   G1_ENDPOINT      default http://127.0.0.1:11435/v1
#   G1_MODEL         default qwen3-coder-30b-a3b-instruct
#   G2_MODEL         default sonnet
# Generation is not deterministic; `generate` writes new files and refuses to overwrite
# existing ones. A replay of the measurement uses the committed queries/*.jsonl.
set -u
self="$0"
case "$self" in /*) ;; *) self="$PWD/$self" ;; esac
cd "$(dirname "$0")" || exit 2
export RUN_WORK="${RUN_WORK:-./work}"
mkdir -p "$RUN_WORK" logs/build
RUN_WORK="$(cd "$RUN_WORK" && pwd)"
export RUN_WORK
export MEASURE_SET="${MEASURE_SET-measure}"
DATAFUSION_URL="${DATAFUSION_URL:-https://github.com/apache/datafusion.git}"
REV_BEFORE=408527ae58b5b706f5c02df8c37e096122cd8c78   # parent of the PR 24917 merge
REV_AFTER=3dfa245d61dde362e2c077761783bc735931659c    # PR 24917 squash merge
REV_ISSUEDATE=b426232b8a13c641a522bba414e932914f3b79f5  # last main commit before issue 22185 (2026-05-14T21:53:10Z)
export REV_BEFORE REV_AFTER REV_ISSUEDATE

build_steps() (
    # arguments: mode, then label:revision pairs (default before and after)
    mode="$1"; shift
    pairs="${*:-before:$REV_BEFORE after:$REV_AFTER}"
    echo "# $(date '+%Y-%m-%dT%H:%M:%S%z') $mode start"
    uname -a; sysctl -n machdep.cpu.brand_string hw.ncpu hw.memsize 2>/dev/null
    for pair in $pairs; do
      label="${pair%%:*}"
      if [ "$mode" = build ] && [ "$label" != issuedate ] && [ ! -f "harness/plan_time/Cargo.lock.$label" ]; then
        echo "missing harness/plan_time/Cargo.lock.$label; run ./run.sh resolve-locks first" >&2
        exit 1
      fi
    done
    if [ ! -d "$RUN_WORK/src/.git" ]; then
      git init -q "$RUN_WORK/src" || exit 1
      git -C "$RUN_WORK/src" remote add origin "$DATAFUSION_URL" || exit 1
    fi
    git -C "$RUN_WORK/src" fetch -q --depth 2 origin "$REV_AFTER" || exit 1
    case "$pairs" in *issuedate*) git -C "$RUN_WORK/src" fetch -q --depth 1 origin "$REV_ISSUEDATE" || exit 1 ;; esac
    for pair in $pairs; do
      label="${pair%%:*}"; rev="${pair#*:}"
      [ -d "$RUN_WORK/$label" ] || git -C "$RUN_WORK/src" worktree add -q --detach "../$label" "$rev" || exit 1
      echo "$label checkout: $(git -C "$RUN_WORK/$label" rev-parse HEAD)"
      git -C "$RUN_WORK/$label" status --porcelain | sed 's/^/  dirty: /'
    done
    for pair in $pairs; do
      label="${pair%%:*}"
      b="$RUN_WORK/build-$label"
      mkdir -p "$b" || exit 1
      sed -e "s|@LABEL@|$label|g" -e "s|@DATAFUSION@|$RUN_WORK/$label/datafusion/core|g" \
        harness/plan_time/Cargo.toml.in > "$b/Cargo.toml" || exit 1
      rm -rf "$b/src"; cp -R harness/plan_time/src "$b/src" || exit 1
      cp harness/plan_time/rust-toolchain.toml "$b/rust-toolchain.toml" || exit 1
      expected_rustc=$(cat harness/plan_time/TOOLCHAIN.expected) || exit 1
      actual_rustc=$(cd "$b" && rustc --version) || exit 1
      actual_cargo=$(cd "$b" && cargo --version) || exit 1
      echo "$label toolchain:"
      echo "$actual_rustc"
      echo "$actual_cargo"
      if [ "$actual_rustc" != "$expected_rustc" ]; then
        echo "toolchain mismatch for $label: expected '$expected_rustc', got '$actual_rustc'" >&2
        exit 1
      fi
      locked=no
      if [ "$mode" = build ] && [ -f "harness/plan_time/Cargo.lock.$label" ]; then
        expected_hash=$(python3 harness/lockfiles.py verify "$label") || exit 1
        echo "LOCKFILE_SHA256 $label committed $expected_hash"
        cp "harness/plan_time/Cargo.lock.$label" "$b/Cargo.lock" || exit 1
        copied_hash=$(python3 harness/lockfiles.py hash "$b/Cargo.lock") || exit 1
        if [ "$copied_hash" != "$expected_hash" ]; then
          echo "lockfile sha256 mismatch after copying $label" >&2
          exit 1
        fi
        locked=yes
      else
        if [ "$mode" = build ]; then
          if [ "$label" != issuedate ]; then
            echo "missing harness/plan_time/Cargo.lock.$label; run ./run.sh resolve-locks first" >&2
            exit 1
          fi
          echo "no Cargo.lock.$label; falling back to historical resolution from the checkout's Cargo.lock (without --locked)"
        fi
        cp "$RUN_WORK/$label/Cargo.lock" "$b/Cargo.lock" || exit 1
      fi
      cp "$b/Cargo.lock" "$b/Cargo.lock.orig" || exit 1
      initial_hash=$(python3 harness/lockfiles.py hash "$b/Cargo.lock") || exit 1
      echo "LOCKFILE_SHA256 $label before-build $initial_hash"
      echo "# $(date '+%Y-%m-%dT%H:%M:%S%z') cargo build $label"
      start=$(date +%s)
      if [ "$locked" = yes ]; then
        (cd "$b" && CARGO_TARGET_DIR="$RUN_WORK/target" cargo build --release --locked) || exit 1
      else
        (cd "$b" && CARGO_TARGET_DIR="$RUN_WORK/target" cargo build --release) || exit 1
      fi
      end=$(date +%s)
      echo "BUILD_SECONDS $label $((end - start))"
      final_hash=$(python3 harness/lockfiles.py hash "$b/Cargo.lock") || exit 1
      echo "LOCKFILE_SHA256 $label after-build $final_hash"
      if [ "$locked" = yes ] && [ "$final_hash" != "$expected_hash" ]; then
        echo "lockfile sha256 mismatch after building $label: expected $expected_hash, got $final_hash" >&2
        exit 1
      fi
      echo "lockfile changes against the checkout's Cargo.lock ($label):"
      diff "$RUN_WORK/$label/Cargo.lock" "$b/Cargo.lock" | sed 's/^/  /'
      for p in datafusion regex regex-syntax regex-automata arrow tokio; do
        printf '  %s ' "$p"; awk -v p="$p" '$0=="name = \""p"\""{getline; print $3; exit}' "$b/Cargo.lock"
      done
      binary_hash=$(python3 harness/lockfiles.py hash "$RUN_WORK/target/release/plan_time_$label") || exit 1
      printf '%s  %s\n' "$binary_hash" "$RUN_WORK/target/release/plan_time_$label"
    done
    if [ "$mode" = resolve-locks ]; then
      for pair in $pairs; do
        label="${pair%%:*}"
        cp "$RUN_WORK/build-$label/Cargo.lock" "harness/plan_time/Cargo.lock.$label" || exit 1
      done
      python3 harness/lockfiles.py record || exit 1
    fi
    echo "# $(date '+%Y-%m-%dT%H:%M:%S%z') $mode end"
)

build() {
  log="logs/build/build-$(date +%Y%m%dT%H%M%S)-$$.txt"
  status_file="$RUN_WORK/build-status-$$"
  (build_steps "$@"; echo "$?" > "$status_file") 2>&1 | tee "$log"
  tee_status=$?
  build_status=$(cat "$status_file") || return 1
  rm -f "$status_file"
  [ "$tee_status" -eq 0 ] || return "$tee_status"
  return "$build_status"
}

case "${1:-}" in
  build) build build ;;
  resolve-locks) build resolve-locks ;;
  generate) python3 harness/generate.py ;;
  measure) python3 harness/measure.py ;;
  results) python3 harness/analyze.py ;;
  compare) [ "$#" -eq 2 ] || { echo "usage: ./run.sh compare SET" >&2; exit 2; }; python3 harness/compare.py "$2" ;;
  all) build build && python3 harness/measure.py && python3 harness/analyze.py ;;
  explore) build build "issuedate:$REV_ISSUEDATE" && python3 harness/explore.py ;;
  *) sed -n '2,/^set -u/{ /^set -u/!p; }' "$self"; exit 2 ;;
esac
