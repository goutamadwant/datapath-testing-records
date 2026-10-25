"""Build results.json from queries/, logs/measure/ and logs/generation/, and print the tables."""
import hashlib
import json
import math
import pathlib
import statistics

HERE = pathlib.Path(__file__).resolve().parent.parent
STALL_MS = 1000.0
TIMEOUT_MS = 20000.0
BUILDS = ("before", "after")


def jl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def p95(xs):
    s = sorted(xs)
    return s[max(0, math.ceil(0.95 * len(s)) - 1)]


def dist(xs):
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "median_ms": round(statistics.median(xs), 3), "p95_ms": round(p95(xs), 3),
            "max_ms": round(max(xs), 3), "over_1s": sum(x > STALL_MS for x in xs)}


def bucket(n):
    return None if n is None else ("<=20" if n <= 20 else "21-50" if n <= 50 else ">50")


def outcome(runs):
    """runs: list of run records for one (query, build)."""
    st = [r["status"] for r in runs]
    if "timeout" in st:
        return {"status": "timeout", "time_ms": TIMEOUT_MS, "reps": len(runs)}
    if "crash" in st:
        return {"status": "crash", "reps": len(runs)}
    if "error" in st:
        errs = sorted({r.get("error", "") for r in runs if r["status"] == "error"})
        return {"status": "error", "error": errs[0][:500], "stage": runs[0].get("stage"), "reps": len(runs)}
    tot = [r["total_ms"] for r in runs]
    return {"status": "ok", "time_ms": statistics.median(tot), "reps_ms": tot,
            "logical_ms_median": statistics.median(r["logical_ms"] for r in runs),
            "physical_ms_median": statistics.median(r["physical_ms"] for r in runs), "reps": len(runs)}


def main():
    controls = jl(HERE / "harness/controls.jsonl")
    queries = []
    for f in sorted((HERE / "queries").glob("*.jsonl")):
        queries += jl(f)
    cls = {c["query_id"]: c for c in jl(HERE / "logs/measure/classify.jsonl")}
    runs = {}
    for r in jl(HERE / "logs/measure/runs.jsonl"):
        runs.setdefault((r["query_id"], r["build"]), []).append(r)
    gen_summary = json.loads((HERE / "logs/generation/summary.json").read_text())

    def record(item):
        c = cls[item["query_id"]]
        calls = c["regexp_like_calls"]
        lit = [k for k in calls if k["pattern_is_literal"]]
        rec = {"query_id": item["query_id"], "sql": item["sql"],
               "uses_regexp_like": bool(calls), "regexp_like_calls": len(calls),
               "all_literal_call": any(k["all_literal"] for k in calls),
               "literal_patterns": [k["pattern"] for k in lit],
               "max_pattern_len": max((len(k["pattern"].encode()) for k in lit), default=None),
               "nested_counted": any(k.get("classification", {}).get("nested_counted") for k in lit),
               "max_counted_depth": max((k.get("classification", {}).get("counted_depth", 0) for k in lit), default=0),
               "pattern_too_big_256k": any(k.get("classification", {}).get("compile_256k") == "too_big" for k in lit),
               "pattern_too_big_10m": any(k.get("classification", {}).get("compile_10m") == "too_big" for k in lit),
               "max_compile_10m_ms": max((k.get("classification", {}).get("compile_10m_ms", 0) for k in lit), default=None),
               "other_regex": {k: v for k, v in c["other_regex"].items() if v}}
        rec["pattern_len_bucket"] = bucket(rec["max_pattern_len"])
        for b in BUILDS:
            rec[b] = outcome(runs.get((item["query_id"], b), []))
        return rec

    ctl = [dict(record(c), kind=c["kind"], note=c["note"]) for c in controls]
    recs = [dict(record(q), generator=q["generator"], theme_index=q["theme_index"]) for q in queries]

    def summarise(rs):
        plannable = [r for r in rs if all(r[b]["status"] in ("ok", "timeout") for b in BUILDS)]
        s = {"queries": len(rs),
             "uses_regexp_like": sum(r["uses_regexp_like"] for r in rs),
             "all_literal_regexp_like": sum(r["all_literal_call"] for r in rs),
             "nested_counted": sum(r["nested_counted"] for r in rs),
             "pattern_too_big_256k": sum(r["pattern_too_big_256k"] for r in rs),
             "pattern_too_big_10m": sum(r["pattern_too_big_10m"] for r in rs),
             "status_before": {}, "status_after": {},
             "plannable_both": len(plannable)}
        for b in BUILDS:
            for r in rs:
                s[f"status_{b}"][r[b]["status"]] = s[f"status_{b}"].get(r[b]["status"], 0) + 1
            s[f"timeouts_{b}"] = sum(r[b]["status"] == "timeout" for r in rs)
            s[f"dist_{b}"] = dist([r[b]["time_ms"] for r in plannable])
        s["stall_before"] = sum(r["before"]["status"] == "timeout" or (r["before"].get("time_ms", 0) > STALL_MS) for r in plannable)
        s["stall_after"] = sum(r["after"]["status"] == "timeout" or (r["after"].get("time_ms", 0) > STALL_MS) for r in plannable)
        s["rule_of_three_upper_95"] = round(3 / len(plannable), 4) if plannable and s["stall_before"] == 0 else None
        return s

    groups = {"g1": [r for r in recs if r["generator"] == "g1"],
              "g2": [r for r in recs if r["generator"] == "g2"], "pooled": recs}
    summary = {g: summarise(rs) for g, rs in groups.items()}
    strata = {}
    for name, key in (("nested_counted", lambda r: str(r["nested_counted"])),
                      ("pattern_len_bucket", lambda r: str(r["pattern_len_bucket"])),
                      ("all_literal_regexp_like", lambda r: str(r["all_literal_call"]))):
        vals = sorted({key(r) for r in recs})
        strata[name] = {v: summarise([r for r in recs if key(r) == v]) for v in vals}
    slow = [{k: r[k] for k in ("query_id", "sql", "before", "after", "nested_counted")}
            for r in recs if any(r[b].get("time_ms", 0) > STALL_MS or r[b]["status"] == "timeout" for b in BUILDS)]
    errors_differ = [{k: r[k] for k in ("query_id", "sql", "before", "after")}
                     for r in recs if r["before"]["status"] != r["after"]["status"]]
    nested_list = [{k: r[k] for k in ("query_id", "generator", "theme_index", "literal_patterns", "max_counted_depth",
                                      "all_literal_call", "pattern_too_big_256k", "max_compile_10m_ms")}
                   | {"before_ms": r["before"].get("time_ms"), "after_ms": r["after"].get("time_ms"),
                      "before_status": r["before"]["status"], "after_status": r["after"]["status"]}
                   for r in recs if r["nested_counted"]]
    hashes = {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted((HERE / "logs").rglob("*")) if p.is_file()}
    hashes.update({str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted((HERE / "queries").glob("*.jsonl"))})
    out = {"stall_threshold_ms": STALL_MS, "timeout_ms": TIMEOUT_MS,
           "generation": {k: v for k, v in gen_summary.items() if k != "g1_models_listing"},
           "summary": summary, "strata": strata, "controls": ctl, "slow_queries": slow,
           "status_differs_between_builds": errors_differ, "nested_counted_queries": nested_list,
           "queries": recs, "sha256": hashes}
    exp = HERE / "logs/exploratory/summary.json"
    if exp.exists():
        out["exploratory_not_preregistered"] = {
            "note": "decided after the positive control stayed below 1 s; builds: issuedate = "
                    "b426232b8a13c641a522bba414e932914f3b79f5 (last main commit before issue 22185), "
                    "before, after; median of 3 repetitions in ms",
            "summary": json.loads(exp.read_text())}
    (HERE / "results.json").write_text(json.dumps(out, indent=1))
    print_tables(out)


def fmt(d, k):
    return "-" if d.get("n", 0) == 0 else f"{d[k]:.1f}"


def print_tables(out):
    print("| | G1 | G2 | Pooled |\n|---|---:|---:|---:|")
    S = out["summary"]
    rows = [("Queries extracted", "queries"), ("Using regexp_like", "uses_regexp_like"),
            ("With an all-literal regexp_like call", "all_literal_regexp_like"),
            ("With a nested counted quantifier", "nested_counted"),
            ("Pattern over the 256 KiB planning limit", "pattern_too_big_256k"),
            ("Planned without error at both builds", "plannable_both")]
    for label, k in rows:
        print(f"| {label} | {S['g1'][k]} | {S['g2'][k]} | {S['pooled'][k]} |")
    for b in BUILDS:
        for label, k in (("median ms", "median_ms"), ("p95 ms", "p95_ms"), ("max ms", "max_ms")):
            print(f"| {b}: {label} | " + " | ".join(fmt(S[g][f'dist_{b}'], k) for g in ("g1", "g2", "pooled")) + " |")
        print(f"| {b}: queries over 1 s | " + " | ".join(str(S[g][f'dist_{b}'].get('over_1s', 0)) for g in ("g1", "g2", "pooled")) + " |")
        print(f"| {b}: timeouts (20 s) | " + " | ".join(str(S[g][f'timeouts_{b}']) for g in ("g1", "g2", "pooled")) + " |")
    print()
    print("| Stratum | n | before median / p95 / max ms | after median / p95 / max ms | over 1 s before / after |")
    print("|---|---:|---|---|---|")
    for name, vals in out["strata"].items():
        for v, s in vals.items():
            db, da = s["dist_before"], s["dist_after"]
            print(f"| {name} = {v} | {s['plannable_both']} | {fmt(db,'median_ms')} / {fmt(db,'p95_ms')} / {fmt(db,'max_ms')} | "
                  f"{fmt(da,'median_ms')} / {fmt(da,'p95_ms')} / {fmt(da,'max_ms')} | {db.get('over_1s',0)} / {da.get('over_1s',0)} |")
    print()
    print("| Control | before | after |\n|---|---|---|")
    for c in out["controls"]:
        def cell(o):
            if o["status"] == "ok":
                return f"{o['time_ms']:.1f} ms (reps {', '.join(f'{x:.1f}' for x in o['reps_ms'])})"
            return o["status"] + (": " + o.get("error", "")[:80] if o["status"] == "error" else "")
        print(f"| {c['query_id']} | {cell(c['before'])} | {cell(c['after'])} |")


if __name__ == "__main__":
    main()
