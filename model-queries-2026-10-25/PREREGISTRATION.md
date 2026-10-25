# Pre-registration: model-written regexp_like queries and DataFusion planning time

Written 2026-10-25, before any query was generated. Its sha256 is recorded in
`logs/preregistration.sha256` with a timestamp before the first generation call. Any later
change to the design is listed under "Deviations" in `README.md`; this file is not edited after
generation starts.

## Question

Do SQL queries written by language models, asked to use `regexp_like` for ordinary text-matching
tasks, trigger the planning stall reported in Apache DataFusion issue 22185 ("Slow logical
planning (>1s) for regexp_like with nested {N} quantifiers") at the parent of the fix, and not at
the fix?

## Code under test

The fix for issue 22185 is apache/datafusion pull request 24917, "fix(optimizer): bound
planning-time regex compilation", squash-merged as commit
`3dfa245d61dde362e2c077761783bc735931659c` (after). Its single parent is
`408527ae58b5b706f5c02df8c37e096122cd8c78` (before). (Pull request 24193 is the
`RepartitionExec` fix for issue 24044 and does not touch regex planning; it is not used here.)

A small Rust program (`harness/plan_time`) is built twice, once against each checkout through a
path dependency on `datafusion` with its default features, in the release profile, sharing one
target directory. Each build starts from the checkout's own `Cargo.lock`.

## Schema

Two empty in-memory tables are registered in every session:

```
logs(ts TIMESTAMP, level VARCHAR, service VARCHAR, message VARCHAR)
events(id BIGINT, user_id BIGINT, path VARCHAR, status INT)
```

## Generation

Two generators, the same 20 prompts each, one prompt per task theme, each asking for 10 queries:

* G1: `qwen3-coder-30b-a3b-instruct` served by LM Studio through its OpenAI-compatible
  endpoint, temperature 0.7, `max_tokens` 4096. The model id and any version information the
  server returns are recorded.
* G2: Claude Sonnet through the `claude` command-line client
  (`claude -p --model sonnet --output-format json`), default sampling settings. The model id
  reported in the JSON result is recorded.

The prompt template is fixed in `prompts/template.txt` and the 20 themes in
`prompts/themes.txt`. The themes describe ordinary matching tasks (error codes, IPv4 addresses,
e-mail addresses, repeated characters, nested groups with counted repetitions, identifiers,
timestamps, paths and similar). No prompt asks for slow, pathological, adversarial or
deliberately complex patterns. The theme "nested groups with counted repetitions" names the
syntactic class of the issue as a matching task; this is a design choice that raises the chance
of seeing the class and is reported as such.

One call is made per prompt and generator. If a call yields fewer than 10 extractable queries,
one more call is made with the same prompt; no further calls. Every raw response is kept. All
extracted queries are measured, including ones that later fail to plan, so the final count may
differ from 200 per generator. A query is extracted from a response line that parses as a JSON
object with a string field `sql`; responses inside a code fence are unwrapped first. Lines that
do not parse are kept in the raw log and counted as unextractable.

## Measurement

For each query and each build, three repetitions. Each repetition is a separate process with a
20 s wall-clock timeout. Inside the process a fresh `SessionContext` is created and the two
tables are registered (not timed); then the program times `ctx.sql(query).await` (logical
planning) and `df.create_physical_plan().await` (optimisation and physical planning) with a
monotonic clock and prints both. Nothing is executed. The repetition loop is ordered
repetition-major over all queries, and the build order alternates by query index.

Per query and build the outcome is `ok` (all three repetitions planned), `error` (planning
returned an error; the message is kept), or `timeout` (a repetition exceeded 20 s; the time is
recorded as censored at 20 s). The planning time of a query at a build is the median of its
three repetition totals.

## Classification

Each `regexp_like` call is found in the SQL text by a scanner that respects SQL string literals
and parentheses. For each call the following are recorded:

* whether every argument is a literal (only then can constant folding compile the pattern
  during planning; with a column argument the call is not folded),
* the pattern literal (second argument) if it is a single string literal, and the flags,
* pattern length in bytes, bucketed as <=20, 21-50, >50,
* nested counted quantifier: a counted repetition (`{n}`, `{n,}`, `{n,m}`) whose operand
  contains another counted repetition, including stacked forms such as `a{5}{5}`, determined
  from the `regex-syntax` 0.8 abstract syntax tree (the parser the regex engine uses), plus the
  maximum nesting depth of counted repetitions,
* whether the pattern compiles under the 256 KiB planning limit introduced by the fix, and under
  the regex crate's default 10 MiB limit, measured with `regex` 1.13.1 (the version in both
  lockfiles).

Other regex constructs (`~`, `~*`, `!~`, `!~*`, `SIMILAR TO`, `regexp_match`, `regexp_replace`,
`regexp_count`, `regexp_instr`, `regexp_substr`) are counted but not analysed.

## Hypotheses (stated before data)

* H1 (mechanism): a stall requires constant folding, so it can occur only when all arguments of
  the `regexp_like` call are literals and the pattern exceeds the 256 KiB compiled-size limit.
  Model-written queries are expected to apply `regexp_like` to a column, so few or none are
  expected to stall at either build, even when the pattern has nested counted quantifiers.
* H2: patterns with nested counted quantifiers will appear mainly under the theme that names
  them.
* H3: queries that do stall before (median > 1 s or timeout) will not stall after.

## Reported outcomes

For each generator and pooled: number of responses, extracted queries, queries using
`regexp_like`, queries with an all-literal `regexp_like` call, queries with a nested counted
quantifier, queries planning without error at each build; planning-time median, p95 (nearest
rank) and max at each build; number of queries above 1 s and number of timeouts at each build;
the same stratified by nested counted quantifier and by pattern length bucket. Every query above
1 s at either build is listed individually. A "stall" is a median planning time above 1 s or a
timeout. If no model-written query stalls before the fix, the result is reported as "not
triggered in this sample of n queries", with the rule-of-three 95 % upper bound 3/n on the
per-query rate for this schema, these prompts and these two models.

## Controls (author-designed, not counted among model-written queries)

* Positive control: the issue's reproducer
  `SELECT regexp_like('aaaaa', 'a{5}{5}{5}{5}{5}{5}{5}{5}');` and the 18-nesting statement from
  the issue's fuzzer report, at both builds, with the same harness and repetitions. Expected:
  about 1 s or more before (the issue reports about 1 s on an Apple M-series machine), well under
  1 s after.
* Mechanism control: the same 8-nesting pattern applied to a column,
  `SELECT * FROM logs WHERE regexp_like(message, 'a{5}{5}{5}{5}{5}{5}{5}{5}');`, at both builds.
  Expected under H1: no stall at either build.
* Negative control: `SELECT regexp_like('E123-456', '^E[0-9]{3}-[0-9]{3}$');` at both builds.

## Limits fixed in advance

Two generators, one schema, 20 themes, planning only (no execution, so a pattern deferred to
execution is not timed at execution), one machine, empty tables, default session configuration.
The result speaks to these prompts and models, not to model-generated SQL in general.
