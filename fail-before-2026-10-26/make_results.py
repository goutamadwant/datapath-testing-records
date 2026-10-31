#!/usr/bin/env python3
"""Derive the outcome of every recorded run from its log and write results.json.

Reads logs/runs.jsonl (one record per executed run, written by run.sh). For each record the
outcome is taken from the log itself (and, for Maven runs, from the surefire XML reports copied
next to the log), never from the exit code alone:

  COMPILE_ERROR  the test sources of the module under test did not compile against this tree
  BUILD_ERROR    the build failed before the test sources were compiled (harness problem, not a
                 test outcome)
  FAIL           the named test ran and at least one test case failed or errored
  PASS           the named test ran and every test case passed
  NO_TESTS_RUN   the build succeeded but the filter selected no test, or every selected test
                 was ignored or skipped
  UNKNOWN        none of the above could be established from the log, or the log is
                 internally inconsistent (summary line disagrees with the per-test lines)
  SETUP_ERROR    the side was never run: a setup step (clone, checkout, transplant or patch
                 apply, missing JDK, refusal) failed; the record names the step and the log holds
                 its output

A run is PASS only if the test named in its command (the cargo filter or the Maven -Dtest value)
was actually executed and every executed case passed. Each case must have a completed before
and after record; a case is reported as comparison "incomplete" when a side has no record, when
a side's latest record is SETUP_ERROR, or when the latest invocation that requested the case
(logs/requested.json, written by run.sh before any build) has no record for a requested side
(listed under "missing").

Parser revision 3 (2026-10-30) recognises the literal $FAILBEFORE_WORK/ prefix like an
absolute path for Maven test-source errors; re-running it over all retained logs changes
no historical outcome.

Usage: python3 make_results.py
"""
import hashlib
import json
import pathlib
import re
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
LOGS = HERE / "logs"


def expected_cargo_test(command):
    """The test filter: the last positional argument of `cargo test` before any `--`."""
    args = command.split(" -- ")[0].split()
    # drop values of options that take one (-p NAME, --test NAME, --profile NAME)
    out, skip = [], False
    for a in args[2:]:
        if skip:
            skip = False
            continue
        if a in ("-p", "--test", "--profile", "--package"):
            skip = True
            continue
        if not a.startswith("-"):
            out.append(a)
    return out[-1] if out else None


def expected_maven_tests(command):
    m = re.search(r"-Dtest=(\S+)", command)
    return m.group(1).split(",") if m else []


def cargo_outcome(text, expected=None):
    tests = [
        {"name": m.group(1), "result": {"ok": "PASS", "FAILED": "FAILED", "ignored": "IGNORED"}[m.group(2)]}
        for m in re.finditer(r"^test (\S+) \.\.\. (ok|FAILED|ignored)\s*$", text, re.M)
    ]
    panics = re.findall(r"^thread '.*' panicked at .*\n(.*)$", text, re.M)
    errors = re.findall(r"^(error(?:\[E\d+\])?: .*)$", text, re.M)
    if "could not compile" in text or (errors and not tests):
        return "COMPILE_ERROR", tests, errors[:20]
    summaries = re.findall(
        r"^test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored;", text, re.M
    )
    if not summaries:
        return "UNKNOWN", tests, ["no `test result:` summary line in the log"]
    passed = sum(int(s[1]) for s in summaries)
    failed = sum(int(s[2]) for s in summaries)
    ignored = sum(int(s[3]) for s in summaries)
    counted = {
        "PASS": sum(t["result"] == "PASS" for t in tests),
        "FAILED": sum(t["result"] == "FAILED" for t in tests),
        "IGNORED": sum(t["result"] == "IGNORED" for t in tests),
    }
    if (counted["PASS"], counted["FAILED"], counted["IGNORED"]) != (passed, failed, ignored):
        return "UNKNOWN", tests, [
            f"summary lines say {passed} passed/{failed} failed/{ignored} ignored, "
            f"per-test lines say {counted}"
        ]
    executed = [t for t in tests if t["result"] != "IGNORED"]
    if not executed:
        return "NO_TESTS_RUN", tests, (["every selected test was ignored"] if tests else [])
    if expected and not any(t["name"].endswith(expected) for t in executed):
        return "UNKNOWN", tests, [f"expected test {expected!r} was not executed"]
    if any(t["result"] == "FAILED" for t in executed):
        return "FAIL", tests, panics
    return "PASS", tests, []


def maven_outcome(text, surefire_dir, module, expected=()):
    if "COMPILATION ERROR" in text:
        errs = re.findall(r"^\[ERROR\] ((?:/|\$FAILBEFORE_WORK/)\S+\.java:\[\d+,\d+\] .*)$", text, re.M)
        errs = list(dict.fromkeys(re.sub(r"^.*/trees/[^/]+/", "", e) for e in errs))
        in_test = [e for e in errs if e.startswith(module + "/src/test/")]
        if in_test:
            return "COMPILE_ERROR", [], in_test[:30]
        return "BUILD_ERROR", [], errs[:5]
    tests, msgs = [], []
    for xml in sorted(surefire_dir.glob("TEST-*.xml")) if surefire_dir.is_dir() else []:
        for tc in ET.parse(xml).getroot().iter("testcase"):
            name = f"{tc.get('classname')}#{tc.get('name')}"
            bad = tc.find("failure") if tc.find("failure") is not None else tc.find("error")
            skipped = tc.find("skipped") is not None
            res = "SKIPPED" if skipped else ("FAIL" if bad is not None else "PASS")
            entry = {"name": name, "result": res, "time_s": float(tc.get("time") or 0)}
            if bad is not None:
                entry["failure"] = (bad.get("type") or "") + ": " + (bad.get("message") or "")[:400]
            tests.append(entry)
    if not tests:
        if "BUILD SUCCESS" in text:
            return "NO_TESTS_RUN", tests, []
        return "UNKNOWN", tests, re.findall(r"^\[ERROR\] .*$", text, re.M)[:20]
    if all(t["result"] == "SKIPPED" for t in tests):
        return "NO_TESTS_RUN", tests, ["every selected test was skipped"]
    for want in expected:
        cls, _, method = want.partition("#")
        hit = [t for t in tests if t["name"].split("#")[0].endswith(cls) and (not method or t["name"].endswith("#" + method))]
        if not hit or all(t["result"] == "SKIPPED" for t in hit):
            return "UNKNOWN", tests, [f"expected test {want!r} was not executed"]
    if any(t["result"] == "FAIL" for t in tests):
        return "FAIL", tests, []
    return "PASS", tests, []


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def setup_outcome(record, text):
    """A side whose setup failed: the failed step and the last lines of its setup output."""
    lines = text.splitlines()
    try:
        output = lines[lines.index("# setup output:") + 1:]
    except ValueError:
        output = []
    output = [l[4:] if l.startswith("#   ") else l for l in output if not l.startswith("# end:")
              and not l.startswith("# exit code:")]
    return "SETUP_ERROR", [], [f"setup step failed: {record['setup_error']}"] + output[-10:]


def derive(record, text, surefire_dir):
    """(outcome, tests, detail, expected test) of one record, from its log."""
    command = record["command"]
    if "cargo test" in command:
        expected = expected_cargo_test(command)
    else:
        expected = expected_maven_tests(command)
    if record.get("setup_error"):
        return (*setup_outcome(record, text), expected)
    if "cargo test" in command:
        return (*cargo_outcome(text, expected), expected)
    module = re.search(r"-pl (\S+)", command).group(1)
    return (*maven_outcome(text, surefire_dir, module, expected), expected)


def compare(runs, requests):
    """Per case: the latest outcome of each side, missing requested sides, complete/incomplete."""
    comparisons = {}
    for r in runs:
        comparisons.setdefault(r["case"], {})[r["side"]] = r["outcome"]
    latest = {}  # case -> (invocation, sides) of the latest invocation that requested it
    for req in requests:
        sides = {}
        for s in req["sides"]:
            sides.setdefault(s["case"], []).append(s["side"])
        for case, ss in sides.items():
            latest[case] = (req["invocation"], ss)
    for case, (inv, ss) in latest.items():
        have = {r["side"] for r in runs if r["case"] == case and r.get("invocation") == inv}
        missing = [s for s in ss if s not in have]
        entry = comparisons.setdefault(case, {})
        if missing:
            entry["missing"] = [f"{s} (invocation {inv})" for s in missing]
    for case, sides in comparisons.items():
        ok = (
            {"before", "after"} <= set(sides)
            and "SETUP_ERROR" not in (sides["before"], sides["after"])
            and not sides.get("missing")
        )
        sides["comparison"] = "complete" if ok else "incomplete"
    return comparisons


def main():
    runs = [json.loads(line) for line in (LOGS / "runs.jsonl").read_text().splitlines() if line.strip()]
    req_file = LOGS / "requested.json"
    requests = json.loads(req_file.read_text()) if req_file.exists() else []
    out = []
    for r in runs:
        log = HERE / r["log"]
        text = log.read_text(errors="replace")
        outcome, tests, detail, expected = derive(r, text, log.with_suffix(".surefire"))
        r = dict(r, outcome=outcome, tests=tests, detail=detail, expected_test=expected,
                 log_sha256=sha256(log))
        out.append(r)
    comparisons = compare(out, requests)
    files = sorted(p for p in LOGS.rglob("*") if p.is_file())
    result = {
        "description": "Fail-before / pass-after runs of the regression tests named in the article. "
        "before = first parent of the merge commit plus only the pull request's test change; "
        "after = merge commit. The df24917-budget-nohook case adds separate hook-free test "
        "functions to both commits. Outcomes are parsed from the logs listed here.",
        "parser": "make_results.py rev 3 (2026-10-30): PASS requires the named test to have been "
        "executed; ignored-only or skipped-only runs are NO_TESTS_RUN; a summary line that disagrees "
        "with the per-test lines is UNKNOWN; every case needs a before and an after record; a record "
        "with setup_error is SETUP_ERROR and leaves its case incomplete; a case is also incomplete "
        "when the latest invocation in logs/requested.json that requested it has no record for a "
        "requested side. Revision 3 recognises the literal $FAILBEFORE_WORK/ prefix like an "
        "absolute path for Maven test-source errors; re-running it over all retained logs "
        "changes no historical outcome.",
        "runs": out,
        "comparisons": comparisons,
        "log_files": {str(p.relative_to(HERE)): sha256(p) for p in files},
        "patches": {str(p.relative_to(HERE)): sha256(p) for p in sorted((HERE / "patches").glob("*"))},
    }
    (HERE / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    for r in out:
        print(f"{r['case']:18} {r['side']:6} {r['outcome']:14} {r['duration_s']:>8} s  {r['log']}")
    for case, sides in comparisons.items():
        if sides["comparison"] != "complete":
            present = sorted(k for k in sides if k not in ("comparison", "missing"))
            print(f"{case:18} comparison INCOMPLETE: sides {present}"
                  + (f", missing {sides['missing']}" if sides.get("missing") else ""))


if __name__ == "__main__":
    main()
