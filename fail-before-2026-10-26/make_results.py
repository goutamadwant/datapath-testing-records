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
  NO_TESTS_RUN   the build succeeded but the filter selected no test
  UNKNOWN        none of the above could be established from the log

Usage: python3 make_results.py
"""
import hashlib
import json
import pathlib
import re
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
LOGS = HERE / "logs"


def cargo_outcome(text):
    tests = [
        {"name": m.group(1), "result": "PASS" if m.group(2) == "ok" else m.group(2)}
        for m in re.finditer(r"^test (\S+) \.\.\. (ok|FAILED|ignored)\s*$", text, re.M)
    ]
    panics = re.findall(r"^thread '.*' panicked at .*\n(.*)$", text, re.M)
    errors = re.findall(r"^(error(?:\[E\d+\])?: .*)$", text, re.M)
    if "could not compile" in text or (errors and not tests):
        return "COMPILE_ERROR", tests, errors[:20]
    if not tests:
        return ("NO_TESTS_RUN" if "test result: ok. 0 passed" in text else "UNKNOWN"), tests, []
    if any(t["result"] == "FAILED" for t in tests):
        return "FAIL", tests, panics
    return "PASS", tests, []


def maven_outcome(text, surefire_dir, module):
    if "COMPILATION ERROR" in text:
        errs = re.findall(r"^\[ERROR\] (/\S+\.java:\[\d+,\d+\] .*)$", text, re.M)
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
    if any(t["result"] == "FAIL" for t in tests):
        return "FAIL", tests, []
    if all(t["result"] == "SKIPPED" for t in tests):
        return "NO_TESTS_RUN", tests, []
    return "PASS", tests, []


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    runs = [json.loads(line) for line in (LOGS / "runs.jsonl").read_text().splitlines() if line.strip()]
    out = []
    for r in runs:
        log = HERE / r["log"]
        text = log.read_text(errors="replace")
        if "cargo test" in r["command"]:
            outcome, tests, detail = cargo_outcome(text)
        else:
            module = re.search(r"-pl (\S+)", r["command"]).group(1)
            outcome, tests, detail = maven_outcome(text, log.with_suffix(".surefire"), module)
        r = dict(r, outcome=outcome, tests=tests, detail=detail, log_sha256=sha256(log))
        out.append(r)
    files = sorted(p for p in LOGS.rglob("*") if p.is_file())
    result = {
        "description": "Fail-before / pass-after runs of the regression tests named in the article. "
        "before = first parent of the merge commit plus only the pull request's test change; "
        "after = merge commit. Outcomes are parsed from the logs listed here.",
        "runs": out,
        "log_files": {str(p.relative_to(HERE)): sha256(p) for p in files},
        "patches": {str(p.relative_to(HERE)): sha256(p) for p in sorted((HERE / "patches").glob("*"))},
    }
    (HERE / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    for r in out:
        print(f"{r['case']:18} {r['side']:6} {r['outcome']:14} {r['duration_s']:>8} s  {r['log']}")


if __name__ == "__main__":
    main()
