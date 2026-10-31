# Schedule Backend (nightly) failed jobs, 2 to 23 October 2026

Saved GitHub REST API job records and log-pattern counts for apache/seatunnel. The run conclusions are those in the [saved run list](nightly-run-list-2026-10-02_2026-10-23.md): 22 runs, 13 failures, 9 cancellations and no successful runs. A cancelled run can contain failed jobs; selection here is by each job's `conclusion`, not the run's conclusion.

- Source workflow: https://github.com/apache/seatunnel/actions/workflows/schedule_backend.yml
- Job-list source: `GET https://api.github.com/repos/apache/seatunnel/actions/runs/<run_id>/jobs`.
- Job-log source: `GET https://api.github.com/repos/apache/seatunnel/actions/jobs/<job_id>/logs`.
- Job lists retrieved (UTC): 2026-10-31T01:26:52Z, as recorded in the supplied retrieval record.
- Log scan started (UTC): 2026-10-31T01:45:17.368951Z. Per-job log retrieval times range from 2026-10-31T01:45:19.197418Z to 2026-10-31T01:51:48.410682Z; each is preserved in the [scan summary](nightly-failed-jobs-scan-summary.json) and the corresponding [excerpt](nightly-failed-job-excerpts/).
- Scanned: the full streamed logs of all 58 jobs with conclusion `failure` across the 22 runs. The 517 `cancelled`, 1,154 `success` and 273 `skipped` jobs' logs were not scanned. Representative cancelled-job time-limit annotations are saved in [nightly-time-limit-annotations.md](nightly-time-limit-annotations.md); the 22 October manual cancellation is saved in [nightly-manual-cancellation-2026-10-22.md](nightly-manual-cancellation-2026-10-22.md).
- Excerpts retain job metadata followed by matching full-log line number, pattern name and up to 400 characters of line text. The cap is 1,500 matching entries per job. The largest supplied excerpt contains 105 matching entries; all saved per-pattern counts reconcile with the excerpt entries, so the entry cap did not omit matches. The character cap still truncates long lines. Three additional context files preserve surrounding log lines without that character cap: [38154064718-114513930530.context.txt](nightly-failed-job-excerpts/38154064718-114513930530.context.txt), lines 1530–1600, retrieved 2026-10-31T01:58:52Z; [37338260777-111895225539.context.txt](nightly-failed-job-excerpts/37338260777-111895225539.context.txt), lines 10925–10950, retrieved 2026-10-31T01:58:54Z; and [39282837181-118226773412.context.txt](nightly-failed-job-excerpts/39282837181-118226773412.context.txt), lines 9262–9290, retrieved 2026-10-31T01:58:56Z. Each context file records its source URL and retrieval time on its first line.
- API fields, log lengths and log hashes are copied as saved. Nothing was recomputed beyond pattern counting and its job-level tallies; tests were not rerun. Test-class names below are transcribed from matched test-failure lines, and interpretations distinguish error messages from informational and warning output.
- The final scan has no recorded fetch errors. Four jobs have different `first_pass_sha256` and `log_sha256` values after the recorded HTTP 503 re-fetches: 118226772526, 118226772554, 119331077123 and 119331077512. Table C uses the final `log_sha256`; the earlier hashes remain in the copied summary.

## Exact scan patterns

The following JSON copies the `patterns` object from the saved scan summary. Backslashes are JSON escapes. Pattern names are labels, not diagnoses: a match labelled `maven transfer error` need not come from Maven.

```json
{
  "failing test": "<<< (FAILURE|ERROR)!|^\\S*\\[ERROR\\]\\s{2,}\\S+\\.\\S+(:\\d+)?\\s|Tests run: \\d+, Failures: [1-9]|Errors: [1-9], Skipped",
  "maven transfer error": "Could not transfer artifact|Server returned HTTP response code: (429|502|403)|status code: (429|502|403)|Too Many Requests|Bad Gateway|403 Forbidden|Could not resolve dependencies|Connection reset|Premature end of|Failed to download",
  "missing slots": "Missing resources|Could not acquire the minimum required resources|NoResourceAvailableException|not enough slots|Slot request .* timed out",
  "409 conflict": "ConflictException|version_conflict|status 409|HTTP/1\\.1 409|\\b409 Conflict",
  "execInContainer error": "(ERROR|Exception).*execInContainer|execInContainer.*(ERROR|Exception)",
  "container teardown": "Failed to remove container|Removal In Progress|removal of container .* is already in progress|Error response from daemon|Could not stop container|Could not kill container",
  "file collect test": "FileCollectReader|rediscover",
  "condition timeout": "ConditionTimeout",
  "canceled": "The operation was canceled|##\\[error\\]The operation was canceled",
  "exit code": "Process completed with exit code",
  "time limit": "exceeded the maximum execution time"
}
```

## Table A: failed jobs and test classes by run

One row per failed job, grouped by run; runs with no failed jobs still have a row. Job names are copied exactly, including their JDK and OS matrix values. “Not in name” means those values are not supplied in the job name. Test classes come from the saved `failing test` entries (`[ERROR] Class.method` or `<<< FAILURE!` / `<<< ERROR!` summaries), with methods omitted. “No matched test failure” does not establish that tests passed or that all failure output uses these strings. Job-id links open the saved excerpts.

| Run id (UTC date; conclusion) | Failed job name | JDK / OS from name | Job id / excerpt | Failing test classes or other observed failure |
| --- | --- | --- | --- | --- |
| 37031600571 (2026-10-02; failure) | Run / Dead links | Not in name | [110919510517](nightly-failed-job-excerpts/37031600571-110919510517.txt) | No matched test failure. |
| 37031600571 (2026-10-02; failure) | Run / unit-test (8, ubuntu-latest) | 8 / ubuntu-latest | [110924412941](nightly-failed-job-excerpts/37031600571-110924412941.txt) | `SavePointTest` |
| 37031600571 (2026-10-02; failure) | Run / engine-v2-it (8, ubuntu-latest) | 8 / ubuntu-latest | [110924413031](nightly-failed-job-excerpts/37031600571-110924413031.txt) | `SplitClusterFaultToleranceIT` |
| 37031600571 (2026-10-02; failure) | Run / transform-v2-it-part-1 (8, ubuntu-latest) | 8 / ubuntu-latest | [110924414382](nightly-failed-job-excerpts/37031600571-110924414382.txt) | `TestFilterRowKindIT` |
| 37031600571 (2026-10-02; failure) | Run / all-connectors-it-7 (8, ubuntu-latest) | 8 / ubuntu-latest | [110924414901](nightly-failed-job-excerpts/37031600571-110924414901.txt) | `PostgresCDCIT` |
| 37140101463 (2026-10-03; cancelled) | Run / Dead links | Not in name | [111252568308](nightly-failed-job-excerpts/37140101463-111252568308.txt) | No matched test failure. |
| 37140101463 (2026-10-03; cancelled) | Run / engine-v2-it (8, ubuntu-latest) | 8 / ubuntu-latest | [111253104192](nightly-failed-job-excerpts/37140101463-111253104192.txt) | `BackpressureSlowSinkIT`, `CheckpointRestoreWithStopIT` |
| 37220159986 (2026-10-04; cancelled) | Run / Dead links | Not in name | [111488699314](nightly-failed-job-excerpts/37220159986-111488699314.txt) | No matched test failure. |
| 37220159986 (2026-10-04; cancelled) | Run / engine-v2-it (8, ubuntu-latest) | 8 / ubuntu-latest | [111489330777](nightly-failed-job-excerpts/37220159986-111489330777.txt) | `SplitClusterFaultToleranceIT` |
| 37338260777 (2026-10-05; failure) | Run / Dead links | Not in name | [111858458903](nightly-failed-job-excerpts/37338260777-111858458903.txt) | No matched test failure. |
| 37338260777 (2026-10-05; failure) | Run / unit-test (8, ubuntu-latest) | 8 / ubuntu-latest | [111895224208](nightly-failed-job-excerpts/37338260777-111895224208.txt) | `SeaTunnelEngineClusterRoleTest` |
| 37338260777 (2026-10-05; failure) | Run / kafka-connector-it (8, ubuntu-latest) | 8 / ubuntu-latest | [111895225539](nightly-failed-job-excerpts/37338260777-111895225539.txt) | No matched test failure; Maven dependency transfer failed with `Connection reset`, `BUILD FAILURE` and exit code 1; see the saved context. |
| 37338260777 (2026-10-05; failure) | Run / hbase-connector-it (11, ubuntu-latest) | 11 / ubuntu-latest | [111895225703](nightly-failed-job-excerpts/37338260777-111895225703.txt) | No matched test failure; `The operation was canceled.` at error level; test step is `cancelled` in the job list. |
| 37338260777 (2026-10-05; failure) | Run / paimon-connector-it (11, ubuntu-latest) | 11 / ubuntu-latest | [111895226290](nightly-failed-job-excerpts/37338260777-111895226290.txt) | `PaimonWithS3IT` |
| 37493133612 (2026-10-06; cancelled) | Run / Dead links | Not in name | [112370721758](nightly-failed-job-excerpts/37493133612-112370721758.txt) | No matched test failure. |
| 37649502426 (2026-10-07; cancelled) | None: no job has conclusion `failure` | — | — | No failed-job log to scan. |
| 37806311745 (2026-10-08; failure) | Run / elasticsearch-connector-it (11, ubuntu-latest) | 11 / ubuntu-latest | [113449233880](nightly-failed-job-excerpts/37806311745-113449233880.txt) | `ElasticsearchIT` |
| 37806311745 (2026-10-08; failure) | Run / elasticsearch-connector-it (8, ubuntu-latest) | 8 / ubuntu-latest | [113449233997](nightly-failed-job-excerpts/37806311745-113449233997.txt) | `ElasticsearchIT` |
| 37806311745 (2026-10-08; failure) | Run / all-connectors-it-7 (11, ubuntu-latest) | 11 / ubuntu-latest | [113449234170](nightly-failed-job-excerpts/37806311745-113449234170.txt) | `PostgresCDCIT` |
| 37806311745 (2026-10-08; failure) | Run / all-connectors-it-7 (8, ubuntu-latest) | 8 / ubuntu-latest | [113449234290](nightly-failed-job-excerpts/37806311745-113449234290.txt) | `PostgresCDCIT` |
| 37956696715 (2026-10-09; cancelled) | Run / elasticsearch-connector-it (17, ubuntu-latest) | 17 / ubuntu-latest | [113928828317](nightly-failed-job-excerpts/37956696715-113928828317.txt) | `ElasticsearchIT` |
| 37956696715 (2026-10-09; cancelled) | Run / elasticsearch-connector-it (11, ubuntu-latest) | 11 / ubuntu-latest | [113928828447](nightly-failed-job-excerpts/37956696715-113928828447.txt) | `ElasticsearchIT` |
| 38066284030 (2026-10-10; failure) | Run / engine-v2-it (11, ubuntu-latest) | 11 / ubuntu-latest | [114255062740](nightly-failed-job-excerpts/38066284030-114255062740.txt) | `BackpressureSlowSinkIT` |
| 38066284030 (2026-10-10; failure) | Run / all-connectors-it-6 (11, ubuntu-latest) | 11 / ubuntu-latest | [114255063104](nightly-failed-job-excerpts/38066284030-114255063104.txt) | `DatabendCDCSinkIT` |
| 38066284030 (2026-10-10; failure) | Run / elasticsearch-connector-it (11, ubuntu-latest) | 11 / ubuntu-latest | [114255063134](nightly-failed-job-excerpts/38066284030-114255063134.txt) | `ElasticsearchIT` |
| 38066284030 (2026-10-10; failure) | Run / elasticsearch-connector-it (17, ubuntu-latest) | 17 / ubuntu-latest | [114255063319](nightly-failed-job-excerpts/38066284030-114255063319.txt) | `ElasticsearchIT` |
| 38154064718 (2026-10-11; failure) | Run / engine-v2-it (17, ubuntu-latest) | 17 / ubuntu-latest | [114513930231](nightly-failed-job-excerpts/38154064718-114513930231.txt) | `SplitClusterFaultToleranceIT` |
| 38154064718 (2026-10-11; failure) | Run / all-connectors-it-2 (11, ubuntu-latest) | 11 / ubuntu-latest | [114513930366](nightly-failed-job-excerpts/38154064718-114513930366.txt) | `CassandraIT` |
| 38154064718 (2026-10-11; failure) | Run / all-connectors-it-2 (17, ubuntu-latest) | 17 / ubuntu-latest | [114513930444](nightly-failed-job-excerpts/38154064718-114513930444.txt) | `CassandraIT` |
| 38154064718 (2026-10-11; failure) | Run / jdbc-connectors-it-part-5 (17, ubuntu-latest) | 17 / ubuntu-latest | [114513930530](nightly-failed-job-excerpts/38154064718-114513930530.txt) | No matched test failure; all five attempts to download `maven-wrapper-3.1.0.jar` returned HTTP `403 Forbidden`, with 5/10/20/40-second backoff, followed by `Could not find or load main class org.apache.maven.wrapper.MavenWrapperMain` and exit code 1; see the saved context. |
| 38275077586 (2026-10-12; failure) | Run / Dead links | Not in name | [114898429359](nightly-failed-job-excerpts/38275077586-114898429359.txt) | No matched test failure. |
| 38275077586 (2026-10-12; failure) | Run / all-connectors-it-2 (11, ubuntu-latest) | 11 / ubuntu-latest | [114948427039](nightly-failed-job-excerpts/38275077586-114948427039.txt) | `CassandraIT` |
| 38275077586 (2026-10-12; failure) | Run / all-connectors-it-2 (17, ubuntu-latest) | 17 / ubuntu-latest | [114948427073](nightly-failed-job-excerpts/38275077586-114948427073.txt) | `CassandraIT` |
| 38427829225 (2026-10-13; failure) | Run / all-connectors-it-6 (17, ubuntu-latest) | 17 / ubuntu-latest | [115558251894](nightly-failed-job-excerpts/38427829225-115558251894.txt) | `DatabendCDCSinkIT` |
| 38595233433 (2026-10-14; cancelled) | None: no job has conclusion `failure` | — | — | No failed-job log to scan. |
| 38766089085 (2026-10-15; cancelled) | None: no job has conclusion `failure` | — | — | No failed-job log to scan. |
| 38929296111 (2026-10-16; cancelled) | Run / all-connectors-it-6 (17, ubuntu-latest) | 17 / ubuntu-latest | [117076660376](nightly-failed-job-excerpts/38929296111-117076660376.txt) | `DatabendCDCSinkIT` |
| 39047866221 (2026-10-17; failure) | Run / unit-test (17, ubuntu-latest) | 17 / ubuntu-latest | [117440667447](nightly-failed-job-excerpts/39047866221-117440667447.txt) | `SavePointTest` |
| 39047866221 (2026-10-17; failure) | Run / unit-test (11, ubuntu-latest) | 11 / ubuntu-latest | [117440667619](nightly-failed-job-excerpts/39047866221-117440667619.txt) | `SavePointTest` |
| 39143363034 (2026-10-18; failure) | Run / unit-test (11, windows-latest) | 11 / windows-latest | [117722745501](nightly-failed-job-excerpts/39143363034-117722745501.txt) | `JdbcOptionRuleCompletenessTest` |
| 39143363034 (2026-10-18; failure) | Run / unit-test (17, ubuntu-latest) | 17 / ubuntu-latest | [117722745506](nightly-failed-job-excerpts/39143363034-117722745506.txt) | `JdbcOptionRuleCompletenessTest` |
| 39143363034 (2026-10-18; failure) | Run / unit-test (17, windows-latest) | 17 / windows-latest | [117722745538](nightly-failed-job-excerpts/39143363034-117722745538.txt) | `JdbcOptionRuleCompletenessTest` |
| 39143363034 (2026-10-18; failure) | Run / unit-test (11, ubuntu-latest) | 11 / ubuntu-latest | [117722745560](nightly-failed-job-excerpts/39143363034-117722745560.txt) | `JdbcOptionRuleCompletenessTest` |
| 39282837181 (2026-10-19; failure) | Run / unit-test (17, windows-latest) | 17 / windows-latest | [118226772526](nightly-failed-job-excerpts/39282837181-118226772526.txt) | `LLMBooleanOutputTest` |
| 39282837181 (2026-10-19; failure) | Run / engine-resource-managers-it (17, ubuntu-latest) | 17 / ubuntu-latest | [118226772554](nightly-failed-job-excerpts/39282837181-118226772554.txt) | No matched test failure. |
| 39282837181 (2026-10-19; failure) | Run / unit-test (17, ubuntu-latest) | 17 / ubuntu-latest | [118226772555](nightly-failed-job-excerpts/39282837181-118226772555.txt) | `LLMBooleanOutputTest` |
| 39282837181 (2026-10-19; failure) | Run / unit-test (11, windows-latest) | 11 / windows-latest | [118226772660](nightly-failed-job-excerpts/39282837181-118226772660.txt) | `LLMBooleanOutputTest` |
| 39282837181 (2026-10-19; failure) | Run / unit-test (11, ubuntu-latest) | 11 / ubuntu-latest | [118226772815](nightly-failed-job-excerpts/39282837181-118226772815.txt) | `LLMBooleanOutputTest` |
| 39282837181 (2026-10-19; failure) | Run / connector-redis-it (17, ubuntu-latest) | 17 / ubuntu-latest | [118226773412](nightly-failed-job-excerpts/39282837181-118226773412.txt) | No matched test failure; Maven dependency transfer failed with `Connection reset`, `BUILD FAILURE` and exit code 1; see the saved context. |
| 39454491638 (2026-10-20; failure) | Run / Dead links | Not in name | [118737635261](nightly-failed-job-excerpts/39454491638-118737635261.txt) | No matched test failure. |
| 39454491638 (2026-10-20; failure) | Run / unit-test (17, ubuntu-latest) | 17 / ubuntu-latest | [118911186603](nightly-failed-job-excerpts/39454491638-118911186603.txt) | `LLMBooleanOutputTest` |
| 39454491638 (2026-10-20; failure) | Run / unit-test (17, windows-latest) | 17 / windows-latest | [118911186637](nightly-failed-job-excerpts/39454491638-118911186637.txt) | `LLMBooleanOutputTest` |
| 39454491638 (2026-10-20; failure) | Run / unit-test (11, ubuntu-latest) | 11 / ubuntu-latest | [118911186794](nightly-failed-job-excerpts/39454491638-118911186794.txt) | `LLMBooleanOutputTest` |
| 39454491638 (2026-10-20; failure) | Run / unit-test (11, windows-latest) | 11 / windows-latest | [118911186936](nightly-failed-job-excerpts/39454491638-118911186936.txt) | `LLMBooleanOutputTest` |
| 39454491638 (2026-10-20; failure) | Run / engine-v2-it (17, ubuntu-latest) | 17 / ubuntu-latest | [118911187060](nightly-failed-job-excerpts/39454491638-118911187060.txt) | `BackpressureSlowSinkIT` |
| 39454491638 (2026-10-20; failure) | Run / engine-v2-it (11, ubuntu-latest) | 11 / ubuntu-latest | [118911187227](nightly-failed-job-excerpts/39454491638-118911187227.txt) | No matched test failure. |
| 39631631551 (2026-10-21; failure) | Run / Dead links | Not in name | [119331077123](nightly-failed-job-excerpts/39631631551-119331077123.txt) | No matched test failure. |
| 39631631551 (2026-10-21; failure) | Run / changes | Not in name | [119331077151](nightly-failed-job-excerpts/39631631551-119331077151.txt) | No matched test failure. |
| 39631631551 (2026-10-21; failure) | Run / Code style | Not in name | [119331077512](nightly-failed-job-excerpts/39631631551-119331077512.txt) | No matched test failure. |
| 39811105168 (2026-10-22; cancelled) | None: no job has conclusion `failure` | — | — | No failed-job log to scan. |
| 39983952265 (2026-10-23; failure) | Run / Dead links | Not in name | [120518154119](nightly-failed-job-excerpts/39983952265-120518154119.txt) | No matched test failure. |
| 39983952265 (2026-10-23; failure) | Run / unit-test (11, windows-latest) | 11 / windows-latest | [120645954108](nightly-failed-job-excerpts/39983952265-120645954108.txt) | No matched test failure. |

Run 39631631551 has three failed jobs: `Run / Dead links`, `Run / changes` and `Run / Code style`; none has a matched test failure. Run 39811105168 is cancelled and has no failed jobs. These are not the only runs without matched test-failure lines: 37493133612 has only a failed `Run / Dead links` job; 37649502426, 38595233433 and 38766089085 have no failed jobs; 39983952265 has failed `Run / Dead links` and `Run / unit-test (11, windows-latest)` jobs but no matched test failure. Thus seven runs have no matched test failure in the scanned logs, including four with no failed jobs.

The `failing test` pattern matches 157 lines across 40 failed jobs. The most frequent named classes are `LLMBooleanOutputTest` (8 jobs), `ElasticsearchIT` (6), `CassandraIT` (4) and `JdbcOptionRuleCompletenessTest` (4). These are job counts, not method counts or distinct root causes. One job names both `BackpressureSlowSinkIT` and `CheckpointRestoreWithStopIT`.

## Table B: targeted signatures in failed-job logs

Counts refer to distinct failed jobs out of 58. Raw matching-job and line counts are independent per pattern and must not be added as distinct failures. Error-level counts require an explicit error marker or an identified command failure; a pattern name, `STDERR`, an exception name or a failed job conclusion alone is not an error-level diagnosis.

| Target / pattern | Jobs with literal matches (matching lines) | Failed jobs with the targeted error established | Interpretation from the saved evidence |
| --- | --- | --- | --- |
| PR 12467: overlapping-run or time-limit cancellation (`canceled`, `time limit`) | `canceled`: 1 (1); `time limit`: 0 (0) | 0 with overlap or time limit established; 1 with a generic cancellation error | [111895225703](nightly-failed-job-excerpts/37338260777-111895225703.txt) (`hbase-connector-it`, JDK 11, Ubuntu) has `##[error]The operation was canceled.` at log line 220563. Its test step is `cancelled`, although the job conclusion is `failure`. The excerpt does not identify overlap or a time limit as the cause. The exact patterns contain no separate overlap detector. Cancelled-job annotations are separate evidence. |
| PR 12468: Maven dependency transfer (`maven transfer error`) | 14 (134) | 2 explicit Maven dependency-transfer errors | [111895225539 context](nightly-failed-job-excerpts/37338260777-111895225539.context.txt) (`kafka-connector-it`, JDK 8, Ubuntu), line 10935, reports `Could not transfer artifact com.ververica:frocksdbjni:jar:5.17.2-ververica-2.1` from Maven Central with `Connection reset`. [118226773412 context](nightly-failed-job-excerpts/39282837181-118226773412.context.txt) (`connector-redis-it`, JDK 17, Ubuntu), line 9272, reports `Could not transfer artifact org.apache.flink:flink-shaded-netty:jar:4.1.49.Final-13.0` from Maven Central with `Connection reset`; `com.typesafe.akka:akka-actor_2.12:jar:2.5.21` is also listed as unresolved. Both contexts show `BUILD FAILURE` and exit code 1. Neither reports HTTP 429 or 502 as the transfer cause. |
| HTTP 403 within `maven transfer error` | 1 (5), included in the 14 above | 1 Maven wrapper-download failure | [114513930530 context](nightly-failed-job-excerpts/38154064718-114513930530.context.txt), run 38154064718, `Run / jdbc-connectors-it-part-5 (17, ubuntu-latest)`: the `./mvnw` step attempts to download `maven-wrapper-3.1.0.jar` from `https://repo.maven.apache.org/maven2/org/apache/maven/wrapper/maven-wrapper/3.1.0/maven-wrapper-3.1.0.jar`. All five attempts receive HTTP `403 Forbidden` at 16:11:52, 16:11:57, 16:12:07, 16:12:27 and 16:13:07 UTC on 11 October (lines 1549, 1556, 1563, 1570 and 1577). Between attempts, `Maven wrapper download failed, retrying in … seconds` records backoff of 5, 10, 20 and 40 seconds. Line 1580 reports `Could not find or load main class org.apache.maven.wrapper.MavenWrapperMain`, followed by `ClassNotFoundException` and exit code 1 at line 1582. The wrapper-download retry loop added by PR 12468 ran in the nightly job, but the 403 responses persisted through its five-attempt budget. |
| Connection resets within `maven transfer error` | 11 (127) in capped excerpts; 13 (129) with context, included in the 14 above | 2 established Maven dependency-transfer errors | The two transfer-error lines above contain `Connection reset` beyond the 400-character excerpt cap; the context files establish their Maven artifact-download failures. These are existing matches in the saved 14-job, 134-line pattern total, not additional scan matches. The other 11 jobs have reset lines including Akka and Pekko remote-transport `WARN` messages in Flink output, PostgreSQL client-reset `LOG` messages, SQL client prelogin warnings, and bare or container `STDERR` `java.io.IOException` lines. Those excerpts do not establish Maven download failures; unlabelled exceptions are not assigned a cause or severity. |
| PR 12481: Flink slot/resource failure (`missing slots`) | 25 (718) | 0 error-level slot/resource matches | All matches are `Missing resources:`: 596 lines are container `STDOUT` relayed at `INFO`, and 122 are bare continuation/output lines without an error level. The labelled output is consistent with Flink JobManager scheduling diagnostics, not evidence of an error-level teardown/reuse failure. No saved matching line is error-level or matches the other alternatives in this pattern. |
| PR 12481: `409 conflict` | 0 (0) | 0 | No line matched the saved conflict pattern. |
| PR 12481: `execInContainer error` | 0 (0) | 0 | No line matched this exact expression, which requires `ERROR` or `Exception` on the same line as `execInContainer`; this is not an unrestricted search for every container-state message. |
| PR 12481: `container teardown` | 0 (0) | 0 | No line matched `Failed to remove container` or any of the other saved teardown alternatives. |
| PR 12472: file-collect reader failures (`file collect test`) | 16 (96) | 0 | All 16 are unit-test jobs. Each reports `FileCollectReaderBehaviorTest` with `Tests run: 3, Failures: 0, Errors: 0`. The matched `FileCollectReaderPositionTest` and `FileCollectReaderMultilineTest` summaries also report zero failures and errors; some multiline tests are skipped on Windows. No matched file-collect test failed. |

For the four pull requests, the failed-job evidence establishes: PR 12467, no overlap/time-limit cause (0), with a separate generic cancellation error (1); PR 12468, three failed jobs showing its targeted download-failure mode (3): one Maven wrapper download rejected with HTTP 403 on all five attempts, outlasting the 5/10/20/40-second retry backoff, and two Maven dependency transfers ending in `Connection reset`, `BUILD FAILURE` and exit code 1; PR 12481, no targeted error-level container/slot signature (0); PR 12472, no file-collect reader test failure (0). The wrapper context directly shows the retry budget being exhausted; the two dependency contexts show terminal transfer failures but do not show their retry attempts. These counts establish occurrence of the targeted failures, not a before/after reliability improvement or a defect in the retry implementation.

For completeness, the other saved patterns match `condition timeout` in 13 jobs (35 lines) and `exit code` in 56 jobs (56 lines). These broad strings do not identify any of the four targeted causes by themselves.

## What this does and does not show

- The 517 cancelled jobs' logs were not scanned. Representative time-limit annotations and the manual-cancellation record remain separate evidence; the failed-job scan cannot rule out overlap or time limits in those jobs.
- Patterns are literal text matches under the exact regular expressions above. A failure mode can occur without those strings. Absence of a match is not proof of absence of the failure mode, and a broad match is not proof of its cause.
- The dominant failure classes are named by test class only. The scan does not diagnose their root causes, count every failed method, or establish that they are caused by any of the four changes.
- Surrounding context is saved for three jobs only: 114513930530 establishes the wrapper URL, all five HTTP 403 responses, retry backoff and terminal wrapper error; 111895225539 and 118226773412 establish the complete dependency-transfer errors, `BUILD FAILURE` and exit code 1. The dependency contexts do not show retry-attempt counts. All other log interpretations remain based on the capped pattern excerpts; no full logs are included.
- The run tally is unchanged: 13 failures and 9 cancellations across 22 runs, with no successful run. Reliability remains unknown; this scan does not measure a before/after improvement.

## Table C: full-log lengths and SHA-256 hashes

Copied from the final scan summary, one row for each of the 58 failed jobs. Hashes identify the full streamed log bytes, not the saved excerpts. A fresh download from the job-log endpoint can be compared with these values; no full logs are included here. Job metadata, exact per-job retrieval times, first-pass hashes and all pattern counts are in [nightly-failed-jobs-scan-summary.json](nightly-failed-jobs-scan-summary.json).

| Run id | Job id | log_lines | log_sha256 |
| --- | --- | --- | --- |
| 37031600571 | 110919510517 | 4923 | `2a481ff195d74ddf56a58ffe1e0193be9177986b04e956717bb0c0bc7a6307ee` |
| 37031600571 | 110924412941 | 80160 | `e59e3fe2e44392da51e70c97579d569b08258e13351a1dc58474239b159ff143` |
| 37031600571 | 110924413031 | 615832 | `0f233acfa4f0f8be4e48f05c6384ac879815df447eb363522eccb16ce8997535` |
| 37031600571 | 110924414382 | 406517 | `d08e56204f171b8d19df8adfd2a6c797220389d55f85c7b63b9412cb2a16d5b6` |
| 37031600571 | 110924414901 | 248777 | `85978afacd4e55b550c39381721084de5ee58f2b4d1a045aaecac633c8fda70f` |
| 37140101463 | 111252568308 | 4626 | `5059bcf98a43dbcb594205cc90ec86876a110322b2f22269ce6ccf0105926a74` |
| 37140101463 | 111253104192 | 579907 | `c37bc1cad0d0d1bbcfb97dc7a06d786c06598f627614895b6adf49492f5a2217` |
| 37220159986 | 111488699314 | 4626 | `9fd8d0447c8e1dcb45f934f2ab7ee4665febd06b55e72c498f0ea1fec77dd68e` |
| 37220159986 | 111489330777 | 579816 | `4cb55f4bcde6f30d3fe7ab96bfe762fc6acd6cad64538c2da60a323f1750e7de` |
| 37338260777 | 111858458903 | 4631 | `526d2f81d650752358b4b7795d320625c6a111f9576782ca6c83df3abe06ec62` |
| 37338260777 | 111895224208 | 135004 | `5fb9a6d0ce2f0ea3898f4a30bd8a32277979ec8f4bcf239af0cde3a89ce6a002` |
| 37338260777 | 111895225539 | 11069 | `02b7bbccf046eb02f7d014ba149dc09efd7ebf161d6b64cbd028909f97dbab1d` |
| 37338260777 | 111895225703 | 220566 | `7ca5df9d79831ab10b14b97de7b19858d486ca8f9f441954270ded7a9270d82a` |
| 37338260777 | 111895226290 | 187259 | `44c64a611cff59dfaa405a35d7d7bb24dbc4028c20e4e2c651ffb45fa48bb067` |
| 37493133612 | 112370721758 | 4629 | `b36767973b0b9cd8ff7a20d8b37fa5104a4e6836ea30ae7f5ac1ed779024c1cb` |
| 37806311745 | 113449233880 | 203700 | `a11625860355654e2d6f4cce9ab0b66729d374ca27f9a1176a15423fa0969266` |
| 37806311745 | 113449233997 | 204381 | `bf1182268f9e0af41728ec5883a0bf1020e66144856ae54043a0b595746164c8` |
| 37806311745 | 113449234170 | 247641 | `7fe8b12874e1dd0b030c036fe92f9a02651a51dfe1d759c9f0fe4f1f122c96e1` |
| 37806311745 | 113449234290 | 246076 | `571ce2d07df75f6361d5d6aaad75d1641487e700d193374b77edf32a0457b3ff` |
| 37956696715 | 113928828317 | 203279 | `b5ddbcfb83f351586a47fc19ea053a458dd533911919bcc78e15e83fecf31d73` |
| 37956696715 | 113928828447 | 204729 | `6a8066f0849b2cf97506f6f72c7265773fded0ff10a37a301037476454f599c2` |
| 38066284030 | 114255062740 | 396425 | `0c26113940646dfb967f9d47acec6291882e84fa938d3517d319d53ebf76a2df` |
| 38066284030 | 114255063104 | 119542 | `585b17e64aeb9ef1fea9323e0799d0b37e9130807dd1a456a5762835210abda7` |
| 38066284030 | 114255063134 | 204960 | `d990ca753db5ed61474afaf08bb5878e70da689d1fc51345dbf47a51d66c672a` |
| 38066284030 | 114255063319 | 203374 | `716ff9f2d0521cca59b265d33c667e12f448c1dfa427cdc36684bc272b92903a` |
| 38154064718 | 114513930231 | 573999 | `60e3a497aca6f9419f07b2ed854ea6c4b670bb51ac36e2e6525a570e6ba5134f` |
| 38154064718 | 114513930366 | 81896 | `4f3bf251a36d515615baa7d3f70df568d4022d6674109754aa79ae472205bd97` |
| 38154064718 | 114513930444 | 79953 | `4b9a6fc35efc719829909529f46e1db1b56ff6220220ae6343b23c9cbe6ac071` |
| 38154064718 | 114513930530 | 1702 | `fcc833de121ae9c72812804abc26f519d681f564391abea74bc94629bc12b7d9` |
| 38275077586 | 114898429359 | 4667 | `5c0c791c6e0935d2592a99067cac51576fcb5bd527725bdcca92b3e89c2a7123` |
| 38275077586 | 114948427039 | 80856 | `37164c46e1a6a3341246254ecbdbf6ea184baa81e826efbbb0922380bec4e784` |
| 38275077586 | 114948427073 | 80893 | `2fb1f6cab642d8d4c3f2b732c6ff92f3bfbb6b3142a7eebe5aa87fbb23590770` |
| 38427829225 | 115558251894 | 114478 | `51ab8e526d5c1f1dfb8166c9f44f8878a101b64f335a507c83d0b1e5d70b646f` |
| 38929296111 | 117076660376 | 117587 | `6f343816bbf675a9664a8839ea4e8578c526d3cc444b1a0e64e6503e844c33a5` |
| 39047866221 | 117440667447 | 83689 | `8b04771bab5c500e710a3e273a1ae322cdbe46f01343a32f58670ed625e2fde4` |
| 39047866221 | 117440667619 | 82573 | `958c37e36e4ed5e73bb1d030a0d91df488b5c1d41b88766e6f02a9528828221a` |
| 39143363034 | 117722745501 | 16768 | `6ac63e3cb1dac9a5c2b3aaeb9429dee988afa7ab2e300652d025e2f79999e726` |
| 39143363034 | 117722745506 | 12974 | `38ab37ed6f5b78ff5571aa105f22d7cd8fc89782ed0d819e6a1a58962136b9b4` |
| 39143363034 | 117722745538 | 16766 | `a4a269c1cd182b52aec36ad80479872de0ea6cc53db6e65fa99db4e36a2cecc1` |
| 39143363034 | 117722745560 | 12976 | `0b448612d315a44b90c9a1b8598e883522749d77ac171fd4bac8e3b45b319733` |
| 39282837181 | 118226772526 | 13100 | `792789767b2ef4e7db254e3bbdb35059dec3658451816e2e782081e492919608` |
| 39282837181 | 118226772554 | 1687 | `fe8a930f9f9a31a332fec06104c7aa9bebd1d826d138004b4e0162f63fd1b266` |
| 39282837181 | 118226772555 | 9257 | `a7dfe0ddbd38f65db09dd1f76286bc680478740c939188ec22e429ab3196955c` |
| 39282837181 | 118226772660 | 13098 | `03e69d7ffd3a34867d9772f8152f8087da786bfceb27f6453994afd7915b7d38` |
| 39282837181 | 118226772815 | 9271 | `daed3b74671bee1d71f1e0d41da34435bfa4365fd9612b8d318f523e08e0e60a` |
| 39282837181 | 118226773412 | 9409 | `bf523174dadc70306ea3fb85fba3621c45b9561e98ba4408c10197b21092723d` |
| 39454491638 | 118737635261 | 4832 | `5f19c1784568269b7d798c5edf5c99c5933c5d54e4d7d92e442f1cd660c2ca6e` |
| 39454491638 | 118911186603 | 9255 | `66012ed74424099e1e62f2153a0bcaff5e18ac8b2b2930e197bfc113a9068f1a` |
| 39454491638 | 118911186637 | 13092 | `f80adbfd6c1b4ee5b252e95b1bb4e374da570b99b35e2c81ab1466b432dbf7c6` |
| 39454491638 | 118911186794 | 9255 | `0827ebff51f8074714e93228871fdd566429c65d36de5bb9c78b22a4f7f6b51e` |
| 39454491638 | 118911186936 | 13088 | `d32af9bdf5c2ecfd9ef29de83e1bebb90dcaad2a97c02af7bd3e334e63c2e71f` |
| 39454491638 | 118911187060 | 309948 | `f1a67e5f0ce500b2d4ad87bb3824e2d3a0c540512a171ac9a12dfce24f8982de` |
| 39454491638 | 118911187227 | 2369 | `2428e847c0fe5d766586956b313b2bccb90be139a559885b88630396ece17f31` |
| 39631631551 | 119331077123 | 6287 | `49b9109a3ff39b39c0a6de7912aa6eea08b8e203ed5ba7471383db813eb16c62` |
| 39631631551 | 119331077151 | 185 | `bae956ea85c450297442f7ce36385a46356ff107971120401d1245ba25d4973f` |
| 39631631551 | 119331077512 | 589 | `b3807544f41f482ff6bb1e35168c1e5718dbbeb3f18d93c77c9b2a550296f705` |
| 39983952265 | 120518154119 | 6296 | `ce5c4cb541e411d597756ed2c29497e4b4c64fc08d9f0f19d1d4e9bb015f3e80` |
| 39983952265 | 120645954108 | 389 | `6231eb3d7510ff088b91c86bdc9280deb9cc317ffe357df8d83a573570000bed` |
