# Replay bundle 2026-10-26: Table 1 rows 1-7 and the PR 12472 stall records

This bundle is the second reconstruction of the SeaTunnel records behind the article's Table 1
(rows 1-7) and the PR 12472 stall-injection rates. The first reconstruction, the 2026-10-25
bundle, is kept unchanged at the root of the records repository. Both bundles are reconstructions: the original harnesses of PRs 12468,
12472 and 12481 were never published and their logs were not kept. The harnesses were rewritten
from the pull-request texts.

Every value this README and `results.json` give for this bundle's runs is parsed from a log
under `logs/` that an executed run wrote. The "Article" and "2026-10-25" columns are quoted from
the article and from the 2026-10-25 bundle's `results.json`. Failed, interrupted and invalid runs are kept. `results.json` lists the
sha256 of every file under `logs/`. The comparison tables below are printed by
`harness/tables.py` from `results.json`.

The runs were executed on 2026-10-25 between 13:26 and 14:26 local time (UTC-7) on the
machine described under "Toolchain". The directory name gives the bundle date, not the run date.

## What changed compared with the 2026-10-25 bundle

| Topic | 2026-10-25 bundle | This bundle |
| --- | --- | --- |
| Entry point | separate scripts with absolute workstation paths; prepared worktrees, warm repository and launcher jar assumed | one script, `./replay.sh --part A\|B\|C\|all [--runs N]`. It checks the toolchain, clones apache/seatunnel at the six pinned commits into `./work`, creates the worktrees, builds, fetches the wrapper and launcher jars from Maven Central (sha1 checked), warms the Part A mirror repository from Maven Central, runs the parts and regenerates `results.json`. Scripts and configs contain no absolute workstation path |
| Part A repetitions | 1 run per cell | 5 runs per cell, interleaved (repetition k of every cell before repetition k+1 of any cell); 24 cells, 120 runs |
| Part A empty-body 429 variant | `before` only, 1 run per JDK | separate labelled cell, `before` and `after`, 5 runs each per JDK |
| Part B | one 20-iteration loop per cell | one more 20-iteration loop per cell, same hooks and sweep positions (50 iterations for the contention cells); results added to the sweep table |
| Part C | outcome lines only; any Docker inspection error counted as "removed"; cleanup errors suppressed | explicit assertions, one `ASSERT` line each, every result recorded: container absent after teardown (Docker 404 only), teardown and next-job time bounds, next-job exit code, new TaskManager at its own JobManager, no leftover container before and after each run. The script adds cell-level checks (JVM completed, no engine container left, no new Docker network, cell time bound, host mount directory absent) |
| Logs | could be overwritten by a re-run | never overwritten: Part A renames a leftover log of an interrupted run to `*.interrupted-<epoch>`, and Parts B and C number the logs of repeated invocations (neither occurred) |
| CI evidence | inline links in the article | saved GitHub Actions records transcribed into `../ci-evidence/` (run ids and retrieval times as saved) |

## Exact commands

From a checkout of this directory (bash, git, curl, python3, patch, shasum; JDK 8 and JDK 11 with
`javac`; Docker for Part C):

```
./replay.sh --part all                 # A (5 runs/cell), B (1 loop/cell), C (5 runs/cell)
./replay.sh --part A --runs 5          # one part; --runs = runs per cell (A, C) or loops per cell (B)
./replay.sh --part C --prepare-only    # toolchain check, clone, worktrees, builds, images; no runs
./replay.sh --part B --cells "dev-hook-jdk8 patch-hook-jdk8"   # a subset of cells
python3 harness/make_results.py        # regenerate results.json from logs/part*/runs.jsonl
python3 harness/tables.py --old <2026-10-25 results.json>      # print the comparison tables
```

Optional environment: `JAVA8_HOME`, `JAVA11_HOME` (otherwise found with `/usr/libexec/java_home`
or under `/usr/lib/jvm`, and a JDK must contain `javac`), `REPLAY_WORK` (default `./work`),
`REPLAY_SEATUNNEL_URL`, `REPLAY_MAVEN_REPO` (local Maven repository for the Part B and C builds;
default: Maven's own), `REPLAY_PULL_ZETA=1`. Part A skips runs that are already recorded in `logs/partA/runs.jsonl`. Parts B and C add new
logs (`loop2.txt`, `<cell>-2.txt`) next to the existing ones. A fresh replay therefore starts from
a copy of this directory without `logs/` and `results.json`.

The invocations that produced this bundle, in order (consoles in `logs/setup/` and
`logs/partA/console.txt`):

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

"Article" quotes Table 1 of the article. The article's Table 1 itself reports the 2026-10-25
runs. For Part B it quotes PR 12472, because the article leaves out the rates. "Primary-path
requests" counts the GET requests the fault mirror logged for
`junit/junit/4.13.2/junit-4.13.2.pom`, the first fault target. Wrapper times are measured from
the first wrapper-jar request. Wall times cover the whole `./mvnw` process.

#### Part A (PR 12468; Table 1 rows 1-5)

| Row | Fault | Config | JDK | Article (Table 1) | 2026-10-25 (n=1) | 2026-10-26 (n per cell as listed) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | HTTP 503 on first 2 requests | before | jdk8 | fails on first 503 | FAIL; primary-path requests: 1 | 0 PASS / 5 FAIL; primary-path requests per run: 1,1,1,1,1; wall 5.4/6.2/11.7 s (min/median/max) |
| 1 | HTTP 503 on first 2 requests | after | jdk8 | succeeds on third request | PASS; primary-path requests: 3 | 5 PASS / 0 FAIL; primary-path requests per run: 3,3,3,3,3; wall 19.7/22.9/36.9 s (min/median/max) |
| 2 | Connection reset on first 4 requests | before | jdk8 | fails after four attempts | FAIL; primary-path requests: 4 | 0 PASS / 5 FAIL; primary-path requests per run: 4,4,4,4,4; wall 5.1/6.4/11.4 s (min/median/max) |
| 2 | Connection reset on first 4 requests | after | jdk8 | succeeds on fifth | PASS; primary-path requests: 5 | 5 PASS / 0 FAIL; primary-path requests per run: 5,5,5,5,5; wall 10.0/13.0/16.1 s (min/median/max) |
| 3 | HTTP 429 on first 2 requests | before | jdk8 | fails after receiving 200, unlike the PR | FAIL; primary-path requests: 3 | 0 PASS / 5 FAIL; primary-path requests per run: 3,3,3,3,3; `Attempted read from closed stream` in 5/5; wall 20.2/21.9/26.6 s (min/median/max) |
| 3 | HTTP 429 on first 2 requests | after | jdk8 | succeeds | PASS; primary-path requests: 3 | 5 PASS / 0 FAIL; primary-path requests per run: 3,3,3,3,3; wall 20.1/27.7/31.5 s (min/median/max) |
| 4 | First response body cut off halfway | before | jdk8 | fails | FAIL; primary-path requests: 1 | 0 PASS / 5 FAIL; primary-path requests per run: 1,1,1,1,1; wall 5.2/9.1/11.5 s (min/median/max) |
| 4 | First response body cut off halfway | after | jdk8 | still fails without retry | FAIL; primary-path requests: 1 | 0 PASS / 5 FAIL; primary-path requests per run: 1,1,1,1,1; wall 5.0/6.8/12.3 s (min/median/max) |
| 5 | Wrapper jar 429 for 30 s | before | jdk8 | five failed attempts; last at 20.2-20.5 s; main class not found | FAIL; primary-path requests: 0; wrapper-jar requests 5, last at 20.5 s | 0 PASS / 5 FAIL; primary-path requests per run: 0,0,0,0,0; wrapper-jar requests per run: 5,5,5,5,5, last at 20.2-20.9 s; main class not found in 5/5; wall 20.6/21.3/22.9 s (min/median/max) |
| 5 | Wrapper jar 429 for 30 s | after | jdk8 | fourth attempt succeeds at 35.2-35.6 s | PASS; primary-path requests: 1; wrapper-jar requests 4, last at 35.6 s | 5 PASS / 0 FAIL; primary-path requests per run: 1,1,1,1,1; wrapper-jar requests per run: 4,4,4,4,4, last at 35.2-35.3 s; wall 46.0/47.6/54.0 s (min/median/max) |
| 3 (variant) | HTTP 429 with empty body on first 2 requests (not a Table 1 row) | before | jdk8 | (boundary note: body-less 429s passed only after checksum-triggered redownload) | PASS; primary-path requests: 4 | 5 PASS / 0 FAIL; primary-path requests per run: 4,4,4,4,4; checksum-triggered re-download in 5/5; wall 86.1/89.8/91.6 s (min/median/max) |
| 3 (variant) | HTTP 429 with empty body on first 2 requests (not a Table 1 row) | after | jdk8 | - | not run | 5 PASS / 0 FAIL; primary-path requests per run: 3,3,3,3,3; wall 20.6/23.0/26.5 s (min/median/max) |
| 1 | HTTP 503 on first 2 requests | before | jdk11 | fails on first 503 | FAIL; primary-path requests: 1 | 0 PASS / 5 FAIL; primary-path requests per run: 1,1,1,1,1; wall 5.1/6.2/8.2 s (min/median/max) |
| 1 | HTTP 503 on first 2 requests | after | jdk11 | succeeds on third request | PASS; primary-path requests: 3 | 5 PASS / 0 FAIL; primary-path requests per run: 3,3,3,3,3; wall 19.2/22.5/24.1 s (min/median/max) |
| 2 | Connection reset on first 4 requests | before | jdk11 | fails after four attempts | FAIL; primary-path requests: 4 | 0 PASS / 5 FAIL; primary-path requests per run: 4,4,4,4,4; wall 5.0/6.6/7.9 s (min/median/max) |
| 2 | Connection reset on first 4 requests | after | jdk11 | succeeds on fifth | PASS; primary-path requests: 5 | 5 PASS / 0 FAIL; primary-path requests per run: 5,5,5,5,5; wall 9.3/11.8/13.2 s (min/median/max) |
| 3 | HTTP 429 on first 2 requests | before | jdk11 | fails after receiving 200, unlike the PR | FAIL; primary-path requests: 3 | 0 PASS / 5 FAIL; primary-path requests per run: 3,3,3,3,3; `Attempted read from closed stream` in 5/5; wall 20.0/22.6/23.8 s (min/median/max) |
| 3 | HTTP 429 on first 2 requests | after | jdk11 | succeeds | PASS; primary-path requests: 3 | 5 PASS / 0 FAIL; primary-path requests per run: 3,3,3,3,3; wall 20.9/23.0/28.2 s (min/median/max) |
| 4 | First response body cut off halfway | before | jdk11 | fails | FAIL; primary-path requests: 1 | 0 PASS / 5 FAIL; primary-path requests per run: 1,1,1,1,1; wall 5.5/7.0/7.4 s (min/median/max) |
| 4 | First response body cut off halfway | after | jdk11 | still fails without retry | FAIL; primary-path requests: 1 | 0 PASS / 5 FAIL; primary-path requests per run: 1,1,1,1,1; wall 5.4/5.6/7.0 s (min/median/max) |
| 5 | Wrapper jar 429 for 30 s | before | jdk11 | five failed attempts; last at 20.2-20.5 s; main class not found | FAIL; primary-path requests: 0; wrapper-jar requests 5, last at 20.2 s | 0 PASS / 5 FAIL; primary-path requests per run: 0,0,0,0,0; wrapper-jar requests per run: 5,5,5,5,5, last at 20.2-20.2 s; main class not found in 5/5; wall 20.7/20.8/21.0 s (min/median/max) |
| 5 | Wrapper jar 429 for 30 s | after | jdk11 | fourth attempt succeeds at 35.2-35.6 s | PASS; primary-path requests: 1; wrapper-jar requests 4, last at 35.2 s | 5 PASS / 0 FAIL; primary-path requests per run: 1,1,1,1,1; wrapper-jar requests per run: 4,4,4,4,4, last at 35.2-35.2 s; wall 44.7/49.1/55.1 s (min/median/max) |
| 3 (variant) | HTTP 429 with empty body on first 2 requests (not a Table 1 row) | before | jdk11 | (boundary note: body-less 429s passed only after checksum-triggered redownload) | PASS; primary-path requests: 4 | 5 PASS / 0 FAIL; primary-path requests per run: 4,4,4,4,4; checksum-triggered re-download in 5/5; wall 84.7/87.0/93.0 s (min/median/max) |
| 3 (variant) | HTTP 429 with empty body on first 2 requests (not a Table 1 row) | after | jdk11 | - | not run | 5 PASS / 0 FAIL; primary-path requests per run: 3,3,3,3,3; wall 19.4/22.5/25.7 s (min/median/max) |

#### Part B (PR 12472)

| Cell | PR 12472 | 2026-10-25 | 2026-10-26 |
| --- | --- | --- | --- |
| dev-hook-jdk8 | 15/20 failed | 20/20 failed | 17/20 failed |
| dev-hook-jdk11 | 7/20 failed | 20/20 failed | 19/20 failed |
| patch-hook-jdk8 | 0/20 failed | 0/20 failed | 0/20 failed |
| patch-hook-jdk11 | 0/20 failed | 0/20 failed | 0/20 failed |
| dev-nohook-contention-jdk8 | 0/50 failed (50/50 passed) | 0/50 failed | 0/50 failed |
| dev-nohook-contention-jdk11 | 0/50 failed (50/50 passed) | 0/50 failed | 0/50 failed |

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

| Cell | Article (Table 1) | 2026-10-25 (n=5) | 2026-10-26 |
| --- | --- | --- | --- |
| flink-before | teardown threw in 5/5 records; 2/5 next jobs timed out at 150 s | teardown threw 5/5; next job exit 0 3/5; hung 2/5 | teardown threw 5/5; killed engine's containers absent after teardown 0/5; next job exit 0 2/5; timed out 3/5 |
| flink-after | teardown completed and next job exited 0 in 5/5 records | teardown threw 0/5; next job exit 0 5/5; hung 0/5 | teardown threw 0/5; killed engine's containers absent after teardown 5/5; next job exit 0 5/5; timed out 0/5 |
| spark-before | teardown threw in 5/5 records; all next jobs exited 0 | teardown threw 5/5; next job exit 0 5/5; hung 0/5 | teardown threw 5/5; killed engine's containers absent after teardown 0/5; next job exit 0 5/5; timed out 0/5 |
| spark-after | teardown completed and next job exited 0 in 5/5 records | teardown threw 0/5; next job exit 0 5/5; hung 0/5 | teardown threw 0/5; killed engine's containers absent after teardown 5/5; next job exit 0 5/5; timed out 0/5 |

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

Cell-level checks (run by `harness/part_c.sh` after the JVM exited):

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
  had the outcome and the primary-path request count of the 2026-10-25 run and of Table 1.
- **Part A, row 3 "before" (HTTP 429 with a body):** FAIL in 5/5 runs per JDK. Each run made 3
  requests (429, 429, 200), and every run logged `Attempted read from closed stream`. This
  repeats the 2026-10-25 finding that the PR's "succeeds" does not reproduce for 429s with a body.
- **Part A, row 5 (wrapper jar 429 for 30 s):** "before" made 5 wrapper-jar requests and failed
  with "main class not found" in 5/5 runs per JDK. The last request came at 20.2-20.2 s on JDK 11
  and at 20.2-20.9 s on JDK 8. The 20.9 s value (JDK 8, run 4, `logs/partA/jdk8_wrapper429s_before/r4.server.jsonl`)
  lies outside the article's 20.2-20.5 s. "After" succeeded on the fourth request in 5/5 runs per
  JDK, at 35.2-35.3 s (article: 35.2-35.6 s).
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
marked. Interpretations 22-34 are new.

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

- `replay.sh`: the entry point.
- `harness/part_a.py`, `harness/fault_mirror.py`, `harness/tiny-pom.xml`,
  `harness/settings-mirror.template.xml`, `harness/settings-empty.xml`: Part A.
- `harness/part_b.sh`, `harness/hook-dev-deb16a3c3-stall45.patch`,
  `harness/hook-patch-87ed0afe0-stalls.patch`, `harness/java/RepeatMethod.java`: Part B.
- `harness/part_c.sh`, `harness/parse_part_c.py`, `harness/java/ReplayKillTeardownTest.java`:
  Part C.
- `harness/make_results.py`, `harness/tables.py`: `results.json` and the tables above.
- `logs/setup/`: toolchain records, setup logs and consoles of every invocation.
- `logs/partA/<cell>/r<k>.mvn.txt` and `r<k>.server.jsonl`, `logs/partA/runs.jsonl`,
  `logs/partA/warm-repo-build.txt`, `logs/partA/maven-version.txt`, `logs/partA/console.txt`.
- `logs/partB/<cell>/loop<k>.txt`, `logs/partB/runs.jsonl`, build and compile logs.
- `logs/partC/<cell>.txt`, `logs/partC/runs.jsonl` (and `runs.parser-v1.jsonl`, see
  interpretation 25), build and compile logs.
- `results.json`: per-run records, per-cell summaries, and sha256 of every log and harness file.
- `.gitignore`: excludes `work/`.
