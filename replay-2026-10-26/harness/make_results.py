#!/usr/bin/env python3
"""Regenerate results.json from the per-run records in logs/part{A,B,C}/runs.jsonl.

Every value comes from a run record written by part_a.py / part_b.sh / part_c.sh, which in turn
parse the run's own log. All paths are relative to the bundle root. The sha256 of every file
under logs/ (and of every harness file) is recorded. Run: python3 harness/make_results.py
"""
import collections
import hashlib
import json
import os
import re
import time

B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(part):
    p = os.path.join(B, "logs", part, "runs.jsonl")
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


def files_under(d):
    out = []
    for root, dirs, files in os.walk(os.path.join(B, d)):
        dirs.sort()
        for f in sorted(files):
            if f == ".DS_Store":
                continue
            p = os.path.join(root, f)
            out.append({"path": os.path.relpath(p, B), "bytes": os.path.getsize(p), "sha256": sha(p)})
    return out


def part_a(runs):
    cells = collections.OrderedDict()
    for r in runs:
        if not r.get("valid", True):
            continue
        c = cells.setdefault(r["cell"], {"jdk": r["jdk"], "fault": r["fault"], "config": r["config"],
                                         "runs": 0, "pass": 0, "fail": 0, "timed_out": 0,
                                         "primary_attempts": [], "primary_actions": [],
                                         "wrapper_jar_attempts": [], "wrapper_jar_offsets_s": [],
                                         "closed_stream_error": 0, "main_class_not_found": 0,
                                         "wall_seconds": []})
        c["runs"] += 1
        c["pass" if r["outcome"] == "PASS" else "fail"] += 1
        c["timed_out"] += int(bool(r["timed_out"]))
        c["primary_attempts"].append(r["primary_attempts"])
        c["primary_actions"].append(r["primary_actions"])
        c["wrapper_jar_attempts"].append(r["wrapper_jar_attempts"])
        c["wrapper_jar_offsets_s"].append(r["wrapper_jar_offsets_s"])
        c["closed_stream_error"] += int(r["closed_stream_error"])
        c["main_class_not_found"] += int(r["main_class_not_found"])
        c.setdefault("checksum_validation_failed", 0)
        c["checksum_validation_failed"] += int(
            "Checksum validation failed" in open(os.path.join(B, r["mvn_log"]), errors="replace").read())
        c["wall_seconds"].append(r["wall_seconds"])
    for c in cells.values():
        w = c["wall_seconds"]
        c["wall_seconds_min_median_max"] = [min(w), sorted(w)[len(w) // 2], max(w)]
        c["label"] = ("sensitivity variant (empty-body 429), not a Table 1 row"
                      if c["fault"] == "429x2nobody" else
                      {"503x2": "Table 1 row 1", "reset4": "Table 1 row 2", "429x2": "Table 1 row 3",
                       "truncate1": "Table 1 row 4", "wrapper429s": "Table 1 row 5"}[c["fault"]])
    return cells


def pair_hooks(log):
    """(woke_at_ms or None, outcome) per iteration, pairing each REPLAY-HOOK line with the next ITER."""
    pending, out = None, []
    for line in open(os.path.join(B, log), errors="replace"):
        m = re.search(r"REPLAY-HOOK stall45 at deadline(-?\d+)ms, woke at deadline(-?\d+)ms", line)
        if m:
            pending = int(m.group(2))
            continue
        m = re.match(r"ITER (\d+) (PASS|FAIL|ERROR)", line)
        if m:
            out.append((pending, m.group(2)))
            pending = None
    return out


def part_b(loops):
    cells = collections.OrderedDict()
    bins = collections.OrderedDict((k, [0, 0]) for k in
                                   ("woke before idleDeadlineMs", "woke 0-9 ms after", "woke 10-19 ms after",
                                    "woke >= 20 ms after", "no stall injected"))
    for r in loops:
        c = cells.setdefault(r["cell"], {"jdk": r["jdk"], "hook": r["hook"], "stall_lead_ms": r["stall_lead_ms"],
                                         "loops": 0, "per_loop_failed": [], "iterations_per_loop": []})
        c["loops"] += 1
        c["per_loop_failed"].append(r["failed"])
        c["iterations_per_loop"].append(r["iterations"])
        if r["hook"] == "dev-stall45":
            for woke, outcome in pair_hooks(r["log"]):
                k = ("no stall injected" if woke is None else "woke before idleDeadlineMs" if woke < 0 else
                     "woke 0-9 ms after" if woke < 10 else "woke 10-19 ms after" if woke < 20 else
                     "woke >= 20 ms after")
                bins[k][0] += 1
                bins[k][1] += int(outcome != "PASS")
    for name, c in cells.items():
        want = 50 if "contention" in name else 20
        c["incomplete_loops"] = sum(1 for n in c["iterations_per_loop"] if n != want)
        c["failed_total"] = sum(c["per_loop_failed"])
        c["iterations_total"] = sum(c["iterations_per_loop"])
    return cells, {k: {"iterations": v[0], "failed": v[1]} for k, v in bins.items()}


def part_c(runs):
    cells = collections.OrderedDict()
    for r in runs:
        c = cells.setdefault(r["cell"], {"engine": r["engine"], "revision_label": r["revision_label"],
                                         "runs": 0, "assertions": collections.OrderedDict(),
                                         "teardown_threw": 0, "next_job_exit_zero": 0,
                                         "next_job_timed_out": 0, "teardown_millis": [],
                                         "next_job_seconds": [], "cell_checks": r["cell_checks"]})
        c["runs"] += 1
        c["teardown_threw"] += int(r["teardown_threw"])
        c["next_job_exit_zero"] += int(r["next_job_exit_code"] == 0)
        c["next_job_timed_out"] += int(r["next_job_timed_out"])
        c["teardown_millis"].append(r["teardown_millis"])
        c["next_job_seconds"].append(r["next_job_seconds"])
        for a in r["assertions"]:
            s = c["assertions"].setdefault(a["name"], {"PASS": 0, "FAIL": 0})
            s[a["result"]] += 1
    return cells


def main():
    logs = files_under("logs")
    shas = {f["path"]: f["sha256"] for f in logs}
    a_runs, b_loops, c_runs = load("partA"), load("partB"), load("partC")
    for r in a_runs:
        r["mvn_log_sha256"] = shas.get(r["mvn_log"])
        r["server_log_sha256"] = shas.get(r["server_log"])
    for r in b_loops + c_runs:
        r["log_sha256"] = shas.get(r["log"])
    b_cells, b_bins = part_b(b_loops)
    harness = files_under("harness") + [
        {"path": "replay.sh", "bytes": os.path.getsize(os.path.join(B, "replay.sh")),
         "sha256": sha(os.path.join(B, "replay.sh"))}]
    res = {
        "bundle": "replay-2026-10-26",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "note": "Reconstruction runs. Every value below is parsed from a log under logs/; "
                "paths are relative to this file's directory.",
        "revisions": {k: os.environ.get(k) for k in ("REV_A_BEFORE", "REV_A_AFTER", "REV_B_DEV",
                                                       "REV_B_PATCH", "REV_C_BEFORE", "REV_C_AFTER")}
        if os.environ.get("REV_A_BEFORE") else {
            "REV_A_BEFORE": "a1084015eeb390a6c7f53d3ce7391217e427e4d9",
            "REV_A_AFTER": "ae7c919bcb78f03446dbd2b754a2b9882602946a",
            "REV_B_DEV": "deb16a3c3152f0349a587a504dccc997a131a9d7",
            "REV_B_PATCH": "87ed0afe0f783eda1b1f3ac6f0ac9fadedcb4f98",
            "REV_C_BEFORE": "7ba68325cb7ea1bf1a28f56c4f9c20695d221df3",
            "REV_C_AFTER": "0e4cf52896ee3604a8e7899d7736ffd914ee6ce7"},
        "partA": {"cells": part_a(a_runs), "runs": a_runs},
        "partB": {"cells": b_cells, "hook_wake_position_vs_failure_pooled_dev_hook": b_bins,
                  "loops": b_loops},
        "partC": {"cells": part_c(c_runs), "runs": c_runs},
        "not_run": [
            "Table 1 row 7, Zeta server killed: harness has no Zeta scenario and seatunnelhub/openjdk:8u342 "
            "is not cached (see logs/setup/setup-partC-*.txt)",
            "Table 1 row 6, Flink-only intermediate revision of PR 12481: not in the merged history",
            "PR 12472 200/200 stress run and the two mutation checks",
        ],
        "logs": logs,
        "harness": harness,
    }
    with open(os.path.join(B, "results.json"), "w") as f:
        json.dump(res, f, indent=1)
        f.write("\n")
    print(f"results.json: A {len(a_runs)} runs, B {len(b_loops)} loops, C {len(c_runs)} runs, "
          f"{len(logs)} log files hashed")


if __name__ == "__main__":
    main()
