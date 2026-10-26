#!/usr/bin/env python3
"""Validate the recorded runs and regenerate results.json from logs/part{A,B,C}/runs.jsonl.

Every value comes from a run record written by part_a.py / part_b.sh / part_c.sh, which in turn
parse the run's own log. part_c.sh and parse_part_c.py are in harness/historical-part-c/: replay.sh
no longer runs Part C, and the recorded Part C runs are validated here from their retained logs. All paths are relative to the bundle root. The sha256 of every file
under logs/ (and of every harness file) is recorded. Run: python3 harness/make_results.py

Validation (revision 2026-10-25). The requested matrix is read from the invocation records
logs/setup/setup-part<P>-*.txt (first line: "replay.sh --part P runs=N prepare_only=0 cells=...").
"--part all" requests Parts A and B (since the fourth revision, 2026-10-25, replay.sh does not run
Part C and writes no invocation record for --part C).
For every requested cell the run records and the logs they name are checked:
  - a missing or unparsable runs.jsonl, run log or server log is a hard error;
  - a record that disagrees with a re-parse of its log is a hard error;
  - a cell with fewer recorded or valid runs than requested fails, with the counts stated;
  - Part A: a run is valid if the mirror was reached (the driver's rule), the requested fault was
    delivered first (the first request for the fault target got the fault) and the Maven log
    has its trailer; a repetition number may occur only once among valid runs;
  - Part B: a loop is valid if its JVM exited 0, it recorded exactly the requested iterations
    (ITER 1..n), each hooked dev iteration logged its stall, and a contention loop logged its
    busy loops;
  - Part C: see harness/historical-part-c/parse_part_c.py (requested runs, complete assertion sets, harness
    validity checks, cell-level checks).
On any error the errors are listed on stderr, results.json is NOT written, and the exit status
is 1. Each cell in results.json carries runs_requested, runs_recorded and runs_valid; the
summaries are computed over the valid runs.
"""
import collections
import glob
import hashlib
import json
import os
import re
import sys
import time

B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(B, "harness", "historical-part-c"))
sys.dont_write_bytecode = True
import parse_part_c  # noqa: E402

DEFAULT_RUNS = {"A": 5, "B": 1, "C": 5}  # replay.sh defaults when --runs is not given
FAULTS = ["503x2", "reset4", "429x2", "truncate1", "wrapper429s", "429x2nobody"]
CELLS = {
    "A": [f"{j}_{f}_{c}" for j in ("jdk8", "jdk11") for f in FAULTS for c in ("before", "after")],
    "B": ["dev-hook-jdk8", "dev-hook-jdk11", "patch-hook-jdk8", "patch-hook-jdk11",
          "dev-hook-lead45-jdk8", "dev-hook-lead45-jdk11", "dev-hook-lead55-jdk8",
          "dev-hook-lead55-jdk11", "dev-hook-lead65-jdk8", "dev-hook-lead65-jdk11",
          "dev-nohook-contention-jdk8", "dev-nohook-contention-jdk11"],
    "C": ["flink-before", "flink-after", "spark-before", "spark-after"],
}
# first action the fault mirror must log for the fault target (Part A fault delivery)
FIRST_ACTION = {"503x2": "503", "reset4": "reset", "429x2": "429", "truncate1": "truncate",
                "429x2nobody": "429nobody", "wrapper429s": "429"}
PRIMARY = "junit/junit/4.13.2/junit-4.13.2.pom"

# Files changed after the recorded runs. sha256_as_run identifies the version the runs (or, for
# the aggregation scripts, the published records) were produced with.
MOVE = ("2026-10-25 (fourth revision): moved from {old} to {new} with its content unchanged (same "
        "sha256); replay.sh no longer runs Part C. Kept for inspection, not for execution; see "
        "harness/historical-part-c/README.md.")
AS_RUN = {
    "harness/historical-part-c/part_c.sh": {
        "path_as_run": "harness/part_c.sh",
        "sha256_as_run": "a75658e64990ce934935601d2c3f380003e049f84bd80d52a3243e9844835cdb",
        "revised_after_runs":
            "2026-10-25 (first revision): cleanup scoped to containers that appeared during the cell. "
            "2026-10-25 (second revision): refuses to start when /tmp/seatunnel_mnt exists. "
            "2026-10-25 (third revision): refuses to start a cell while any container of the Flink, Spark "
            "or Zeta images exists; removes a leftover only if it did not exist before the cell, was created "
            "after the cell start, runs the cell's engine image and carries the cell JVM's Testcontainers "
            "session label, logging every container considered; a cell fails and the script stops when a "
            "cell-level check fails, including /tmp/seatunnel_mnt present after the cell. The executed runs "
            "used the as-run version; its cleanup loop wrote no logs/partC/*.cleanup.txt file, i.e. it "
            "removed nothing (no engine container remained after any cell). "
            + MOVE.format(old="harness/part_c.sh", new="harness/historical-part-c/part_c.sh")},
    "harness/historical-part-c/java/ReplayKillTeardownTest.java": {
        "path_as_run": "harness/java/ReplayKillTeardownTest.java",
        "sha256_as_run": "e0049c6c63c15d6fa037ab6b57261139c54fdd9145b29365e0e2dfe5867be259",
        "revised_after_runs":
            "2026-10-25: a failed pre_run_no_engine_containers check aborts the cell (JVM exit 3) instead of "
            "being recorded and continued; prints the Testcontainers session id. The executed runs used the "
            "as-run version (its sha256 is in every Part C cell log header); the check passed in all 20 runs. "
            + MOVE.format(old="harness/java/ReplayKillTeardownTest.java",
                          new="harness/historical-part-c/java/ReplayKillTeardownTest.java")},
    "harness/historical-part-c/parse_part_c.py": {
        "path_as_run": "harness/parse_part_c.py",
        "sha256_as_run": "bdad4ea98f03da6f6321d2237d3d0e5f9c178064604190a8e38fda5e5568802d",
        "revised_after_runs":
            "2026-10-25: validation added (missing or unparsable log, fewer runs than requested, missing "
            "assertions, failed validity checks make the exit status 1); record format unchanged. Re-parsing "
            "the four recorded cell logs with this version reproduces logs/partC/runs.jsonl byte for byte. "
            + MOVE.format(old="harness/parse_part_c.py", new="harness/historical-part-c/parse_part_c.py")
            + " It only reads logs; make_results.py imports it from there to validate the recorded Part C runs."},
    "harness/make_results.py": {
        "sha256_as_run": "0176e7b397d565bf75e5b7fcde44bf6b1872512032c303e29ce5513d8f9527b8",
        "revised_after_runs":
            "2026-10-25 (third revision): fail-closed validation of the requested matrix and per-cell runs_requested, "
            "runs_recorded, runs_valid; as-run hashes kept here. Re-running it over the recorded logs left "
            "every count and summary unchanged. "
            "2026-10-25 (fourth revision): imports parse_part_c from harness/historical-part-c; --part all "
            "requests Parts A and B only; harness entries of moved files carry path_as_run. Re-running it "
            "over the recorded logs left every count, summary and log hash unchanged."},
    "replay.sh": {
        "sha256_as_run": "6e85b14156590e4dc5217668afd3287f5829e93c5aa9876c2973f31195ca0d0b",
        "revised_after_runs":
            "2026-10-25: --runs must be a positive integer; a failed validation is reported and the exit "
            "status is 1. sha256_as_run is the version published with the runs (interpretation 26: the "
            "maven-version block was added after Parts A and C had started). "
            "2026-10-25 (fourth revision): Part C is no longer run. --part C prints why and exits 0 before "
            "creating, cloning, building or contacting anything; --part all prints the same reason and runs "
            "Parts A and B only. The Part C preparation (image pulls, e2e build) and the Docker lines of the "
            "toolchain record were removed."},
    "harness/historical-part-c/selftest_part_c_guards.sh": {
        "path_as_run": "harness/selftest_part_c_guards.sh",
        "revised_after_runs":
            "2026-10-25 (fourth revision): moved from harness/selftest_part_c_guards.sh with its content "
            "unchanged (same sha256). Written after the runs (third revision) and executed there on "
            "2026-10-25 at its old path; it creates and removes the host path /tmp/seatunnel_mnt. Kept for "
            "inspection, not for execution."},
    "harness/tables.py": {
        "sha256_as_run": "1e4db5170a6a1984fec5799644e854af43ebc7c4cb7294aee3bcc14691e97bb2",
        "revised_after_runs":
            "2026-10-25 (fourth revision): the Article column now quotes Table 1 and the stall counts of the "
            "article revision of 25 October 2026 that cites these records at commit fe561f6; the Part B "
            "table gains that column. sha256_as_run is the version published with the runs, which quoted an "
            "earlier article text. Data columns unchanged."},
}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def files_under(d):
    out = []
    for root, dirs, files in os.walk(os.path.join(B, d)):
        dirs.sort()
        dirs[:] = [x for x in dirs if x != "__pycache__"]
        for f in sorted(files):
            if f == ".DS_Store":
                continue
            p = os.path.join(root, f)
            out.append({"path": os.path.relpath(p, B), "bytes": os.path.getsize(p), "sha256": sha(p)})
    return out


class Problems(list):
    def add(self, msg):
        self.append(msg)


def load(part, problems):
    p = os.path.join(B, "logs", part, "runs.jsonl")
    if not os.path.exists(p):
        return None
    out = []
    for i, line in enumerate(open(p, errors="replace"), 1):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            problems.add(f"logs/{part}/runs.jsonl line {i}: not valid JSON")
    return out


def requested(problems):
    """cell -> requested runs (A: max, B and C: sum over invocations), per part; plus sources."""
    req = {p: collections.OrderedDict() for p in "ABC"}
    sources = []
    for f in sorted(glob.glob(os.path.join(B, "logs", "setup", "setup-part*-*.txt"))):
        first = open(f, errors="replace").readline()
        m = re.match(r"# \S+ replay\.sh --part (A|B|C|all) runs=(\S+) prepare_only=(\d) cells=(.*) work=\S*\s*$", first)
        if not m:
            problems.add(f"{os.path.relpath(f, B)}: invocation line not parsable")
            continue
        part, runs, prep, cells = m.groups()
        if prep != "0":
            continue
        sources.append(os.path.relpath(f, B))
        for p in ("AB" if part == "all" else part):
            if runs == "default":
                n = DEFAULT_RUNS[p]
            elif runs.isdigit() and int(runs) > 0:
                n = int(runs)
            else:
                problems.add(f"{os.path.relpath(f, B)}: runs={runs} is not a positive integer")
                continue
            named = cells.split() if cells != "all" else CELLS[p]
            for c in [c for c in CELLS[p] if c in named]:
                req[p][c] = max(req[p].get(c, 0), n) if p == "A" else req[p].get(c, 0) + n
    return req, sources


def server_actions(path):
    reqs = []
    for i, line in enumerate(open(path, errors="replace"), 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except ValueError:
            raise ValueError(f"line {i} is not valid JSON")
        if "path" in r:
            reqs.append(r)
    prim = [r["action"] for r in reqs if r.get("target") and r["path"].split("/maven2/", 1)[-1] == PRIMARY]
    wrapper = [r["action"] for r in reqs if "/maven-wrapper-" in r["path"] and r["path"].endswith(".jar")]
    return prim, wrapper, len(reqs)


def validate_a(runs, req, problems):
    """Return (valid runs, per-cell counts)."""
    counts = {c: {"runs_requested": n, "runs_recorded": 0, "runs_valid": 0, "invalid_runs": []} for c, n in req.items()}
    valid, seen = [], set()
    for r in runs:
        c = r.get("cell")
        if c not in counts:
            problems.add(f"partA: record {r.get('run_id')} belongs to cell {c!r}, which was not requested")
            continue
        counts[c]["runs_recorded"] += 1
        why = []
        mvn, srv = os.path.join(B, r["mvn_log"]), os.path.join(B, r["server_log"])
        if not os.path.isfile(mvn):
            problems.add(f"partA {r['run_id']}: Maven log {r['mvn_log']} missing")
            why.append("mvn_log_missing")
        elif not re.search(r"^# exit=\S+ timed_out=\S+ wall_seconds=", open(mvn, errors="replace").read(), re.M):
            problems.add(f"partA {r['run_id']}: Maven log {r['mvn_log']} has no trailer (unparsable or truncated)")
            why.append("mvn_log_incomplete")
        if not os.path.isfile(srv):
            problems.add(f"partA {r['run_id']}: server log {r['server_log']} missing")
            why.append("server_log_missing")
        else:
            try:
                prim, wrapper, total = server_actions(srv)
                if (prim, wrapper, total) != (r["primary_actions"], r["wrapper_jar_actions"], r["total_requests"]):
                    problems.add(f"partA {r['run_id']}: record disagrees with {r['server_log']}")
                    why.append("record_log_mismatch")
            except ValueError as e:
                problems.add(f"partA {r['run_id']}: server log {r['server_log']} unparsable ({e})")
                why.append("server_log_unparsable")
        if not r.get("valid", True):
            why.append("mirror_not_reached")
        first = (r["wrapper_jar_actions"] if r["fault"] == "wrapper429s" else r["primary_actions"])[:1]
        if first != [FIRST_ACTION[r["fault"]]]:
            why.append("fault_not_delivered")
        if not why and (c, r["rep"]) in seen:
            problems.add(f"partA {r['run_id']}: repetition {r['rep']} of {c} recorded twice as valid")
            why.append("duplicate_repetition")
        if why:
            counts[c]["invalid_runs"].append({"run_id": r["run_id"], "reasons": why})
            continue
        seen.add((c, r["rep"]))
        counts[c]["runs_valid"] += 1
        valid.append(r)
    return valid, counts


def validate_b(loops, req, problems):
    counts = {c: {"runs_requested": n, "runs_recorded": 0, "runs_valid": 0, "invalid_runs": []} for c, n in req.items()}
    valid = []
    for r in loops:
        c = r.get("cell")
        if c not in counts:
            problems.add(f"partB: loop record {r.get('log')} belongs to cell {c!r}, which was not requested")
            continue
        counts[c]["runs_recorded"] += 1
        why, log = [], os.path.join(B, r["log"])
        if not os.path.isfile(log):
            problems.add(f"partB {r['log']}: loop log missing")
            counts[c]["invalid_runs"].append({"log": r["log"], "reasons": ["log_missing"]})
            continue
        text = open(log, errors="replace").read()
        m = re.search(r"^# JAVA_HOME=.* iterations=(\d+) busy_loops=(\d+)", text, re.M)
        if not re.search(r"^# cell=\S+ loop=\d+ start=", text, re.M) or not m:
            problems.add(f"partB {r['log']}: header missing (unparsable log)")
            why.append("header_missing")
        if not re.search(r"^# exit=-?\d+ wall_seconds=\d+", text, re.M):
            problems.add(f"partB {r['log']}: trailer missing (JVM did not finish or log truncated)")
            why.append("trailer_missing")
        iters = [(int(a), o) for a, o in re.findall(r"^ITER (\d+) (PASS|FAIL|ERROR) ", text, re.M)]
        hooks = len(re.findall(r"REPLAY-HOOK stall45 at deadline-?\d+ms, woke at deadline-?\d+ms", text))
        n_req = int(m.group(1)) if m else None
        if (len(iters), sum(o != "PASS" for _, o in iters)) != (r["iterations"], r["failed"]):
            problems.add(f"partB {r['log']}: record disagrees with the log")
            why.append("record_log_mismatch")
        if n_req is None or [i for i, _ in iters] != list(range(1, n_req + 1)):
            why.append(f"iterations_{len(iters)}_of_{n_req}")
        if r["exit_code"] != 0:
            why.append(f"jvm_exit_{r['exit_code']}")
        if r["hook"] == "dev-stall45" and hooks != len(iters):
            why.append(f"stall_logged_in_{hooks}_of_{len(iters)}_iterations")
        if "contention" in c and not re.search(r"^# load_with_busy_loops:", text, re.M):
            why.append("busy_loops_not_logged")
        if why:
            counts[c]["invalid_runs"].append({"log": r["log"], "reasons": why})
            continue
        counts[c]["runs_valid"] += 1
        valid.append(r)
    return valid, counts


def validate_c(runs, req, problems):
    counts = {c: {"runs_requested": n, "runs_recorded": 0, "runs_valid": 0, "logs": []} for c, n in req.items()}
    by_log = collections.defaultdict(list)
    for r in runs:
        if r.get("cell") not in counts:
            problems.add(f"partC: record {r.get('log')} run {r.get('run')} belongs to cell {r.get('cell')!r}, which was not requested")
            continue
        by_log[r["log"]].append(r)
    valid = []
    for c in counts:
        logs = sorted(os.path.relpath(p, B) for p in glob.glob(os.path.join(B, "logs", "partC", c + ".txt"))
                      + glob.glob(os.path.join(B, "logs", "partC", c + "-[0-9]*.txt")))
        logs += [l for l in by_log if by_log[l][0]["cell"] == c and l not in logs]
        if not logs:
            problems.add(f"partC {c}: no cell log (logs/partC/{c}.txt missing)")
        for rel in logs:
            recs, s = parse_part_c.parse(os.path.join(B, rel), c, B)
            problems.extend(f"partC {p}" for p in s["problems"]
                            if "runs valid" not in p and "fewer runs than requested" not in p)
            stored = [{k: v for k, v in r.items() if k != "log_sha256"} for r in by_log.get(rel, [])]
            if recs != stored:
                problems.add(f"partC {rel}: logs/partC/runs.jsonl records disagree with a re-parse of the log")
            counts[c]["logs"].append(rel)
            counts[c]["runs_recorded"] += s["runs_recorded"]
            counts[c]["runs_valid"] += s["runs_valid"]
            if s["runs_valid"] == s["runs_recorded"] and not s["problems"]:
                valid += by_log.get(rel, [])
    return valid, counts


def part_a(runs):
    cells = collections.OrderedDict()
    for r in runs:
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


def part_b(loops, all_loops):
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
        c["incomplete_loops"] = sum(1 for r in all_loops if r["cell"] == name and r["iterations"] != want)
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


def attach(cells, counts, order):
    """Add runs_requested/recorded/valid to each cell summary, in the requested cell order."""
    out = collections.OrderedDict()
    for c in order:
        if c in cells:
            out[c] = cells[c]
        else:
            out[c] = {}
        for k in ("runs_requested", "runs_recorded", "runs_valid"):
            out[c][k] = counts[c][k]
        extra = counts[c].get("invalid_runs")
        if extra:
            out[c]["invalid_runs"] = extra
    return out


def main():
    problems = Problems()
    req, sources = requested(problems)
    logs = files_under("logs")
    shas = {f["path"]: f["sha256"] for f in logs}
    data = {}
    for p, key in (("A", "partA"), ("B", "partB"), ("C", "partC")):
        recs = load(key, problems)
        if recs is None:
            if req[p]:
                problems.add(f"logs/{key}/runs.jsonl missing, but Part {p} was requested by {sources}")
            recs = []
        elif not req[p] and recs:
            problems.add(f"logs/{key}/runs.jsonl has {len(recs)} records but no recorded invocation requested Part {p}")
        data[p] = recs
    a_valid, a_counts = validate_a(data["A"], req["A"], problems)
    b_valid, b_counts = validate_b(data["B"], req["B"], problems)
    c_valid, c_counts = validate_c(data["C"], req["C"], problems)
    for p, counts in (("A", a_counts), ("B", b_counts), ("C", c_counts)):
        for c, k in counts.items():
            if k["runs_recorded"] < k["runs_requested"]:
                problems.add(f"Part {p} cell {c}: fewer runs than requested: {k['runs_recorded']} of {k['runs_requested']} recorded")
            if k["runs_valid"] < k["runs_requested"]:
                problems.add(f"Part {p} cell {c}: {k['runs_valid']} of {k['runs_requested']} requested runs valid")
    if problems:
        print(f"make_results.py: validation FAILED, results.json not written ({len(problems)} problems):", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    for r in data["A"]:
        r["mvn_log_sha256"] = shas.get(r["mvn_log"])
        r["server_log_sha256"] = shas.get(r["server_log"])
    for r in data["B"] + data["C"]:
        r["log_sha256"] = shas.get(r["log"])
    b_cells, b_bins = part_b(b_valid, data["B"])
    harness = files_under("harness") + [
        {"path": "replay.sh", "bytes": os.path.getsize(os.path.join(B, "replay.sh")),
         "sha256": sha(os.path.join(B, "replay.sh"))}]
    for h in harness:
        h.update(AS_RUN.get(h["path"], {}))
    res = {
        "bundle": "replay-2026-10-26",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "note": "Reconstruction runs. Every value below is parsed from a log under logs/; "
                "paths are relative to this file's directory.",
        "validation": {
            "result": "PASS",
            "requested_from": sources,
            "rules": "requested matrix from the recorded invocations; every requested cell has at least "
                     "runs_requested valid runs; every run log exists, parses and agrees with its record; "
                     "summaries are computed over the valid runs (see harness/make_results.py)",
        },
        "revisions": {k: os.environ.get(k) for k in ("REV_A_BEFORE", "REV_A_AFTER", "REV_B_DEV",
                                                       "REV_B_PATCH", "REV_C_BEFORE", "REV_C_AFTER")}
        if os.environ.get("REV_A_BEFORE") else {
            "REV_A_BEFORE": "a1084015eeb390a6c7f53d3ce7391217e427e4d9",
            "REV_A_AFTER": "ae7c919bcb78f03446dbd2b754a2b9882602946a",
            "REV_B_DEV": "deb16a3c3152f0349a587a504dccc997a131a9d7",
            "REV_B_PATCH": "87ed0afe0f783eda1b1f3ac6f0ac9fadedcb4f98",
            "REV_C_BEFORE": "7ba68325cb7ea1bf1a28f56c4f9c20695d221df3",
            "REV_C_AFTER": "0e4cf52896ee3604a8e7899d7736ffd914ee6ce7"},
        "partA": {"cells": attach(part_a(a_valid), a_counts, req["A"]), "runs": data["A"]},
        "partB": {"cells": attach(b_cells, b_counts, req["B"]), "hook_wake_position_vs_failure_pooled_dev_hook": b_bins,
                  "loops": data["B"]},
        "partC": {"cells": attach(part_c(c_valid), c_counts, req["C"]), "runs": data["C"]},
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
    print(f"results.json: validation PASS; A {len(a_valid)} valid runs, B {len(b_valid)} valid loops, "
          f"C {len(c_valid)} valid runs, {len(logs)} log files hashed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
