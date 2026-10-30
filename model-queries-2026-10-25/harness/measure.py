"""Classify regex patterns and time planning of every query and control at both builds.

Reads harness/controls.jsonl and queries/*.jsonl. Writes:
  logs/<MEASURE_SET>/classify.jsonl  scanner output plus pattern classification
  logs/<MEASURE_SET>/runs.jsonl      one line per (query, build, repetition) process run
MEASURE_SET defaults to measure.
Each repetition is a separate process with a 20 s wall-clock timeout. Repetition-major order;
the build order alternates by item index. Fresh mode refuses existing records.
MEASURE_RESUME=1 verifies manifest.json before reusing recorded runs and classification.
"""
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sqlscan import scan  # noqa: E402
from measurement_sets import check_fresh, paths, prepare_manifest, save_manifest  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent.parent
WORK = pathlib.Path(os.environ.get("RUN_WORK", HERE / "work")).resolve()
BIN = {b: WORK / "target/release" / f"plan_time_{b}" for b in ("before", "after")}
TIMEOUT_S = 20.0
REPS = 3
OUT, _, _ = paths(HERE)


def now():
    return dt.datetime.now().astimezone().isoformat(timespec="milliseconds")


def load_items():
    items = []
    for line in (HERE / "harness/controls.jsonl").read_text().splitlines():
        items.append(json.loads(line))
    for f in sorted((HERE / "queries").glob("*.jsonl")):
        for line in f.read_text().splitlines():
            if line.strip():
                items.append(json.loads(line))
    return items


def classify_pattern(pattern, flags):
    p = subprocess.run([str(BIN["after"]), "classify"], input=json.dumps({"pattern": pattern, "flags": flags}),
                       capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        return {"classify_error": p.stderr[-2000:]}
    return json.loads(p.stdout)


def classify_all(items):
    path = OUT / "classify.jsonl"
    if path.exists():
        return
    cache = {}
    with open(path, "w") as fh:
        for it in items:
            sc = scan(it["sql"])
            for call in sc["regexp_like_calls"]:
                if call["pattern_is_literal"]:
                    key = (call["pattern"], call["flags"])
                    if key not in cache:
                        cache[key] = classify_pattern(*key)
                    call["classification"] = cache[key]
            fh.write(json.dumps({"query_id": it["query_id"], **sc}) + "\n")


def run_one(build, sql):
    t = time.monotonic()
    try:
        p = subprocess.run([str(BIN[build]), "plan"], input=sql, capture_output=True, text=True,
                           timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "process_wall_s": round(time.monotonic() - t, 3)}
    rec = {"process_wall_s": round(time.monotonic() - t, 3), "returncode": p.returncode}
    try:
        rec.update(json.loads(p.stdout.strip().splitlines()[-1]))
    except (json.JSONDecodeError, IndexError):
        rec.update(status="crash", stdout=p.stdout[-2000:])
    if p.stderr:
        rec["stderr"] = p.stderr[-2000:]
    return rec


def main():
    started = now()
    resume = os.environ.get("MEASURE_RESUME") == "1"
    check_fresh(OUT, resume)
    items = load_items()
    manifest = prepare_manifest(HERE, OUT, BIN, len(items), started, resume)
    executed = reused = 0
    try:
        classify_all(items)
        runs_path = OUT / "runs.jsonl"
        done = set()
        if runs_path.exists():
            for line in runs_path.read_text().splitlines():
                r = json.loads(line)
                done.add((r["query_id"], r["build"], r["rep"]))
        with open(runs_path, "a") as fh:
            for rep in range(1, REPS + 1):
                for i, it in enumerate(items):
                    order = ("before", "after") if i % 2 == 0 else ("after", "before")
                    for b in order:
                        if (it["query_id"], b, rep) in done:
                            reused += 1
                            continue
                        run_started = now()
                        rec = {"query_id": it["query_id"], "build": b, "rep": rep,
                               "started": run_started, **run_one(b, it["sql"])}
                        fh.write(json.dumps(rec) + "\n")
                        fh.flush()
                        executed += 1
                print(f"{now()} repetition {rep} done ({len(items)} items)", flush=True)
    finally:
        manifest["invocations"].append({"start": started, "end": now(),
                                        "executed": executed, "reused": reused})
        save_manifest(OUT, manifest)
        print(f"executed {executed} process runs, reused {reused} recorded runs", flush=True)


if __name__ == "__main__":
    main()
