| | G1 | G2 | Pooled |
|---|---:|---:|---:|
| Queries extracted | 211 | 201 | 412 |
| Using regexp_like | 211 | 201 | 412 |
| With an all-literal regexp_like call | 0 | 0 | 0 |
| With a nested counted quantifier | 18 | 29 | 47 |
| Pattern over the 256 KiB planning limit | 0 | 0 | 0 |
| Planned without error at both builds | 189 | 186 | 375 |
| before: median ms | 1.4 | 1.6 | 1.5 |
| before: p95 ms | 2.1 | 2.4 | 2.3 |
| before: max ms | 2.6 | 2.9 | 2.9 |
| before: queries over 1 s | 0 | 0 | 0 |
| before: timeouts (20 s) | 0 | 0 | 0 |
| after: median ms | 1.4 | 1.6 | 1.5 |
| after: p95 ms | 2.1 | 2.3 | 2.2 |
| after: max ms | 2.5 | 2.7 | 2.7 |
| after: queries over 1 s | 0 | 0 | 0 |
| after: timeouts (20 s) | 0 | 0 | 0 |

| Stratum | n | before median / p95 / max ms | after median / p95 / max ms | over 1 s before / after |
|---|---:|---|---|---|
| nested_counted = False | 330 | 1.5 / 2.3 / 2.9 | 1.5 / 2.2 / 2.7 | 0 / 0 |
| nested_counted = True | 45 | 1.5 / 2.2 / 2.8 | 1.5 / 2.2 / 2.7 | 0 / 0 |
| pattern_len_bucket = 21-50 | 207 | 1.5 / 2.3 / 2.9 | 1.5 / 2.3 / 2.7 | 0 / 0 |
| pattern_len_bucket = <=20 | 102 | 1.5 / 2.1 / 2.3 | 1.5 / 2.2 / 2.5 | 0 / 0 |
| pattern_len_bucket = >50 | 66 | 1.4 / 2.3 / 2.8 | 1.4 / 2.2 / 2.7 | 0 / 0 |
| pattern_len_bucket = None | 0 | - / - / - | - / - / - | 0 / 0 |
| all_literal_regexp_like = False | 375 | 1.5 / 2.3 / 2.9 | 1.5 / 2.2 / 2.7 | 0 / 0 |

| Control | before | after |
|---|---|---|
| control-positive-issue-8 | 61.6 ms (reps 119.2, 61.6, 59.9) | 2.0 ms (reps 10.9, 2.0, 2.0) |
| control-positive-issue-18-verbatim | error: SQL error: TokenizerError("Unterminated string literal at Line: 1, Column: 29") | error: SQL error: TokenizerError("Unterminated string literal at Line: 1, Column: 29") |
| control-positive-issue-18-quoted | 58.6 ms (reps 58.7, 58.5, 58.6) | 2.1 ms (reps 2.0, 2.1, 2.1) |
| control-mechanism-column-8 | 1.5 ms (reps 9.7, 1.4, 1.5) | 1.4 ms (reps 2.7, 1.4, 1.3) |
| control-negative-literal | 1.5 ms (reps 3.7, 1.3, 1.5) | 1.4 ms (reps 1.7, 1.4, 1.3) |
