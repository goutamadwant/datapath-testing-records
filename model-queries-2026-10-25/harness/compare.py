"""Compare historical results with a named measurement set."""
import json
import pathlib
import sys

from measurement_sets import (
    BUILDS, REPS, FROZEN_COUNTS, FROZEN_SETS, paths, set_name,
)

HERE = pathlib.Path(__file__).resolve().parent.parent


def stalled(result, outcome):
    return (outcome["status"] == "timeout"
            or outcome.get("time_ms", 0) > result["stall_threshold_ms"])


def categorical_outcomes(result):
    """Compare discrete outcomes without requiring equal elapsed times."""
    def summaries(groups):
        return {g: {k: v for k, v in s.items() if not k.startswith("dist_")}
                for g, s in groups.items()}

    def statuses(records):
        return {r["query_id"]: {b: (r[b]["status"], stalled(result, r[b])) for b in BUILDS}
                for r in records}

    facts = ("sql", "generator", "theme_index", "uses_regexp_like", "regexp_like_calls",
             "all_literal_call", "literal_patterns", "max_pattern_len", "nested_counted",
             "max_counted_depth", "pattern_too_big_256k", "pattern_too_big_10m")
    return {
        "Query counts and pattern classifications": {
            r["query_id"]: {k: r[k] for k in facts} for r in result["queries"]},
        "Per-generator and pooled counts, statuses and stalls": summaries(result["summary"]),
        "Per-query statuses and stalls": statuses(result["queries"]),
        "Stratum counts, statuses and stalls": {k: summaries(v) for k, v in result["strata"].items()},
        "Control statuses and stalls": statuses(result["controls"]),
        "Stall and timeout thresholds": (result["stall_threshold_ms"], result["timeout_ms"]),
    }


def completeness_problems(result, frozen=False):
    # Historical results predate explicit counts. Fresh analyses declare all counts.
    problems = []
    queries = result.get("queries", [])
    controls = result.get("controls", [])
    validation = result.get("validation", {})
    counts = (FROZEN_COUNTS if frozen or "query_count" not in validation else
              {key: validation.get(key) for key in FROZEN_COUNTS})
    for records, key, label in ((queries, "query_count", "query"),
                                (controls, "control_count", "control")):
        if len(records) != counts[key]:
            problems.append(f"{label} count is {len(records)}; expected {counts[key]}")
    records = queries + controls
    if len({r["query_id"] for r in records}) != counts["item_count"]:
        problems.append(f"expected {counts['item_count']} distinct item IDs")
    expected_runs = len(records) * len(BUILDS) * REPS
    if counts["expected_process_runs"] != expected_runs:
        problems.append(f"expected_process_runs is {counts['expected_process_runs']}; expected {expected_runs}")
    if validation.get("result") != "PASS" or validation.get("complete", True) is not True:
        problems.append("measurement set is incomplete or validation did not PASS")
    for field in ("expected_process_runs", "recorded_process_runs"):
        if field in validation and validation[field] != counts["expected_process_runs"]:
            problems.append(f"{field} is {validation[field]}; expected {counts['expected_process_runs']}")
    for field in ("item_count", "query_count", "control_count"):
        if field in validation and validation[field] != counts[field]:
            problems.append(f"{field} is {validation[field]}; expected {counts[field]}")
    if any(r.get(b, {}).get("reps") != REPS for r in records for b in BUILDS):
        problems.append(f"incomplete repetitions; expected {REPS} per item and build")
    return problems


def complete(result):
    return not completeness_problems(result)


def cell(outcome):
    return f"{outcome['time_ms']:.3f}" if outcome["status"] == "ok" else outcome["status"]


def slowest(result, build):
    records = [r for r in result["queries"]
               if all(r[b]["status"] in ("ok", "timeout") for b in BUILDS)]
    if not records:
        return "-"
    r = max(records, key=lambda r: r[build]["time_ms"])
    return f"{r[build]['time_ms']:.3f} ms ({r['query_id']})"


def report(historical, replay, name):
    for filename, result, frozen in (("results.json", historical, True),
                                     (f"results-{name}.json", replay, name in FROZEN_SETS)):
        problems = completeness_problems(result, frozen=frozen)
        if problems:
            raise ValueError(f"{filename}: " + "; ".join(problems))
    old_controls = {c["query_id"]: c for c in historical["controls"]}
    new_controls = {c["query_id"]: c for c in replay["controls"]}
    if len(old_controls) != FROZEN_COUNTS["control_count"] or old_controls.keys() != new_controls.keys():
        raise ValueError("expected the same five controls in both sets")
    lines = [f"# Measurement comparison: measure and {name}", "",
             f"Sources: `results.json` and `results-{name}.json`.", "",
             "Wall-clock values are not expected to be identical across runs or machines. "
             "This comparison reports observed differences only.", "",
             "## Controls", "",
             "Median planning time in ms; unsuccessful controls show their status.", "",
             f"| Control | measure before | measure after | {name} before | {name} after |",
             "|---|---:|---:|---:|---:|"]
    for q, old in old_controls.items():
        new = new_controls[q]
        lines.append(f"| {q} | {cell(old['before'])} | {cell(old['after'])} | "
                     f"{cell(new['before'])} | {cell(new['after'])} |")
    lines += ["", "## Pooled queries", "",
              f"| Outcome | measure | {name} |", "|---|---:|---:|"]
    s0, s1 = (r["summary"]["pooled"] for r in (historical, replay))
    rows = [("Queries extracted", s0["queries"], s1["queries"]),
            ("Queries planned without error at both builds", s0["plannable_both"], s1["plannable_both"])]
    for b in BUILDS:
        rows += [(f"Slowest query {b}", slowest(historical, b), slowest(replay, b)),
                 (f"p95 {b} (ms)", s0[f"dist_{b}"].get("p95_ms", "-"), s1[f"dist_{b}"].get("p95_ms", "-")),
                 (f"Queries over 1 s {b}", s0[f"dist_{b}"].get("over_1s", 0), s1[f"dist_{b}"].get("over_1s", 0))]
    rows.append(("Status differences between builds", len(historical["status_differs_between_builds"]),
                 len(replay["status_differs_between_builds"])))
    lines += [f"| {label} | {old} | {new} |" for label, old, new in rows]
    a, b = categorical_outcomes(historical), categorical_outcomes(replay)
    agree = all(a[k] == b[k] for k in a)
    timings_equal = all(
        historical["summary"][g][f"dist_{build}"] == replay["summary"][g][f"dist_{build}"]
        for g in historical["summary"] for build in BUILDS)
    lines += ["", "## Outcome comparison", "",
              f"Categorical outcomes agree between the sets: **{'yes' if agree else 'no'}**. "
              "Different query inputs represent separate samples; agreement is not expected. "
              "Agreement here requires identical counts, pattern classifications, planning statuses "
              "and stall/timeout outcomes, including controls and strata.", "",
              f"Planning-time distributions (per generator and pooled) are "
              f"**{'identical' if timings_equal else 'different'}**. "
              "Continuous timing outcomes have no equality or tolerance requirement.", "",
              "| Outcome group | Agreement |", "|---|---|"]
    lines += [f"| {k} | {'yes' if a[k] == b[k] else 'no'} |" for k in a]
    return "\n".join(lines) + "\n"


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 harness/compare.py SET")
    try:
        name = set_name(sys.argv[1])
        if name == "measure":
            raise ValueError("SET must name a replay, not measure")
        _, source, _ = paths(HERE, name)
        historical = json.loads((HERE / "results.json").read_text())
        replay = json.loads(source.read_text())
        destination = HERE / f"COMPARISON-{name}.md"
        destination.write_text(report(historical, replay, name))
        print(destination.name)
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise SystemExit(f"compare.py: {e}")


if __name__ == "__main__":
    main()
