#!/usr/bin/env python3
"""Parse one Part C cell log (logs/partC/<cell>.txt) into one JSON record per run (stdout).

Everything is read from the log: the header (start, build revision), the harness's RESULT and
ASSERT lines, the trailer (# exit=... wall_seconds=...) and the ASSERT-CELL lines that
part_c.sh appends after the JVM exits.
usage: parse_part_c.py <log> <cell> <bundle root>
"""
import json
import os
import re
import sys

log, cell, bundle = sys.argv[1:]
runs, cell_checks, start, rev, rc, wall = {}, [], None, None, None, None
for line in open(log, errors="replace"):
    m = re.match(r"# cell=\S+ start=(\S+) build_rev=(\S+)", line)
    if m:
        start, rev = m.group(1), m.group(2)
        continue
    m = re.match(r"# exit=(-?\d+) wall_seconds=(\d+)", line)
    if m:
        rc, wall = int(m.group(1)), int(m.group(2))
        continue
    m = re.match(r"ASSERT (\S+) run=(\d+) name=(\S+) result=(PASS|FAIL) expected=(\S*) observed=(.*)", line)
    if m:
        runs.setdefault(int(m.group(2)), {"assertions": [], "events": []})["assertions"].append(
            {"name": m.group(3), "result": m.group(4), "expected": m.group(5), "observed": m.group(6).strip()})
        continue
    m = re.match(r"RESULT \S+ run=(\d+) (.*)", line)
    if m:
        runs.setdefault(int(m.group(1)), {"assertions": [], "events": []})["events"].append(m.group(2)[:400])
        continue
    m = re.match(r"ASSERT-CELL \S+ name=(\S+) result=(PASS|FAIL) expected=(\S*) observed=(.*)", line)
    if m:
        cell_checks.append({"name": m.group(1), "result": m.group(2), "expected": m.group(3),
                            "observed": m.group(4).strip()})
engine, revlabel = cell.split("-")
for n in sorted(runs):
    r = runs[n]
    job = next((e[len("next job "):] for e in r["events"] if e.startswith("next job ")), None)
    td = next((int(e.split("=")[1]) for e in r["events"] if e.startswith("teardown millis=")), None)
    jm = re.match(r"exit=(-?\d+) seconds=(\d+)", job or "")
    print(json.dumps({
        "part": "C", "cell": cell, "engine": engine, "revision_label": revlabel, "run": n,
        "cell_start": start, "build_revision": rev,
        "teardown_threw": any(e.startswith("teardown threw") for e in r["events"]),
        "teardown_millis": td,
        "next_job": job,
        "next_job_exit_code": int(jm.group(1)) if jm else None,
        "next_job_seconds": int(jm.group(2)) if jm else None,
        "next_job_timed_out": bool(job and job.startswith("TIMEOUT")),
        "assertions": r["assertions"], "events": r["events"],
        "cell_jvm_exit": rc, "cell_wall_seconds": wall, "cell_checks": cell_checks,
        "log": os.path.relpath(log, bundle)}))
