# Replay bundle 2026-10-26: Table 1 rows 1-7 and the PR 12472 stall records

This bundle is the second reconstruction of the SeaTunnel records behind the article's Table 1
(rows 1-7) and the PR 12472 stall-injection rates. The first reconstruction, the 2026-10-25
bundle, is kept unchanged at the root of the records repository. Both bundles are reconstructions: the original harnesses of PRs 12468,
12472 and 12481 were never published and their logs were not kept. The harnesses were rewritten
from the pull-request texts.

Every value this README and `results.json` give for this bundle's runs is parsed from a log
under `logs/` that an executed run wrote. The "Article" columns quote, word for word, Table 1 and
the PR 12472 stall counts of the article revision of 25 October 2026 that cites these records at
commit `fe561f6`; that revision's Table 1 reports this bundle's runs (see "Results" below). The
"2026-10-25" columns are read from the 2026-10-25 bundle's `results.json`. Failed, interrupted and
invalid runs are kept. `results.json` lists the sha256 of every file under `logs/`. The comparison
tables below are printed by `harness/tables.py` from `results.json`.

**Part C is no longer run by `replay.sh`** (fourth revision, 2026-10-25). Its 20 recorded runs are
historical records: their logs stay under `logs/partC/` and their hashes in `results.json`. The
scripts that ran them are in `harness/historical-part-c/`, kept for inspection and not for
execution; see "Revision (2026-10-25, fourth revision after the runs)" below.

The runs were executed on 2026-10-25 between 13:26 and 14:26 local time (UTC-7) on the
machine described under "Toolchain". The directory name gives the bundle date, not the run date.

## What changed compared with the 2026-10-25 bundle

| Topic | 2026-10-25 bundle | This bundle |
| --- | --- | --- |
| Entry point | separate scripts with absolute workstation paths; prepared worktrees, warm repository and launcher jar assumed | one script, `./replay.sh --part A\|B\|C\|all [--runs N]` when the runs were made (since the fourth revision it runs Parts A and B only). It checks the toolchain, clones apache/seatunnel at the six pinned commits into `./work`, creates the worktrees, builds, fetches the wrapper and launcher jars from Maven Central (sha1 checked), warms the Part A mirror repository from Maven Central, runs the parts and regenerates `results.json`. Scripts and configs contain no absolute workstation path |
| Part A repetitions | 1 run per cell | 5 runs per cell, interleaved (repetition k of every cell before repetition k+1 of any cell); 24 cells, 120 runs |
| Part A empty-body 429 variant | `before` only, 1 run per JDK | separate labelled cell, `before` and `after`, 5 runs each per JDK |
| Part B | one 20-iteration loop per cell | one more 20-iteration loop per cell, same hooks and sweep positions (50 iterations for the contention cells); results added to the sweep table |
| Part C | outcome lines only; any Docker inspection error counted as "removed"; cleanup errors suppressed | explicit assertions, one `ASSERT` line each, every result recorded: container absent after teardown (Docker 404 only), teardown and next-job time bounds, next-job exit code, new TaskManager at its own JobManager, no leftover container before and after each run. The script adds cell-level checks (JVM completed, no engine container left, no new Docker network, cell time bound, host mount directory absent) |
| Logs | could be overwritten by a re-run | never overwritten: Part A renames a leftover log of an interrupted run to `*.interrupted-<epoch>`, and Parts B and C number the logs of repeated invocations (neither occurred) |
| CI evidence | inline links in the article | saved GitHub Actions records transcribed into `../ci-evidence/` (run ids and retrieval times as saved) |

## Exact commands

From a checkout of this directory (bash, git, curl, python3, patch, shasum; JDK 8 and JDK 11 with
`javac`; Docker is not used):

```
./replay.sh --part all                 # A (5 runs/cell) and B (1 loop/cell); Part C is not run
./replay.sh --part A --runs 5          # one part; --runs = runs per cell (A) or loops per cell (B)
./replay.sh --part B --prepare-only    # toolchain check, clone, worktrees, builds; no runs
./replay.sh --part B --cells "dev-hook-jdk8 patch-hook-jdk8"   # a subset of cells
python3 harness/make_results.py        # validate the recorded runs, then regenerate results.json
python3 harness/tables.py --old <2026-10-25 results.json>      # print the comparison tables
python3 harness/selftest_validation.py # negative tests of the validation (temporary copies)
```

**Part C is not run.** `./replay.sh --part C` prints the following reason and exits 0 before it
creates, clones, builds or contacts anything; `./replay.sh --part all` prints the same reason and
runs Parts A and B only. Part C executed SeaTunnel's real end-to-end teardown against the host's
Docker daemon, not in a sandbox, and that teardown deletes the host path `/tmp/seatunnel_mnt`.
The recorded Part C runs are historical records; their logs stay under `logs/partC/`, their
hashes in `results.json`, and `harness/make_results.py` still validates them from those logs. The
Part C scripts are kept in `harness/historical-part-c/` for inspection, not for execution (see
its `README.md`).

Optional environment: `JAVA8_HOME`, `JAVA11_HOME` (otherwise found with `/usr/libexec/java_home`
or under `/usr/lib/jvm`, and a JDK must contain `javac`), `REPLAY_WORK` (default `./work`),
`REPLAY_SEATUNNEL_URL`, `REPLAY_MAVEN_REPO` (local Maven repository for the Part B build;
default: Maven's own). Part A skips runs that are already recorded in `logs/partA/runs.jsonl`.
Part B adds new logs (`loop2.txt`) next to the existing ones. A fresh replay of Parts A and B
therefore starts from a copy of this directory without `logs/partA`, `logs/partB`, the Part A and
Part B files in `logs/setup/`, and `results.json`; keeping `logs/partC/` and
`logs/setup/*partC*` keeps the historical Part C records in the regenerated `results.json`.

`results.json` is written only if validation passes. The requested matrix is read from the
invocation records (`logs/setup/setup-part*-*.txt`, first line, `prepare_only=0`): the cells
named there (all cells by default) and `--runs` (Part A: runs per cell; Part B: loops added per
cell; Part C: runs added per cell). A missing or unparsable run log, a record that disagrees with
its log, or fewer recorded or valid runs than requested is listed on stderr, `results.json` is left
unchanged, and `replay.sh` exits 1. Each cell in `results.json` has `runs_requested`,
`runs_recorded` and `runs_valid`.

The invocations that produced this bundle, in order (consoles in `logs/setup/` and
`logs/partA/console.txt`). The two Part C invocations ran with the replay script of that time;
the current `replay.sh` no longer runs them:

```
./replay.sh --part A --runs 5          # 13:26-14:16
./replay.sh --part B --prepare-only    # 13:27-13:29, overlapping Part A
./replay.sh --part C --prepare-only    # 13:29-13:35, overlapping Part A
./replay.sh --part C --runs 5          # 13:36-14:14, overlapping Part A
./replay.sh --part A --prepare-only    # 14:17, records logs/partA/maven-version.txt
./replay.sh --part B --runs 1          # 14:17-14:26, alone
python3 harness/make_results.py
```

## Toolchain

Records: `logs/setup/toolchain-*.txt`, `logs/partA/maven-version.txt`, the header of every log.

- Host: Apple M1 Pro (10 cores), 16 GB, macOS 27.0 (26A428). Normal desktop load from other
  applications was present. The 1-minute load averages in the toolchain records are 5.4-9.5. In
  the Part B log headers they are 2.4-5.9, except 17.9 before `dev-nohook-contention-jdk11`,
  which directly followed the JDK 8 busy-loop cell. The machine was not isolated.
- JDK 8: Oracle `1.8.0_172-b11`; JDK 11: Temurin `11.0.19+7`. Both are x86_64 builds and ran
  under Rosetta 2.
- Maven 3.8.4 through the project wrapper (maven-wrapper 3.1.0), wagon-http 3.4.3 (shaded),
  maven-resolver 1.6.3. The wrapper distribution was downloaded from Maven Central into
  `work/mvn-home` (zip sha256 `ccd67d1ee4fd79339c9b6f95d1e5e1e0e0209a8c1b095d9291e009afa0a492a5`).
  The maven-wrapper 3.1.0 jar (sha1 `32f70e9f2cd92fd7629aba8214d1c9ae58a1e2fd`) and the
  junit-platform-launcher 1.9.0 jar were fetched from Maven Central and matched Central's `.sha1`.
- Python 3.12.7, git 2.55.0, curl 8.9.1 (`wget` is not installed), GNU bash 5.3.15.
- Docker Desktop 29.9.2, linux/arm64 VM. The Flink and Spark images are amd64 and ran under
  emulation: `tyrantlucifer/flink:1.18.0-scala_2.12_hadoop27`
  (`sha256:462136d88da3d4fcddd3c43dcfee401d872f4ed3d8c32c6250f65fd85f3474e7`) and
  `tyrantlucifer/spark:3.3.0`
  (`sha256:3589672d223cedfc5570c1df91e88c598683a3001472d1290e1dc0eab208ce8d`).

Fresh in `work/` for this bundle: the apache/seatunnel clone and its three worktrees, the Maven
wrapper distribution, the Part A warm repository and the two jars. Present on the host before the
run: both JDKs, Docker and the two engine images, and the Maven local repository used by the
Part B and C builds. Those builds downloaded nothing: no `Downloaded from` line appears in
`logs/partB/build-*.txt` or `logs/partC/build-*.txt`. The bundle was not replayed on a second
machine.

Revisions (apache/seatunnel):

| Use | Commit |
| --- | --- |
| PR 12468 "before" (parent of the merge) | `a1084015eeb390a6c7f53d3ce7391217e427e4d9` |
| PR 12468 "after" (merge) | `ae7c919bcb78f03446dbd2b754a2b9882602946a` |
| PR 12472 unchanged `dev` (as named in the PR) | `deb16a3c3152f0349a587a504dccc997a131a9d7` |
| PR 12472 patched (merge) | `87ed0afe0f783eda1b1f3ac6f0ac9fadedcb4f98` |
| PR 12481 "before" (parent of the merge) | `7ba68325cb7ea1bf1a28f56c4f9c20695d221df3` |
| PR 12481 "after" (merge) | `0e4cf52896ee3604a8e7899d7736ffd914ee6ce7` |

## Results: article vs 2026-10-25 vs this run, per cell

"Article" quotes, word for word, the article revision of 25 October 2026 that cites these records
at commit `fe561f6`: its Table 1 for Parts A and C, and its text for the PR 12472 stall counts
(marked "(text)"); the empty-body 429 variant is not in Table 1. That Table 1 reports this bundle's runs (the
2026-10-26 column), five runs per cell. An earlier version of this README quoted an earlier
article text, whose Table 1 reported the 2026-10-25 runs. "PR 12472" quotes the pull request.
"Primary-path
requests" counts the GET requests the fault mirror logged for
`junit/junit/4.13.2/junit-4.13.2.pom`, the first fault target. Wrapper times are measured from
the first wrapper-jar request. Wall times cover the whole `./mvnw` process.

#### Part A (PR 12468; Table 1 rows 1-5)

| Row | Fault | Config | JDK | Article (Table 1, 25 Oct 2026 revision) | 2026-10-25 (n=1) | 2026-10-26 (n per cell as listed) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | HTTP 503 on first 2 requests | before | jdk8 | fails on first 503, 5/5 per JDK | FAIL; primary-path requests: 1 | 0 PASS / 5 FAIL; primary-path requests per run: 1,1,1,1,1; wall 5.4/6.2/11.7 s (min/median/max) |
| 1 | HTTP 503 on first 2 requests | after | jdk8 | succeeds on third request, 5/5 per JDK | PASS; primary-path requests: 3 | 5 PASS / 0 FAIL; primary-path requests per run: 3,3,3,3,3; wall 19.7/22.9/36.9 s (min/median/max) |
| 2 | Connection reset on first 4 requests | before | jdk8 | fails after four attempts, 5/5 per JDK | FAIL; primary-path requests: 4 | 0 PASS / 5 FAIL; primary-path requests per run: 4,4,4,4,4; wall 5.1/6.4/11.4 s (min/median/max) |
| 2 | Connection reset on first 4 requests | after | jdk8 | succeeds on fifth, 5/5 per JDK | PASS; primary-path requests: 5 | 5 PASS / 0 FAIL; primary-path requests per run: 5,5,5,5,5; wall 10.0/13.0/16.1 s (min/median/max) |
| 3 | HTTP 429 on first 2 requests | before | jdk8 | closed-stream error after receiving 200, 5/5 per JDK; unlike the PR | FAIL; primary-path requests: 3 | 0 PASS / 5 FAIL; primary-path requests per run: 3,3,3,3,3; `Attempted read from closed stream` in 5/5; wall 20.2/21.9/26.6 s (min/median/max) |
| 3 | HTTP 429 on first 2 requests | after | jdk8 | succeeds, 5/5 per JDK | PASS; primary-path requests: 3 | 5 PASS / 0 FAIL; primary-path requests per run: 3,3,3,3,3; wall 20.1/27.7/31.5 s (min/median/max) |
| 4 | First response body cut off halfway | before | jdk8 | fails, 5/5 per JDK | FAIL; primary-path requests: 1 | 0 PASS / 5 FAIL; primary-path requests per run: 1,1,1,1,1; wall 5.2/9.1/11.5 s (min/median/max) |
| 4 | First response body cut off halfway | after | jdk8 | fails without retry, 5/5 per JDK; earlier JDK 11 hang not reproduced | FAIL; primary-path requests: 1 | 0 PASS / 5 FAIL; primary-path requests per run: 1,1,1,1,1; wall 5.0/6.8/12.3 s (min/median/max) |
| 5 | Wrapper jar 429 for 30 s | before | jdk8 | five attempts; main class not found, 5/5 per JDK | FAIL; primary-path requests: 0; wrapper-jar requests 5, last at 20.5 s | 0 PASS / 5 FAIL; primary-path requests per run: 0,0,0,0,0; wrapper-jar requests per run: 5,5,5,5,5, last at 20.2-20.9 s; main class not found in 5/5; wall 20.6/21.3/22.9 s (min/median/max) |
| 5 | Wrapper jar 429 for 30 s | after | jdk8 | fourth attempt succeeds, 5/5 per JDK | PASS; primary-path requests: 1; wrapper-jar requests 4, last at 35.6 s | 5 PASS / 0 FAIL; primary-path requests per run: 1,1,1,1,1; wrapper-jar requests per run: 4,4,4,4,4, last at 35.2-35.3 s; wall 46.0/47.6/54.0 s (min/median/max) |
| 3 (variant) | HTTP 429 with empty body on first 2 requests (not a Table 1 row) | before | jdk8 | - (not in Table 1) | PASS; primary-path requests: 4 | 5 PASS / 0 FAIL; primary-path requests per run: 4,4,4,4,4; checksum-triggered re-download in 5/5; wall 86.1/89.8/91.6 s (min/median/max) |
| 3 (variant) | HTTP 429 with empty body on first 2 requests (not a Table 1 row) | after | jdk8 | - (not in Table 1) | not run | 5 PASS / 0 FAIL; primary-path requests per run: 3,3,3,3,3; wall 20.6/23.0/26.5 s (min/median/max) |
| 1 | HTTP 503 on first 2 requests | before | jdk11 | fails on first 503, 5/5 per JDK | FAIL; primary-path requests: 1 | 0 PASS / 5 FAIL; primary-path requests per run: 1,1,1,1,1; wall 5.1/6.2/8.2 s (min/median/max) |
| 1 | HTTP 503 on first 2 requests | after | jdk11 | succeeds on third request, 5/5 per JDK | PASS; primary-path requests: 3 | 5 PASS / 0 FAIL; primary-path requests per run: 3,3,3,3,3; wall 19.2/22.5/24.1 s (min/median/max) |
| 2 | Connection reset on first 4 requests | before | jdk11 | fails after four attempts, 5/5 per JDK | FAIL; primary-path requests: 4 | 0 PASS / 5 FAIL; primary-path requests per run: 4,4,4,4,4; wall 5.0/6.6/7.9 s (min/median/max) |
| 2 | Connection reset on first 4 requests | after | jdk11 | succeeds on fifth, 5/5 per JDK | PASS; primary-path requests: 5 | 5 PASS / 0 FAIL; primary-path requests per run: 5,5,5,5,5; wall 9.3/11.8/13.2 s (min/median/max) |
| 3 | HTTP 429 on first 2 requests | before | jdk11 | closed-stream error after receiving 200, 5/5 per JDK; unlike the PR | FAIL; primary-path requests: 3 | 0 PASS / 5 FAIL; primary-path requests per run: 3,3,3,3,3; `Attempted read from closed stream` in 5/5; wall 20.0/22.6/23.8 s (min/median/max) |
| 3 | HTTP 429 on first 2 requests | after | jdk11 | succeeds, 5/5 per JDK | PASS; primary-path requests: 3 | 5 PASS / 0 FAIL; primary-path requests per run: 3,3,3,3,3; wall 20.9/23.0/28.2 s (min/median/max) |
| 4 | First response body cut off halfway | before | jdk11 | fails, 5/5 per JDK | FAIL; primary-path requests: 1 | 0 PASS / 5 FAIL; primary-path requests per run: 1,1,1,1,1; wall 5.5/7.0/7.4 s (min/median/max) |
| 4 | First response body cut off halfway | after | jdk11 | fails without retry, 5/5 per JDK; earlier JDK 11 hang not reproduced | FAIL; primary-path requests: 1 | 0 PASS / 5 FAIL; primary-path requests per run: 1,1,1,1,1; wall 5.4/5.6/7.0 s (min/median/max) |
| 5 | Wrapper jar 429 for 30 s | before | jdk11 | five attempts; main class not found, 5/5 per JDK | FAIL; primary-path requests: 0; wrapper-jar requests 5, last at 20.2 s | 0 PASS / 5 FAIL; primary-path requests per run: 0,0,0,0,0; wrapper-jar requests per run: 5,5,5,5,5, last at 20.2-20.2 s; main class not found in 5/5; wall 20.7/20.8/21.0 s (min/median/max) |
| 5 | Wrapper jar 429 for 30 s | after | jdk11 | fourth attempt succeeds, 5/5 per JDK | PASS; primary-path requests: 1; wrapper-jar requests 4, last at 35.2 s | 5 PASS / 0 FAIL; primary-path requests per run: 1,1,1,1,1; wrapper-jar requests per run: 4,4,4,4,4, last at 35.2-35.2 s; wall 44.7/49.1/55.1 s (min/median/max) |
| 3 (variant) | HTTP 429 with empty body on first 2 requests (not a Table 1 row) | before | jdk11 | - (not in Table 1) | PASS; primary-path requests: 4 | 5 PASS / 0 FAIL; primary-path requests per run: 4,4,4,4,4; checksum-triggered re-download in 5/5; wall 84.7/87.0/93.0 s (min/median/max) |
| 3 (variant) | HTTP 429 with empty body on first 2 requests (not a Table 1 row) | after | jdk11 | - (not in Table 1) | not run | 5 PASS / 0 FAIL; primary-path requests per run: 3,3,3,3,3; wall 19.4/22.5/25.7 s (min/median/max) |

#### Part B (PR 12472)

| Cell | Article (25 Oct 2026 revision) | PR 12472 | 2026-10-25 | 2026-10-26 |
| --- | --- | --- | --- | --- |
| dev-hook-jdk8 | (text) 17/20 failures on unchanged dev with JDK 8 | 15/20 failed | 20/20 failed | 17/20 failed |
| dev-hook-jdk11 | (text) 19/20 with JDK 11 | 7/20 failed | 20/20 failed | 19/20 failed |
| patch-hook-jdk8 | (text) The patch failed 0/20 per JDK under different stalls | 0/20 failed | 0/20 failed | 0/20 failed |
| patch-hook-jdk11 | (text) The patch failed 0/20 per JDK under different stalls | 0/20 failed | 0/20 failed | 0/20 failed |
| dev-nohook-contention-jdk8 | (text) unhooked dev passed 50/50 under CPU contention | 0/50 failed (50/50 passed) | 0/50 failed | 0/50 failed |
| dev-nohook-contention-jdk11 | (text) unhooked dev passed 50/50 under CPU contention | 0/50 failed (50/50 passed) | 0/50 failed | 0/50 failed |

#### Part B sensitivity sweep (stall placed at <= N ms before `idleDeadlineMs`)

| N | JDK 8, 2026-10-25 | JDK 8, 2026-10-26 | JDK 11, 2026-10-25 | JDK 11, 2026-10-26 |
| --- | --- | --- | --- | --- |
| 35 (primary reading) | 20/20 | 17/20 | 20/20 | 19/20 |
| 45 | 17/20 | 18/20 | 18/20 | 16/20 |
| 55 | 11/20 | 10/20 | 11/20 | 11/20 |
| 65 | 7/20 | 4/20 | 2/20 | 4/20 |

Pooled hook wake position vs failure, 2026-10-26 dev-hook loops:

| Closing poll woke | Iterations | Failed |
| --- | --- | --- |
| woke before idleDeadlineMs | 35 | 0 |
| woke 0-9 ms after | 36 | 18 |
| woke 10-19 ms after | 35 | 31 |
| woke >= 20 ms after | 54 | 50 |
| no stall injected | 0 | 0 |

#### Part C (PR 12481; Table 1 rows 6-7)

| Cell | Article (Table 1, 25 Oct 2026 revision) | 2026-10-25 (n=5) | 2026-10-26 |
| --- | --- | --- | --- |
| flink-before | teardown threw, containers left, 5/5; next job timed out at 150 s, 3/5 | teardown threw 5/5; next job exit 0 3/5; hung 2/5 | teardown threw 5/5; killed engine's containers absent after teardown 0/5; next job exit 0 2/5; timed out 3/5 |
| flink-after | teardown completed, containers removed, next job exited 0, 5/5 | teardown threw 0/5; next job exit 0 5/5; hung 0/5 | teardown threw 0/5; killed engine's containers absent after teardown 5/5; next job exit 0 5/5; timed out 0/5 |
| spark-before | Spark: teardown threw, master left, next job exited 0, 5/5 | teardown threw 5/5; next job exit 0 5/5; hung 0/5 | teardown threw 5/5; killed engine's containers absent after teardown 0/5; next job exit 0 5/5; timed out 0/5 |
| spark-after | Spark: teardown completed, master removed, next job exited 0, 5/5 | teardown threw 0/5; next job exit 0 5/5; hung 0/5 | teardown threw 0/5; killed engine's containers absent after teardown 5/5; next job exit 0 5/5; timed out 0/5 |

#### Part C assertions (PASS/FAIL counts per cell)

| Assertion | flink-before | flink-after | spark-before | spark-after |
| --- | --- | --- | --- | --- |
| pre_run_no_engine_containers | 5 PASS / 0 FAIL | 5 PASS / 0 FAIL | 5 PASS / 0 FAIL | 5 PASS / 0 FAIL |
| teardown_no_exception | 0 PASS / 5 FAIL | 5 PASS / 0 FAIL | 0 PASS / 5 FAIL | 5 PASS / 0 FAIL |
| teardown_time_bound | 5 PASS / 0 FAIL | 5 PASS / 0 FAIL | 5 PASS / 0 FAIL | 5 PASS / 0 FAIL |
| containers_absent_after_teardown | 0 PASS / 5 FAIL | 5 PASS / 0 FAIL | 0 PASS / 5 FAIL | 5 PASS / 0 FAIL |
| new_taskmanager_at_own_jobmanager | 2 PASS / 3 FAIL | 5 PASS / 0 FAIL | - | - |
| next_job_exit_zero | 2 PASS / 3 FAIL | 5 PASS / 0 FAIL | 5 PASS / 0 FAIL | 5 PASS / 0 FAIL |
| next_job_time_bound | 2 PASS / 3 FAIL | 5 PASS / 0 FAIL | 5 PASS / 0 FAIL | 5 PASS / 0 FAIL |
| post_run_no_leftover_containers | 5 PASS / 0 FAIL | 5 PASS / 0 FAIL | 5 PASS / 0 FAIL | 5 PASS / 0 FAIL |

Cell-level checks (run by `part_c.sh`, now `harness/historical-part-c/part_c.sh`, after the JVM exited):

| Cell | Check | Result | Observed |
| --- | --- | --- | --- |
| flink-before | harness_jvm_completed | PASS | rc=0 |
| flink-before | no_engine_container_after_cell | PASS | none |
| flink-before | no_new_docker_network_after_cell | PASS | none |
| flink-before | cell_time_bound | PASS | 917s |
| flink-before | host_tmp_seatunnel_mnt_absent | PASS | absent |
| flink-after | harness_jvm_completed | PASS | rc=0 |
| flink-after | no_engine_container_after_cell | PASS | none |
| flink-after | no_new_docker_network_after_cell | PASS | none |
| flink-after | cell_time_bound | PASS | 614s |
| flink-after | host_tmp_seatunnel_mnt_absent | PASS | absent |
| spark-before | harness_jvm_completed | PASS | rc=0 |
| spark-before | no_engine_container_after_cell | PASS | none |
| spark-before | no_new_docker_network_after_cell | PASS | none |
| spark-before | cell_time_bound | PASS | 407s |
| spark-before | host_tmp_seatunnel_mnt_absent | PASS | absent |
| spark-after | harness_jvm_completed | PASS | rc=0 |
| spark-after | no_engine_container_after_cell | PASS | none |
| spark-after | no_new_docker_network_after_cell | PASS | none |
| spark-after | cell_time_bound | PASS | 284s |
| spark-after | host_tmp_seatunnel_mnt_absent | PASS | absent |

### Reading the results

- **Part A, rows 1, 2 and 4, and row 3 "after":** on both JDKs, every one of the 5 runs per cell
  had the outcome stated in Table 1 and the outcome and primary-path request count of the
  2026-10-25 run.
- **Part A, row 3 "before" (HTTP 429 with a body):** FAIL in 5/5 runs per JDK. Each run made 3
  requests (429, 429, 200), and every run logged `Attempted read from closed stream`. This
  repeats the 2026-10-25 finding that the PR's "succeeds" does not reproduce for 429s with a body.
- **Part A, row 5 (wrapper jar 429 for 30 s):** "before" made 5 wrapper-jar requests and failed
  with "main class not found" in 5/5 runs per JDK. The last request came at 20.2-20.2 s on JDK 11
  and at 20.2-20.9 s on JDK 8. The 20.9 s value (JDK 8, run 4, `logs/partA/jdk8_wrapper429s_before/r4.server.jsonl`)
  lies outside the 20.2-20.5 s of the 2026-10-25 runs. "After" succeeded on the fourth request in
  5/5 runs per JDK, at 35.2-35.3 s (2026-10-25: 35.2-35.6 s). The article's Table 1 gives no
  request times for this row.
- **Empty-body 429 variant:** "before" passed in 5/5 runs per JDK, with 4 requests per path and a
  checksum-triggered re-download (`Checksum validation failed`) in every run. "After" passed in
  5/5 runs per JDK with 3 requests and no checksum failure.
- **Part B:** hooked `dev` at the primary hook position failed 17/20 (JDK 8) and 19/20 (JDK 11),
  against 20/20 and 20/20 on 2026-10-25 and 15/20 and 7/20 in the PR. The patched test with stalls
  failed 0/20 on both JDKs, and unhooked `dev` under contention passed 50/50 on both JDKs, as in
  the PR and on 2026-10-25. All 99 failures in the new loops carried the CI message
  `expected: <1> but was: <0> within 3 seconds`. The sweep moves in the same direction as on
  2026-10-25: across both bundles, the failure counts per position are 17-20/20 at 35 ms,
  16-18/20 at 45 ms, 10-11/20 at 55 ms and 2-7/20 at 65 ms. In the pooled new loops, no iteration
  failed whose closing poll woke before `idleDeadlineMs` (0 of 35). Failures rose with how late
  the poll woke: 18 of 36 at 0-9 ms after, 31 of 35 at 10-19 ms and 50 of 54 at 20 ms or more
  (2026-10-25: 0/35, 21/36, 41/44, 44/45). The PR's 15/20 (JDK 8) falls between the 45 ms and
  55 ms positions, and its 7/20 (JDK 11) between the 55 ms and 65 ms positions. No single hook
  position reproduces both PR rates. The reconstruction supports the mechanism and the direction,
  not the PR's specific rates.
- **Part C, Flink "before" (row 6):** in 5/5 runs, `tearDown()` threw
  `ConflictException: Status 409 ... is not running`, and the first JobManager was still
  running (the killed TaskManager exited, not removed) after teardown, so
  `containers_absent_after_teardown` failed 5/5. The new TaskManager registered with the leaked
  JobManager in 3/5 runs (runs 1, 4, 5; `taskmanagers` at its own JobManager 0, at the leaked
  one 1). In exactly those 3 runs the next job timed out at 150 s, with the JobManager logging
  `Missing resources`. In the other 2 runs it exited 0 (24 s and 30 s). The 2026-10-25 bundle had 2/5
  timeouts. Across both bundles, 5 of 10 next jobs timed out.
- **Part C, Flink "after":** all eight assertions passed in 5/5 runs. Teardown took 0.5-1.4 s and
  logged the "is not running, skipping the removal" warning in each run. Both first containers
  were removed, the new TaskManager registered at its own JobManager, and the next job exited 0
  in 30-52 s.
- **Part C, Spark "before" (row 7):** `tearDown()` threw the same 409 in 5/5 runs, and the killed
  master was left behind (exited, not removed) in 5/5. The next job exited 0 in 5/5 (34-58 s).
- **Part C, Spark "after":** teardown completed in 5/5 with the warning
  `... is not running, skipping the removal of /tmp/seatunnel_mnt inside it`. The master was
  removed in 5/5, and the next job exited 0 in 5/5 (29-34 s).
- **Part C validity:** in every run, no container of the engine image existed before the run
  or after the harness cleanup. The harness force-removed the killed engine's leftovers in the
  "before" runs (`cleanup force-removed leftover ...`, 15 lines). After each cell no engine
  container and no new Docker network remained, and `/tmp/seatunnel_mnt` was absent.

## Interpretations and deviations

Interpretations 1-21 carry over from the 2026-10-25 bundle; some are updated, and the updates are
marked. Interpretations 22-34 are new. File paths below are those of the runs; since the fourth
revision the Part C files (`part_c.sh`, `parse_part_c.py`, `java/ReplayKillTeardownTest.java`) are
in `harness/historical-part-c/`, and `replay.sh` no longer builds or runs Part C.

Part A

1. The mirror (`harness/fault_mirror.py`, byte-identical to the 2026-10-25 file) is a new Python
   implementation. It serves the warm repository over HTTP/1.1 with keep-alive and
   Content-Length. It computes checksum files on the fly and serves `maven-metadata.xml` from the
   repository's `maven-metadata-<repo>.xml`.
2. "Faults for `junit` paths" is read as every request path that contains `/junit/` and is not a
   checksum file. The first N requests **per path** get the fault. The dependency plugin's own
   `junit:3.8.1` and `junit:3.8.2` therefore also receive faults.
3. "Body cut off halfway" truncates only the **first** request per path. A retry would get the
   full body, so a failure shows that no retry happened. The original's choice is unknown.
4. The wrapper-429 window starts at the first wrapper-jar request. In this `mvnw`, `wrapperUrl` in
   `.mvn/wrapper/maven-wrapper.properties` overrides `MVNW_REPOURL`, so the run's copy points
   `wrapperUrl` at the mirror (only for this fault). `distributionUrl` is unchanged. Updated: the
   distribution is cached in `work/mvn-home` (downloaded once from Maven Central during setup),
   not in the user's `~/.m2/wrapper`. The downloader is curl (`-f`), not wget.
5. The tiny project resolves `junit:junit:4.13.2`. Plugin versions come from the Maven 3.8.4
   super POM (maven-dependency-plugin 2.8).
6. Updated: 5 runs per cell, not 1. Each run gets a new mirror process on a free loopback port, a
   new project directory and an empty local repository.
7. Updated: no invalid run occurred in this bundle. The validity rule is now in the driver: a run
   whose Maven never reached the mirror (0 requests logged) is marked `"valid": false`, kept in
   `runs.jsonl`, and repeated. The 2026-10-25 invalid run and its deleted smoke-test logs belong
   to that bundle.

Part B

8. The hook is the 2026-10-25 patch file, byte-identical. "35 ms before the idle deadline" is
   read as 35 ms before the test's `idleDeadlineMs`. The sweep (45, 55, 65 ms) covers the other
   readings, including the reader's close threshold (65 ms before `idleDeadlineMs`).
9. "This patch" is the merge commit `87ed0afe0`, whose parent already contains PR 12381
   (Awaitility budgets 3 s to 10 s in the final wait). The PR's own patched runs were based on
   `deb16a3c3`. The stall points match the PR text: 45 ms before the close step, 700 ms after the
   close, 700 ms after rediscovery.
10. Both revisions were built, and the hooked tests compiled, with JDK 8 only. The JDK 11 cells
    run the JDK 8-compiled classes on JDK 11 (the PR built per JDK).
11. CPU contention is 20 `bash` busy loops (`while :; do :; done`) for the duration of the
    contention cells. The load average printed 2 s after they start understates the load.
12. The PR's 200/200 stress run and its two mutation checks were not re-run.

Part C

13. The harness (`harness/java/ReplayKillTeardownTest.java`) drives the framework's own
    `Flink18Container` and `Spark3Container`, subclassed only to read the container handles. Each
    run starts the engine, runs `docker kill` on the TaskManager (Flink) or master (Spark), calls
    `tearDown()`, starts a new container of the same engine and runs `/fake_to_assert.conf` with
    a 150 s limit. It then tears down and force-removes leftovers. Updated: it also prints the
    `ASSERT` lines listed in its header.
14. "Before" is the merge build with the four teardown classes from the parent `7ba68325c`
    (`AbstractTestContainer`, `AbstractTestFlinkContainer`, `AbstractTestSparkContainer`,
    `SeaTunnelContainer`) compiled and placed first on the classpath. PR 12481 changes only those
    test-framework files.
15. The JobManager that the new TaskManager joined is read from each JobManager's REST `/overview`
    (`taskmanagers`), because the TaskManager log names the JobManager only by its alias.
    Updated: this is now an assertion (`new_taskmanager_at_own_jobmanager`) in every Flink run.
    The 2026-10-25 IP-based first run does not apply.
16. The Flink-only intermediate revision of PR 12481 is not in the merged history and was not run.
    Zeta was not run (see "Not run").
17. Docker Desktop on Apple silicon runs the amd64 images under emulation. The host architecture
    of the PR's runs is unknown.
18. Updated: the e2e build passes `-De2e.dependency.skip=false` from the start, so the test
    classpath is written by the same build that compiles the module. No classpath-only
    invocation was used.

General

19. Logs are `.txt` and `.jsonl` files.
20. No log was truncated. All logs together take about 20 MB. The Part C container logs are
    complete as captured by Testcontainers' log consumers.
21. The E2E framework uses the fixed host path `/tmp/seatunnel_mnt`. The cell-level check
    `host_tmp_seatunnel_mnt_absent` found it absent after every cell.

New in this bundle

22. "Container absent after teardown" holds only when the Docker API answers 404
    (`NotFoundException`) for the container id. Any other inspection error is recorded as
    `inspect-error` and fails the check. In the 2026-10-25 harness any exception counted as
    removal. Cleanup errors other than 404 are now printed; none occurred.
23. Bounds are harness choices, not PR values: `tearDown()` within 60 s, the next job within
    150 s (the job limit, longer than the PR's "> 120 s" hang), and a cell within 600 s per run.
    The 2026-10-25 harness used the same 150 s job limit.
24. In the "before" cells, the containers-absent check is expected to FAIL (that is the defect
    PR 12481 fixes), and it is recorded, not thrown. A FAIL in this table is an observation, not a
    harness failure. `harness_jvm_completed` and the pre- and post-run leftover checks are the
    harness's own validity checks.
25. The per-run records of Part C were first written by a parser inside `part_c.sh`. That parser
    misread a next-job timeout as "not timed out", because it tested the whole matched line, not
    the job outcome. After the runs, the parser moved to `harness/parse_part_c.py` with the fix,
    and `logs/partC/runs.jsonl` was regenerated from the four unchanged cell logs. The first
    output is kept as `logs/partC/runs.parser-v1.jsonl`. Only `next_job_timed_out` differs
    (3 Flink "before" runs). The ASSERT lines in the logs were never affected.
26. Scripts changed after their runs, with no effect on the logic that produced the logs:
    `replay.sh` gained the block that writes `logs/partA/maven-version.txt` after Parts A and C
    had started, and that block ran in the 14:17 `--part A --prepare-only` invocation.
    `part_b.sh` and `part_c.sh` now number repeated invocations' logs (`loop2.txt`,
    `<cell>-2.txt`) rather than renaming the earlier log. `part_c.sh` calls `parse_part_c.py`
    (interpretation 25). `make_results.py` and `tables.py` were extended while the runs
    progressed. The sha256 values in `results.json` are those of the final files.
27. The copy of `ReplayKillTeardownTest.java` that `replay.sh` places in `connector-fake-e2e`
    before the build is only there so the module builds. `part_c.sh` compiles
    `harness/java/ReplayKillTeardownTest.java` separately and puts it first on the classpath
    (sha256 in `logs/partC/compile-harness.txt` and in each cell log header). The module was
    built with an earlier revision of that file, from before the 404-only change.
28. Part A ran at the same time as the Part B and C builds (13:27-13:35) and as the Part C runs
    (13:36-14:14). Part B ran alone afterwards. The Part A measurements are request counts and
    request offsets measured by the mirror, but Part A wall times include that concurrent load.
29. The Part A warm repository is built by `replay.sh` from Maven Central: two `dependency:resolve`
    runs (JDK 11, then JDK 8; `logs/partA/warm-repo-build.txt`), plus the maven-wrapper 3.1.0 jar
    and POM fetched from Central and checked against Central's `.sha1`. In the 2026-10-25 bundle
    the wrapper jar was put into the warm repository by an unrecorded step.
30. The mirror's stderr (Python tracebacks for client-side connection resets, printed by the
    standard library's HTTP server) goes to `logs/partA/console.txt`, not to the per-run logs.
31. The Part B and C builds use the default Maven local repository of the host, through the
    worktree's own `mvnw` and the host's wrapper cache. On this host every dependency was already
    cached. On a clean machine they are downloaded, and `REPLAY_MAVEN_REPO` keeps them out of
    `~/.m2`. The builds use `package`, not `install`.
32. Part B: every loop runs in one JVM, as in the PR. The loop logs print the hook's stall and
    wake offsets per iteration; the pooled table pairs each `REPLAY-HOOK` line with the next
    `ITER` line.
33. "Clean checkout" here means that `work/` started empty. A second machine or a container was
    not used, so host state outside `work/` (JDKs, Docker images, the Maven local repository for
    the B and C builds) was not re-created.
34. The empty-body 429 variant (`429x2nobody`) is not a Table 1 row. Its `after` cell is new in
    this bundle.

## Not run

- **Table 1 row 7, Zeta server killed (before and after):** not re-run. The harness has no Zeta
  scenario, and `SeaTunnelContainer` needs `seatunnelhub/openjdk:8u342`, which is not in the
  local Docker cache (`logs/setup/setup-partC-*.txt`). `REPLAY_PULL_ZETA=1` pulls it, but this
  bundle contains no Zeta harness.
- **Table 1 row 6, the Flink-only intermediate revision of PR 12481:** not in the merged history
  and not run. Only the parent and the merge were run.
- **PR 12472 200/200 stress run and the two mutation checks:** not run.
- **Windows:** nothing here ran on Windows.
- **A second machine:** the bundle was not replayed on another host or in a container.
- **The DataFusion repartition regression and the other article cases:** outside this bundle.

## Paths

The scripts and configs in this bundle contain no absolute workstation path. They resolve every
location from the bundle directory (`./work`, `./logs`, `./harness`) or from the optional
environment variables above. The logs are kept exactly as written, and some of them contain
absolute paths of the machine the runs were executed on: tool output such as Maven's
`Maven home`, compiler and build output, Java classpaths, and `JAVA_HOME` in log headers. Those
paths are records of that machine, not inputs. The `<work>` placeholder in log headers stands for
the bundle's `work/` directory. `results.json` stores only bundle-relative paths.

## Files

- `replay.sh`: the entry point (Parts A and B).
- `harness/part_a.py`, `harness/fault_mirror.py`, `harness/tiny-pom.xml`,
  `harness/settings-mirror.template.xml`, `harness/settings-empty.xml`: Part A.
- `harness/part_b.sh`, `harness/hook-dev-deb16a3c3-stall45.patch`,
  `harness/hook-patch-87ed0afe0-stalls.patch`, `harness/java/RepeatMethod.java`: Part B.
- `harness/historical-part-c/`: the Part C scripts (`part_c.sh`, `parse_part_c.py`,
  `java/ReplayKillTeardownTest.java`, `selftest_part_c_guards.sh`) and a `README.md`. Kept for
  inspection, not for execution; `make_results.py` imports `parse_part_c.py` to validate the
  recorded Part C logs.
- `harness/make_results.py`, `harness/tables.py`: validation, `results.json` and the tables above.
- `harness/selftest_validation.py`: self-test of the validation (third revision; it executes no
  experiment).
- `logs/setup/`: toolchain records, setup logs and consoles of every invocation.
- `logs/partA/<cell>/r<k>.mvn.txt` and `r<k>.server.jsonl`, `logs/partA/runs.jsonl`,
  `logs/partA/warm-repo-build.txt`, `logs/partA/maven-version.txt`, `logs/partA/console.txt`.
- `logs/partB/<cell>/loop<k>.txt`, `logs/partB/runs.jsonl`, build and compile logs.
- `logs/partC/<cell>.txt`, `logs/partC/runs.jsonl` (and `runs.parser-v1.jsonl`, see
  interpretation 25), build and compile logs.
- `results.json`: per-run records, per-cell summaries, and sha256 of every log and harness file.
- `.gitignore`: excludes `work/`.

## Revision after the runs (2026-10-25)

`harness/part_c.sh` originally removed every container built from the engine image at the end of a cell (`docker ps -aq --filter ancestor=$IMAGE`), which would also remove unrelated containers on a developer's machine. The published script now records the containers present before the cell and removes only those created during it. The recorded runs were executed with the original line, and `results.json` keeps the executed script's hash as `sha256_as_run`. Correction (2026-10-25, third revision): this paragraph said the original line's removals are in `logs/partC/*.cleanup.txt`. No such file exists. The original line appended the output of each `docker rm -f` to `<cell>.txt.cleanup.txt`, so the missing files show that it removed nothing, which agrees with `no_engine_container_after_cell` (PASS, observed `none`) in all four cells.

Second revision (2026-10-25): `harness/part_c.sh` now refuses to start when `/tmp/seatunnel_mnt` already exists on the host. SeaTunnel's end-to-end teardown (`deleteHostVolumeMountPath`) deletes the contents of that path, so a pre-existing directory could have lost unrelated data. The recorded runs were executed on a host where the path did not exist (the `host_tmp_seatunnel_mnt_absent` check passed in every cell).

## Revision (2026-10-25, third revision after the runs)

This revision changes no recorded run, log or count. It makes the Part C driver refuse unsafe
hosts and scope its cleanup, and makes the aggregation fail when runs are missing or invalid. None
of the revised scripts has been executed against Docker: the revised Part C path is exercised only
by `harness/selftest_part_c_guards.sh` with a simulated `docker` and JVM, not in a disposable
environment with the real images. The 20 recorded Part C runs were made with the as-run versions.
`results.json` lists, for every revised file, the current `sha256`, the `sha256_as_run` and a
`revised_after_runs` note.

| File | Change | sha256 now | sha256_as_run |
| --- | --- | --- | --- |
| `harness/part_c.sh` | (a) Before the build steps and before every cell, refuses to start (exit 2, reason on stderr) if `/tmp/seatunnel_mnt` exists, if Docker cannot be listed, or if any container, running or stopped, of the Flink, Spark or Zeta image exists. (b) After every cell, considers every container of the engine images and removes one only if it did not exist before the cell, was created at or after the cell's start time (`docker inspect` `.Created`), runs the cell's engine image, and carries the Testcontainers session label that the cell's JVM printed. Each container considered is written to the cell log as a `CLEANUP` line with the decision and the reasons. (c) A non-zero JVM exit fails `harness_jvm_completed`. (d) `/tmp/seatunnel_mnt` present after the cell, an engine container left after the cell or after cleanup (new check `no_engine_container_after_cleanup`), or incomplete run records fail the cell; the script then writes `# cell_result=FAIL`, starts no further cell and exits 1. The log header gains the driver's sha256 and the pre-cell guard result. | `b7757fbd6360...` | `a75658e64990...` (the version that ran; the published `59fbd0c8eb78...` of the second revision is superseded) |
| `harness/java/ReplayKillTeardownTest.java` | A failed `pre_run_no_engine_containers` check is still recorded, then the harness prints `RESULT <engine> run=<n> aborted: ...` and exits the JVM with status 3 before starting any container (it previously logged the failure and continued). Each test method prints `RESULT testcontainers_session=<id>` for the cleanup rule above. The harness still force-removes only the container ids of the containers it started. | `b715134750ac...` | `e0049c6c63c1...` (in every Part C cell log header) |
| `harness/parse_part_c.py` | Importable `parse()`; a missing or unreadable log, a missing header or trailer, no runs, fewer runs than the header's `runs=N`, a missing or duplicated assertion, a failed harness validity check (`pre_run_no_engine_containers`, `post_run_no_leftover_containers`, any `ASSERT-CELL` check) or an aborted run is listed on stderr with exit status 1. The records it prints are unchanged. | `1bafe4d218af...` | `bdad4ea98f03...` (the version that wrote `logs/partC/runs.jsonl`, interpretation 25) |
| `harness/make_results.py` | Fail-closed validation as described under "Exact commands": requested matrix from the invocation records; every run log must exist, parse and agree with its record; Part A runs are valid only if the mirror was reached, the requested fault was the first response for the fault target and the Maven log has its trailer, and a repetition may be valid only once; Part B loops only if the JVM exited 0 with exactly the requested iterations, every hooked `dev` iteration logged its stall, and the contention loops logged their busy loops; Part C as in `parse_part_c.py`. Per-cell `runs_requested`, `runs_recorded`, `runs_valid`; summaries over the valid runs; the as-run hashes are kept in the script so that a regeneration keeps them. | `5a781d8e56c1...` | `0176e7b397d5...` (the version that wrote the published `results.json`) |
| `replay.sh` | `--runs` must be a positive integer (`--runs 0` would have requested nothing); a failed validation is reported and the exit status is 1. The help text states the Part C host requirement. | `613d4434bcb7...` | `6e85b1415659...` (as published with the runs; see interpretation 26) |
| `harness/selftest_validation.py`, `harness/selftest_part_c_guards.sh` | New. | `c45d833be3b3...`, `cd6f9d9da31f...` | - |

Revalidation over the recorded logs (no new executions). `python3 harness/make_results.py` was
re-run over the existing `logs/`. It reported `validation PASS; A 120 valid runs, B 12 valid
loops, C 20 valid runs, 289 log files hashed`. Every requested cell has `runs_requested`,
`runs_recorded` and `runs_valid` equal: 5/5/5 for the 24 Part A cells and the 4 Part C cells,
1/1/1 for the 12 Part B cells (requests read from `logs/setup/setup-partA-20261025T132617.txt`,
`setup-partB-20261025T141709.txt` and `setup-partC-20261025T133629.txt`). Compared with the
previously published `results.json`, every per-cell summary, per-run record, the pooled hook table
and the log hash list are identical; the differences are the added count fields, the `validation`
block, the generation time and the harness hashes. `harness/tables.py` prints the same tables as
before. Re-parsing the four Part C cell logs with the revised `parse_part_c.py` reproduces
`logs/partC/runs.jsonl` byte for byte. No number changed, so no second output is kept.

Self-tests (run on 2026-10-25). `python3 harness/selftest_validation.py`: 14 of 14 cases as
expected. The unmodified copy passes; each of the following makes `make_results.py` exit 1 without
writing `results.json`: a Part A repetition removed, a Part A repetition duplicated, a Part A Maven
log missing, a Part A server log line unparsable, the Part A fault not delivered, a Part B loop
truncated, a Part B loop log missing, a Part C run removed from its cell log, a Part C cell log
missing, a failed `pre_run_no_engine_containers`, `/tmp/seatunnel_mnt` recorded as present after a
cell, a `runs.jsonl` line that is not JSON, and the Part C records missing.
`bash harness/selftest_part_c_guards.sh`: 8 of 8 checks as expected, against the simulated Docker:
a pre-existing stopped Flink container stops the script before any cell (exit 2, container
untouched, no cell log); an unreachable Docker daemon and an existing `/tmp/seatunnel_mnt` stop it
(exit 2); a clean cell passes (exit 0); with six containers created during the cell, only the one
carrying the cell JVM's session label, the cell's engine image and a creation time after the cell
start is removed, the four other engine containers are kept with their reasons logged
(`session_label_mismatch` twice, `not_cell_engine_image`, `created_before_cell_start`), the
`postgres:16` container is not considered, and the cell fails (exit 1); a harness abort (JVM exit 3)
fails the cell (exit 1); `/tmp/seatunnel_mnt` created during the cell fails it (exit 1).

## Revision (2026-10-25, fourth revision after the runs)

This revision changes no recorded run, log or count. It takes Part C off the replay entry point
and makes the "Article" columns quote the current article.

**Part C is no longer run.** Part C executed SeaTunnel's real end-to-end teardown against the
host's Docker daemon, not in a sandbox, and that teardown deletes the host path
`/tmp/seatunnel_mnt` (both revisions delete it with `FileUtils.deleteFile`). The
checks of the third revision refuse unsafe starting states but do not isolate the host: a path or
container created by another process during a cell is not protected. `replay.sh` therefore no
longer runs Part C. `./replay.sh --part C` (with or without `--prepare-only` or `--runs`) prints
why and exits 0 before it creates, clones, builds or contacts anything, and writes no invocation
record; `./replay.sh --part all` prints the same reason and runs Parts A and B only. The Part C
preparation (engine image pulls, the end-to-end module build, the copy of the harness into
`connector-fake-e2e`) and the Docker lines of the toolchain record were removed from `replay.sh`.
The 20 recorded Part C runs are historical records: their logs stay under `logs/partC/`, their
sha256 values and results in `results.json`, and `make_results.py` still validates them from
those logs.

The Part C scripts were moved, unchanged, to `harness/historical-part-c/`, which has its own
`README.md`: they are kept for inspection, not for execution. In `results.json` each moved file is
listed at its new path with `path_as_run` giving the old one; its `sha256` is unchanged, and
`sha256_as_run` and `revised_after_runs` are kept, with a note on the move added.

| File | Change | sha256 now | sha256_as_run |
| --- | --- | --- | --- |
| `harness/historical-part-c/part_c.sh` (was `harness/part_c.sh`) | moved, content unchanged | `b7757fbd6360...` | `a75658e64990...` |
| `harness/historical-part-c/java/ReplayKillTeardownTest.java` (was `harness/java/ReplayKillTeardownTest.java`) | moved, content unchanged | `b715134750ac...` | `e0049c6c63c1...` |
| `harness/historical-part-c/parse_part_c.py` (was `harness/parse_part_c.py`) | moved, content unchanged; still imported by `make_results.py` (it only reads logs) | `1bafe4d218af...` | `bdad4ea98f03...` |
| `harness/historical-part-c/selftest_part_c_guards.sh` (was `harness/selftest_part_c_guards.sh`) | moved, content unchanged | `cd6f9d9da31f...` | - |
| `harness/historical-part-c/README.md` | new | `ef0b37461e1f...` | - |
| `replay.sh` | Part C taken off as described above | `4b612c5de438...` | `6e85b1415659...` |
| `harness/make_results.py` | imports `parse_part_c` from `harness/historical-part-c`; reads `--part all` as Parts A and B; records `path_as_run` for the moved files and the as-run hash of `tables.py` | `e040312d67d6...` | `0176e7b397d5...` |
| `harness/tables.py` | the "Article" columns quote the current article (below); the Part B table gains an "Article" column | `734492705072...` | `1e4db5170a6a...` (the version published with the runs) |

**"Article" columns.** The comparison tables above quote, word for word, Table 1 and the PR 12472
stall counts of the article revision of 25 October 2026 that cites these records at commit
`fe561f6`. In that revision, Table 1 reports this bundle's runs (five per cell), and the stall
counts (17/20 on JDK 8 and 19/20 on JDK 11 for hooked `dev`, 20/20 each in the first
reconstruction, 0/20 per JDK for the patch, 50/50 passes under contention) are in its text on the
test system; its checkpoint section gives no stall counts. Before this revision the column quoted
an earlier article text, whose Table 1 reported the 2026-10-25 runs ("teardown threw in 5/5
records; 2/5 next jobs timed out at 150 s"; wrapper request times 20.2-20.5 s and 35.2-35.6 s), and
the Part B table quoted only the pull request. "Reading the results" now compares the wrapper
request times with the 2026-10-25 runs, from which those ranges came. Only the "Article" columns
and their headers changed; every 2026-10-25 and 2026-10-26 cell is as before.

Checks (run on 2026-10-25, no new executions):

- `python3 harness/make_results.py` over the recorded logs: `validation PASS; A 120 valid runs, B 12
  valid loops, C 20 valid runs, 289 log files hashed`. Compared with the previous `results.json`,
  only `generated` and the `harness` list differ; every per-cell summary, per-run record,
  validation block and log hash is identical.
- Hashes recomputed from the files: 289 of 289 log hashes match and no file under `logs/` is
  unlisted; 18 of 18 harness hashes match (every file under `harness/` and `replay.sh` is listed);
  272 of 272 per-run log hash references match; each of the 6 `sha256_as_run` values matches the
  file at its `path_as_run` in commit `4877661`; the Part C cell log headers carry
  `e0049c6c63c1...`, the `sha256_as_run` of `ReplayKillTeardownTest.java`. The 62 hashes in
  `../model-queries-2026-10-25/results.json` match.
- `python3 harness/selftest_validation.py`: 14 of 14 cases as expected.
- `replay.sh` in a copy of this directory, with a `docker` on `PATH` that records every call:
  `--part C`, `--part C --prepare-only` and `--part C --runs 5` each printed the reason and exited
  0, created no file and no `work/` directory, and called `docker` 0 times. `--part all` printed
  the reason, wrote its invocation and toolchain records, and stopped at the clone (exit 4, the
  clone URL was pointed at a missing path for this check); `docker` was called 0 times.
- A copy without `logs/partA`, `logs/partB`, their `logs/setup` files and `results.json` validates
  with `C 20 valid runs`, as "Exact commands" states.

Not done: Part C was not executed in a disposable environment, and no revised Part C script has
been executed against Docker. Parts A and B were not re-run.
