#!/usr/bin/env python3
"""Compare a fresh results.json with the published one, cell by cell (Parts A and B).

usage: python3 replay-clean/compare.py <published results.json> <fresh results.json>
Prints Markdown tables. Part A: pass/fail/timed-out counts and, per run, the attempt counts for the
primary artifact and the wrapper jar (compared as sorted lists: run order is not a property of the
cell), the first-attempt action sequences, and the error-signature counts. Wall times are shown but
not compared. Part B: failed/total iterations per cell. Part C is historical in both files; the script
only checks that its cells are identical.
"""
import json
import sys

pub = json.load(open(sys.argv[1]))
new = json.load(open(sys.argv[2]))


def srt(x):
    return sorted(x, key=lambda v: json.dumps(v))


A_COUNTS = ["runs_valid", "pass", "fail", "timed_out", "closed_stream_error", "main_class_not_found",
            "checksum_validation_failed"]
A_LISTS = ["primary_attempts", "primary_actions", "wrapper_jar_attempts"]

print("## Part A (5 runs per cell)\n")
print("| Cell | Label | Published pass/fail | Fresh pass/fail | Published primary attempts | Fresh primary attempts "
      "| Published wrapper-jar attempts | Fresh wrapper-jar attempts | Published wall s (min/med/max) "
      "| Fresh wall s (min/med/max) | Match |")
print("|" + " --- |" * 11)
a_same = a_total = 0
diffs = []
for cell, p in pub["partA"]["cells"].items():
    n = new["partA"]["cells"].get(cell)
    a_total += 1
    if n is None:
        print(f"| {cell} | {p.get('label', '')} | {p['pass']}/{p['fail']} | missing | | | | | | | NO |")
        diffs.append(f"{cell}: missing in the fresh results")
        continue
    bad = [k for k in A_COUNTS if p.get(k) != n.get(k)]
    bad += [k for k in A_LISTS if srt(p.get(k, [])) != srt(n.get(k, []))]
    same = not bad
    a_same += same
    if bad:
        diffs.append(f"{cell}: " + "; ".join(f"{k} published {p.get(k)} fresh {n.get(k)}" for k in bad))
    print(f"| {cell} | {p.get('label', '')} | {p['pass']}/{p['fail']} | {n['pass']}/{n['fail']} "
          f"| {sorted(p['primary_attempts'])} | {sorted(n['primary_attempts'])} "
          f"| {sorted(p['wrapper_jar_attempts'])} | {sorted(n['wrapper_jar_attempts'])} "
          f"| {p['wall_seconds_min_median_max']} | {n['wall_seconds_min_median_max']} "
          f"| {'yes' if same else 'NO: ' + ', '.join(bad)} |")
print(f"\nPart A: {a_same} of {a_total} cells identical in every compared field.\n")
if diffs:
    print("Part A differences:\n")
    for d in diffs:
        print(f"- {d}")
    print()

print("## Part B (1 loop per cell)\n")
print("| Cell | Hook | Published failed/iterations | Fresh failed/iterations | Fresh loops valid | Same count |")
print("| --- | --- | --- | --- | --- | --- |")
b_same = b_total = 0
pb = pub["partB"]["cells"]
nb = new.get("partB", {}).get("cells", {}) if isinstance(new.get("partB"), dict) else {}
for cell, p in pb.items():
    n = nb.get(cell)
    b_total += 1
    if not n:
        print(f"| {cell} | {p['hook']} | {p['failed_total']}/{p['iterations_total']} | not run | | |")
        continue
    same = (p["failed_total"], p["iterations_total"]) == (n["failed_total"], n["iterations_total"])
    b_same += same
    print(f"| {cell} | {p['hook']} | {p['failed_total']}/{p['iterations_total']} "
          f"| {n['failed_total']}/{n['iterations_total']} | {n.get('runs_valid')}/{n.get('runs_requested')} "
          f"| {'yes' if same else 'no'} |")
print(f"\nPart B: {b_same} of {b_total} cells with the same failed count.\n")

pc, nc = pub.get("partC"), new.get("partC")
print(f"Part C (historical records, not re-run): cells identical in both files: {pc == nc}")
