# Model-written regexp_like queries and DataFusion planning time (2026-10-25)

`./run.sh measure` is fresh by default and refuses a set that already holds records.
Records are reused only with `MEASURE_RESUME=1` after manifest and input-identity
verification. `./run.sh results` derives results and tables from the selected set's
records; it does not run measurements. `./run.sh all` runs build, measure and results
in fresh mode, setting `MEASURE_RESUME=0`.

Question: do SQL queries that language models write with `regexp_like`, for ordinary
text-matching tasks, trigger the planning stall of Apache DataFusion issue 22185 before the fix
(pull request 24917) and not after?

Answer for this sample: no. None of 412 model-written queries (375 of them planned without error)
took more than 1 s to plan, before or after the fix. The slowest took 2.9 ms before and 2.7 ms
after. No query passed `regexp_like` only literal arguments, which constant folding requires
before it compiles a pattern during planning. 47 queries contained a nested counted quantifier,
all of depth 2 (for example `([0-9]{1,3}\.){3}`). None of those patterns exceeded the fix's
256 KiB compiled-size limit. The positive control, the issue's own reproducer, planned in 61.6 ms
before and 2.0 ms after. That shows the mechanism, but the planning time stays well under the
issue's "about 1 s" on this machine in a release build.

The design, hypotheses and outcome definitions were fixed in `PREREGISTRATION.md` before the
first generation call. Its sha256 and the time it was recorded are in
`logs/preregistration.sha256`. Every number below is parsed from logs under `logs/` written by
executed runs. `results.json` lists the sha256 of every log and query file.

## Code under test

| Label | apache/datafusion commit | Meaning |
| --- | --- | --- |
| before | `408527ae58b5b706f5c02df8c37e096122cd8c78` | single parent of the PR 24917 merge |
| after | `3dfa245d61dde362e2c077761783bc735931659c` | PR 24917 "fix(optimizer): bound planning-time regex compilation", squash merge, closes issue 22185 |
| issuedate (exploratory) | `b426232b8a13c641a522bba414e932914f3b79f5` | last main commit before issue 22185 was opened (2026-05-14T21:53:10Z) |

The regex fix is PR 24917. PR 24193 is the `RepartitionExec` fix for issue 24044 and is not
involved. The pre-registration names PR 24917 and these commits. `logs/commit-verification.txt`
checks the merge commit and its parent against the GitHub API.

## Toolchain and machine

Apple M1 Pro (10 cores, 16 GiB), macOS (Darwin 27.0.0); `cargo 1.99.0-nightly (59800466c
2026-07-07)`, `rustc 1.99.0-nightly (3d50c25bc 2026-07-16)`. The harness `harness/plan_time` is
built three times, each time against one checkout's `datafusion/core` with default features, in
the release profile (`debug = false`). Each build starts from that checkout's own `Cargo.lock`,
and the three builds share one target directory. Resolved versions in all three builds: `regex`
1.13.1, `regex-syntax` 0.8.11; `regex-automata` 0.4.16 (before, after) and 0.4.18 (issuedate);
`datafusion` 55.0.0 (before, after) and 53.1.0 (issuedate). Build wall times: before 444 s
(first build, empty target directory), after 276 s and issuedate 395 s (sharing the already
compiled dependencies) (`logs/build/`).

## Locked replay (2026-10-29)

`./run.sh measure` is fresh by default and refuses a set that already holds records.
Reuse requires `MEASURE_RESUME=1` and successful manifest and input-identity verification.
`./run.sh results` derives outputs from that set's records; `./run.sh all` runs build,
measure and results in fresh mode, setting `MEASURE_RESUME=0`.

`harness/plan_time/rust-toolchain.toml` declares `nightly-2026-07-17` with the minimal
profile. Its compiler is `rustc 1.99.0-nightly (3d50c25bc 2026-07-16)`, the same compiler
as the historical builds. The runner checks this exact version against
`harness/plan_time/TOOLCHAIN.expected` and logs both the rustc and cargo versions from
each build directory. Rustup selects the declared toolchain.

The resolved harness dependency graphs are committed as
`harness/plan_time/Cargo.lock.before` and `harness/plan_time/Cargo.lock.after`, with their
sha256 values in `harness/plan_time/lockfiles.sha256`. `./run.sh build` verifies each
lockfile, copies it into its build directory and enforces `cargo build --release --locked`.
It checks that the lockfile hash is unchanged after building. Build logs retain the
lockfile differences, dependency versions, build times and binary hashes, and add the
toolchain and lockfile hashes. The builds still share one target directory.

To create or deliberately refresh the resolved lockfiles, run `./run.sh resolve-locks`.
This starts from each checkout's own `Cargo.lock`, builds without `--locked`, prints the
lockfile differences, saves the resolved lockfiles and rewrites `lockfiles.sha256`.
`build` stops if either resolved lockfile is missing and names this command.
`./run.sh explore` uses a verified `Cargo.lock.issuedate` when present; otherwise it logs
that it is using historical resolution from the issue-date checkout's lockfile.

For a fresh measurement from an empty build state (`work/`, or the directory selected
by `RUN_WORK`, absent or empty):

```sh
./run.sh build
export MEASURE_SET=measure-locked-$(date +%Y%m%d)
./run.sh measure
./run.sh results
./run.sh compare "$MEASURE_SET"
```

Choose a set name that does not already exist under `logs/`; change the example name
if it has already been used. Measurement defaults to fresh mode and refuses a set
containing `classify.jsonl`, `runs.jsonl`, `manifest.json` or `inputs.jsonl`. To continue an interrupted
set, use `MEASURE_RESUME=1 ./run.sh measure` with the same `MEASURE_SET` and binaries.
Resume requires a matching `logs/<set>/manifest.json`. Before planning, it validates
classification against all 417 loaded item ids, rejecting duplicates and malformed
lines. Missing or incomplete classification is regenerated completely, with a message;
classification is written to a temporary file in the set directory and renamed into
`classify.jsonl` only after validation. Recorded (query, build, repetition) runs are
reused without duplication. Then run `./run.sh results` with the same `MEASURE_SET`;
analysis refuses incomplete classification with an explicit completeness diagnostic.
Existing results and tables are retained; differing output is written beside them
with `.regenerated` before the extension.

The first invocation writes the manifest with sha256 hashes of `plan_time_before`,
`plan_time_after` and both committed lockfiles, the item count and start timestamp.
The compiler line is read from `harness/plan_time/TOOLCHAIN.expected`, which `build`
checks against `rustc --version` in each build directory. Resume verifies the binary
and lockfile hashes, compiler line and item count before using any records; a mismatch
aborts the measurement. Each invocation appends its start, end, executed and reused
counts to `invocations` and prints `executed N process runs, reused M recorded runs`.
These counts cover planning processes; classification is recorded separately.

Each set also binds the ordered, full loaded control and query records with
`inputs_sha256`: sha256 of sorted-key JSON with no spaces, encoded as UTF-8. Controls
come first, followed by queries in file order. `inputs.jsonl` records each item's id,
record hash and zero-based position. Resume and analysis validate this identity before
using retained records; a mismatch names the first differing item and writes nothing.
Changed workloads require a fresh set. The manifests and input lists for `measure`
and `measure-locked-2026-10-29` were reconstructed on 2026-10-29 from the committed
inputs: query-file hashes match `results.json`, and every loaded control field matches
its retained result (that file does not list a controls-file hash). The historical
manifest includes the binary hashes from `logs/build/build-20261025T153358.txt` and
omits build and invocation fields without a retained manifest source.

`MEASURE_SET` defaults to `measure`; a named set keeps classification, process runs and
tables together. The historical classification, process runs and `results.json` are
unchanged. The locked replay's records are `logs/measure-locked-2026-10-29/`,
`results-measure-locked-2026-10-29.json` and `COMPARISON-measure-locked-2026-10-29.md`.
Its manifest was added from the retained build hashes, committed lockfile hashes and
compiler line, with 417 items, 2,502 executed runs and 0 reused runs. Its start and end
timestamps are the `started` values of the first and last process records; the latter
is the last process start, rather than a separately recorded invocation completion time.
Analysis validates all expected process runs: (5 controls + 412 queries) × 2 builds ×
3 repetitions = 2502, and records the expected count and completeness in the results.
The comparison reports controls, pooled summaries and agreement of categorical outcomes;
wall-clock values are not expected to be identical across runs or machines.

Result of the locked replay run on 29 October 2026 (`logs/build/build-20261029T075258-12046.txt`,
`logs/measure-locked-2026-10-29/`): both builds completed with the declared toolchain and
unchanged lockfile hashes (385 s and 320 s from an empty target directory); all 2,502 process
runs were recorded; every categorical pre-registered outcome agrees with the historical
measurement (375 queries planned without error at both builds, no query over 1 s, no status
difference between builds, 0 all-literal calls, 47 nested counted quantifiers); the positive
control planned in 63.0 ms before and 2.3 ms after (historical: 61.6 and 2.0 ms), and the
quoted variant in 57.1 and 2.1 ms (historical: 58.6 and 2.1 ms). Planning-time distributions
differ between the two runs, as expected for wall-clock measurements.

## Generators

| | G1 | G2 |
| --- | --- | --- |
| Model | `qwen3-coder-30b-a3b-instruct` (LM Studio, GGUF, Q4_K_M, arch `qwen3moe`, publisher `lmstudio-community`; `logs/generation-g1-model-info.json`) | `claude-sonnet-5` (the model id reported by the `claude` client for `--model sonnet`) |
| Interface | OpenAI-compatible `/v1/chat/completions`, temperature 0.7, `max_tokens` 4096 | `claude -p --model sonnet --output-format json`, default sampling, no tools, no settings sources, run from an empty temporary directory |
| Calls | 25 (20 themes; second calls for themes 8, 14, 15, 18, 20) | 20 |
| Queries extracted | 211 | 201 (theme 7 returned 11) |
| Response lines not parseable as JSON | 39 (malformed JSON, e.g. a stray `}` after the SQL string) | 0 |

Both generators received the same 20 prompts (`prompts/template.txt` with each line of
`prompts/themes.txt`) and the system message "You are a helpful assistant.". Every raw response
is kept in `logs/generation/g1/` and `logs/generation/g2/`. Generation ran from 15:35:03 to
15:38:24 local time (UTC-7) on 2026-10-25.

## Measurement

Each query and control was planned at each build in three repetitions. Each repetition ran in its
own process with a 20 s timeout. The process creates a fresh `SessionContext`, registers the two
empty tables, and times `ctx.sql(sql).await` followed by `df.create_physical_plan().await`
(nothing is executed). The order is repetition-major, and the build order alternates by item.
The planning time of a query is the median of its three repetitions. The p95 is nearest-rank.
Measurement ran 15:46:46 to 15:47:21 (`logs/measure/runs.jsonl`, 2,502 process runs). The
patterns were classified with `regex-syntax` 0.8.11 and `regex` 1.13.1 inside the after binary
(`logs/measure/classify.jsonl`).

## Results (pre-registered outcomes)

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

| Stratum (planned at both builds) | n | before median / p95 / max ms | after median / p95 / max ms | over 1 s before / after |
|---|---:|---|---|---|
| nested counted quantifier: no | 330 | 1.5 / 2.3 / 2.9 | 1.5 / 2.2 / 2.7 | 0 / 0 |
| nested counted quantifier: yes | 45 | 1.5 / 2.2 / 2.8 | 1.5 / 2.2 / 2.7 | 0 / 0 |
| longest pattern <= 20 bytes | 102 | 1.5 / 2.1 / 2.3 | 1.5 / 2.2 / 2.5 | 0 / 0 |
| longest pattern 21-50 bytes | 207 | 1.5 / 2.3 / 2.9 | 1.5 / 2.3 / 2.7 | 0 / 0 |
| longest pattern > 50 bytes | 66 | 1.4 / 2.3 / 2.8 | 1.4 / 2.2 / 2.7 | 0 / 0 |

No query stalled before the fix, so the result is "not triggered in this sample": 0 of the 375
queries planned at both builds (0 of 189 G1, 0 of 186 G2) took more than 1 s, before or after. No
confidence bound is given. The queries come in batches from 20 prompts chosen by the
experimenter, so they are not independent draws from a defined population, and the rule-of-three
bound proposed in `PREREGISTRATION.md` has no justified sampling model here (see "Revision").

Planning errors were identical at both builds: 37 queries, 22 G1 and 15 G2. 22 failed in the
`simplify_expressions` rule with "Invalid regex", because the patterns use syntax the Rust regex
engine rejects, mostly backreferences such as `(.)\1{2,}` under the repeated-characters theme.
Eight failed on type coercion or the schema, four on functions DataFusion lacks
(`regexp_extract`, `regexp_matches`) and three on SQL parsing. No query changed status between
builds.

Pattern facts: the queries contain 485 `regexp_like` calls, and 7 of them take a non-literal
pattern. The deepest counted-repetition nesting is 2, and the longest literal pattern is 166 bytes.
The slowest model-written pattern to compile under the 10 MiB default limit took 0.67 ms.
Five queries also used `regexp_match` and two used `regexp_replace`.

### Controls (author-designed, not counted above)

| Control | before | after |
|---|---|---|
| positive: issue reproducer, `SELECT regexp_like('aaaaa', 'a{5}{5}{5}{5}{5}{5}{5}{5}');` | 61.6 ms (reps 119.2, 61.6, 59.9) | 2.0 ms (reps 10.9, 2.0, 2.0) |
| positive: 18-nesting fuzzer statement as printed in the issue (pattern's closing quote missing) | tokenizer error, unterminated string | same error |
| positive: the same 18-nesting statement with the closing quote added | 58.6 ms (reps 58.7, 58.5, 58.6) | 2.1 ms (reps 2.0, 2.1, 2.1) |
| mechanism: 8-nesting pattern on a column, `... WHERE regexp_like(message, 'a{5}...{5}')` | 1.5 ms (reps 9.7, 1.4, 1.5) | 1.4 ms (reps 2.7, 1.4, 1.3) |
| negative: `SELECT regexp_like('E123-456', '^E[0-9]{3}-[0-9]{3}$');` | 1.5 ms | 1.4 ms |

The positive control shows the mechanism. When every argument is a literal and the pattern nests
counted repetitions eight or more deep, planning before the fix took about 58-62 ms, and after
the fix it took 2 ms, about 30 times less. The pre-registered expectation of "about 1 s or more
before" was not met on this machine in a release build. Under the pre-registered 1 s threshold,
the positive control itself does not count as a stall. The pattern alone fails the 10 MiB
compile in 6.1 ms (`compile_10m_ms` in `classify.jsonl`), so most of the 58-62 ms comes from the
planner and not from one compilation. The same pattern applied to a column planned in 1.4-1.5 ms
at both builds.

### Hypotheses

* H1 (stall requires all-literal arguments): consistent with the data. No model-written call had
  all-literal arguments, and no query stalled. The mechanism control on a column did not slow
  down. The pre-registration says a column-argument pattern "is not folded". That is correct, but
  the optimizer's `simplify_expressions` rule still parses the pattern of `column ~ 'literal'`
  with `regex_syntax::Parser`, to rewrite simple regexes as LIKE. This is why 22 queries fail
  planning with "Invalid regex". Parsing does not expand counted repetitions into an automaton,
  and the mechanism control measures it at 1.4-1.5 ms.
* H2 (nested counted quantifiers mainly under the theme that names them): not supported. Of 47
  queries, 9 came from the "nested groups with counted repetitions" theme (all G2, 0 G1). 18 came
  from IPv4 addresses, 15 from MAC addresses, 3 from card numbers and secrets, 1 from UUIDs and 1
  from base64 tokens. All are of the form `(atom{m,n}sep){k}`, at depth 2. None is stacked like
  `a{5}{5}`.
* H3 (stalls before do not stall after): not testable, because nothing stalled before.

## Exploratory, not pre-registered (decided after the positive control stayed below 1 s)

To check whether the issue's figure reproduces at the code the issue was filed against, the
harness was also built at `issuedate`. The controls and the issue's nesting series were then
timed at all three commits (`./run.sh explore`, `logs/exploratory/`, runs 15:55:18 to 15:55:23). Values are medians of 3
repetitions in ms, with an all-literal `SELECT regexp_like('aaaaa', 'a{5}...')`:

| `{5}` nestings | issuedate | before | after | issue 22185 table |
|---:|---:|---:|---:|---:|
| 4 | 1.2 | 1.4 | 1.4 | 6 ms |
| 6 | 2.2 | 2.4 | 2.2 | 17 ms |
| 8 | 58.1 | 57.5 | 2.1 | 1008 ms |
| 10 | 57.6 | 58.0 | 2.0 | 1005 ms |
| 12 | 58.3 | 58.0 | 2.0 | 757 ms |
| 18 | 58.0 | 58.0 | 1.9 | ~1 s |

The shape matches the issue: cost rises sharply at 8 nestings and then plateaus once the size
limit trips. The magnitude is about 17 times smaller on this machine in a release build, at the
issue-date commit too. The issue says its scaling numbers were "measured via the fuzz target";
how that build was configured is not known here, and the cause of the difference is not
established. In the article, the "about a second" figure is therefore the issue reporter's
measurement and not a reproduction.

## Deviations and details not fixed in the pre-registration

1. The system message "You are a helpful assistant." was sent to both generators. G2 ran with no
   tools, no settings sources and an empty working directory, so no local files entered its
   prompt.
2. G1 took 5 second calls (themes 8, 14, 15, 18, 20) under the pre-registered rule. G2 theme 7
   returned 11 queries; all were measured, as pre-registered.
3. The 18-nesting statement is malformed in the issue text. It was run verbatim (tokenizer error
   at both builds), and also with the closing quote added.
4. The exploratory issue-date build and nesting series were added after the results above were
   known. They are reported separately and do not change any pre-registered outcome.
5. The remark on H1 about regex parsing in `simplify_expressions` is an interpretation added
   after seeing the "Invalid regex" errors.

## Limits

Two generators and one sample each; generation is not deterministic, so a new run produces
different queries. One schema with two empty tables; 20 themes chosen by the experimenter,
including one that names the issue's syntactic class. Planning only: a pattern deferred to
execution by the fix is not timed at execution, and nothing here measures execution cost. One
machine, release builds, default session configuration, three repetitions; the first repetition
of some items is slower (process and cache warm-up), which is why medians are reported. Only
`regexp_like` patterns are classified; the 7 queries using `regexp_match` or `regexp_replace`
were timed but their patterns were not analysed. The scanner treats an argument as literal only
when it is a bare string, number, NULL, TRUE or FALSE; a constant expression such as
`lower('X')` would be counted as non-literal, though none of the 412 queries stalled anyway.
Log files contain the workstation paths printed by the tools.

## Files

* `PREREGISTRATION.md`: design, written before generation; `logs/preregistration.sha256`
* `prompts/template.txt`, `prompts/themes.txt`: the prompts
* `queries/g1.jsonl`, `queries/g2.jsonl`: every extracted query (id, theme, call, task, SQL)
* `harness/plan_time/`: the Rust planning and classification program (`Cargo.toml.in`, `src/main.rs`)
* `harness/generate.py`, `harness/sqlscan.py`, `harness/measure.py`, `harness/analyze.py`,
  `harness/explore.py`, `harness/controls.jsonl`
* `logs/build/`: build logs with commits, versions, lockfile differences, build times, binary sha256
* `logs/generation/`: raw responses per call, `summary.json`, and the `/v1/models` listing
* `logs/measure/`: `classify.jsonl`, `runs.jsonl`; `logs/tables.md` is the printed tables
* `logs/exploratory/`: issue-date series runs and summary
* `results.json`: per-query outcomes, summaries (counts and planning-time distributions), strata,
  controls, exploratory summary, sha256 of logs, validation result and revision note

## Commands

```
./run.sh build      # clone apache/datafusion at the pinned commits into ./work and build (RUN_WORK overrides)
./run.sh measure    # classify patterns and time every query in queries/ and every control
./run.sh results    # rebuild results.json and print the tables
./run.sh explore    # exploratory issue-date build and nesting series
./run.sh generate   # new queries (needs an LM Studio endpoint and the claude client; refuses to overwrite)
```

`measure` skips (query, build, repetition) runs already in `logs/<MEASURE_SET>/runs.jsonl`
(default `logs/measure/runs.jsonl`). Select a new `MEASURE_SET` for a fresh replay.
`explore` refuses to overwrite `logs/exploratory/runs.jsonl`.

## Revision (2026-10-25, after the runs)

The analysis no longer reports a confidence bound, and `harness/analyze.py` now refuses
incomplete measurements. No run, log, query or count changed.

* `README.md`: the rule-of-three 95 % upper bound (0.8 % pooled, 1.6 % per generator) was removed
  from the results. The queries are batched and come from 20 selected prompts, so the independence
  that the bound assumes is not justified. The results are the raw counts: 0 of 375 queries
  planned at both builds stalled before or after the fix.
* `PREREGISTRATION.md` is unchanged and still proposes that bound (section "Reported outcomes").
  It is kept as the record of the plan; the bound is not part of the accepted analysis.
* `harness/analyze.py` (sha256 now `a58480d18b7c8aebe5781469ebe7dfe317716f787856a7561d129f011036d815`,
  `sha256_as_run` `d3d460e05a5424b21924a2ec06d1d55b09548c0d82e83c43a13577c33fe4afb2`, the version
  that produced the first published `results.json`): it no longer writes `rule_of_three_upper_95`.
  It also checks that every query and control has exactly 3 repetitions (numbered 1 to 3) per
  build and that every log line parses. Otherwise it lists the problems, does not write
  `results.json` and exits 1. Removing one repetition record, or duplicating one, in a temporary
  copy of `logs/measure/runs.jsonl` made it exit 1 with the item named.
* `results.json` was regenerated with `./run.sh results` from the recorded logs (no new
  measurement). Compared with the first published file, the only differences are the 10 removed
  `rule_of_three_upper_95` fields (3 summaries, 7 strata) and the added `validation` and
  `revisions` entries (`revisions` holds the hashes above). The printed tables are identical to
  `logs/tables.md`.
