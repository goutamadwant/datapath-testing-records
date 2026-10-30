# Fail-before / pass-after runs of the regression tests named in the article

This bundle runs every regression test the article names against the code before and after the
pull request that added it:

- **before**: the first parent of the pull request's merge commit, with only the pull request's
  test change applied on top (whole test files copied from the merge commit; for DataFusion PR
  24193, whose test lives in the same file as the fix, only the hunks inside `mod tests`, see
  `patches/df24193-tests-only.patch`; likewise for the PR 24917 planning-budget tests,
  `patches/df24917-budget-tests-only.patch`). Production code is the unfixed code.
- **after**: the merge commit as is.

The same command runs on both trees. Every outcome below is parsed by `make_results.py` from a log
under `logs/` that an executed run wrote; `results.json` lists every run, its outcome, the per-test
results, the commands, the commit hashes, the durations and the sha256 of every log and patch.
Retained failed and interrupted runs are included; two stopped attempts whose records were
deleted are documented in the [2026-10-30 registry addendum](logs/aborted-invocations-2026-10-30.md).

Runs executed on 2026-10-25 between 19:02 and 19:51 local time (UTC-7) on an Apple M1 Pro,
16 GB, macOS 27.0 (Darwin 27.0.0 arm64). The directory name gives the bundle date, not the run
date. Toolchains: rustc/cargo 1.97.0 (pinned by DataFusion's `rust-toolchain.toml`); JDK
1.8.0_172 with the Maven wrapper of each SeaTunnel commit. The `df24917-budget` case was run
later, on 2026-10-26 between 01:54 and 01:56 local time (UTC-7), on the same machine with the
same Rust toolchain and with no other build running.

## Results

Outcome codes: FAIL / PASS = the test named in the command was executed; COMPILE_ERROR = the
test sources of the module under test did not compile against that tree, so the test could not
run; NO_TESTS_RUN = the filter selected nothing, or every selected test was ignored or skipped;
UNKNOWN = the log does not establish an outcome (no summary line, a summary that disagrees with
the per-test lines, or the named test absent from the executed tests); SETUP_ERROR = the side was
never run because a setup step (clone, checkout, transplant or patch apply, missing JDK, refusal)
failed (no recorded run has this outcome).

Parser revision 2 (2026-10-26). The first `make_results.py` would have reported PASS for a cargo run
whose only selected test was `ignored`, and did not check that the named test was among the
executed ones. The revised parser requires the named test to have executed, treats ignored-only
and skipped-only runs as NO_TESTS_RUN, reports a log whose summary line disagrees with its
per-test lines as UNKNOWN, and marks a case without both a before and an after record as
`comparison: incomplete` in `results.json`. No recorded run was affected: every outcome, test
list and log hash in `results.json` is the same under both parsers (the logs are unchanged;
`results.json` gains the `parser`, `expected_test` and `comparisons` fields). The checks are in
`test_make_results.py` (`python3 -I test_make_results.py`). The addition of the SETUP_ERROR
outcome and the requested-sides check described under "Run record" changed no earlier outcome,
test list, comparison or log hash either.

Parser revision 3 (2026-10-30) recognises the literal `$FAILBEFORE_WORK/` prefix like an
absolute path for Maven test-source errors; re-running it over all retained logs changes
none of the 23 historical run outcomes.

| PR | Test | Before commit | After commit | Before outcome | After outcome | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| DataFusion 24193 | `repartition::tests::unbounded_input_emits_before_batch_size` (`datafusion-physical-plan`) | `d5868e683435` | `047f531488f6` | **FAIL** (1/1): panicked `unbounded repartition withheld a partial batch: Elapsed(())` after the 5 s timeout (`finished in 5.01s`) | **PASS** (1/1) | Fails before, passes after. Only the test-module hunks were applied on the parent |
| DataFusion 24917 | `optimizer::expensive_regexp_like_is_deferred_to_execution` (`datafusion`, `--test core_integration`) | `408527ae58b5` | `3dfa245d61dd` | **PASS** (1/1) | **PASS** (1/1) | The test does not fail on the unfixed code. A diagnostic run (`df24917-diag`, same test with the plans and the planning time printed, 3 runs per tree) shows identical logical plans on both trees: `Projection: Utf8("aaaaa") ~ Utf8("a{5}{5}{5}{5}{5}{5}{5}{5}")` and `Projection: Boolean(NULL)`. Only the planning time of the literal query differs: 550.5 / 488.2 / 478.7 ms before, 31.6 / 12.1 / 10.0 ms after (unoptimized `ci` profile). The test asserts the plan shape, which the fix does not change; it does not assert time |
| DataFusion 24917 | `test_constant_regex_respects_planning_budget` in `simplify_expressions::expr_simplifier::tests` (`datafusion-optimizer`) and in `simplifier::tests` (`datafusion-physical-expr`), `--lib` | `408527ae58b5` | `3dfa245d61dd` | **COMPILE_ERROR**, 2 errors: `error[E0407]: method should_evaluate_const is not a member of trait ScalarUDFImpl`, once in each package (the test UDFs implement the hook the pull request added) | **PASS** (2/2: 1/1 per package) | Not runnable against the unfixed code; no shim. Only the hunks that add the two tests (and the physical test's imports) were applied on the parent. See below |
| SeaTunnel 12038 | `AmazonSqsSourceReaderTest` (9 methods, `connector-amazonsqs`) | `9ebb27e8f920` | `1e450e11f7c8` | **COMPILE_ERROR**: `no suitable constructor found for AmazonSqsSourceConfig(String,String,<null>,<null>,<null>,boolean,boolean,<null>)` (the pull request added `ignoreParseErrors` to the all-arguments constructor) | **PASS** (9/9) | Not runnable unmodified against the unfixed code. With a one-line shim (`patches/st12038-reader-test-drop-ignore-arg.patch`, drops that constructor argument): before **FAIL 6/9**, after **PASS 9/9**; see below |
| SeaTunnel 12038 | `AmazonSqsSourceFactoryTest#testOptionRule` (extended by the same PR) | `9ebb27e8f920` | `1e450e11f7c8` | **COMPILE_ERROR**: `cannot find symbol` for `AmazonSqsSourceOptions.IGNORE_PARSE_ERRORS` (and the reader-test error above) | **PASS** (1/1) | The test checks the new option itself; not runnable against the unfixed code. No shim |
| SeaTunnel 12360 | `IncrementalSourceReaderTest` (14 methods, `connector-cdc-base`) | `4648c9956ec8` | `eb76f81c823a` | **PASS** (14/14) | **PASS** (14/14) | The pull request changed only this test file (415 insertions), so before-with-test and after are the same source tree. No production change exists that the test could detect; this matches the article's negative result. A fail-before comparison is not applicable |
| SeaTunnel 12472 | `FileCollectReaderBehaviorTest#rediscoversFileAfterInactiveCursorClosed` (`seatunnel-edge-agent-connector`) | `e1a7e64b6733` | `87ed0afe0f78` | **COMPILE_ERROR**: `constructor FileCollectReader in class FileCollectReader cannot be applied to given types` (the test passes a clock through the constructor the pull request added) | **PASS** (1/1) | Not runnable against the unfixed code. No shim: the missing constructor is the production change itself. The pull request made the test deterministic; it did not fix reader behavior |
| SeaTunnel 12481 | `AbstractTestContainerTest` (12 methods) and `AbstractTestFlinkContainerTest` (5 methods) (`seatunnel-e2e-common`) | `7ba68325cb7e` | `0e4cf52896ee` | **COMPILE_ERROR**, 9 errors: `cannot find symbol` for the static helpers the pull request added (`removeContainerVolumeMountPath`, `deleteHostPath`, ...), and `method does not override or implement a method from a supertype` for the test doubles' `deleteHostVolumeMountPath()` (2 in `AbstractTestContainerTest`, 1 in `AbstractTestFlinkContainerTest`) | **PASS** (17/17) | Not runnable unmodified. `AbstractTestContainerTest` calls the new helpers directly; no shim. With a one-line shim for the Flink test only (`patches/st12481-flink-test-drop-override.patch`, drops one `@Override`): before **FAIL 5/5**, after **PASS 5/5**; see below. No Docker container is started by these tests (mocked containers) |
| SeaTunnel 12467 | none | `c8c497376030` | `7ba68325cb7e` | not applicable | not applicable | Workflow concurrency-group change; the pull request adds no test |
| SeaTunnel 12468 | none | `a1084015eeb3` | `ae7c919bcb78` | not applicable | not applicable | `.mvn/maven.config` and `mvnw` change; the pull request adds no test (fault-injection reconstructions are in the 2026-10-26 replay bundle) |

### DataFusion 24917 planning-budget tests on the parent

Pull request 24917 also added `test_constant_regex_respects_planning_budget` to the logical
expression simplifier and to the physical expression simplifier. Both tests check that the
constant pattern `a{5}{5}{5}{5}{5}{5}`, valid under the runtime regex size limit but over the new
256 KiB planning limit, is left unevaluated during simplification (as a regex operator, under an
alias, and for the physical simplifier also as `regexp_like` with a flag argument), that a small
pattern is still folded, and that the new `ScalarUDFImpl::should_evaluate_const` hook works: in
the logical test a UDF opts out of constant evaluation through it, in the physical test the hook
is not consulted for a call with a column argument. Each test defines its own UDF implementing that hook,
so on the parent neither test compiles: the log shows one `E0407` error in each package and no
test runs. On the merge commit both tests pass. The regex assertions, which do not use the hook,
were therefore never executed against the unfixed code; this run establishes neither a failure
nor a pass for them before the fix. No shim was applied: the missing member is the extension point
the fix introduces, and removing it would mean deleting a three-line method from each test, not a
one-line adaptation.

### Shimmed runs, per method

These runs modify the transplanted test by one line so that it compiles against the unfixed code.
They are reported separately from the unmodified runs above; the shim is in `patches/`.

**SeaTunnel 12038, `AmazonSqsSourceReaderTest` with `st12038-reader-test-drop-ignore-arg.patch`**
(before = `9ebb27e8f920` + test + shim; after = `1e450e11f7c8` unmodified; the same applies to the
12481 shim below)

| Method | Before | After | Failing line before |
| --- | --- | --- | --- |
| shouldNotDeleteMessageWhenDeserializationThrows | FAIL: expected `AmazonSqsConnectorException`, nothing thrown | PASS | 74 (`assertThrows`) |
| shouldNotDeleteMessageWhenDeserializerReturnsNull | FAIL: expected `AmazonSqsConnectorException`, nothing thrown | PASS | 95 (`assertThrows`) |
| shouldStopBatchAtFailedMessageWithoutDeletingItOrLaterMessages | FAIL: expected `AmazonSqsConnectorException`, nothing thrown | PASS | 166 (`assertThrows`) |
| shouldSkipFailedMessageAndContinueWhenParseErrorsIgnored | FAIL: `NullPointerException` reading collected values | PASS | 196 |
| shouldKeepIgnoredNullMessageWhenDeletionDisabled | FAIL: `expected: <true> but was: <false>` (collector not empty) | PASS | 213 |
| shouldApplyIgnoreParseErrorsToJsonMessagesCreatedByFactory | FAIL: `SeaTunnelRuntimeException ... COMMON-02 ... 'invalid'` | PASS | 249 (`pollNext`) |
| shouldDeleteMessageAfterSuccessfulCollectionWhenEnabled | PASS | PASS | |
| shouldKeepMessageAfterSuccessfulCollectionWhenDeletionDisabled | PASS | PASS | |
| shouldNotDeleteMessageWhenCollectionFails | PASS | PASS | |

The first three failures are the behavior the pull request fixed (a failed parse did not raise, so
the message could be deleted). The next three request `ignoreParseErrors=true`, an option the
unfixed reader does not have; with the shim they run with the unfixed reader's only behavior, so
their failures show the absent option and the null row reaching the collector, not a separate
defect. The three passing methods cover successful collection and collector failure, which the
pull request did not change.

**SeaTunnel 12481, `AbstractTestFlinkContainerTest` with `st12481-flink-test-drop-override.patch`**

| Method | Before | After | Failing line before |
| --- | --- | --- | --- |
| shouldStopJobManagerWhenTaskManagerIsNotRunning | FAIL: `NeverWantedButInvoked` `execInContainer("rm", "-rf", "/tmp/seatunnel_mnt")` on the TaskManager that is not running | PASS | 43 |
| shouldNotFailWhenTaskManagerStopsBeforeVolumeCleanup | FAIL: tearDown threw `IllegalStateException: container is not running` | PASS | 63 (`assertDoesNotThrow`) |
| shouldStopJobManagerAndRethrowWhenVolumeCleanupIsInterrupted | FAIL: `WantedButNotInvoked` TaskManager `stop()` | PASS | 101 |
| shouldKeepFirstFailureAndSuppressLaterOnes | FAIL: `array lengths differ, expected: <1> but was: <0>` (JobManager stop failure not recorded; JobManager stop not reached) | PASS | 120 |
| shouldNotFailWhenVolumeCleanupExitsWithError | FAIL: `expected: <true> but was: <false>` | PASS | 85 (`hostVolumeDeleted`) |

Four failures are at assertions on teardown behavior (lines 43, 63, 101, 120). The fifth fails only
at the `hostVolumeDeleted` flag (line 85), which the unfixed teardown cannot set because it deletes
the host path itself instead of calling the overridable method the pull request added; every
behavioral assertion before line 85 passed. That failure is an artifact of the shim, not evidence
of the defect. The host path did not exist before or after the historical run.

### Safety

`st12481-shim` has a host-deletion hazard: parent-side Flink teardown calls
`FileUtils.deleteFile(HOST_VOLUME_MOUNT_PATH)` on the real host path
`/tmp/seatunnel_mnt`, even with mocked containers. It is excluded from the default
matrix. Running it requires both explicit selection and `FAILBEFORE_DISPOSABLE=1`
in a disposable filesystem environment without host-path mounts. The runner
refuses if the path exists, checking before cloning and immediately before test
execution. These checks do not protect files created during the test.

The historical runs of 2026-10-25 and the `df24917-budget` run of 2026-10-26 were produced
before this guard and are retained as historical.
Inside a disposable filesystem environment without host-path mounts, run:

```sh
FAILBEFORE_DISPOSABLE=1 ./run.sh st12481-shim
```

## What could not be run, and why

- **Fail-before for the DataFusion 24917 planning-budget tests**: both tests implement the
  `should_evaluate_const` hook the pull request added and do not compile against the unfixed code;
  no shim, for the reason given above.
- **Unmodified fail-before for SeaTunnel 12038, 12472 and 12481**: the transplanted tests do not
  compile against the unfixed code because they call constructors, options or methods the pull
  requests added. These tests are not runnable against the unfixed code as written. One-line shims
  were applied only where the change was a compile adapter (12038 reader test, 12481 Flink test);
  none was applied where the missing symbol is the fix itself (12472 clock constructor, 12481
  `AbstractTestContainerTest` helpers, 12038 factory test option).
- **SeaTunnel 12360**: no production change, so there is nothing for the test to fail against.
- **SeaTunnel 12467 and 12468**: no regression test in the pull requests.
- **`seatunnel-edge-agent-e2e` (`EdgeAgentFileToEngineIT`)** and the engine-container E2E suites:
  need Docker E2E images; not run here. Windows behavior was not run.

## Exact commands

```
./run.sh                       # default matrix, excluding st12481-shim
./run.sh df24193 st12038-shim  # selected cases
./run.sh df24917-budget        # the PR 24917 planning-budget tests
python3 make_results.py        # parse logs/runs.jsonl and the logs, write results.json
```

Cases: `df24193`, `df24917`, `df24917-diag`, `df24917-budget`, `st12038`, `st12038-shim`, `st12038-factory`,
`st12360`, `st12472`, `st12481`, `st12481-shim`. Per run the script prepares a git worktree at the
commit (hard reset, `git clean -fdx`), applies the transplant, writes a log header (commits,
`git status`, `git diff --stat`, toolchain, command, start/end, exit code) and runs:

- DataFusion: `cargo test --locked --profile ci -p datafusion-physical-plan --lib unbounded_input_emits_before_batch_size`
  and `cargo test --locked --profile ci -p datafusion --test core_integration expensive_regexp_like_is_deferred_to_execution`
  and `cargo test --locked --profile ci --no-fail-fast -p datafusion-optimizer -p datafusion-physical-expr --lib test_constant_regex_respects_planning_budget`
  (`--no-fail-fast` so that a failure in one package does not stop the other's test)
  (`ci` is DataFusion's own profile without debug info; chosen to fit the available disk). One
  shared cargo target directory.
- SeaTunnel (JDK 8): `./mvnw -B -ntp -pl <module> -am -DskipUT=false -DskipIT=true -Dskip.spotless=true -Dspotless.check.skip=true -Dspotless.apply.skip=true -Dlicense.skipAddThirdParty=true -Dtest=<selector> -DfailIfNoTests=false clean package`.
  Surefire XML reports are copied next to each log (`*.surefire/`).

Environment (optional): `FAILBEFORE_WORK` (worktrees and cargo target, default `./work`, ignored by
Git), `DATAFUSION_REPO` and `SEATUNNEL_REPO` (existing local clones to add worktrees from; by default
the script clones apache/datafusion and apache/seatunnel), `JAVA8_HOME`.

## Run record, including failed attempts

Requested cases and setup errors. Before any build, `run.sh` appends the requested cases and sides
(before and after of every case) with an invocation id and a timestamp to `logs/requested.json`,
and every record it then writes to `logs/runs.jsonl` carries that id. When a setup step fails
(clone, checkout, transplant or patch apply, missing JDK 8, or the `/tmp/seatunnel_mnt` refusal of
`st12481-shim`), the side is not skipped: the runner writes a log with the failed step and its
output and a record with `setup_error` naming the step, which `make_results.py` reports as
SETUP_ERROR; the other side is still attempted. At the end the runner exits 1 if any requested side
has no record from that invocation or only a setup-error record (exit 2 for an unknown case name);
a failing test is an outcome and does not change the exit status. `make_results.py` marks a case
`comparison: incomplete` when a side is missing or SETUP_ERROR, or when the latest invocation that
requested the case has no record for a requested side (listed under `missing`). The runs of
2026-10-25 predate this check and have no invocation id; their runner skipped a case whose setup
failed without writing a record, so for those runs completeness rests on `runs.jsonl` and the
individual logs, which hold a before and an after record for every case. `logs/requested.json`
now contains the `df24917-budget` invocation and the 2026-10-30 default-matrix invocation; every
requested side of both invocations is recorded. See the 2026-10-30 run record below.

- `logs/df24917-budget/`: in these two logs the absolute path of the local scratch work directory
  (`FAILBEFORE_WORK`) was replaced by the literal `$FAILBEFORE_WORK` before hashing; nothing else
  in them was changed.

- `logs/st12472/before.log`: first attempt with `clean test` instead of `clean package`; the
  build stopped in the upstream module `seatunnel-config-shade` (`cannot find symbol` in its main
  sources) because the reactor needs that module's shaded jar, which only `package` builds.
  Classified BUILD_ERROR; a harness problem, not a test outcome. `run.sh` was switched to
  `clean package` and the case re-run (`before-2.log`).
- `logs/st12472/after.interrupted.log`: the after run of that first attempt, stopped by hand when
  the harness problem was found; it has no record in `runs.jsonl`.
- `logs/console/`: consoles of the invocations. `run.sh` gained cases while the first DataFusion
  invocation was running; after its last case that shell read the edited file at an old offset and
  printed `inerTest: command not found` and a syntax error. All of its runs had completed and are
  recorded; later edits replaced the file atomically.
- DataFusion and SeaTunnel invocations overlapped in time, so durations include contention from
  the other build. The timing figures for PR 24917 above come from the diagnostic run only and are
  descriptive.
- Raw logs contain local paths of the machine they ran on.

### Run record (2026-10-30, default command)

One recorded invocation, `20261030T123542Z-26639`, covers all 20 requested sides of the
10-case default matrix of `./run.sh` on 2026-10-30. The runner is unchanged from repository
commit `af71f397d410c330cf37cf52d7165e63158ec207`. `logs/requested.json` records the request
at 05:35:42 local time (UTC-7); `logs/runs.jsonl` records each before and after side with that
invocation id and no setup error. These records satisfy the runner's completeness check,
whose success exit status is 0.

The operator states that this registered invocation was the third attempt of the morning;
two earlier attempts were stopped and their records were not retained. The
[registry addendum](logs/aborted-invocations-2026-10-30.md) records the operator's account
and the only retained console excerpts from those attempts.

For the registered attempt, the operator states that the clean-checkout procedure was a
fresh `git clone` of this repository, checkout of `af71f39`
(`af71f397d410c330cf37cf52d7165e63158ec207`), and an empty `FAILBEFORE_WORK` directory,
with no pre-existing build state, on the same host as the historical runs.
`JAVA8_HOME` was explicitly set to
`/Library/Java/JavaVirtualMachines/jdk1.8.0_172.jdk/Contents/Home`.
The full console is retained in
[`logs/console/console-20261030T123542Z-26639.txt`](logs/console/console-20261030T123542Z-26639.txt).
The operator states that the wrapper wrote the first and last lines, `START ...` and
`RUN_EXIT 0 ...`, and that the scratch path was replaced by the literal `$FAILBEFORE_WORK`.

The new log headers record Darwin 27.0.0 arm64, matching the operating system and architecture
of the historical Apple M1 Pro host. The Java logs record version 1.8.0_172, the version used
historically. The new Maven XML reports record its runtime under
`/Library/Java/JavaVirtualMachines/jdk1.8.0_172.jdk/Contents/Home/jre`.
The 20 new command logs and nine new XML reports use the literal `$FAILBEFORE_WORK` for the
work-directory path; their retained bytes match the hashes in `results.json`.

The test and compilation behavior matches the historical runs. Before / after outcomes and
wall times in seconds (from `results.json`) are:

- `df24193`: FAIL / PASS; 74.9 / 27.0 s.
- `df24917`: PASS / PASS; 118.7 / 90.0 s.
- `df24917-diag`: PASS / PASS; 87.7 / 85.7 s.
- `df24917-budget`: COMPILE_ERROR / PASS; 32.3 / 32.2 s.
- `st12038`: COMPILE_ERROR / PASS; 71.1 / 76.6 s.
- `st12038-shim`: FAIL / PASS; 75.3 / 74.9 s. All nine tests ran on both sides:
  four failures and two errors before, zero failures and zero errors after.
- `st12038-factory`: COMPILE_ERROR / PASS; 70.4 / 73.3 s.
- `st12360`: PASS / PASS; 82.4 / 83.6 s.
- `st12472`: COMPILE_ERROR / PASS; 56.0 / 60.1 s.
- `st12481`: COMPILE_ERROR / PASS; 94.6 / 105.4 s.

The four SeaTunnel before-side COMPILE_ERROR outcomes (`st12038`, `st12038-factory`,
`st12472` and `st12481`) are classified by parser revision 3, written on 2026-10-30 after
the run. For substituted Maven error paths, it recognises only the literal
`$FAILBEFORE_WORK/` prefix; without that recognition these four outcomes were labelled
BUILD_ERROR. The regenerated `results.json` reports COMPILE_ERROR, matching the historical
outcomes. All 23 historical
run outcomes are unchanged. `st12481-shim` was excluded from the
default matrix and was not run in this invocation; its historical records are retained.

New command logs (paths relative to this bundle):

```text
logs/df24193/before-2.log
logs/df24193/after-2.log
logs/df24917/before-2.log
logs/df24917/after-2.log
logs/df24917-diag/before-2.log
logs/df24917-diag/after-2.log
logs/df24917-budget/before-2.log
logs/df24917-budget/after-2.log
logs/st12038/before-2.log
logs/st12038/after-2.log
logs/st12038-shim/before-2.log
logs/st12038-shim/after-2.log
logs/st12038-factory/before-2.log
logs/st12038-factory/after-2.log
logs/st12360/before-2.log
logs/st12360/after-2.log
logs/st12472/before-3.log
logs/st12472/after-2.log
logs/st12481/before-2.log
logs/st12481/after-2.log
```

New Maven XML reports:

```text
logs/st12038/after-2.surefire/TEST-org.apache.seatunnel.connectors.seatunnel.amazonsqs.source.AmazonSqsSourceReaderTest.xml
logs/st12038-shim/before-2.surefire/TEST-org.apache.seatunnel.connectors.seatunnel.amazonsqs.source.AmazonSqsSourceReaderTest.xml
logs/st12038-shim/after-2.surefire/TEST-org.apache.seatunnel.connectors.seatunnel.amazonsqs.source.AmazonSqsSourceReaderTest.xml
logs/st12038-factory/after-2.surefire/TEST-org.apache.seatunnel.connectors.seatunnel.amazonsqs.AmazonSqsSourceFactoryTest.xml
logs/st12360/before-2.surefire/TEST-org.apache.seatunnel.connectors.cdc.base.source.reader.IncrementalSourceReaderTest.xml
logs/st12360/after-2.surefire/TEST-org.apache.seatunnel.connectors.cdc.base.source.reader.IncrementalSourceReaderTest.xml
logs/st12472/after-2.surefire/TEST-org.apache.seatunnel.edge.agent.connector.file.FileCollectReaderBehaviorTest.xml
logs/st12481/after-2.surefire/TEST-org.apache.seatunnel.e2e.common.container.AbstractTestContainerTest.xml
logs/st12481/after-2.surefire/TEST-org.apache.seatunnel.e2e.common.container.flink.AbstractTestFlinkContainerTest.xml
```

## Files

- `run.sh`: the runner (relative paths only).
- `make_results.py`: outcome parser; writes `results.json`. `test_make_results.py`: its checks.
- `results.json`: every run with outcome, per-test results, failure messages, commits, command,
  duration and log hash; hashes of all logs and patches.
- `patches/df24193-tests-only.patch`: the test-module hunks of PR 24193.
- `patches/df24917-diagnostic-print-plan.patch`: prints the plans and planning time (diagnostic).
- `patches/df24917-budget-tests-only.patch`: the hunks of PR 24917 that add the two
  planning-budget tests (and the physical test's imports).
- `patches/st12038-reader-test-drop-ignore-arg.patch`, `patches/st12481-flink-test-drop-override.patch`: the one-line shims.
- `logs/<case>/<side>.log` (+ `.surefire/` for Maven), `logs/runs.jsonl`, `logs/console/`,
  `logs/requested.json` (requested cases and sides per invocation).
