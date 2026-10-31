# Destructive commands

This inventory covers every `rm -rf`, `rm -r`, `docker rm`, `docker system prune`
and `docker container rm` in the repository's shell scripts, excluding
`replay-clean/out/`. Line numbers refer to the current scripts. There are no
`rm -r`, `docker system prune` or `docker container rm` commands.

The retired historical Part C scripts exit 2 before any work unless
`REPLAY_HISTORICAL_DESTRUCTIVE=1` is set. They are kept for inspection. Their
SeaTunnel teardown also deletes the host path `/tmp/seatunnel_mnt`; the variable
does not isolate that path or the Docker daemon.

| Script | Line | Command | Affected path or object | Confined to own work or output directory under configured work root? | Guard |
| --- | --- | --- | --- | --- | --- |
| `harness/run_part_b.sh` | 33 | `rm -rf "$out" "$out.src"` | Compiled hook classes and copied sources at `$RT/partB/classes/{dev-hook,patch-hook}` and their `.src` directories | Yes; both callers supply paths under the script's fixed `RT` work root | confined to own work directory (`RT`) |
| `harness/run_part_c.sh` | 37 | `rm -rf "$HC"` | `$RT/partC/harness-classes` | Yes; under the script's fixed `RT` work root | `REPLAY_HISTORICAL_DESTRUCTIVE=1` |
| `model-queries-2026-10-25/run.sh` | 81 | `rm -rf "$b/src"` | `$RUN_WORK/build-<label>/src`, the copied build sources | Yes; under `RUN_WORK` (default `./work` relative to the script) | confined to own work directory (`RUN_WORK`) |
| `replay-2026-10-26/harness/part_b.sh` | 40 | `rm -rf "$out" "$out.src"` | `$W/partB/classes/<name>` and its `.src` directory; callers use fixed hook names | Yes; `W` is `REPLAY_WORK` | confined to own work directory (`REPLAY_WORK`, via `W`) |
| `replay-2026-10-26/harness/historical-part-c/part_c.sh` | 109 | `rm -rf "$OV"` | `$W/partC/before-overrides`, copied sources and compiled classes | Yes; `W` is `REPLAY_WORK` | `REPLAY_HISTORICAL_DESTRUCTIVE=1` |
| `replay-2026-10-26/harness/historical-part-c/part_c.sh` | 122 | `rm -rf "$HC"` | `$W/partC/harness-classes` | Yes; `W` is `REPLAY_WORK` | `REPLAY_HISTORICAL_DESTRUCTIVE=1` |
| `replay-2026-10-26/harness/historical-part-c/part_c.sh` | 206 | `docker rm -f "$id"` | Engine containers attributed to the cell: absent before it, created since its start, matching its engine image and session label | No; objects in the host Docker daemon | `REPLAY_HISTORICAL_DESTRUCTIVE=1`, plus the existing per-cell attribution checks |
| `replay-2026-10-26/harness/historical-part-c/selftest_part_c_guards.sh` | 12 | `rm -rf "$T"` in the exit trap | Temporary directory created by `mktemp -d "${TMPDIR:-/tmp}/part-c-selftest.XXXXXX"` | Yes; the self-test's own temporary work directory | confined to own work directory (`T`, created under `TMPDIR`) |
| `replay-clean/in_container.sh` | 68 | `rm -rf "$B/logs/partA" "$B/logs/partB" "$B/results.json"` | Parts A/B logs and results in the fresh clone at `$SRC/replay-2026-10-26` | Yes; `SRC=/src/records`, `B=$SRC/replay-2026-10-26`, inside the replay container; clone must succeed first | confined to own work directory (`SRC`, via `B`) |
| `replay-clean/selftest_require_toolchain.sh` | 25 | `rm -rf /src` | The self-test container's copied work tree | Yes; literal `/src` inside `docker run`; repository input is mounted read-only at `/ro` and output at `/out` | confined to own work directory (literal `/src`; no directory variable) |
| `replay-clean/selftest_require_toolchain.sh` | 26 | `rm -rf /src/replay-2026-10-26/work /src/replay-clean/out /src/replay-clean/out-selftest` | Work and output directories in the self-test container's copied tree | Yes; under the same container-local `/src` work root | confined to own work directory (literal `/src`; no directory variable) |

`fail-before-2026-10-26/run.sh` has no command matching the inventory above.
Its `st12481_guard` at line 293 requires explicit `st12481-shim` selection and
`FAILBEFORE_DISPOSABLE=1` in a disposable filesystem environment without host-path
mounts. That case invokes teardown that deletes `/tmp/seatunnel_mnt` on the host,
outside `FAILBEFORE_WORK`. The runner refuses an existing path before cloning and
again before execution; it cannot protect files created there during the test.
The two guarded cases were executed once under the guard on 2026-10-31 in a disposable container with no host-path mounts.

Run the offline checks with:

```sh
python3 test_safety.py
python3 fail-before-2026-10-26/test_run_guard.py
```
