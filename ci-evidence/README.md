# CI evidence: saved apache/seatunnel GitHub Actions records

The article's CI section cites apache/seatunnel GitHub Actions runs as inline links and run ids.
This directory holds the saved records behind those citations, so that they can be read without
the GitHub UI. The Markdown records give the source API or page URL and retrieval time (UTC),
as saved. API values are transcribed as returned at that time. The failed-job scan additionally
preserves log excerpts and pattern counts in text and JSON, with class names and interpretations
in its Markdown record. Its scope, exact patterns, retrieval times and excerpt limits are stated
there; no test results were rerun or recomputed.

| File | What it holds | Run ids |
| --- | --- | --- |
| [`nightly-run-list-2026-10-02_2026-10-23.md`](nightly-run-list-2026-10-02_2026-10-23.md) | The post-merge run list of the `Schedule Backend` (nightly) workflow, query `created=2026-10-02..2026-10-23`, all 22 runs returned | 37031600571 ... 39983952265 |
| [`nightly-failed-jobs-2026-10-02_2026-10-23.md`](nightly-failed-jobs-2026-10-02_2026-10-23.md) | Failed jobs across all 22 nightly runs: matched test classes, targeted signature counts and interpretations, exact patterns, and full-log hashes for 58 failed jobs | 37031600571 ... 39983952265 |
| [`nightly-failed-job-excerpts/`](nightly-failed-job-excerpts/) | 58 saved per-job excerpts: metadata, full-log line numbers, pattern names and matched text, subject to the documented character and entry caps; plus three surrounding-context files: [38154064718-114513930530.context.txt](nightly-failed-job-excerpts/38154064718-114513930530.context.txt) (wrapper download, lines 1530–1600), [37338260777-111895225539.context.txt](nightly-failed-job-excerpts/37338260777-111895225539.context.txt) (Kafka dependency transfer, lines 10925–10950), and [39282837181-118226773412.context.txt](nightly-failed-job-excerpts/39282837181-118226773412.context.txt) (Redis dependency transfer, lines 9262–9290), each with its source URL and retrieval time | 37031600571 ... 39983952265 |
| [`nightly-failed-jobs-scan-summary.json`](nightly-failed-jobs-scan-summary.json) | Saved scan summary: exact patterns, per-job counts, retrieval times, full-log lengths and final/first-pass SHA-256 hashes | 37031600571 ... 39983952265 |
| [`nightly-time-limit-annotations.md`](nightly-time-limit-annotations.md) | For each nightly run with job time-limit annotations: run metadata, the annotations of one cancelled job, and the list of failed and cancelled jobs | 38929296111, 38766089085, 38595233433, 37956696715, 37649502426, 37493133612, 37220159986, 37140101463 |
| [`nightly-manual-cancellation-2026-10-22.md`](nightly-manual-cancellation-2026-10-22.md) | The 22 October nightly: run metadata, the manual-cancellation annotation, the cancelled jobs | 39811105168 |
| [`concurrency-overlap-runs-2026-09.md`](concurrency-overlap-runs-2026-09.md) | Push (`Build`) and nightly (`Schedule Backend`) run records of 22 and 23 September 2026 (before PR 12467) | 35744532059, 35751822291, 35886457185, 35886465482 |
| [`windows-job-120758452075.md`](windows-job-120758452075.md) | Windows unit-test job metadata and the two saved log lines for `FileCollectReaderBehaviorTest` | run 40055606262, job 120758452075 |

Run pages: `https://github.com/apache/seatunnel/actions/runs/<run id>`.
