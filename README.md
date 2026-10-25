# Datapath-testing records

This repository holds the reconstruction records for the SeaTunnel cases of the article
(Table 1 and the PR 12472 stall records) and the saved CI records it cites.

| Location | Contents |
| --- | --- |
| Repository root: this README (from the next heading on), [`harness/`](harness/), [`logs/`](logs/), [`results.json`](results.json) | The first reconstruction, 2026-10-25: one run per Part A cell. Kept as published. |
| [`replay-2026-10-26/`](replay-2026-10-26/) | The second reconstruction: a portable replay bundle with one entry point (`replay.sh --part A\|B\|C\|all --runs N`). It clones apache/seatunnel at the pinned commits into `work/`, builds, and runs 5 runs per Part A and Part C cell, one more loop per Part B cell, and explicit teardown assertions. It has its own [README](replay-2026-10-26/README.md), `results.json` (with the sha256 of every log) and `logs/`, and its README compares each cell with the article and with 2026-10-25. |
| [`ci-evidence/`](ci-evidence/) | Saved GitHub Actions records of apache/seatunnel that the article cites inline: the nightly run list for 2 to 23 October 2026, the job time-limit annotations, the 22 October manual cancellation, the September push/nightly run records and the Windows job excerpt. Run ids and retrieval times are as saved. |

---

# Replay of Table 1 and the PR 12472 stall-injection records (reconstruction, 2026-10-25)

Everything in this directory is a **reconstruction made on 2026-10-25**. The author's original
harnesses (the fault-injecting Maven mirror, the stall hook, the killed-container harness) were
local-only and were never published; their raw logs are lost. The harnesses here were rewritten
from the text of the pull-request descriptions, run once on 2026-10-25, and every number below
comes from a log in `logs/` (per-cell paths and sha256 in `results.json`). Nothing here is the
original evidence, and where the reconstruction had to guess, the guess is listed under
"Deviations and interpretation choices".

This record does not edit the article, the resolutions or any review file, and decides no
approval (FIX-02-TABLE-EVIDENCE remains with the author).

## Summary

- Part A (rows 1-5): 9 of 10 article cells reproduced on both JDKs (one run per cell). Row 3
  "Before" (429 control "succeeds") did **not** reproduce: Maven 3.8.4 failed on both JDKs with
  `Attempted read from closed stream`, a wagon-http 3.4.3 429-path defect; it passes only when the
  429 responses carry no body, and then via a checksum-triggered re-download.
- Part B: hooked `dev` failed 20/20 on both JDKs (article/PR: 15/20 and 7/20); patched test with
  stalls 0/20 and 0/20 (matches); unhooked `dev` under contention 50/50 passes per JDK (matches).
  The exact rates depend on where the 45 ms stall lands, which the PR text does not pin down; a
  sweep gives 2/20 to 20/20.
- Part C (rows 6-7, 5 runs per cell): Flink before: teardown threw 5/5, JobManager leaked 5/5,
  next job hung 2/5; Flink after: 5/5 clean, next job exit 0 5/5; Spark before: teardown threw 5/5,
  master left behind 5/5; Spark after: 5/5 completed with the warning, removed, next job exit 0.
  Zeta not re-run (image not cached).

## Sources the reconstruction was built from

| Part | Article text | PR text used to rebuild the harness |
| --- | --- | --- |
| A | `manuscript/article.md` Table 1 rows 1-5 and the PR 12468 paragraph | `source/raw/seatunnel_12468.md`, "Before vs after" table and "How was this patch tested?" |
| B | `manuscript/article.md` PR 12472 paragraphs (numbers omitted in the article; the PR reports them) | `source/raw/seatunnel_12472.md`, "Forced timing window on unchanged `dev`" |
| C | `manuscript/article.md` Table 1 rows 6-7 | `source/raw/seatunnel_12481.md`, "E2E, local (Docker Desktop, JDK 8)" |

Revisions (apache/seatunnel, blobless clone in
`/Users/goutamadwant/Documents/ResearchPaper/runtime/replay/seatunnel`, gitignored runtime dir;
nothing was pushed):

| Use | Commit |
| --- | --- |
| PR 12468 "before" (parent of the merge) | `a1084015eeb390a6c7f53d3ce7391217e427e4d9` |
| PR 12468 "after" (merge) | `ae7c919bcb78f03446dbd2b754a2b9882602946a` |
| PR 12472 unchanged `dev` (as named in the PR) | `deb16a3c3152f0349a587a504dccc997a131a9d7` |
| PR 12472 patched (merge) | `87ed0afe0f783eda1b1f3ac6f0ac9fadedcb4f98` |
| PR 12481 "before" (parent of the merge) | `7ba68325cb7ea1bf1a28f56c4f9c20695d221df3` |
| PR 12481 "after" (merge, "final shared revision") | `0e4cf52896ee3604a8e7899d7736ffd914ee6ce7` |

## Environment and toolchain (full record: `logs/toolchain.txt`)

- MacBook Pro, Apple M1 Pro (10 cores), 16 GB, macOS 27.0 (26A428). Normal desktop load from
  other applications was present during all runs (load averages 5-7 are printed in the Part B
  log headers); the machine was not isolated.
- JDK 8: Oracle `1.8.0_172-b11`; JDK 11: Temurin `11.0.19+7`. Both are x86_64 builds and ran
  under Rosetta 2. These are the same version strings the PRs name.
- Maven 3.8.4 through the project wrapper (maven-wrapper 3.1.0), wagon-http 3.4.3 (shaded),
  maven-resolver 1.6.3. Wrapper jar sha1 `32f70e9f2cd92fd7629aba8214d1c9ae58a1e2fd` (matches
  Maven Central's published .sha1).
- curl 8.9.1 (the wrapper's downloader here; `wget` is not installed, the CI log in PR 12468 shows
  wget). Python 3.12.7. Docker Desktop 29.9.2, linux/arm64 VM; the Flink and Spark images are
  amd64 and ran under emulation.
- **Installs performed: none.** Both JDKs, the Maven 3.8.4 wrapper distribution, docker, gh and
  python3 were already on the machine.

## Results: reconstruction vs article, per cell

### Part A: PR 12468, Table 1 rows 1-5 (one run per cell, as in the PR)

`before` = `mvnw` from `a1084015e`, no `.mvn/maven.config`; `after` = `mvnw` and
`.mvn/maven.config` from `ae7c919bc`. "junit pom requests" = GET requests the fault mirror logged
for `junit/junit/4.13.2/junit-4.13.2.pom` (the first fault target); the same pattern held for every
other junit path (`junit-4.13.2.jar`, `junit-3.8.1.pom/.jar`, `junit-3.8.2.pom`, pulled in by the
dependency plugin).

| Row | Fault | Config | Article | JDK 8 replay | JDK 11 replay | Match |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | HTTP 503 on first 2 requests | before | fails on the first 503 | FAIL; 1 request (503); 5.0 s | FAIL; 1 request (503); 10.2 s | yes |
| 1 | | after | succeeds on the third request | PASS; 3 requests (503, 503, 200), 1.0 s apart; 19.5 s | PASS; same pattern; 19.6 s (second attempt, see invalid run) | yes |
| 2 | Connection reset on first 4 requests | before | fails after four attempts | FAIL; 4 requests (all reset), `Connection reset`; 4.6 s | FAIL; same; 5.9 s | yes |
| 2 | | after | succeeds on the fifth | PASS; 5 requests (4 reset, then 200); 9.1 s | PASS; same; 11.4 s | yes |
| 3 | HTTP 429 on first 2 requests (control) | before | succeeds, transport backs off on 429 | **FAIL**; 3 requests at 0, 5.0, 15.0 s (429, 429, 200), then `GET request of: junit/junit/4.13.2/junit-4.13.2.pom from faultmirror failed: Attempted read from closed stream.`; 20.1 s | **FAIL**; same; 21.0 s | **no** |
| 3 | | after | succeeds | PASS; 3 requests at 0, 1.0, 2.0 s; 26.6 s | PASS; same; 23.1 s | yes |
| 4 | Response body cut off halfway (first request) | before | fails | FAIL; 1 request; `Premature end of Content-Length delimited message body (expected: 27,018; ...)`; 9.8 s | FAIL; same; 7.5 s | yes |
| 4 | | after | still fails | FAIL; 1 request, same message (no retry); 11.7 s | FAIL; same; 6.8 s; **no hang** | yes |
| 5 | Wrapper jar 429 for 30 s | before | fails at 21 s, main class not found | FAIL; 5 attempts at 0, 5.1, 10.2, 15.3, 20.5 s (all 429); `Could not find or load main class org.apache.maven.wrapper.MavenWrapperMain` | FAIL; attempts at 0, 5.1, 10.1, 15.2, 20.2 s; same message | yes (last attempt at 20.2-20.5 s) |
| 5 | | after | succeeds at 35 s on the fourth attempt | PASS; attempts at 0, 5.1, 15.3, 35.6 s, 4th served | PASS; attempts at 0, 5.0, 15.1, 35.2 s, 4th served | yes |

Times in the "attempts at" lists are relative to the first request the mirror saw; the trailing
seconds value is the wall time of the whole `./mvnw` process (JVM start, plugin download and
resolution included).

**Row 3 does not reproduce.** In this reconstruction, Maven 3.8.4 without the new config fails
on the 429 control on both JDKs. The cause is visible in the wagon-http 3.4.3 bytecode
(`javap -c` of
`org.apache.maven.wagon.providers.http.wagon.shared.AbstractHttpClientWagon.fillInputData`): the
429 branch consumes the 429 response's entity, backs off, calls `fillInputData` recursively (which
fetches the 200 response correctly), and then falls through to the common tail, which reads
`Content-Length` and the input stream from the **outer 429 response** again. With a 429 that has a
body, that stream is already consumed and closed: `Attempted read from closed stream`.

Sensitivity variant (not a Table 1 row; `429x2nobody`, run after the primary matrix): the same
cell with 429 responses that have an empty body (`Content-Length: 0`). Both JDKs then PASS
(84.7 s and 84.4 s), but not by a clean backoff: each junit path is requested four times (429,
429, 200, 200); the backoff path stores an empty file
(`Checksum validation failed, expected 73bc5be6... but is da39a3ee...`, the SHA-1 of the empty
string), and the resolver's checksum failure triggers the extra download. So the article's
"succeeds" for row 3 holds in this reconstruction only for body-less 429s and only because the
mirror serves checksums; with a 429 that carries a body it fails. Which kind the original server
sent is not recorded.

### Part B: PR 12472 stall injection (`FileCollectReaderBehaviorTest.rediscoversFileAfterInactiveCursorClosed`)

One JVM per cell, the single method run N times through the JUnit Platform launcher
(`harness/java/RepeatMethod.java`), as the PR describes. Every iteration's outcome and duration is
in the cell's log.

| Cell | Code | Article / PR | JDK 8u172 replay | JDK 11.0.19 replay | Match |
| --- | --- | --- | --- | --- | --- |
| Hook as reconstructed (one 45 ms sleep at the first evaluation of the first Awaitility loop that is <= 35 ms before the test's `idleDeadlineMs`) | `deb16a3c3` + `hook-dev-deb16a3c3-stall45.patch` | 15/20 and 7/20 failed | **20/20 failed** | **20/20 failed** | no (direction yes, rate no) |
| Patch with stalls (45 ms before close step, 700 ms after close, 700 ms after rediscovery) | `87ed0afe0` + `hook-patch-87ed0afe0-stalls.patch` | 0/20 and 0/20 failed | 0/20 failed | 0/20 failed | yes |
| No hook, CPU contention (20 busy-loop shell processes) | `deb16a3c3` unchanged | 50/50 passed per JDK | 50/50 passed | 50/50 passed | yes |

Every failure, in every hooked cell, carried the CI message: `ConditionTimeoutException ...
expected: <1> but was: <0> within 3 seconds`.

Sensitivity sweep over the hook position (not in the article; same hook, the system property
`replay.stall.lead.ms` moves the stall earlier). The stall position is the one thing the PR text
leaves ambiguous ("35 ms before the idle deadline": the test's `idleDeadlineMs`, which is close
threshold + 30 ms, or the reader's close threshold itself, which is 65 ms before
`idleDeadlineMs`):

| Stall placed at <= N ms before `idleDeadlineMs` | JDK 8 failed | JDK 11 failed |
| --- | --- | --- |
| 35 (primary reading) | 20/20 | 20/20 |
| 45 | 17/20 | 18/20 |
| 55 | 11/20 | 11/20 |
| 65 (= 35 ms before the reader's 500 ms close threshold) | 7/20 | 2/20 |

The hook logs where each stall started and ended relative to `idleDeadlineMs`. Pooled over all
eight hooked cells (160 iterations), by the time the stalled (closing) poll woke relative to
`idleDeadlineMs`: woke before it, 0 of 35 failed; woke 0-9 ms after, 21 of 36 failed; 10-19 ms
after, 41 of 44 failed; 20 ms or more after, 44 of 45 failed. A closing poll pushed past the
deadline leaves no scan interval for rediscovery before the append, which is the mechanism the
article describes. The PR's 15/20 and 7/20 fall inside the range this sweep spans,
but no single reconstructed hook position reproduces both numbers, so the reconstruction confirms
the mechanism and the direction (hooked `dev` fails, patched test survives the stalls, unhooked
`dev` passes under contention), not the specific rates.

### Part C: PR 12481, Table 1 rows 6-7 (Docker E2E)

Docker Desktop, JDK 8u172 on the host, images `tyrantlucifer/flink:1.18.0-scala_2.12_hadoop27` and
`tyrantlucifer/spark:3.3.0` (both already cached). Each run: start the engine, `docker kill` the
TaskManager (Flink) or master (Spark), call `tearDown()`, start a new container of the same engine,
run `/fake_to_assert.conf` with a 150 s limit. 5 runs per cell. Run order (wall clock):
Flink after run 1 00:50-00:52; Flink before runs 1-5 00:53-01:05; Flink after runs 2-5 01:05-01:12;
Spark before 01:12-01:16; Spark after 01:16-01:21.

| Row | Scenario | Revision | Article | Replay (5 runs) | Match |
| --- | --- | --- | --- | --- | --- |
| 6 | Flink 1.18 TaskManager killed, teardown, next job | before (`7ba68325c` teardown classes) | on dev, teardown threw in 11 of 11 runs; in 6 of them the next job hung > 120 s | teardown threw in **5/5** (`ConflictException: Status 409 ... is not running`); first JobManager left running in 5/5; new TaskManager registered with the **leaked** JobManager in 2/5 (REST `/overview`: 0 at its own, 1 at the leaked one) and in those 2 the next job hung past the 150 s limit, the JobManager logging `Missing resources ... numberOfRequiredSlots=1 / Current resources: (none)`; in the other 3/5 the next job exited 0 | yes (pattern; 2/5 vs 6/11 hang share) |
| 6 | | after (merge `0e4cf5289`) | final shared revision: 2 of 2 completed, next job exit 0 | teardown completed **5/5**; both first containers removed 5/5; new TaskManager at its own JobManager (4/4 measured; run 1 used the IP check, inconclusive); next job exit 0 in **5/5** | yes |
| 7 | Spark 3.3 master killed, teardown, next job | before | teardown threw, killed container left behind | teardown threw **5/5** (`ConflictException: Status 409 ... is not running`); killed master left behind (exited, not removed) 5/5; next job exit 0 5/5 | yes |
| 7 | | after | teardown completed with a warning, container removed, next job exit 0 | teardown completed **5/5** with `WARN ... is not running, skipping the removal of /tmp/seatunnel_mnt inside it`; master removed 5/5; next job exit 0 5/5 | yes |
| 7 | Zeta server killed | both | (as above) | **not re-run**: image `seatunnelhub/openjdk:8u342` is not cached | - |

The macOS runs logged no host-directory cleanup warning (the article's Linux CI warning concerns
root-owned files on Linux runners; this replay cannot speak to it).

## Exact commands

All scripts are in `harness/`; all paths absolute.

Part A (fault mirror, tiny pom, settings template, driver):

```
# warm the served repository from Maven Central (once; log: logs/partA/warm-repo-build.txt)
cd /Users/goutamadwant/Documents/ResearchPaper/runtime/replay/partA/warmdir
JAVA_HOME=<jdk> ./mvnw -B -s harness/settings-empty.xml -Dmaven.repo.local=/Users/goutamadwant/Documents/ResearchPaper/runtime/replay/partA/warm-repo -f pom.xml dependency:resolve
# the matrix (20 primary cells), then the re-run of the invalid cell and the sensitivity variant
python3 harness/run_part_a.py
python3 harness/run_part_a.py jdk11_503x2_after
python3 harness/run_part_a.py jdk8_429x2nobody_before jdk11_429x2nobody_before
```

Per run the driver starts
`python3 -I harness/fault_mirror.py --root <warm-repo> --fault <fault> --log <server log> --port-file <f>`
on a free loopback port, writes a `settings.xml` with one mirror (`<mirrorOf>*</mirrorOf>`,
`http://127.0.0.1:<port>/maven2`), creates a fresh project directory with the configuration's
`mvnw`/`.mvn` files and `tiny-pom.xml`, an empty local repository, and runs (exact line, recorded
at the top of every `logs/partA/*.mvn.txt`):

```
./mvnw -B -s <run>/settings.xml -Dmaven.repo.local=<run>/repo -f pom.xml dependency:resolve
```

with `JAVA_HOME` set to the JDK under test and `MAVEN_OPTS` empty. Run order: JDK 8 then JDK 11;
within each, faults in the order 503, reset, 429, truncate, wrapper; `before` then `after`.

Part B:

```
harness/build_partB.sh /Users/goutamadwant/Documents/ResearchPaper/runtime/replay/wt-dev   <jdk8> logs/partB/build-dev-deb16a3c3-jdk8.full.txt
harness/build_partB.sh /Users/goutamadwant/Documents/ResearchPaper/runtime/replay/wt-patch <jdk8> logs/partB/build-patch-87ed0afe0-jdk8.full.txt
#   = ./mvnw -B -T 1 -pl seatunnel-edge-agent/seatunnel-edge-agent-connector -am package dependency:build-classpath
#       -DskipUT=true -DskipTests -Dspotless.check.skip=true -Dspotless.apply.skip=true -Dlicense.skipAddThirdParty=true
#       -Dmdep.outputFile=target/test-classpath.txt -Dmdep.includeScope=test --no-snapshot-updates
harness/run_part_b.sh dev-hook-jdk8 dev-hook-jdk11 patch-hook-jdk8 patch-hook-jdk11
harness/run_part_b.sh dev-nohook-contention-jdk8 dev-nohook-contention-jdk11 dev-hook-lead65-jdk8 dev-hook-lead65-jdk11
harness/run_part_b.sh dev-hook-lead45-jdk8 dev-hook-lead45-jdk11 dev-hook-lead55-jdk8 dev-hook-lead55-jdk11
```

`run_part_b.sh` applies the hook patch to a copy of the test file, compiles it with JDK 8
`javac -source 8 -target 8` against the module's test classpath, puts it first on the classpath
and runs `java -cp <cp> RepeatMethod <class> rediscoversFileAfterInactiveCursorClosed <N>`; the
exact java command and classpath are in each log header.

Part C:

```
harness/build_partC.sh /Users/goutamadwant/Documents/ResearchPaper/runtime/replay/wt-e2e <jdk8> logs/partC/build-after-0e4cf5289-jdk8-2.full.txt
#   = ./mvnw -B -T 1C -pl seatunnel-core/seatunnel-flink-starter/seatunnel-flink-15-starter,seatunnel-core/seatunnel-spark-starter/seatunnel-spark-3-starter,
#       seatunnel-connectors-v2/connector-fake,seatunnel-connectors-v2/connector-assert,seatunnel-transforms-v2,
#       seatunnel-e2e/seatunnel-connector-v2-e2e/connector-fake-e2e -am package dependency:build-classpath
#       -DskipUT=true -DskipIT=true -DskipTests -Dspotless.check.skip=true -Dspotless.apply.skip=true
#       -Dlicense.skipAddThirdParty=true -De2e.dependency.skip=false -Dmdep.outputFile=target/test-classpath.txt
#       -Dmdep.includeScope=test --no-snapshot-updates
harness/run_part_c.sh before flink118TaskManagerKilled 5
harness/run_part_c.sh after  flink118TaskManagerKilled 1   # first run
harness/run_part_c.sh after  flink118TaskManagerKilled 4
harness/run_part_c.sh before spark3MasterKilled 5
harness/run_part_c.sh after  spark3MasterKilled 5
python3 harness/make_results.py
```

## Deviations and interpretation choices

Part A

1. The mirror is a new Python implementation. It serves the warm repository over HTTP/1.1 with
   keep-alive and Content-Length; checksum files are computed on the fly, and `maven-metadata.xml`
   is served from the local repository's `maven-metadata-<repo>.xml`.
2. "Faults for `junit` paths" was read as: every request path containing `/junit/` that is not a
   checksum file; the first N requests **per path** get the fault. The dependency plugin's own
   dependencies `junit:3.8.1` and `junit:3.8.2` therefore also received faults.
3. "Body cut off halfway" truncates only the **first** request per path (a retry would get the full
   body), so a failure shows that no retry happened. The original's choice is unknown.
4. The wrapper-429 window starts at the first wrapper-jar request. Because `wrapperUrl` in
   `.mvn/wrapper/maven-wrapper.properties` overrides `MVNW_REPOURL` in this `mvnw`, the harness
   rewrites `wrapperUrl` to the local mirror in the run's copy (only for that case). The
   distribution URL was left unchanged; Maven 3.8.4 was already in `~/.m2/wrapper`. The downloader
   was curl (`-f`), not wget.
5. The tiny project resolves `junit:junit:4.13.2`; plugin versions come from the Maven 3.8.4 super
   POM (maven-dependency-plugin 2.8).
6. One run per cell, as in the PR; no repetitions. Review item DOM-02-003 asks for at least 5; that
   was not done for Part A within the time box.
7. Invalid run kept: the first `jdk11_503x2_after` run (order 12) never reached the mirror because
   a stale port file from a 00:17 smoke test pointed `settings.xml` at a dead port (`No plugin found
   for prefix 'dependency'`). The driver was fixed (port file removed before start) and the cell
   re-ran at order 21. Logs: `logs/partA/invalid/`. The smoke-test run's own logs were deleted
   before the matrix (it was the same cell; this is the only deleted run record).

Part B

8. The hook is reconstructed as a patch file. "35 ms before the idle deadline" was read as 35 ms
   before the test's `idleDeadlineMs`; the alternative readings are covered by the sensitivity
   sweep. The hook prints one `REPLAY-HOOK` line per iteration.
9. "This patch" was run as the merge commit `87ed0afe0`, whose parent already contains PR 12381
   (Awaitility budgets 3 s -> 10 s in the final wait). The PR's own patched runs were based on
   `deb16a3c3`. The stall points match the PR text (45 ms before the close step, 700 ms after the
   close, 700 ms after rediscovery).
10. Both revisions were built and the hooked tests compiled with JDK 8 only; the JDK 11 cells ran
   the JDK 8-compiled classes on JDK 11 (the PR built per JDK).
11. CPU contention = 20 `bash` busy loops (`while :; do :; done`) for the duration of the run (the
   PR's stress section names 20 busy-loop processes; the contention used for its 50/50 run is not
   described further). The load average printed 2 s after starting them understates the load.
12. The PR's 200/200 stress run and the two mutation checks were not part of this task and were
   not re-run.

Part C

13. The harness (`harness/java/ReplayKillTeardownTest.java`) is new. It drives the framework's
   own `Flink18Container` / `Spark3Container` (subclassed only to read the container handles): start,
   `docker kill` the TaskManager (Flink) or master (Spark), `tearDown()`, start a new container of
   the same engine, run `/fake_to_assert.conf` with a 150 s limit, then tear down and force-remove
   any leftovers so runs are independent.
14. "Before" is the merge build with the four teardown classes from the parent `7ba68325c`
   (`AbstractTestContainer`, `AbstractTestFlinkContainer`, `AbstractTestSparkContainer`,
   `SeaTunnelContainer`) compiled and placed first on the classpath; the starters and connectors
   are byte-identical between the two revisions (PR 12481 changes only those test-framework files).
15. Which JobManager the new TaskManager joined is read from each JobManager's REST `/overview`
   (`taskmanagers`), because the TaskManager log names the JobManager only by its alias. The
   first "after" run used an earlier harness revision that compared container IPs (inconclusive,
   both removed/reused); its teardown and job outcome are unaffected. Harness sha256 is in each log.
16. The Flink-only intermediate revision of PR 12481 (article: 12 of 12) is not reconstructible
   from the merged history and was not run. Zeta was not run (see below).
17. Docker Desktop on Apple silicon runs the amd64 images under emulation; the PR's runs were on
   Docker Desktop with an unknown host architecture.
18. The first attempt of the first "after" Flink run failed before starting (the test classpath
   was not written because the e2e parent pom skips `maven-dependency-plugin` unless
   `-De2e.dependency.skip=false`); a classpath-only invocation then resolved reactor modules to the
   user's stale `~/.m2` snapshots and was discarded. Both are kept in `logs/partC/invalid/`; the
   module was rebuilt with the flag (`build-after-0e4cf5289-jdk8-2.full.txt`).

General

19. Logs are stored as `.txt`/`.jsonl` because the repository's `.gitignore` ignores `*.log`.
20. No log was truncated: all logs together are 8.2 MB (Part A 2.7 MB, Part B 0.25 MB, Part C
   5.2 MB including two 0.7 MB build logs), under the 50 MB limit. The container logs in Part C are
   complete as captured by Testcontainers' log consumers.
21. The E2E framework uses the fixed host path `/tmp/seatunnel_mnt`; it was created and removed by
   the framework itself and is absent after the runs.

## Not re-run

- **Table 1 row 7, Zeta server killed (before and after):** not re-run. `SeaTunnelContainer`
  needs `seatunnelhub/openjdk:8u342`, which is not in the local Docker cache, and the task allowed
  Part C only with cached images.
- **Table 1 row 6, Flink-only intermediate revision of PR 12481 ("teardown completed in 12 of 12
  runs"):** not re-run; that revision is not in the merged history (only the parent and the merge
  were run).
- **Repetitions for Part A:** one run per cell, as in the PR and as requested; review item
  DOM-02-003 asks for at least 5 per row, which was not done for rows 1-5.
- **PR 12472 200/200 stress run and the two mutation checks:** not part of this task.
- **Windows:** nothing here ran on Windows; Part B says nothing about Windows failure rates.

## Files

- `/Users/goutamadwant/Documents/ResearchPaper/lanes/ieeesw2026-datapath-testing/experiments/replay-2026-10-25/README.md`
- `/Users/goutamadwant/Documents/ResearchPaper/lanes/ieeesw2026-datapath-testing/experiments/replay-2026-10-25/results.json`
- `/Users/goutamadwant/Documents/ResearchPaper/lanes/ieeesw2026-datapath-testing/experiments/replay-2026-10-25/harness/`
  (`fault_mirror.py`, `run_part_a.py`, `tiny-pom.xml`, `settings-mirror.template.xml`,
  `settings-empty.xml`, `build_partB.sh`, `run_part_b.sh`, `hook-dev-deb16a3c3-stall45.patch`,
  `hook-patch-87ed0afe0-stalls.patch`, `java/RepeatMethod.java`, `build_partC.sh`, `run_part_c.sh`,
  `java/ReplayKillTeardownTest.java`, `make_results.py`)
- `/Users/goutamadwant/Documents/ResearchPaper/lanes/ieeesw2026-datapath-testing/experiments/replay-2026-10-25/logs/`
  (`toolchain.txt`, `partA/`, `partB/`, `partC/`)

## Paths

Absolute paths in `results.json` and the logs refer to the workstation where the runs were executed on 2026-10-25; relative to this repository they resolve under `./`.
