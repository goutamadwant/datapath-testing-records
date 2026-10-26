#!/usr/bin/env python3
"""Negative tests for the validation in make_results.py and parse_part_c.py.

Each case copies logs/, harness/ and replay.sh of this bundle into a temporary directory, damages
the copy in one way, runs the copy's harness/make_results.py and expects exit status 1 with a
matching message (the unmodified copy must pass). Nothing in the bundle itself is changed and no
experiment is executed. Run: python3 harness/selftest_validation.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rewrite(path, fn):
    with open(path, errors="replace") as f:
        text = f.read()
    with open(path, "w") as f:
        f.write(fn(text))


def jsonl_edit(path, fn):
    rows = [json.loads(l) for l in open(path) if l.strip()]
    rows = fn(rows)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def a_drop_rep(d):
    jsonl_edit(f"{d}/logs/partA/runs.jsonl",
               lambda rs: [r for r in rs if r["run_id"] != "jdk8_503x2_before_r3"])


def a_duplicate_rep(d):
    def f(rs):
        dup = next(r for r in rs if r["run_id"] == "jdk11_reset4_after_r2")
        return rs + [dict(dup)]
    jsonl_edit(f"{d}/logs/partA/runs.jsonl", f)


def a_missing_log(d):
    os.remove(f"{d}/logs/partA/jdk8_429x2_after/r4.mvn.txt")


def a_unparsable_server_log(d):
    rewrite(f"{d}/logs/partA/jdk11_truncate1_before/r1.server.jsonl", lambda t: t + "{not json\n")


def a_fault_not_delivered(d):
    # first request for the fault target served normally, in the log and in the record
    p = f"{d}/logs/partA/jdk8_503x2_after/r5.server.jsonl"
    lines = open(p).read().splitlines(True)
    for i, l in enumerate(lines):
        if '"target": true' in l and "junit-4.13.2.pom\"" in l:
            lines[i] = l.replace('"action": "503"', '"action": "serve"', 1)
            break
    open(p, "w").write("".join(lines))

    def f(rs):
        for r in rs:
            if r["run_id"] == "jdk8_503x2_after_r5":
                r["primary_actions"][0] = "serve"
        return rs
    jsonl_edit(f"{d}/logs/partA/runs.jsonl", f)


def b_truncated_loop(d):
    p = f"{d}/logs/partB/dev-hook-jdk8/loop1.txt"
    rewrite(p, lambda t: "".join(l for l in t.splitlines(True)
                                 if not re.match(r"ITER (1[89]|20) |SUMMARY|# exit=", l)))


def b_missing_log(d):
    os.remove(f"{d}/logs/partB/patch-hook-jdk11/loop1.txt")


def c_run_missing(d):
    rewrite(f"{d}/logs/partC/spark-after.txt",
            lambda t: "".join(l for l in t.splitlines(True) if not re.match(r"(ASSERT|RESULT) spark3 run=5 ", l)))


def c_missing_log(d):
    os.remove(f"{d}/logs/partC/flink-after.txt")


def c_validity_fail(d):
    rewrite(f"{d}/logs/partC/flink-before.txt",
            lambda t: t.replace("run=2 name=pre_run_no_engine_containers result=PASS",
                                "run=2 name=pre_run_no_engine_containers result=FAIL", 1))


def c_mount_present(d):
    rewrite(f"{d}/logs/partC/spark-before.txt",
            lambda t: t.replace("name=host_tmp_seatunnel_mnt_absent result=PASS expected=absent observed=absent",
                                "name=host_tmp_seatunnel_mnt_absent result=FAIL expected=absent observed=present"))


def runs_jsonl_corrupt(d):
    rewrite(f"{d}/logs/partB/runs.jsonl", lambda t: t + "{truncated\n")


def records_missing(d):
    os.remove(f"{d}/logs/partC/runs.jsonl")


CASES = [
    ("unmodified copy", None, None),
    ("Part A: one repetition removed", a_drop_rep, "jdk8_503x2_before: fewer runs than requested: 4 of 5"),
    ("Part A: repetition duplicated", a_duplicate_rep, "recorded twice as valid"),
    ("Part A: Maven log missing", a_missing_log, "Maven log logs/partA/jdk8_429x2_after/r4.mvn.txt missing"),
    ("Part A: server log unparsable", a_unparsable_server_log, "unparsable"),
    ("Part A: fault not delivered", a_fault_not_delivered, "jdk8_503x2_after: 4 of 5 requested runs valid"),
    ("Part B: loop truncated", b_truncated_loop, "dev-hook-jdk8: 0 of 1 requested runs valid"),
    ("Part B: loop log missing", b_missing_log, "loop log missing"),
    ("Part C: run 5 missing from a cell log", c_run_missing, "spark-after: fewer runs than requested: 4 of 5"),
    ("Part C: cell log missing", c_missing_log, "flink-after.txt: log missing or unreadable"),
    ("Part C: pre-run validity check failed", c_validity_fail, "validity check pre_run_no_engine_containers FAIL"),
    ("Part C: /tmp/seatunnel_mnt present after the cell", c_mount_present, "host_tmp_seatunnel_mnt_absent FAIL"),
    ("runs.jsonl line not JSON", runs_jsonl_corrupt, "not valid JSON"),
    ("Part C records missing", records_missing, "logs/partC/runs.jsonl missing"),
]


def main():
    failures = 0
    for name, damage, expect in CASES:
        d = tempfile.mkdtemp(prefix="replay-selftest-")
        try:
            for sub in ("logs", "harness"):
                shutil.copytree(os.path.join(B, sub), os.path.join(d, sub))
            shutil.copy(os.path.join(B, "replay.sh"), d)
            if damage:
                damage(d)
            p = subprocess.run([sys.executable, "-I", os.path.join(d, "harness", "make_results.py")],
                               capture_output=True, text=True)
            out = p.stdout + p.stderr
            if damage is None:
                ok = p.returncode == 0 and "validation PASS" in out
            else:
                ok = p.returncode == 1 and expect in out and not os.path.exists(os.path.join(d, "results.json"))
            failures += int(not ok)
            print(f"{'ok  ' if ok else 'FAIL'} {name}: exit {p.returncode}"
                  + (f"; expected message found: {expect!r}" if damage and ok else ""))
            if not ok:
                print(out)
        finally:
            shutil.rmtree(d)
    print(f"{len(CASES) - failures} of {len(CASES)} cases as expected")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
