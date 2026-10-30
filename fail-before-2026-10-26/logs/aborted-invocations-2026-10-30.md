# Run registry addendum (2026-10-30): two stopped attempts

This dated addendum records the operator's statements about two attempts at the default
matrix on 2026-10-30 before the registered invocation. Times are PDT (UTC-7). No logs from
either stopped attempt survive; the only retained evidence is the operator's console
capture of the excerpts reproduced below. The account of configuration, progress, stopping
and deletion is from the operator, not from retained run records.

## Attempt 1

The operator states that invocation `20261030T123128Z-20046` started at 05:31:28 from a
fresh git clone of this repository at commit
`af71f397d410c330cf37cf52d7165e63158ec207`. `FAILBEFORE_WORK` pointed to a scratch
directory. `JAVA8_HOME` was left to the default lookup, which on this host resolves to a
Java 8 runtime without `javac`.

The operator states that `df24193` ran before and after: the console showed the before
side failing and the after side passing, consistent with the registered outcomes. The
attempt was in `df24917` when the operator killed the process at about 05:34 to restart
with the full JDK. No further side outcomes are established by the retained excerpt.

## Attempt 2

The operator states that a second attempt started at about 05:33 while attempt 1 was
still running, sharing the same `FAILBEFORE_WORK` directory by mistake. Its invocation id
was not captured.

The operator states that it wrote SETUP_ERROR records for checkouts conflicting with
attempt 1's worktrees: `df24917` before and after and `df24917-diag` before, possibly
more. The three retained console lines below identify those setup errors; they do not
establish the full set of affected sides. The operator killed this attempt at about
05:34 after the shared-directory conflicts, before restarting with the full JDK
and an empty work directory.

## Retained console excerpts (verbatim)

The first line is from attempt 1; the three SETUP_ERROR lines are from attempt 2.

```text
invocation 20261030T123128Z-20046: df24193 df24917 df24917-diag df24917-budget st12038 st12038-shim st12038-factory st12360 st12472 st12481
[df24917/before] SETUP_ERROR at 'check out 408527ae58b5b706f5c02df8c37e096122cd8c78' (exit 1) -> logs/df24917/before-3.log
[df24917/after] SETUP_ERROR at 'check out 3dfa245d61dde362e2c077761783bc735931659c' (exit 1) -> logs/df24917/after-3.log
[df24917-diag/before] SETUP_ERROR at 'check out 408527ae58b5b706f5c02df8c37e096122cd8c78' (exit 1) -> logs/df24917-diag/before-3.log
```

## Registry gap and registered attempt

The operator states that both attempts' checkouts, including their `logs/` additions and
`requested.json` / `runs.jsonl` rows, were deleted by the operator before attempt 3.
No log from either attempt survives. This is a registry
gap: the retained registry cannot enumerate or verify every requested or executed side,
setup error, or outcome of attempts 1 and 2. The excerpts above do not replace the deleted
records, and this addendum does not reconstruct rows for them.

Attempt 3, `20261030T123542Z-26639`, is the only invocation of the 2026-10-30 default matrix
with retained records. The operator states that it started at 05:35:42 from a fresh git
clone at `af71f397d410c330cf37cf52d7165e63158ec207`, with an empty `FAILBEFORE_WORK`
directory, no pre-existing build state, and
`JAVA8_HOME=/Library/Java/JavaVirtualMachines/jdk1.8.0_172.jdk/Contents/Home`, on the same
host as the historical runs. Its full console is retained in
[`console/console-20261030T123542Z-26639.txt`](console/console-20261030T123542Z-26639.txt).
The operator states that its first and last lines, `START ...` and `RUN_EXIT 0 ...`, were
written by the operator's wrapper, and that the scratch path was replaced by the literal
`$FAILBEFORE_WORK`.
