#!/usr/bin/env bash
# Model-written regexp_like queries vs DataFusion planning time, before and after PR 24917.
#
#   ./run.sh build      clone apache/datafusion at the two pinned commits into $RUN_WORK and
#                       build harness/plan_time against each (release profile, shared target)
#   ./run.sh generate   generate queries with both generators into queries/ (needs an
#                       OpenAI-compatible endpoint for G1 and the `claude` client for G2)
#   ./run.sh measure    classify patterns and time planning of every query and control
#   ./run.sh results    rebuild results.json and print the tables
#   ./run.sh all        build, measure, results (uses the queries already in queries/)
#   ./run.sh explore    exploratory (not pre-registered): also build at the last main commit
#                       before issue 22185 was filed and time the controls and a nesting
#                       series at all three commits (logs/exploratory/)
#
# Environment (all optional):
#   RUN_WORK         work directory (default ./work, relative to this script)
#   DATAFUSION_URL   clone URL (default https://github.com/apache/datafusion.git)
#   G1_ENDPOINT      default http://127.0.0.1:11435/v1
#   G1_MODEL         default qwen3-coder-30b-a3b-instruct
#   G2_MODEL         default sonnet
# Generation is not deterministic; `generate` writes new files and refuses to overwrite
# existing ones. A replay of the measurement uses the committed queries/*.jsonl.
set -u
cd "$(dirname "$0")" || exit 2
export RUN_WORK="${RUN_WORK:-./work}"
mkdir -p "$RUN_WORK" logs/build
RUN_WORK="$(cd "$RUN_WORK" && pwd)"
export RUN_WORK
DATAFUSION_URL="${DATAFUSION_URL:-https://github.com/apache/datafusion.git}"
REV_BEFORE=408527ae58b5b706f5c02df8c37e096122cd8c78   # parent of the PR 24917 merge
REV_AFTER=3dfa245d61dde362e2c077761783bc735931659c    # PR 24917 squash merge
REV_ISSUEDATE=b426232b8a13c641a522bba414e932914f3b79f5  # last main commit before issue 22185 (2026-05-14T21:53:10Z)
export REV_BEFORE REV_AFTER REV_ISSUEDATE

build() {
  # arguments: label:revision pairs (default before and after)
  local pairs="${*:-before:$REV_BEFORE after:$REV_AFTER}"
  local log="logs/build/build-$(date +%Y%m%dT%H%M%S).txt"
  {
    echo "# $(date '+%Y-%m-%dT%H:%M:%S%z') build start"
    uname -a; sysctl -n machdep.cpu.brand_string hw.ncpu hw.memsize 2>/dev/null
    cargo --version; rustc --version
    if [ ! -d "$RUN_WORK/src/.git" ]; then
      git init -q "$RUN_WORK/src"
      git -C "$RUN_WORK/src" remote add origin "$DATAFUSION_URL"
    fi
    git -C "$RUN_WORK/src" fetch -q --depth 2 origin "$REV_AFTER" || exit 1
    case "$pairs" in *issuedate*) git -C "$RUN_WORK/src" fetch -q --depth 1 origin "$REV_ISSUEDATE" || exit 1 ;; esac
    for pair in $pairs; do
      label="${pair%%:*}"; rev="${pair#*:}"
      [ -d "$RUN_WORK/$label" ] || git -C "$RUN_WORK/src" worktree add -q --detach "../$label" "$rev"
      echo "$label checkout: $(git -C "$RUN_WORK/$label" rev-parse HEAD)"
      git -C "$RUN_WORK/$label" status --porcelain | sed 's/^/  dirty: /'
    done
    for pair in $pairs; do
      label="${pair%%:*}"
      b="$RUN_WORK/build-$label"
      mkdir -p "$b"
      sed -e "s|@LABEL@|$label|g" -e "s|@DATAFUSION@|$RUN_WORK/$label/datafusion/core|g" \
        harness/plan_time/Cargo.toml.in > "$b/Cargo.toml"
      rm -rf "$b/src"; cp -R harness/plan_time/src "$b/src"
      [ -f "$b/Cargo.lock" ] || cp "$RUN_WORK/$label/Cargo.lock" "$b/Cargo.lock"
      cp "$b/Cargo.lock" "$b/Cargo.lock.orig"
      echo "# $(date '+%Y-%m-%dT%H:%M:%S%z') cargo build $label"
      start=$(date +%s)
      (cd "$b" && CARGO_TARGET_DIR="$RUN_WORK/target" cargo build --release 2>&1) || exit 1
      end=$(date +%s)
      echo "BUILD_SECONDS $label $((end - start))"
      echo "lockfile changes against the checkout's Cargo.lock ($label):"
      diff "$RUN_WORK/$label/Cargo.lock" "$b/Cargo.lock" | sed 's/^/  /'
      for p in datafusion regex regex-syntax regex-automata arrow tokio; do
        printf '  %s ' "$p"; awk -v p="$p" '$0=="name = \""p"\""{getline; print $3; exit}' "$b/Cargo.lock"
      done
      shasum -a 256 "$RUN_WORK/target/release/plan_time_$label"
    done
    echo "# $(date '+%Y-%m-%dT%H:%M:%S%z') build end"
  } 2>&1 | tee "$log"
  return "${PIPESTATUS[0]}"
}

case "${1:-}" in
  build) build ;;
  generate) python3 harness/generate.py ;;
  measure) python3 harness/measure.py ;;
  results) python3 harness/analyze.py ;;
  all) build && python3 harness/measure.py && python3 harness/analyze.py ;;
  explore) build "issuedate:$REV_ISSUEDATE" && python3 harness/explore.py ;;
  *) sed -n '2,20p' "$0"; exit 2 ;;
esac
