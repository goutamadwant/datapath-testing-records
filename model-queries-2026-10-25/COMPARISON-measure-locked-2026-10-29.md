# Measurement comparison: measure and measure-locked-2026-10-29

Sources: `results.json` and `results-measure-locked-2026-10-29.json`.

Wall-clock values are not expected to be identical across runs or machines. This comparison reports observed differences only.

## Controls

Median planning time in ms; unsuccessful controls show their status.

| Control | measure before | measure after | measure-locked-2026-10-29 before | measure-locked-2026-10-29 after |
|---|---:|---:|---:|---:|
| control-positive-issue-8 | 61.621 | 2.025 | 62.951 | 2.292 |
| control-positive-issue-18-verbatim | error | error | error | error |
| control-positive-issue-18-quoted | 58.609 | 2.076 | 57.054 | 2.109 |
| control-mechanism-column-8 | 1.469 | 1.377 | 1.470 | 1.460 |
| control-negative-literal | 1.542 | 1.408 | 1.369 | 1.508 |

## Pooled queries

| Outcome | measure | measure-locked-2026-10-29 |
|---|---:|---:|
| Queries planned without error at both builds | 375 | 375 |
| Slowest query before | 2.947 ms (g2-t12-c1-q09) | 2.770 ms (g2-t14-c1-q10) |
| p95 before (ms) | 2.276 | 2.403 |
| Queries over 1 s before | 0 | 0 |
| Slowest query after | 2.740 ms (g2-t14-c1-q10) | 2.900 ms (g2-t12-c1-q09) |
| p95 after (ms) | 2.223 | 2.408 |
| Queries over 1 s after | 0 | 0 |
| Status differences between builds | 0 | 0 |

## Pre-registered outcomes

Categorical outcomes agree between the sets: **yes**. Agreement here requires identical counts, pattern classifications, planning statuses and stall/timeout outcomes, including controls and strata.

Planning-time distributions (per generator and pooled) are **different**. Continuous timing outcomes have no equality or tolerance requirement.

| Outcome group | Agreement |
|---|---|
| Query counts and pattern classifications | yes |
| Per-generator and pooled counts, statuses and stalls | yes |
| Per-query statuses and stalls | yes |
| Stratum counts, statuses and stalls | yes |
| Control statuses and stalls | yes |
| Stall and timeout thresholds | yes |
