#!/usr/bin/env python3
"""Parse one Part C cell log (logs/partC/<cell>.txt) into one JSON record per run (stdout).

Everything is read from the log: the header (start, build revision, requested runs), the
harness's RESULT and ASSERT lines, the trailer (# exit=... wall_seconds=...) and the ASSERT-CELL
lines that part_c.sh appends after the JVM exits.

Validation (revision 2026-10-25): a missing or unreadable log, a log without its header or
trailer, a log without any run, fewer recorded runs than the header's runs=N, a run with a
missing or duplicated assertion, a failed harness validity check (pre_run_no_engine_containers,
post_run_no_leftover_containers, any ASSERT-CELL check) or an aborted run is listed on stderr and
makes the exit status 1. Records of the runs that are in the log are still printed, so that
failed cells stay in logs/partC/runs.jsonl. The record format is unchanged.
usage: parse_part_c.py <log> <cell> <bundle root>
"""
import json
import os
import re
import sys

ASSERTIONS = {
    "flink": ["pre_run_no_engine_containers", "teardown_no_exception", "teardown_time_bound",
              "containers_absent_after_teardown", "new_taskmanager_at_own_jobmanager",
              "next_job_exit_zero", "next_job_time_bound", "post_run_no_leftover_containers"],
    "spark": ["pre_run_no_engine_containers", "teardown_no_exception", "teardown_time_bound",
              "containers_absent_after_teardown", "next_job_exit_zero", "next_job_time_bound",
              "post_run_no_leftover_containers"],
}
# harness validity checks: a FAIL here means the experiment is invalid, not that the code under
# test misbehaved (teardown and next-job FAILs in the "before" cells are expected observations)
VALIDITY = ("pre_run_no_engine_containers", "post_run_no_leftover_containers")
CELL_CHECKS = ("harness_jvm_completed", "no_engine_container_after_cell",
               "no_new_docker_network_after_cell", "cell_time_bound", "host_tmp_seatunnel_mnt_absent")


def parse(log, cell, bundle):
    """Return (records, summary). summary: runs_requested, runs_recorded, runs_valid, problems."""
    problems = []
    rel = os.path.relpath(log, bundle)
    try:
        engine, revlabel = cell.split("-")
        expected = ASSERTIONS[engine]
    except (ValueError, KeyError):
        return [], {"runs_requested": None, "runs_recorded": 0, "runs_valid": 0,
                    "problems": [f"{rel}: unknown cell name {cell!r}"]}
    try:
        lines = open(log, errors="replace").read().splitlines(True)
    except OSError as e:
        return [], {"runs_requested": None, "runs_recorded": 0, "runs_valid": 0,
                    "problems": [f"{rel}: log missing or unreadable ({e.__class__.__name__})"]}
    runs, cell_checks, start, rev, rc, wall, requested = {}, [], None, None, None, None, None
    for line in lines:
        m = re.match(r"# cell=\S+ start=(\S+) build_rev=(\S+)", line)
        if m:
            start, rev = m.group(1), m.group(2)
            r = re.search(r" runs=(\d+)\s*$", line)
            requested = int(r.group(1)) if r else None
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
    records = []
    for n in sorted(runs):
        r = runs[n]
        job = next((e[len("next job "):] for e in r["events"] if e.startswith("next job ")), None)
        td = next((int(e.split("=")[1]) for e in r["events"] if e.startswith("teardown millis=")), None)
        jm = re.match(r"exit=(-?\d+) seconds=(\d+)", job or "")
        records.append({
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
            "log": rel})

    # validation
    if start is None:
        problems.append(f"{rel}: header line '# cell=... start=... build_rev=...' missing (unparsable log)")
    if requested is None:
        problems.append(f"{rel}: requested run count (runs=N in the header) missing")
    if rc is None:
        problems.append(f"{rel}: trailer '# exit=... wall_seconds=...' missing (JVM did not finish or log truncated)")
    if not runs:
        problems.append(f"{rel}: no run recorded")
    if sorted(runs) != list(range(1, len(runs) + 1)):
        problems.append(f"{rel}: run numbers are not 1..{len(runs)}: {sorted(runs)}")
    cell_ok = True
    names = [c["name"] for c in cell_checks]
    for name in CELL_CHECKS:
        if names.count(name) != 1:
            problems.append(f"{rel}: cell check {name} recorded {names.count(name)} times (expected once)")
            cell_ok = False
    for c in cell_checks:
        if c["result"] != "PASS":
            problems.append(f"{rel}: cell check {c['name']} FAIL (observed {c['observed']})")
            cell_ok = False
    valid = 0
    for n in sorted(runs):
        r = runs[n]
        got = [a["name"] for a in r["assertions"]]
        ok = True
        for name in expected:
            if got.count(name) != 1:
                problems.append(f"{rel}: run {n}: assertion {name} recorded {got.count(name)} times (expected once)")
                ok = False
        for a in r["assertions"]:
            if a["name"] in VALIDITY and a["result"] != "PASS":
                problems.append(f"{rel}: run {n}: validity check {a['name']} FAIL (observed {a['observed']})")
                ok = False
        if any(e.startswith("aborted:") for e in r["events"]):
            problems.append(f"{rel}: run {n}: aborted by the harness's pre-run check")
            ok = False
        if "done" not in r["events"]:
            problems.append(f"{rel}: run {n}: no 'done' line (run incomplete)")
            ok = False
        valid += int(ok and cell_ok)
    if requested is not None:
        if len(runs) < requested:
            problems.append(f"{rel}: fewer runs than requested: {len(runs)} of {requested} recorded")
        if valid < requested:
            problems.append(f"{rel}: {valid} of {requested} requested runs valid")
    return records, {"runs_requested": requested, "runs_recorded": len(runs), "runs_valid": valid,
                     "problems": problems}


def main():
    log, cell, bundle = sys.argv[1:]
    records, summary = parse(log, cell, bundle)
    for rec in records:
        print(json.dumps(rec))
    for p in summary["problems"]:
        print(f"parse_part_c.py: {p}", file=sys.stderr)
    return 1 if summary["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
