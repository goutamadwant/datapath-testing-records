#!/usr/bin/env python3
"""Build results.json from the replay logs (reconstruction, 2026-10-25).

Every value is parsed from a log file written by run_part_a.py, run_part_b.sh or the Part C
runner; each cell carries the log path(s) and their sha256.
"""
import glob
import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
LOGS = os.path.join(EXP, "logs")


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def logref(p):
    return {"path": p, "sha256": sha(p), "bytes": os.path.getsize(p)}


ARTICLE_A = {
    "503x2": ("Table 1 row 1", "fails on the first 503", "succeeds on the third request"),
    "reset4": ("Table 1 row 2", "fails after four attempts", "succeeds on the fifth"),
    "429x2": ("Table 1 row 3", "succeeds, the transport already backs off on 429", "succeeds"),
    "truncate1": ("Table 1 row 4", "fails", "still fails"),
    "wrapper429s": ("Table 1 row 5", "fails at 21 seconds, main class not found",
                    "succeeds at 35 seconds on the fourth attempt"),
    "429x2nobody": ("sensitivity variant of row 3 (not a Table 1 row)", None, None),
}


def part_a():
    runs = json.load(open(os.path.join(LOGS, "partA", "partA_runs.json")))
    cells = []
    for r in sorted(runs, key=lambda x: x["order"]):
        row, art_before, art_after = ARTICLE_A[r["fault"]]
        jr = r["junit_requests"]
        first = jr.get("/maven2/junit/junit/4.13.2/junit-4.13.2.pom")
        wr = r["wrapper_jar_requests"]
        cell = {
            "part": "A", "cell": r["run_id"], "table_row": row, "jdk": r["jdk"],
            "fault": r["fault"], "config": r["config"], "run_order": r["order"],
            "start": r["start"], "invalid": r.get("invalid", False),
            "invalid_reason": r.get("invalid_reason"),
            "outcome": ("invalid (harness error)" if r.get("invalid") else
                        ("pass" if r["build_success"] else ("timeout" if r["timed_out"] else "fail"))),
            "exit_code": r["exit_code"], "wall_seconds": r["wall_seconds"],
            "junit_pom_4_13_2_attempts": first["attempts"] if first else 0,
            "junit_pom_4_13_2_actions": first["actions"] if first else [],
            "junit_requests_per_path": {k.rsplit("/", 1)[1]: v["attempts"] for k, v in jr.items()},
            "error": (r["error_lines"][0] if r["error_lines"] else None),
            "command": r["command"], "server_command": r["server_command"],
            "article": {"before": art_before, "after": art_after},
            "logs": [logref(r["mvn_log"]), logref(r["server_log"])],
        }
        if r["fault"] == "wrapper429s":
            cell["wrapper_jar_attempts"] = len(wr)
            cell["wrapper_jar_attempt_times_s"] = [w["t_rel_s"] for w in wr]
            cell["wrapper_jar_actions"] = [w["action"] for w in wr]
            cell["main_class_not_found"] = r["main_class_not_found"]
            if wr:
                cell["seconds_first_to_last_wrapper_attempt"] = round(wr[-1]["t_rel_s"] - wr[0]["t_rel_s"], 2)
        cells.append(cell)
    return cells


ARTICLE_B = {
    "dev-hook-jdk8": "15/20 failed (JDK 8u172)",
    "dev-hook-jdk11": "7/20 failed (JDK 11.0.19)",
    "patch-hook-jdk8": "0/20 failed",
    "patch-hook-jdk11": "0/20 failed",
    "dev-nohook-contention-jdk8": "50/50 passed",
    "dev-nohook-contention-jdk11": "50/50 passed",
}


def part_b():
    cells = []
    for p in sorted(glob.glob(os.path.join(LOGS, "partB", "*.txt"))):
        name = os.path.basename(p)[:-4]
        if name.startswith("build-"):
            continue
        text = open(p, errors="replace").read()
        iters = re.findall(r"^ITER (\d+) (PASS|FAIL|ERROR) (\d+)(.*)$", text, re.M)
        hooks = re.findall(r"REPLAY-HOOK stall45 at deadline(-?\d+)ms, woke at deadline(-?\d+)ms", text)
        m = re.search(r"^SUMMARY failed=(\d+)/(\d+)", text, re.M)
        head = dict(re.findall(r"^# (\w+)=(\S+)", text, re.M))
        cell = {
            "part": "B", "cell": name, "start": head.get("start") or re.search(r"start=(\S+)", text).group(1),
            "revision": re.search(r"rev=(\w+)", text).group(1),
            "jvm": re.search(r"^JVM (.*)$", text, re.M).group(1) if re.search(r"^JVM (.*)$", text, re.M) else None,
            "iterations": len(iters),
            "failed": sum(1 for i in iters if i[1] != "PASS"),
            "passed": sum(1 for i in iters if i[1] == "PASS"),
            "summary_line": m.group(0) if m else None,
            "failure_messages_distinct": sorted({i[3].strip()[:200] for i in iters if i[1] != "PASS"}),
            "per_iteration": [{"i": int(i[0]), "outcome": i[1], "ms": int(i[2])} for i in iters],
            "article": ARTICLE_B.get(name, "not in the article (sensitivity variant)"),
            "logs": [logref(p)],
        }
        if hooks:
            cell["hook_stall_offsets_ms_vs_idleDeadline"] = [
                {"stall_at": int(a), "woke_at": int(b)} for a, b in hooks]
        cells.append(cell)
    for p in sorted(glob.glob(os.path.join(LOGS, "partB", "build-*.txt"))):
        text = open(p, errors="replace").read()
        cells.append({"part": "B", "cell": os.path.basename(p)[:-4], "kind": "build",
                      "outcome": "pass" if "BUILD SUCCESS" in text else "fail", "logs": [logref(p)]})
    return cells


ARTICLE_C = {
    ("flink118TaskManagerKilled", "before"): "Table 1 row 6 Before: on dev, teardown threw in 11 of 11 runs and in 6 of them the next job hung for more than 120 s",
    ("flink118TaskManagerKilled", "after"): "Table 1 row 6 After: final shared revision, 2 of 2 runs completed and the next job exited 0 (Flink-only revision 12 of 12 not reconstructed)",
    ("spark3MasterKilled", "before"): "Table 1 row 7 Before: teardown threw, killed container left behind (n not retained)",
    ("spark3MasterKilled", "after"): "Table 1 row 7 After: teardown completed with a warning, container removed, next job exit 0 (n not retained)",
}


def part_c():
    groups = {}
    for p in sorted(glob.glob(os.path.join(LOGS, "partC", "*.txt"))):
        name = os.path.basename(p)[:-4]
        if name.startswith("build-"):
            text = open(p, errors="replace").read()
            groups[name] = {"part": "C", "cell": name, "kind": "build",
                            "outcome": "pass" if "BUILD SUCCESS" in text else "fail", "logs": [logref(p)]}
            continue
        text = open(p, errors="replace").read()
        method = name.split("-")[0]
        rev = re.search(r"rev_label=(\w+)", text).group(1)
        key = method + "-" + rev
        g = groups.setdefault(key, {"part": "C", "cell": key, "scenario": method, "revision_label": rev,
                                    "article": ARTICLE_C[(method, rev)], "runs": [], "logs": []})
        g["logs"].append(logref(p))
        runs = {}
        for line in re.findall(r"^RESULT (?:flink118|spark3) run=(\d+) (.*)$", text, re.M):
            runs.setdefault(line[0], []).append(line[1])
        for k in sorted(runs, key=int):
            lines = runs[k]
            get = lambda pre: next((l for l in lines if l.startswith(pre)), None)
            td = get("teardown ")
            nj = get("next job ") or get("startUp2/next job threw")
            g["runs"].append({
                "log": os.path.basename(p), "run_in_log": int(k),
                "teardown": "threw" if td and td.startswith("teardown threw") else ("completed" if td else None),
                "teardown_detail": td,
                "after_teardown": get("after-teardown"),
                "taskmanager2_registration": get("taskmanager2 registration"),
                "next_job": nj,
                "next_job_outcome": ("exit 0" if nj and "exit=0" in nj else ("hung (timeout)" if nj and "TIMEOUT" in nj else nj)),
            })
    for g in groups.values():
        if "runs" in g:
            r = g["runs"]
            g["n_runs"] = len(r)
            g["teardown_threw"] = sum(1 for x in r if x["teardown"] == "threw")
            g["next_job_exit0"] = sum(1 for x in r if x["next_job_outcome"] == "exit 0")
            g["next_job_hung"] = sum(1 for x in r if x["next_job_outcome"] == "hung (timeout)")
    for p in sorted(glob.glob(os.path.join(LOGS, "partC", "invalid", "*.txt"))):
        groups[p] = {"part": "C", "cell": "invalid/" + os.path.basename(p)[:-4], "invalid": True,
                     "invalid_reason": "harness/build setup error before any container work (see README deviation 18)",
                     "logs": [logref(p)]}
    return list(groups.values())


def main():
    out = {
        "title": "Replay of Table 1 and the PR 12472 stall-injection records (reconstruction)",
        "reconstruction_date": "2026-10-25",
        "note": ("Reconstructed harnesses, not the originals; every value below was parsed from a "
                 "log of a run executed on 2026-10-25. See README.md for deviations."),
        "cells": part_a() + part_b() + part_c(),
        "not_rerun": [
            {"cell": "Table 1 row 7, Zeta server killed",
             "reason": "SeaTunnelContainer needs the seatunnelhub/openjdk:8u342 image, which is not cached locally; the task allowed Part C only with cached images"},
            {"cell": "Table 1 row 6, Flink-only intermediate revision of PR 12481 (12 of 12)",
             "reason": "that revision is not in the merged history; only the parent and the merge were run"},
            {"cell": "PR 12472 200/200 stress and the two mutation checks",
             "reason": "outside the requested scope"},
        ],
        "invalid_runs_kept": "see cells with invalid=true; logs under logs/partA/invalid and logs/partC/invalid",
    }
    dst = os.path.join(EXP, "results.json")
    json.dump(out, open(dst, "w"), indent=1)
    print(dst, len(out["cells"]), "cells")


if __name__ == "__main__":
    main()
