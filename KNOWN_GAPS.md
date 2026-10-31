# Known gaps

## Regex planning timing

- The pull request's twenty debug iterations took 5.37 seconds before the fix and 0.17 seconds after it, whereas the unoptimized CI-profile measurements overlapped other builds and took about 0.5 seconds before and 10–32 milliseconds after. These timings come from different conditions and do not establish a controlled speedup ratio.
- An exploratory build from the issue date upgraded regex dependencies and took about 58 milliseconds. That result cannot isolate the effect of the source revision from the dependency changes.
- The malformed-regex control was compared after its missing SQL quote was restored, and the timing explanation based on invalid-regex rejection was developed after measurement. These comparisons and explanations are exploratory rather than predictions fixed before measurement.
- Regex matching complexity and behavior on untrusted inputs were not measured. The records do not establish worst-case cost or safety for arbitrary inputs.
- Repeated constant folding, the separate fuzzing build and deferred execution were not measured. Planning results do not establish costs or behavior in those paths.
- The distributed regex inputs verify the published files rather than the original execution bytes. Their verification cannot prove that the original measurements used identical inputs.

## Literal planning and generated queries

- Added methods can prevent copied planning tests from compiling on the parent revision. Such a compilation barrier does not establish the parent's planning behavior.
- The query design was fixed locally and was not externally registered. Reuse should treat the design record as a local specification rather than independent evidence of prior registration.
- The experiment used twenty selected themes, one sample per generator, one empty-table schema and one host. These observations cannot establish population rates or repeatable generation.
- The first generator used Q4_K_M quantization and temperature 0.7, while the second used its defaults. The results are conditional on these settings and do not establish behavior under other generation settings.
- Extraction discarded 39 unparseable lines from the first generator and retained repeated queries. Counts describe the extracted records rather than all generated output or independent unique samples.
- Classification covered only text constants in `regexp_like`, excluding constant expressions and other regex functions. Its literal-query counts do not cover those excluded forms.
- Of 412 queries, 375 planned at both builds and 37 errored, and three repetitions in separate processes found no stall above a one-second median or a 20-second timeout. This bounded observation does not establish the absence of stalls outside the measured queries and thresholds.
- Nested repetitions contradicted the theme hypothesis, and trigger prevalence remains unknown. The selected themes do not support an estimate of how often triggering queries occur.

## SQS reader

- The copied SQS reader test depends on a constructor argument added by the fix, so the unchanged test cannot compile on the parent revision. The compilation barrier alone cannot establish the parent's reader behavior, and the shimmed comparison must be interpreted separately.

## Checkpoint offsets

- The checkpoint's Java Database Connectivity sink setting `exactly_once` was not confirmed. The records cannot establish which delivery guarantee the sink was configured to provide.
- Checkpoint 15279's split state and restored binlog offset were unavailable, leaving reader, sink and deployment explanations unresolved. The evidence does not identify which of these caused the observed checkpoint behavior.

## Flink teardown

- Added methods and helpers prevent the unchanged copied teardown tests from compiling on the parent revision. Compilation failures do not establish the parent's runtime teardown behavior.
- The teardown timeout discrepancy remains unexplained. Reuse cannot assume that the different timeout observations have the same cause.
- Row-filtering and PostgreSQL change-data-capture failures were judged unrelated without causal proof. Their independence from teardown behavior remains an interpretation rather than an established result.
- The shared-base test's twelve methods, the unmerged Flink-only revision and local Linux teardown were not run. Results from other tests and revisions do not validate these cases.
- Windows permissions prevented testing non-writability. The records do not establish cleanup behavior for non-writable Windows paths.

## CI download retries and nightly runs

- CI failure rates were not compared. The records do not quantify a change in overall CI reliability.
- Maven 3.9 and Testcontainers' cleanup were not compared. The results do not establish whether either alternative changes the observed behavior.
- Response bodies and truncation schedules needed to reconstruct the download hang are missing. The historical hang cannot be reconstructed exactly from these records.
- Emulation may explain timing differences. Timing differences alone do not identify a change in download behavior.
- CI start-failure frequency is unknown. The saved nightly records do not establish how often that failure occurs.

## File-collect reader clock

- The copied reader test uses a clock constructor added by the change, and adapting the clock test to the parent was not tried. The compilation barrier does not establish a parent-side reader failure.
- Clock trials shared a Java virtual machine and differed in builds, architectures, waits and stalls. Their results do not isolate the effect of the clock change.
- JDK 11 trials used classes compiled with JDK 8. They do not validate a separate JDK 11 compilation.
- The original pause hook and logs are missing, and ambiguous pull-request text was interpreted as a 45 ms pause within 35 ms before idle close. The reconstructed pause cannot be verified against the original execution.
- Load was not recorded, and package, dependency and image versions were not enforced. These uncontrolled conditions prevent isolating effectiveness.
- Timeout-only trials and the original stress and mutation suites were not run. The records do not validate those timing and fault conditions.
- Patched trials without an injected pause under contention were not run. The evidence does not establish the patched behavior under that combination.
- Windows and file-reader/Docker end-to-end suites were not run. The available trials do not validate those platforms and integration paths.

## Harness provenance

- The selected fixes, uncounted candidates and tests written after fixes may favor successful results, and no third-party fixes were tested. The records cannot establish how representative the observed outcomes are of other fixes.
- Original local harnesses, hooks and raw pull-request logs are unpublished, although reconstructed harnesses, hooks, logs, queries and copied tests are public under Apache-2.0 with attribution. Reuse can inspect the reconstructions but cannot compare them with all original materials.
- The runner covers the Table 1 downloads and does not cover historical teardown. Running that entry point does not reproduce the historical teardown results.
- The evening command-log list initially pointed to morning logs and was corrected on 2026-10-31 using invocation `20261031T014130Z-77153` in `fail-before-2026-10-26/logs/runs.jsonl`. Earlier copies of the README can misidentify the evening evidence, so reuse should select that registry invocation.
- Some files supporting the tables lack anonymous access checks. Public availability of every supporting file has not been established.
- No deposit or DOI was chosen, and preservation is not guaranteed. Continued access depends on the available repository records.
- Compiler, lockfile, command, hardware, timing, warm-up and run-order records are incomplete. Exact reconstruction is not possible from the retained metadata.
- Work-directory paths were replaced with `$FAILBEFORE_WORK` before checksumming. Those checksums verify the distributed logs rather than their original path-bearing bytes.
- One setup-log checksum omits the log's final completion line. That checksum verifies the retained prefix rather than the entire current file.
- Replay inventories distinguish distributed, at-result and as-run hashes. Reuse must identify which version of an artifact a hash verifies.
- The locked replay records process start rather than invocation completion. Its recorded end cannot establish the full invocation duration or completion time.
- Two reportedly stopped morning attempts involved missing Java compilers and shared-directory conflicts, and their records are irrecoverable. The morning records cannot provide a complete account of all attempts.
- Copied-test logs were lost. Those historical executions cannot be independently checked from their original logs.
- An interrupted clock run has no outcome and was excluded from analysis. It cannot be counted as either a pass or a failure.
- JDK 11 retry smoke tests have no retained logs and were excluded from analysis. Their reported behavior cannot serve as independently inspectable execution evidence.
- Rust is pinned, JDKs are not pinned, and Maven dependencies resolve live. A later run can use different Java toolchains or resolved dependencies.
- Lock effectiveness has not been validated. The presence of a lock does not establish that concurrent trials were isolated.
- Retired teardown and the excluded Flink shim can delete host data, and the 25 October results predate deletion authorization. Those historical results do not establish that execution was authorized or that repeating the deletion paths is safe.
- Guarded replacements lack validation with real engines. Guard behavior does not establish real-engine teardown behavior.
- Trial isolation is asserted rather than enforced, and newly created files remain exposed. Reuse cannot assume complete isolation or protection for files created during a trial.
