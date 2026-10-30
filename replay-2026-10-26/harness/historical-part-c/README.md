# Historical Part C scripts: kept for inspection, not for execution

See [SAFETY.md](../../../SAFETY.md) for destructive commands, their scope and required guards.

This directory holds the scripts of Part C of the 2026-10-26 bundle (PR 12481, killed-container
teardown, Table 1 rows 6-7). They were moved here from `harness/` on 2026-10-25 (fourth revision
after the runs; see "Revision (2026-10-25, fourth revision after the runs)" in `../../README.md`).
`replay.sh` does not run them: `./replay.sh --part C` prints why and exits 0, and
`./replay.sh --part all` prints the same reason and runs Parts A and B only.

**Do not run these scripts.** They are kept so that the recorded Part C runs can be read against
the code that produced them.

## What Part C executed

Part C executed SeaTunnel's real end-to-end test framework against the host's Docker daemon. It
was not run in a sandbox, a virtual machine or a disposable container: the engine containers were
started, killed and removed by the Docker Desktop daemon of the workstation described under
"Toolchain" in `../../README.md`, and the teardown under test ran on that host.

That teardown deletes the host path `/tmp/seatunnel_mnt`. In both apache/seatunnel revisions used,
starting an engine container creates the host directory `/tmp/seatunnel_mnt`
(`FileUtils.createNewDir(HOST_VOLUME_MOUNT_PATH)`), and the teardown deletes it
(`FileUtils.deleteFile(HOST_VOLUME_MOUNT_PATH)`): in the parent `7ba68325c` in
`AbstractTestFlinkContainer` and `AbstractTestSparkContainer`, and in the merge `0e4cf5289` through
`AbstractTestContainer.deleteHostVolumeMountPath()`. On Linux and macOS, `HOST_VOLUME_MOUNT_PATH` is
`/tmp/seatunnel_mnt`. Anything at that path on the host, including files that another process puts
there while a cell runs, is deleted by that teardown. The checks that the third revision added to
`part_c.sh` (refuse to start while `/tmp/seatunnel_mnt` or an engine container exists, scoped
cleanup) do not isolate the host and cannot prevent this.

## The recorded runs

The 20 recorded Part C runs (4 cells, 5 runs each) were executed on 2026-10-25 between 13:36 and
14:14 (UTC-7). They are historical records and stay in the bundle unchanged:

- cell logs, run records and build and compile logs: `../../logs/partC/`
  (`flink-before.txt`, `flink-after.txt`, `spark-before.txt`, `spark-after.txt`, `runs.jsonl`,
  `runs.parser-v1.jsonl`, `build-after-0e4cf5289-jdk8.txt`, `compile-*.txt`), and the invocation
  records `../../logs/setup/setup-partC-*.txt`, `toolchain-partC-*.txt` and
  `console-partC-*.txt`;
- the sha256 of every one of those files and the per-run and per-cell results:
  `../../results.json` (`logs`, `partC`);
- the comparison with the article and with the 2026-10-25 bundle: `../../README.md`.

`../make_results.py` still validates these runs from their logs (requested runs, complete
assertion sets, harness validity checks, cell-level checks) every time it regenerates
`results.json`; for that it imports `parse_part_c.py` from this directory. `parse_part_c.py` only
reads log files.

## Files

The files retain the versions published at `harness/` before the move (third revision),
except that `part_c.sh` now requires `REPLAY_HISTORICAL_DESTRUCTIVE=1` before execution.
The table below records the published hashes before that guard was added.
Three of them were revised after the runs; the versions that executed the recorded runs are
identified by `sha256_as_run` in `../../results.json` and are in this repository's history at commit
`4877661`, under their old paths. Paths inside the scripts (for example `$B/harness/parse_part_c.py`
and `$B/harness/java/ReplayKillTeardownTest.java` in `part_c.sh`) refer to the layout before the
move and remain unchanged.

| File | Path before the move (`path_as_run`) | sha256 | sha256_as_run |
| --- | --- | --- | --- |
| `part_c.sh` | `harness/part_c.sh` | `b7757fbd63600d4715781317cf49fbaba5f66de619a178e99453661a252aa865` | `a75658e64990ce934935601d2c3f380003e049f84bd80d52a3243e9844835cdb` |
| `java/ReplayKillTeardownTest.java` | `harness/java/ReplayKillTeardownTest.java` | `b715134750acad0875701c717d2140563dd14f3c49928a6104f0457d9252caf5` | `e0049c6c63c15d6fa037ab6b57261139c54fdd9145b29365e0e2dfe5867be259` |
| `parse_part_c.py` | `harness/parse_part_c.py` | `1bafe4d218af112170e7f373839d11e5d77cbd8db1e12b0d07dda11f09dfe752` | `bdad4ea98f03da6f6321d2237d3d0e5f9c178064604190a8e38fda5e5568802d` |
| `selftest_part_c_guards.sh` | `harness/selftest_part_c_guards.sh` | `cd6f9d9da31fcc373e91643e073cf73f1fcb4a4f9b42eed399722f623eaddcf1` | - (written after the runs) |

`selftest_part_c_guards.sh` exercised the third-revision rules of `part_c.sh` against a simulated
Docker on 2026-10-25 (results in `../../README.md`); two of its scenarios create and remove the real
host directory `/tmp/seatunnel_mnt`.
