#!/usr/bin/env python3
"""Part A driver: PR 12468 Maven retry under injected faults (reconstruction, 2026-10-25).

For each JDK x fault x configuration (before = parent a1084015e, no .mvn/maven.config;
after = merge ae7c919bc, with .mvn/maven.config and the backoff mvnw), start fault_mirror.py on a
free port, run `./mvnw -B -s <mirror settings> -Dmaven.repo.local=<empty dir> -f pom.xml
dependency:resolve` in a fresh project directory, and record outcome, junit request counts and
timings. One run per cell, as in the PR. Logs go to logs/partA/, summaries to partA_runs.json.
"""
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
LOGS = os.path.join(EXP, "logs", "partA")
RT = "<repo>/runtime/replay"
REPO = os.path.join(RT, "seatunnel")
WARM = os.path.join(RT, "partA", "warm-repo")
RUNS = os.path.join(RT, "partA", "runs")
JDKS = {
    "jdk8": "/Library/Java/JavaVirtualMachines/jdk1.8.0_172.jdk/Contents/Home",
    "jdk11": "<home>",
}
CONFIGS = {
    "before": ("a1084015eeb390a6c7f53d3ce7391217e427e4d9",
               ["mvnw", ".mvn/wrapper/maven-wrapper.properties"]),
    "after": ("ae7c919bcb78f03446dbd2b754a2b9882602946a",
              ["mvnw", ".mvn/wrapper/maven-wrapper.properties", ".mvn/maven.config"]),
}
FAULTS = ["503x2", "reset4", "429x2", "truncate1", "wrapper429s"]
# Sensitivity variant (not a Table 1 row), run only when named on the command line.
VARIANTS = ["429x2nobody"]
WRAPPER_JAR = os.path.join(WARM, "org/apache/maven/wrapper/maven-wrapper/3.1.0/maven-wrapper-3.1.0.jar")
TIMEOUT_S = 600


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
            # The wrapperUrl line overrides MVNW_REPOURL in this mvnw, so point it at the local
            # server; distributionUrl is left unchanged (Maven 3.8.4 is already in ~/.m2/wrapper).
            lines = []
            for line in data.decode().splitlines():
                if line.startswith("wrapperUrl="):
                    line = (f"wrapperUrl=http://127.0.0.1:{port}/maven2/org/apache/maven/wrapper/"
                            "maven-wrapper/3.1.0/maven-wrapper-3.1.0.jar")
                lines.append(line)
            data = ("\n".join(lines) + "\n").encode()
        dst = os.path.join(proj, f)
        with open(dst, "wb") as fh:
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


def start_server(run_id, fault):
    port_file = os.path.join(RUNS, run_id + ".port")
    if os.path.exists(port_file):  # a stale port file would point settings.xml at a dead port
        os.remove(port_file)
    log = os.path.join(LOGS, run_id + ".server.jsonl")
    cmd = [sys.executable, "-I", os.path.join(HERE, "fault_mirror.py"), "--root", WARM,
           "--fault", fault, "--log", log, "--port-file", port_file]
    p = subprocess.Popen(cmd)
    for _ in range(100):
        if os.path.exists(port_file) and open(port_file).read().strip():
            return p, int(open(port_file).read()), log, cmd
        time.sleep(0.05)
    p.kill()
    raise RuntimeError("server did not start")


def summarize(server_log, mvn_out, t_start_wall):
    reqs = [json.loads(l) for l in open(server_log) if '"path"' in l]
    junit = {}
    for r in reqs:
        if r["target"]:
            junit.setdefault(r["path"], []).append(r["action"])
    wrapper = [r for r in reqs if "/maven-wrapper-" in r["path"]]
    text = open(mvn_out, errors="replace").read()
    s = {
        "build_success": "BUILD SUCCESS" in text,
        "build_failure": "BUILD FAILURE" in text,
        "main_class_not_found": "Could not find or load main class org.apache.maven.wrapper.MavenWrapperMain" in text,
        "junit_requests": {p: {"attempts": len(a), "actions": a} for p, a in junit.items()},
        "wrapper_jar_requests": [{"t_rel_s": r["t_rel_s"], "wall": r["wall"], "action": r["action"]}
                                 for r in wrapper],
        "total_requests": len(reqs),
        "retry_log_lines": [l for l in text.splitlines()
                            if "Retrying request" in l or "retrying" in l.lower()][:40],
        "error_lines": [l for l in text.splitlines() if l.startswith("[ERROR]")][:6],
    }
    return s


def main():
    os.makedirs(LOGS, exist_ok=True)
    os.makedirs(RUNS, exist_ok=True)
    only = set(sys.argv[1:])
    results = []
    out_json = os.path.join(LOGS, "partA_runs.json")
    if os.path.exists(out_json):
        results = json.load(open(out_json))
    order = len(results)
    for jdk in ["jdk8", "jdk11"]:
        for fault in FAULTS + VARIANTS:
            for config in ["before", "after"]:
                run_id = f"{jdk}_{fault}_{config}"
                if only and run_id not in only:
                    continue
                if not only and fault in VARIANTS:
                    continue
                run_dir = os.path.join(RUNS, run_id)
                if os.path.exists(run_dir):
                    shutil.rmtree(run_dir)
                os.makedirs(run_dir)
                for f in (run_id + ".server.jsonl", run_id + ".mvn.txt"):
                    if os.path.exists(os.path.join(LOGS, f)):
                        os.remove(os.path.join(LOGS, f))
                srv, port, slog, scmd = start_server(run_id, fault)
                proj, settings, repo = prepare(run_dir, config, fault, port)
                cmd = ["./mvnw", "-B", "-s", settings, f"-Dmaven.repo.local={repo}", "-f",
                       "pom.xml", "dependency:resolve"]
                env = dict(os.environ, JAVA_HOME=JDKS[jdk], MAVEN_OPTS="")
                env.pop("MAVEN_ARGS", None)
                env.pop("MVNW_REPOURL", None)
                mvn_out = os.path.join(LOGS, run_id + ".mvn.txt")
                order += 1
                wall0 = time.strftime("%Y-%m-%dT%H:%M:%S%z")
                with open(mvn_out, "w") as fh:
                    fh.write(f"# run_id={run_id} order={order} start={wall0}\n")
                    fh.write(f"# cwd={proj}\n# JAVA_HOME={JDKS[jdk]}\n")
                    fh.write(f"# server: {' '.join(scmd)}\n# command: {' '.join(cmd)}\n")
                    fh.flush()
                    t0 = time.monotonic()
                    timed_out = False
                    try:
                        rc = subprocess.run(cmd, cwd=proj, env=env, stdout=fh,
                                            stderr=subprocess.STDOUT, timeout=TIMEOUT_S).returncode
                    except subprocess.TimeoutExpired:
                        rc, timed_out = None, True
                    dt = time.monotonic() - t0
                    fh.write(f"# exit={rc} timed_out={timed_out} wall_seconds={dt:.2f}\n")
                srv.terminate()
                srv.wait(timeout=10)
                s = summarize(slog, mvn_out, wall0)
                rec = {"run_id": run_id, "order": order, "jdk": jdk, "fault": fault,
                       "config": config, "start": wall0, "exit_code": rc, "timed_out": timed_out,
                       "wall_seconds": round(dt, 2), "command": " ".join(cmd), "cwd": proj,
                       "server_command": " ".join(scmd), "mvn_log": mvn_out, "server_log": slog}
                rec.update(s)
                results = [r for r in results if r["run_id"] != run_id] + [rec]
                json.dump(results, open(out_json, "w"), indent=1)
                print(f"{run_id}: rc={rc} success={s['build_success']} t={dt:.1f}s junit="
                      f"{ {p.rsplit('/',1)[1]: v['actions'] for p, v in s['junit_requests'].items()} }"
                      f" wrapper={[w['action'] for w in s['wrapper_jar_requests']]}", flush=True)


if __name__ == "__main__":
    main()
