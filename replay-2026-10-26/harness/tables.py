#!/usr/bin/env python3
"""Print the README comparison tables (Markdown) from results.json.

usage: python3 harness/tables.py [--old <results.json of the 2026-10-25 bundle>]
The "Article" column quotes, word for word, Table 1 (rows 1-7) and the PR 12472 stall counts of
the article revision of 25 October 2026 that cites these records at commit fe561f6; that Table 1
reports this bundle's runs. The stall counts are in the article's text, not in Table 1, and are
marked "(text)"; the empty-body 429 variant is not in Table 1. The "PR 12472" column quotes the
pull request. The 2026-10-25 column is read from the older bundle's results.json; the 2026-10-26
column from this bundle's results.json.
"""
import argparse
import json
import os

B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROW = {"503x2": "1", "reset4": "2", "429x2": "3", "truncate1": "4", "wrapper429s": "5",
       "429x2nobody": "3 (variant)"}
FAULT = {"503x2": "HTTP 503 on first 2 requests", "reset4": "Connection reset on first 4 requests",
         "429x2": "HTTP 429 on first 2 requests", "truncate1": "First response body cut off halfway",
         "wrapper429s": "Wrapper jar 429 for 30 s",
         "429x2nobody": "HTTP 429 with empty body on first 2 requests (not a Table 1 row)"}
ARTICLE_A = {
    ("503x2", "before"): "fails on first 503, 5/5 per JDK",
    ("503x2", "after"): "succeeds on third request, 5/5 per JDK",
    ("reset4", "before"): "fails after four attempts, 5/5 per JDK",
    ("reset4", "after"): "succeeds on fifth, 5/5 per JDK",
    ("429x2", "before"): "closed-stream error after receiving 200, 5/5 per JDK; unlike the PR",
    ("429x2", "after"): "succeeds, 5/5 per JDK",
    ("truncate1", "before"): "fails, 5/5 per JDK",
    ("truncate1", "after"): "fails without retry, 5/5 per JDK; earlier JDK 11 hang not reproduced",
    ("wrapper429s", "before"): "five attempts; main class not found, 5/5 per JDK",
    ("wrapper429s", "after"): "fourth attempt succeeds, 5/5 per JDK",
    ("429x2nobody", "before"): "- (not in Table 1)",
    ("429x2nobody", "after"): "- (not in Table 1)"}
ARTICLE_B = {
    "dev-hook-jdk8": "(text) 17/20 failures on unchanged dev with JDK 8",
    "dev-hook-jdk11": "(text) 19/20 with JDK 11",
    "patch-hook-jdk8": "(text) The patch failed 0/20 per JDK under different stalls",
    "patch-hook-jdk11": "(text) The patch failed 0/20 per JDK under different stalls",
    "dev-nohook-contention-jdk8": "(text) unhooked dev passed 50/50 under CPU contention",
    "dev-nohook-contention-jdk11": "(text) unhooked dev passed 50/50 under CPU contention"}
ARTICLE_C = {
    "flink-before": "teardown threw, containers left, 5/5; next job timed out at 150 s, 3/5",
    "flink-after": "teardown completed, containers removed, next job exited 0, 5/5",
    "spark-before": "Spark: teardown threw, master left, next job exited 0, 5/5",
    "spark-after": "Spark: teardown completed, master removed, next job exited 0, 5/5"}


def fmt_list(xs):
    return ",".join(str(x) for x in xs)


def a_new(c):
    s = f"{c['pass']} PASS / {c['fail']} FAIL; primary-path requests per run: {fmt_list(c['primary_attempts'])}"
    if c["fault"] == "wrapper429s":
        offs = [o[-1] if o else None for o in c["wrapper_jar_offsets_s"]]
        s += (f"; wrapper-jar requests per run: {fmt_list(c['wrapper_jar_attempts'])}, last at "
              f"{min(offs):.1f}-{max(offs):.1f} s")
    if c["closed_stream_error"]:
        s += f"; `Attempted read from closed stream` in {c['closed_stream_error']}/{c['runs']}"
    if c.get("checksum_validation_failed"):
        s += f"; checksum-triggered re-download in {c['checksum_validation_failed']}/{c['runs']}"
    if c["main_class_not_found"]:
        s += f"; main class not found in {c['main_class_not_found']}/{c['runs']}"
    if c["timed_out"]:
        s += f"; timed out {c['timed_out']}"
    w = c["wall_seconds_min_median_max"]
    return s + f"; wall {w[0]:.1f}/{w[1]:.1f}/{w[2]:.1f} s (min/median/max)"


def a_old(old, cell):
    for c in old.get("cells", []):
        if c.get("cell") == cell and not c.get("invalid"):
            s = f"{c['outcome'].upper()}; primary-path requests: {c['junit_pom_4_13_2_attempts']}"
            if c.get("wrapper_jar_attempts") is not None:
                t = c.get("wrapper_jar_attempt_times_s") or []
                s += f"; wrapper-jar requests {c['wrapper_jar_attempts']}"
                if t:
                    s += f", last at {t[-1] - t[0]:.1f} s"
            return s
    return "not run"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old")
    a = ap.parse_args()
    new = json.load(open(os.path.join(B, "results.json")))
    old = json.load(open(a.old)) if a.old else {}

    print("#### Part A (PR 12468; Table 1 rows 1-5)\n")
    print("| Row | Fault | Config | JDK | Article (Table 1, 25 Oct 2026 revision) | 2026-10-25 (n=1) | 2026-10-26 (n per cell as listed) |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for cell, c in new["partA"]["cells"].items():
        print(f"| {ROW[c['fault']]} | {FAULT[c['fault']]} | {c['config']} | {c['jdk']} | "
              f"{ARTICLE_A[(c['fault'], c['config'])]} | {a_old(old, cell)} | {a_new(c)} |")

    print("\n#### Part B (PR 12472)\n")
    pr = {"dev-hook-jdk8": "15/20 failed", "dev-hook-jdk11": "7/20 failed", "patch-hook-jdk8": "0/20 failed",
          "patch-hook-jdk11": "0/20 failed", "dev-nohook-contention-jdk8": "0/50 failed (50/50 passed)",
          "dev-nohook-contention-jdk11": "0/50 failed (50/50 passed)"}
    oldb = {c["cell"]: c for c in old.get("cells", []) if c.get("part") == "B" and "iterations" in c}
    print("| Cell | Article (25 Oct 2026 revision) | PR 12472 | 2026-10-25 | 2026-10-26 |")
    print("| --- | --- | --- | --- | --- |")
    for cell, c in new["partB"]["cells"].items():
        if "lead" in cell:
            continue
        o = oldb.get(cell)
        n = "; ".join(f"{f}/{i} failed" for f, i in zip(c["per_loop_failed"], c["iterations_per_loop"]))
        art = ARTICLE_B.get(cell, "-")
        print(f"| {cell} | {art} | {pr.get(cell, '-')} | {o['failed']}/{o['iterations']} failed |"
              f" {n} |" if o else f"| {cell} | {art} | {pr.get(cell, '-')} | not run | {n} |")
    print("\n#### Part B sensitivity sweep (stall placed at <= N ms before `idleDeadlineMs`)\n")
    print("| N | JDK 8, 2026-10-25 | JDK 8, 2026-10-26 | JDK 11, 2026-10-25 | JDK 11, 2026-10-26 |")
    print("| --- | --- | --- | --- | --- |")
    for lead in (35, 45, 55, 65):
        row = [str(lead) + (" (primary reading)" if lead == 35 else "")]
        for jdk in ("jdk8", "jdk11"):
            cell = f"dev-hook-jdk{jdk[3:]}" if lead == 35 else f"dev-hook-lead{lead}-{jdk}"
            o = oldb.get(cell)
            c = new["partB"]["cells"].get(cell)
            row.append(f"{o['failed']}/{o['iterations']}" if o else "not run")
            row.append("; ".join(f"{f}/{i}" for f, i in zip(c["per_loop_failed"], c["iterations_per_loop"]))
                       if c else "not run")
        print("| " + " | ".join(row) + " |")
    print("\nPooled hook wake position vs failure, 2026-10-26 dev-hook loops:\n")
    print("| Closing poll woke | Iterations | Failed |")
    print("| --- | --- | --- |")
    for k, v in new["partB"]["hook_wake_position_vs_failure_pooled_dev_hook"].items():
        print(f"| {k} | {v['iterations']} | {v['failed']} |")

    print("\n#### Part C (PR 12481; Table 1 rows 6-7)\n")
    oldname = {"flink-before": "flink118TaskManagerKilled-before", "flink-after": "flink118TaskManagerKilled-after",
               "spark-before": "spark3MasterKilled-before", "spark-after": "spark3MasterKilled-after"}
    oldc = {c["cell"]: c for c in old.get("cells", []) if c.get("part") == "C" and "n_runs" in c}
    print("| Cell | Article (Table 1, 25 Oct 2026 revision) | 2026-10-25 (n=5) | 2026-10-26 |")
    print("| --- | --- | --- | --- |")
    for cell, c in new["partC"]["cells"].items():
        o = oldc.get(oldname[cell])
        os_ = (f"teardown threw {o['teardown_threw']}/{o['n_runs']}; next job exit 0 {o['next_job_exit0']}/"
               f"{o['n_runs']}; hung {o['next_job_hung']}/{o['n_runs']}") if o else "not run"
        ab = c["assertions"].get("containers_absent_after_teardown", {"PASS": 0, "FAIL": 0})
        ns = (f"teardown threw {c['teardown_threw']}/{c['runs']}; killed engine's containers absent after "
              f"teardown {ab['PASS']}/{c['runs']}; next job exit 0 {c['next_job_exit_zero']}/{c['runs']}; "
              f"timed out {c['next_job_timed_out']}/{c['runs']}")
        print(f"| {cell} | {ARTICLE_C[cell]} | {os_} | {ns} |")
    print("\n#### Part C assertions (PASS/FAIL counts per cell)\n")
    names = []
    for c in new["partC"]["cells"].values():
        for n in c["assertions"]:
            if n not in names:
                names.append(n)
    cells = list(new["partC"]["cells"])
    print("| Assertion | " + " | ".join(cells) + " |")
    print("| --- |" + " --- |" * len(cells))
    for n in names:
        row = []
        for cell in cells:
            s = new["partC"]["cells"][cell]["assertions"].get(n)
            row.append(f"{s['PASS']} PASS / {s['FAIL']} FAIL" if s else "-")
        print(f"| {n} | " + " | ".join(row) + " |")
    print("\nCell-level checks (run by `part_c.sh`, now `harness/historical-part-c/part_c.sh`, after the JVM exited):\n")
    print("| Cell | Check | Result | Observed |")
    print("| --- | --- | --- | --- |")
    for cell, c in new["partC"]["cells"].items():
        for k in c["cell_checks"]:
            print(f"| {cell} | {k['name']} | {k['result']} | {k['observed']} |")


if __name__ == "__main__":
    main()
