# Clean-environment replay: comparison with the published results

Published: `replay-2026-10-26/results.json` at commit `d059baf95c8a21850a0b5d9d08ef07128d636ed2`
(runs of 2026-10-25 on the macOS host described in `replay-2026-10-26/README.md`, section "Toolchain").
Fresh: `replay-clean/out/bundle/results.json`, written by the same `replay.sh`
(sha256 `4b612c5de43833fb898b74467fec426204d556c6036db2f9339f156157a81642`) and
`harness/make_results.py` (`e040312d67d6...`) from that commit, in a fresh linux/arm64 container on
2026-10-26 (04:42-06:06 UTC). Validation of the fresh records passed (A 120 valid runs, B 12 valid loops;
the historical Part C records were kept and validated unchanged). The tables were produced by
`python3 replay-clean/compare.py <published results.json> replay-clean/out/bundle/results.json`.

## What differed between the two environments

| | Published runs (2026-10-25) | Clean replay (2026-10-26) |
| --- | --- | --- |
| Machine | Apple M1 Pro, 10 cores, 16 GB, macOS 27.0, other desktop applications running | the same machine; Docker Desktop 29.9.2 Linux VM (kernel 7.0.14-linuxkit, 10 CPUs, 10.7 GiB), Ubuntu 24.04.5 container; other host load was not controlled |
| JDK 8 | Oracle 1.8.0_172-b11, x86_64 under Rosetta 2 | Eclipse Temurin 1.8.0_504-b01, native aarch64 |
| JDK 11 | Temurin 11.0.19+7, x86_64 under Rosetta 2 | Eclipse Temurin 11.0.32.1+1, native aarch64 |
| Maven | 3.8.4 via the project wrapper (maven-wrapper 3.1.0), zip sha256 `ccd67d1e...` | identical (same zip sha256, same wrapper jar sha1 `32f70e9f...`, resolver 1.6.3, wagon-http 3.4.3) |
| Python | 3.12.7 | 3.12.3 |
| Part B build dependencies | host Maven repository, already populated (no download) | empty repository; 1396 artifacts downloaded from Maven Central by the first build |
| Concurrency | Part A overlapped the Part B/C builds and the Part C runs | Part A alone, then Part B alone |
| Cleanliness | `work/` empty; JDKs, Maven repository and Docker state from the host | new container from a pinned base image; records cloned from GitHub; no state from the host except the mounted output directory |

## Part A (PR 12468 Maven retry under injected faults)

Compared per cell: valid runs, passes, failures, time-outs, error-signature counts (closed stream,
wrapper main class not found, checksum validation failed) and, per run, the number of requests for
the primary artifact and for the wrapper jar and the action sequence the mirror served (compared as
sorted lists, since run order is not a property of a cell). Wall times are listed, not compared.

| Cell | Label | Published pass/fail | Fresh pass/fail | Published primary attempts | Fresh primary attempts | Published wrapper-jar attempts | Fresh wrapper-jar attempts | Published wall s (min/med/max) | Fresh wall s (min/med/max) | Match |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| jdk8_503x2_before | Table 1 row 1 | 0/5 | 0/5 | [1, 1, 1, 1, 1] | [1, 1, 1, 1, 1] | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [5.39, 6.19, 11.7] | [4.98, 5.27, 6.04] | yes |
| jdk8_503x2_after | Table 1 row 1 | 5/0 | 5/0 | [3, 3, 3, 3, 3] | [3, 3, 3, 3, 3] | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [19.71, 22.92, 36.87] | [34.17, 35.07, 40.66] | yes |
| jdk8_reset4_before | Table 1 row 2 | 0/5 | 0/5 | [4, 4, 4, 4, 4] | [4, 4, 4, 4, 4] | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [5.14, 6.39, 11.38] | [4.97, 5.02, 7.63] | yes |
| jdk8_reset4_after | Table 1 row 2 | 5/0 | 5/0 | [5, 5, 5, 5, 5] | [5, 5, 5, 5, 5] | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [10.0, 13.02, 16.12] | [24.12, 25.36, 31.28] | yes |
| jdk8_429x2_before | Table 1 row 3 | 0/5 | 0/5 | [3, 3, 3, 3, 3] | [3, 3, 3, 3, 3] | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [20.18, 21.95, 26.56] | [19.82, 20.09, 22.35] | yes |
| jdk8_429x2_after | Table 1 row 3 | 5/0 | 5/0 | [3, 3, 3, 3, 3] | [3, 3, 3, 3, 3] | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [20.06, 27.72, 31.5] | [35.26, 35.5, 45.4] | yes |
| jdk8_truncate1_before | Table 1 row 4 | 0/5 | 0/5 | [1, 1, 1, 1, 1] | [1, 1, 1, 1, 1] | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [5.24, 9.12, 11.53] | [4.86, 5.53, 24.3] | yes |
| jdk8_truncate1_after | Table 1 row 4 | 0/5 | 0/5 | [1, 1, 1, 1, 1] | [1, 1, 1, 1, 1] | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [5.05, 6.8, 12.28] | [4.85, 5.13, 10.59] | yes |
| jdk8_wrapper429s_before | Table 1 row 5 | 0/5 | 0/5 | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [5, 5, 5, 5, 5] | [5, 5, 5, 5, 5] | [20.55, 21.29, 22.86] | [20.21, 20.33, 21.57] | yes |
| jdk8_wrapper429s_after | Table 1 row 5 | 5/0 | 5/0 | [1, 1, 1, 1, 1] | [1, 1, 1, 1, 1] | [4, 4, 4, 4, 4] | [4, 4, 4, 4, 4] | [45.96, 47.63, 54.0] | [60.83, 62.0, 84.64] | yes |
| jdk8_429x2nobody_before | sensitivity variant (empty-body 429), not a Table 1 row | 5/0 | 5/0 | [4, 4, 4, 4, 4] | [4, 4, 4, 4, 4] | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [86.07, 89.75, 91.56] | [100.4, 101.18, 129.82] | yes |
| jdk8_429x2nobody_after | sensitivity variant (empty-body 429), not a Table 1 row | 5/0 | 5/0 | [3, 3, 3, 3, 3] | [3, 3, 3, 3, 3] | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [20.58, 23.03, 26.47] | [34.59, 36.33, 41.68] | yes |
| jdk11_503x2_before | Table 1 row 1 | 0/5 | 0/5 | [1, 1, 1, 1, 1] | [1, 1, 1, 1, 1] | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [5.14, 6.21, 8.23] | [4.92, 5.29, 12.68] | yes |
| jdk11_503x2_after | Table 1 row 1 | 5/0 | 5/0 | [3, 3, 3, 3, 3] | [3, 3, 3, 3, 3] | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [19.18, 22.52, 24.09] | [34.95, 35.18, 37.22] | yes |
| jdk11_reset4_before | Table 1 row 2 | 0/5 | 0/5 | [4, 4, 4, 4, 4] | [4, 4, 4, 4, 4] | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [5.01, 6.6, 7.88] | [4.95, 5.45, 6.19] | yes |
| jdk11_reset4_after | Table 1 row 2 | 5/0 | 5/0 | [5, 5, 5, 5, 5] | [5, 5, 5, 5, 5] | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [9.28, 11.81, 13.24] | [24.59, 25.34, 28.59] | yes |
| jdk11_429x2_before | Table 1 row 3 | 0/5 | 0/5 | [3, 3, 3, 3, 3] | [3, 3, 3, 3, 3] | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [19.96, 22.63, 23.77] | [19.73, 20.51, 21.95] | yes |
| jdk11_429x2_after | Table 1 row 3 | 5/0 | 5/0 | [3, 3, 3, 3, 3] | [3, 3, 3, 3, 3] | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [20.9, 23.04, 28.21] | [34.43, 37.25, 37.53] | yes |
| jdk11_truncate1_before | Table 1 row 4 | 0/5 | 0/5 | [1, 1, 1, 1, 1] | [1, 1, 1, 1, 1] | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [5.52, 7.01, 7.38] | [4.74, 5.09, 5.36] | yes |
| jdk11_truncate1_after | Table 1 row 4 | 0/5 | 0/5 | [1, 1, 1, 1, 1] | [1, 1, 1, 1, 1] | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [5.43, 5.59, 6.96] | [4.81, 5.87, 8.14] | yes |
| jdk11_wrapper429s_before | Table 1 row 5 | 0/5 | 0/5 | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [5, 5, 5, 5, 5] | [5, 5, 5, 5, 5] | [20.73, 20.84, 21.02] | [20.41, 20.6, 21.38] | yes |
| jdk11_wrapper429s_after | Table 1 row 5 | 5/0 | 5/0 | [1, 1, 1, 1, 1] | [1, 1, 1, 1, 1] | [4, 4, 4, 4, 4] | [4, 4, 4, 4, 4] | [44.68, 49.15, 55.07] | [60.83, 63.01, 69.99] | yes |
| jdk11_429x2nobody_before | sensitivity variant (empty-body 429), not a Table 1 row | 5/0 | 5/0 | [4, 4, 4, 4, 4] | [4, 4, 4, 4, 4] | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [84.67, 87.03, 93.03] | [102.77, 103.51, 110.23] | yes |
| jdk11_429x2nobody_after | sensitivity variant (empty-body 429), not a Table 1 row | 5/0 | 5/0 | [3, 3, 3, 3, 3] | [3, 3, 3, 3, 3] | [0, 0, 0, 0, 0] | [0, 0, 0, 0, 0] | [19.39, 22.46, 25.67] | [35.04, 35.88, 39.63] | yes |

Part A: 24 of 24 cells identical in every compared field.

All 24 cells, the 20 Table 1 cells and the 4 empty-body 429 cells, have the same outcome and the same
attempt counts in every run. The retry offsets of the primary artifact also agree (for example
`jdk8_503x2_after` r1: 0.0 / 1.01 / 2.02 s published, 0.0 / 1.01 / 2.01 s fresh).

Wall times. Failing `before` cells end in about the same time; cells that complete the whole
resolution take longer in the container (for example `jdk8_503x2_after` median 22.9 s published,
35.1 s fresh). The total number of requests per run is unchanged (596 in `jdk8_503x2_after`, 606 in
`jdk8_reset4_after`); the difference is spread over all requests, as the median interval between
consecutive mirror requests per cell shows (cells with at least 50 requests):

| Cell | Published median ms per request | Fresh median ms per request | Difference ms |
| --- | --- | --- | --- |
| jdk11_429x2_after | 26.2 | 57.3 | +31.0 |
| jdk11_429x2_before | 212.1 | 238.9 | +26.8 |
| jdk11_429x2nobody_after | 27.7 | 56.6 | +28.9 |
| jdk11_429x2nobody_before | 134.4 | 164.5 | +30.2 |
| jdk11_503x2_after | 27.5 | 56.4 | +28.9 |
| jdk11_503x2_before | 16.6 | 46.2 | +29.6 |
| jdk11_reset4_after | 10.3 | 38.7 | +28.4 |
| jdk11_reset4_before | 18.2 | 46.0 | +27.8 |
| jdk11_truncate1_after | 15.7 | 48.6 | +33.0 |
| jdk11_truncate1_before | 18.6 | 46.4 | +27.8 |
| jdk11_wrapper429s_after | 81.1 | 105.9 | +24.8 |
| jdk8_429x2_after | 28.1 | 56.5 | +28.4 |
| jdk8_429x2_before | 213.0 | 238.8 | +25.8 |
| jdk8_429x2nobody_after | 26.8 | 57.1 | +30.3 |
| jdk8_429x2nobody_before | 134.5 | 163.8 | +29.3 |
| jdk8_503x2_after | 28.0 | 55.7 | +27.7 |
| jdk8_503x2_before | 14.7 | 46.7 | +31.9 |
| jdk8_reset4_after | 10.8 | 38.1 | +27.3 |
| jdk8_reset4_before | 16.4 | 45.5 | +29.1 |
| jdk8_truncate1_after | 16.6 | 47.3 | +30.7 |
| jdk8_truncate1_before | 20.6 | 47.8 | +27.2 |
| jdk8_wrapper429s_after | 78.8 | 104.3 | +25.5 |

The added time is about 25-33 ms per request in every cell. Its cause (the container's loopback or
the Python mirror's HTTP handling on Linux, for example) was not investigated. It does not change
any count, and the article's Part A statements are counts and retry offsets, not wall times.

## Part B (PR 12472 stall injection), one loop per cell

| Cell | Hook | Published failed/iterations | Fresh failed/iterations | Fresh loops valid | Same count |
| --- | --- | --- | --- | --- | --- |
| dev-hook-jdk8 | dev-stall45 | 17/20 | 20/20 | 1/1 | no |
| dev-hook-jdk11 | dev-stall45 | 19/20 | 16/20 | 1/1 | no |
| patch-hook-jdk8 | patch-stalls | 0/20 | 0/20 | 1/1 | yes |
| patch-hook-jdk11 | patch-stalls | 0/20 | 0/20 | 1/1 | yes |
| dev-hook-lead45-jdk8 | dev-stall45 | 18/20 | 17/20 | 1/1 | no |
| dev-hook-lead45-jdk11 | dev-stall45 | 16/20 | 10/20 | 1/1 | no |
| dev-hook-lead55-jdk8 | dev-stall45 | 10/20 | 2/20 | 1/1 | no |
| dev-hook-lead55-jdk11 | dev-stall45 | 11/20 | 5/20 | 1/1 | no |
| dev-hook-lead65-jdk8 | dev-stall45 | 4/20 | 1/20 | 1/1 | no |
| dev-hook-lead65-jdk11 | dev-stall45 | 4/20 | 0/20 | 1/1 | no |
| dev-nohook-contention-jdk8 | none | 0/50 | 4/50 | 1/1 | no |
| dev-nohook-contention-jdk11 | none | 0/50 | 2/50 | 1/1 | no |

Part B: 2 of 12 cells with the same failed count.

Wake position of the injected stall relative to `idleDeadlineMs` against failure, pooled over the
eight hooked `dev` cells (the published pairing of each `REPLAY-HOOK` line with the next `ITER` line):

| Hook woke | Published failed/iterations | Fresh failed/iterations |
| --- | --- | --- |
| woke before idleDeadlineMs | 0/35 | 1/50 |
| woke 0-9 ms after | 18/36 | 13/32 |
| woke 10-19 ms after | 31/35 | 27/36 |
| woke >= 20 ms after | 50/54 | 30/42 |
| no stall injected | 0/0 | 0/0 |

Findings:

- **Unhooked `dev` under CPU contention failed in the container: 4/50 with JDK 8 and 2/50 with JDK 11**
  (published: 0/50 and 0/50). Every failure is the same assertion as in the hooked cells
  (`ConditionTimeoutException ... expected: <1> but was: <0> within 3 seconds`, iterations 24, 29,
  32, 50 with JDK 8 and 22, 30 with JDK 11; `out/bundle/logs/partB/dev-nohook-contention-*/loop1.txt`).
  The published statement that unhooked `dev` passed 50/50 per JDK under contention therefore did not
  reproduce in this environment. With native aarch64 JDKs on 10 container CPUs and 20 busy loops, CPU
  contention alone produced the same assertion failure that the hook forces.
- The patched revision failed 0/20 per JDK in both environments.
- Hooked `dev` at the article's stall position (lead 35 ms): 20/20 (JDK 8) and 16/20 (JDK 11) fresh,
  against 17/20 and 19/20 published. Both are high failure rates; the counts differ.
- The sensitivity sweep moved toward fewer failures in the container (lead 55 ms: 2/20 and 5/20 fresh,
  10/20 and 11/20 published; lead 65 ms: 1/20 and 0/20 fresh, 4/20 and 4/20 published). In the pooled
  table more hooked iterations woke before `idleDeadlineMs` in the container (50 of 160, against 35 of
  160), and those rarely failed in either environment (1/50 fresh, 0/35 published). Iterations that woke
  10 ms or more after the deadline failed in most cases in both (57/78 fresh, 81/89 published); the
  `>= 20 ms` bucket is lower in the container (30/42 against 50/54).
- Part B results are rates of a timing-dependent race with one loop per cell. A single loop per cell
  in each environment does not separate the environment effect from loop-to-loop variation.

## Part C

Not run (the current `replay.sh` does not run it; see `replay-2026-10-26/README.md`). The historical
Part C records in the fresh `results.json` are identical to the published ones
(the container's copies of `logs/partC` and `logs/setup/*partC*` were byte-identical to `replay-2026-10-26/logs/` and are not duplicated under `out/bundle/`).

## Notes

- The `harness` entries of the fresh `results.json` carry the `sha256_as_run` and `revised_after_runs`
  notes written by `make_results.py` at `d059baf`; those notes describe the 2026-10-25 runs. The
  scripts executed in the container are identified by `out/env/records-commit.txt`.
- The fresh `results.json` lists `logs/setup/setup-partA-20261026T044212.txt` and
  `logs/setup/setup-partB-20261026T054604.txt` as the requested matrix (Part A 5 runs per cell, Part B
  one loop per cell).
