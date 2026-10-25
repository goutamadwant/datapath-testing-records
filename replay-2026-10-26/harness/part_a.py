#!/usr/bin/env python3
"""Part A driver: PR 12468 Maven retry under injected faults (bundle 2026-10-26).

Called by ../replay.sh (which prepares work/partA/warm-repo and exports REPLAY_BUNDLE,
REPLAY_WORK, JAVA8_HOME, JAVA11_HOME, MAVEN_USER_HOME, REV_A_BEFORE, REV_A_AFTER).

Cell = JDK x fault x configuration. before = mvnw from the PR 12468 parent, no .mvn/maven.config;
after = mvnw and .mvn/maven.config from the merge. Every run gets a fresh fault_mirror.py on a
free loopback port, a fresh project directory and an empty local repository, and runs
    ./mvnw -B -s <run>/settings.xml -Dmaven.repo.local=<run>/repo -f pom.xml dependency:resolve
Runs are interleaved: repetition k of every cell runs before repetition k+1 of any cell.
One JSON record per run is appended to logs/partA/runs.jsonl (paths relative to the bundle).

usage: part_a.py --runs N [cell ...]     cell = <jdk8|jdk11>_<fault>_<before|after>
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

BUNDLE = os.environ["REPLAY_BUNDLE"]
WORK = os.environ["REPLAY_WORK"]
HERE = os.path.join(BUNDLE, "harness")
LOGS = os.path.join(BUNDLE, "logs", "partA")
REPO = os.path.join(WORK, "seatunnel")
WARM = os.path.join(WORK, "partA", "warm-repo")
RUNS = os.path.join(WORK, "partA", "runs")
JDKS = {"jdk8": os.environ["JAVA8_HOME"], "jdk11": os.environ["JAVA11_HOME"]}
CONFIGS = {
    "before": (os.environ["REV_A_BEFORE"], ["mvnw", ".mvn/wrapper/maven-wrapper.properties"]),
    "after": (os.environ["REV_A_AFTER"],
              ["mvnw", ".mvn/wrapper/maven-wrapper.properties", ".mvn/maven.config"]),
}
# Table 1 rows 1-5, then the empty-body 429 variant (a separate, labelled cell; not a Table 1 row)
FAULTS = ["503x2", "reset4", "429x2", "truncate1", "wrapper429s", "429x2nobody"]
WRAPPER_JAR = os.path.join(WARM, "org/apache/maven/wrapper/maven-wrapper/3.1.0/maven-wrapper-3.1.0.jar")
PRIMARY = "junit/junit/4.13.2/junit-4.13.2.pom"
TIMEOUT_S = 600


def rel(p):
    return os.path.relpath(p, BUNDLE)


def git_show(rev, path):
    return subprocess.run(["git", "-C", REPO, "show", f"{rev}:{path}"], check=True,
                          capture_output=True).stdout


def prepare(run_dir, config, fault, port):
    proj = os.path.join(run_dir, "proj")
    os.makedirs(os.path.join(proj, ".mvn", "wrapper"))
    rev, files = CONFIGS[config]
    for f in files:
        data = git_show(rev, f)
        if fault == "wrapper429s" and f.endswith("maven-wrapper.properties"):
            # wrapperUrl overrides MVNW_REPOURL in this mvnw, so point it at the local mirror;
            # distributionUrl is unchanged (Maven 3.8.4 is already in MAVEN_USER_HOME).
            lines = []
            for line in data.decode().splitlines():
                if line.startswith("wrapperUrl="):
                    line = (f"wrapperUrl=http://127.0.0.1:{port}/maven2/org/apache/maven/wrapper/"
                            "maven-wrapper/3.1.0/maven-wrapper-3.1.0.jar")
                lines.append(line)
            data = ("\n".join(lines) + "\n").encode()
        with open(os.path.join(proj, f), "wb") as fh:
            fh.write(data)
    os.chmod(os.path.join(proj, "mvnw"), 0o755)
    if fault != "wrapper429s":
        shutil.copy(WRAPPER_JAR, os.path.join(proj, ".mvn", "wrapper", "maven-wrapper.jar"))
    shutil.copy(os.path.join(HERE, "tiny-pom.xml"), os.path.join(proj, "pom.xml"))
    tmpl = open(os.path.join(HERE, "settings-mirror.template.xml")).read()
    settings = os.path.join(run_dir, "settings.xml")
    open(settings, "w").write(tmpl.replace("@PORT@", str(port)))
    repo = os.path.join(run_dir, "repo")
    os.makedirs(repo)
    return proj, settings, repo


def start_server(run_id, fault, slog):
    port_file = os.path.join(RUNS, run_id + ".port")
    if os.path.exists(port_file):
        os.remove(port_file)
    cmd = [sys.executable, "-I", os.path.join(HERE, "fault_mirror.py"), "--root", WARM,
           "--fault", fault, "--log", slog, "--port-file", port_file]
    p = subprocess.Popen(cmd)
    for _ in range(200):
        if os.path.exists(port_file) and open(port_file).read().strip():
            return p, int(open(port_file).read())
        time.sleep(0.05)
    p.kill()
    raise RuntimeError("server did not start")


def summarize(server_log, mvn_out):
    reqs = [json.loads(l) for l in open(server_log) if '"path"' in l]
    junit = {}
    for r in reqs:
        if r["target"]:
            junit.setdefault(r["path"].split("/maven2/", 1)[-1], []).append(
                {"action": r["action"], "t_rel_s": r["t_rel_s"]})
    wrapper = [{"t_rel_s": r["t_rel_s"], "action": r["action"]} for r in reqs
               if "/maven-wrapper-" in r["path"] and r["path"].endswith(".jar")]
    text = open(mvn_out, errors="replace").read()
    prim = junit.get(PRIMARY, [])
    t0 = prim[0]["t_rel_s"] if prim else None
    return {
        "build_success": "BUILD SUCCESS" in text,
        "build_failure": "BUILD FAILURE" in text,
        "main_class_not_found":
            "Could not find or load main class org.apache.maven.wrapper.MavenWrapperMain" in text,
        "closed_stream_error": "Attempted read from closed stream" in text,
        "primary_path": PRIMARY,
        "primary_attempts": len(prim),
        "primary_actions": [a["action"] for a in prim],
        "primary_offsets_s": [round(a["t_rel_s"] - t0, 2) for a in prim] if prim else [],
        "junit_attempts_per_path": {p: [a["action"] for a in v] for p, v in junit.items()},
        "wrapper_jar_attempts": len(wrapper),
        "wrapper_jar_actions": [w["action"] for w in wrapper],
        "wrapper_jar_offsets_s": [round(w["t_rel_s"] - wrapper[0]["t_rel_s"], 2) for w in wrapper],
        "total_requests": len(reqs),
        "error_lines": [l for l in text.splitlines() if l.startswith("[ERROR]")][:4],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("cells", nargs="*")
    a = ap.parse_args()
    os.makedirs(LOGS, exist_ok=True)
    os.makedirs(RUNS, exist_ok=True)
    records = os.path.join(LOGS, "runs.jsonl")
    cells = [f"{j}_{f}_{c}" for j in ("jdk8", "jdk11") for f in FAULTS for c in ("before", "after")]
    if a.cells:
        cells = [c for c in cells if c in a.cells]
    done = {}
    if os.path.exists(records):
        for l in open(records):
            r = json.loads(l)
            if r.get("valid", True):
                done[r["cell"]] = max(done.get(r["cell"], 0), r["rep"])
    order = sum(1 for _ in open(records)) if os.path.exists(records) else 0
    for rep in range(1, a.runs + 1):
        for cell in cells:
            if done.get(cell, 0) >= rep:
                continue
            jdk, fault, config = cell.split("_")
            run_id = f"{cell}_r{rep}"
            run_dir = os.path.join(RUNS, run_id)
            if os.path.exists(run_dir):
                shutil.rmtree(run_dir)
            os.makedirs(run_dir)
            cdir = os.path.join(LOGS, cell)
            os.makedirs(cdir, exist_ok=True)
            slog = os.path.join(cdir, f"r{rep}.server.jsonl")
            mvn_out = os.path.join(cdir, f"r{rep}.mvn.txt")
            for f in (slog, mvn_out):
                if os.path.exists(f):  # a previous interrupted attempt: keep it as invalid
                    os.rename(f, f + f".interrupted-{int(time.time())}")
            srv, port = start_server(run_id, fault, slog)
            proj, settings, repo = prepare(run_dir, config, fault, port)
            cmd = ["./mvnw", "-B", "-s", settings, f"-Dmaven.repo.local={repo}", "-f",
                   "pom.xml", "dependency:resolve"]
            env = dict(os.environ, JAVA_HOME=JDKS[jdk], MAVEN_OPTS="")
            for k in ("MAVEN_ARGS", "MVNW_REPOURL", "MVNW_USERNAME", "MVNW_PASSWORD"):
                env.pop(k, None)
            order += 1
            wall0 = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            with open(mvn_out, "w") as fh:
                fh.write(f"# run_id={run_id} order={order} start={wall0}\n")
                fh.write(f"# cwd=<work>/partA/runs/{run_id}/proj JAVA_HOME={JDKS[jdk]}\n")
                fh.write(f"# MAVEN_USER_HOME=<work>/mvn-home revision={CONFIGS[config][0]}\n")
                fh.write("# server: python3 -I harness/fault_mirror.py --root <work>/partA/warm-repo "
                         f"--fault {fault} --log {rel(slog)} --port-file <work>/partA/runs/{run_id}.port"
                         f" (port {port})\n")
                fh.write(f"# command: ./mvnw -B -s <work>/partA/runs/{run_id}/settings.xml "
                         f"-Dmaven.repo.local=<work>/partA/runs/{run_id}/repo -f pom.xml dependency:resolve\n")
                fh.flush()
                t0 = time.monotonic()
                timed_out = False
                try:
                    rc = subprocess.run(cmd, cwd=proj, env=env, stdout=fh, stderr=subprocess.STDOUT,
                                        timeout=TIMEOUT_S).returncode
                except subprocess.TimeoutExpired:
                    rc, timed_out = None, True
                dt = time.monotonic() - t0
                fh.write(f"# exit={rc} timed_out={timed_out} wall_seconds={dt:.2f}\n")
            srv.terminate()
            srv.wait(timeout=10)
            s = summarize(slog, mvn_out)
            # a run whose Maven never reached the mirror is not a measurement of the fault
            valid = s["total_requests"] > 0
            rec = {"part": "A", "cell": cell, "rep": rep, "run_id": run_id, "order": order,
                   "jdk": jdk, "fault": fault, "config": config, "revision": CONFIGS[config][0],
                   "start": wall0, "exit_code": rc, "timed_out": timed_out,
                   "wall_seconds": round(dt, 2), "outcome": "PASS" if s["build_success"] else "FAIL",
                   "valid": valid, "mvn_log": rel(mvn_out), "server_log": rel(slog)}
            rec.update(s)
            with open(records, "a") as fh:
                fh.write(json.dumps(rec) + "\n")
            shutil.rmtree(os.path.join(run_dir, "repo"), ignore_errors=True)
            print(f"{run_id}: {rec['outcome']} rc={rc} t={dt:.1f}s primary={s['primary_actions']} "
                  f"wrapper={s['wrapper_jar_actions']}", flush=True)


if __name__ == "__main__":
    main()
