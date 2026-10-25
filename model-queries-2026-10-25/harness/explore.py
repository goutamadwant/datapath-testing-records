"""Exploratory, not pre-registered: time the controls and the issue's nesting series at three
commits: the last main commit before issue 22185 was filed (issuedate), before and after.

Writes logs/exploratory/runs.jsonl (one line per process run) and logs/exploratory/summary.json.
Same harness, 3 repetitions, separate process per repetition, 20 s timeout.
"""
import json
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import measure  # noqa: E402

HERE = measure.HERE
BUILDS = ("issuedate", "before", "after")
for b in BUILDS:
    measure.BIN[b] = measure.WORK / "target/release" / f"plan_time_{b}"


def items():
    out = [c for c in map(json.loads, (HERE / "harness/controls.jsonl").read_text().splitlines())
           if c["query_id"] != "control-positive-issue-18-verbatim"]
    for n in (4, 6, 8, 10, 12, 18):
        out.append({"query_id": f"series-literal-{n:02d}",
                    "sql": f"SELECT regexp_like('aaaaa', 'a{'{5}' * n}');"})
    return out


def main():
    out = HERE / "logs/exploratory"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "runs.jsonl"
    if path.exists():
        raise SystemExit(f"{path} exists; refusing to overwrite")
    its = items()
    recs = []
    with open(path, "w") as fh:
        for rep in (1, 2, 3):
            for i, it in enumerate(its):
                order = BUILDS if i % 2 == 0 else tuple(reversed(BUILDS))
                for b in order:
                    rec = {"query_id": it["query_id"], "sql": it["sql"], "build": b, "rep": rep,
                           "started": measure.now(), **measure.run_one(b, it["sql"])}
                    fh.write(json.dumps(rec) + "\n")
                    fh.flush()
                    recs.append(rec)
    summary = {}
    for it in its:
        row = {}
        for b in BUILDS:
            rs = [r for r in recs if r["query_id"] == it["query_id"] and r["build"] == b]
            st = {r["status"] for r in rs}
            if st == {"ok"}:
                tot = [r["total_ms"] for r in rs]
                row[b] = {"median_ms": round(statistics.median(tot), 1), "reps_ms": [round(x, 1) for x in tot]}
            else:
                row[b] = {"status": sorted(st)}
        summary[it["query_id"]] = row
        print(it["query_id"], json.dumps(row))
    (out / "summary.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
