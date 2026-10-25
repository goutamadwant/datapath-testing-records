# CI evidence: saved apache/seatunnel GitHub Actions records

The article's CI section cites apache/seatunnel GitHub Actions runs as inline links and run ids.
This directory holds the saved records behind those citations as Markdown, so that they can be
read without the GitHub UI. Each file gives the API or page URL each record came from and its
retrieval time (UTC), as saved. Values are transcribed as returned by the GitHub REST API at that
time. Nothing was added, recomputed or re-fetched for this directory.

| File | What it holds | Run ids |
| --- | --- | --- |
| [`nightly-run-list-2026-10-02_2026-10-23.md`](nightly-run-list-2026-10-02_2026-10-23.md) | The post-merge run list of the `Schedule Backend` (nightly) workflow, query `created=2026-10-02..2026-10-23`, all 22 runs returned | 37031600571 ... 39983952265 |
| [`nightly-time-limit-annotations.md`](nightly-time-limit-annotations.md) | For each nightly run with job time-limit annotations: run metadata, the annotations of one cancelled job, and the list of failed and cancelled jobs | 38929296111, 38766089085, 38595233433, 37956696715, 37649502426, 37493133612, 37220159986, 37140101463 |
| [`nightly-manual-cancellation-2026-10-22.md`](nightly-manual-cancellation-2026-10-22.md) | The 22 October nightly: run metadata, the manual-cancellation annotation, the cancelled jobs | 39811105168 |
| [`concurrency-overlap-runs-2026-09.md`](concurrency-overlap-runs-2026-09.md) | Push (`Build`) and nightly (`Schedule Backend`) run records of 22 and 23 September 2026 (before PR 12467) | 35744532059, 35751822291, 35886457185, 35886465482 |
| [`windows-job-120758452075.md`](windows-job-120758452075.md) | Windows unit-test job metadata and the two saved log lines for `FileCollectReaderBehaviorTest` | run 40055606262, job 120758452075 |

Run pages: `https://github.com/apache/seatunnel/actions/runs/<run id>`.
