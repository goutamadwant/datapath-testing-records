| | G1 | G2 | Pooled |
|---|---:|---:|---:|
| Queries extracted | 211 | 201 | 412 |
| Using regexp_like | 211 | 201 | 412 |
| With an all-literal regexp_like call | 0 | 0 | 0 |
| With a nested counted quantifier | 18 | 29 | 47 |
| Pattern over the 256 KiB planning limit | 0 | 0 | 0 |
| Planned without error at both builds | 189 | 186 | 375 |
| before: median ms | 1.5 | 1.7 | 1.6 |
| before: p95 ms | 2.2 | 2.5 | 2.4 |
| before: max ms | 2.5 | 2.8 | 2.8 |
| before: queries over 1 s | 0 | 0 | 0 |
| before: timeouts (20 s) | 0 | 0 | 0 |
| after: median ms | 1.6 | 1.7 | 1.6 |
| after: p95 ms | 2.3 | 2.5 | 2.4 |
| after: max ms | 2.6 | 2.9 | 2.9 |
| after: queries over 1 s | 0 | 0 | 0 |
| after: timeouts (20 s) | 0 | 0 | 0 |

| Stratum | n | before median / p95 / max ms | after median / p95 / max ms | over 1 s before / after |
|---|---:|---|---|---|
| nested_counted = False | 330 | 1.6 / 2.4 / 2.8 | 1.6 / 2.4 / 2.9 | 0 / 0 |
| nested_counted = True | 45 | 1.6 / 2.4 / 2.7 | 1.7 / 2.4 / 2.8 | 0 / 0 |
| pattern_len_bucket = 21-50 | 207 | 1.6 / 2.4 / 2.8 | 1.6 / 2.4 / 2.9 | 0 / 0 |
| pattern_len_bucket = <=20 | 102 | 1.6 / 2.3 / 2.6 | 1.7 / 2.3 / 2.7 | 0 / 0 |
| pattern_len_bucket = >50 | 66 | 1.5 / 2.4 / 2.8 | 1.5 / 2.4 / 2.8 | 0 / 0 |
| pattern_len_bucket = None | 0 | - / - / - | - / - / - | 0 / 0 |
| all_literal_regexp_like = False | 375 | 1.6 / 2.4 / 2.8 | 1.6 / 2.4 / 2.9 | 0 / 0 |

| Control | before | after |
|---|---|---|
| control-positive-issue-8 | 63.0 ms (reps 69.2, 63.0, 59.4) | 2.3 ms (reps 10.8, 2.3, 2.0) |
| control-positive-issue-18-verbatim | error: SQL error: TokenizerError("Unterminated string literal at Line: 1, Column: 29") | error: SQL error: TokenizerError("Unterminated string literal at Line: 1, Column: 29") |
| control-positive-issue-18-quoted | 57.1 ms (reps 55.9, 63.0, 57.1) | 2.1 ms (reps 2.1, 2.1, 2.2) |
| control-mechanism-column-8 | 1.5 ms (reps 2.8, 1.5, 1.4) | 1.5 ms (reps 3.0, 1.5, 1.4) |
| control-negative-literal | 1.4 ms (reps 1.6, 1.3, 1.4) | 1.5 ms (reps 2.0, 1.4, 1.5) |
