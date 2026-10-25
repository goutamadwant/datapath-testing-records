"""Generate model-written SQL queries for the 20 themes with two generators.

G1: an OpenAI-compatible chat endpoint (LM Studio), G1_ENDPOINT / G1_MODEL.
G2: the `claude` command-line client, G2_MODEL, run from an empty temporary directory with a
    fixed system prompt, no tools and no settings sources, so no project files enter the prompt.

Writes queries/<generator>.jsonl (one line per extracted query) and keeps every raw response
under logs/generation/<generator>/. One call per theme; a second call only when the first
yields fewer than 10 extractable queries. Refuses to overwrite existing outputs.
"""
import concurrent.futures as cf
import datetime as dt
import json
import os
import pathlib
import subprocess
import tempfile
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = (HERE / "prompts/template.txt").read_text()
THEMES = [t for t in (HERE / "prompts/themes.txt").read_text().splitlines() if t.strip()]
SYSTEM = "You are a helpful assistant."
G1_ENDPOINT = os.environ.get("G1_ENDPOINT", "http://127.0.0.1:11435/v1")
G1_MODEL = os.environ.get("G1_MODEL", "qwen3-coder-30b-a3b-instruct")
G2_MODEL = os.environ.get("G2_MODEL", "sonnet")
GENERATORS = {"g1": "G1", "g2": "G2"}


def now():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def prompt_for(theme):
    return TEMPLATE.replace("{THEME}", theme)


def extract(text):
    """Return (queries, unextractable_lines) from a response text."""
    queries, bad = [], []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("```"):
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            bad.append(line)
            continue
        if isinstance(obj, dict) and isinstance(obj.get("sql"), str):
            queries.append({"task": obj.get("task"), "sql": obj["sql"]})
        else:
            bad.append(line)
    return queries, bad


def call_g1(prompt):
    body = json.dumps({
        "model": G1_MODEL,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4096,
    }).encode()
    req = urllib.request.Request(G1_ENDPOINT + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t = time.time()
    with urllib.request.urlopen(req, timeout=600) as r:
        raw = json.load(r)
    return {"request": json.loads(body), "response": raw, "seconds": round(time.time() - t, 2),
            "text": raw["choices"][0]["message"]["content"]}


def call_g2(prompt):
    cmd = ["claude", "-p", "--model", G2_MODEL, "--output-format", "json",
           "--system-prompt", SYSTEM, "--tools", "", "--strict-mcp-config",
           "--setting-sources", "", "--no-session-persistence", prompt]
    with tempfile.TemporaryDirectory() as cwd:
        t = time.time()
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=600)
    rec = {"command": cmd[:-1] + ["<prompt>"], "returncode": p.returncode,
           "seconds": round(time.time() - t, 2), "stderr": p.stderr}
    try:
        raw = json.loads(p.stdout)
    except json.JSONDecodeError:
        raw = {"unparsed_stdout": p.stdout}
    rec["response"] = raw
    rec["text"] = raw.get("result", "") if isinstance(raw, dict) else ""
    return rec


def run_theme(gen, idx, theme):
    out = []
    logdir = HERE / "logs/generation" / gen
    prompt = prompt_for(theme)
    for call in (1, 2):
        started = now()
        try:
            rec = (call_g1 if gen == "g1" else call_g2)(prompt)
        except Exception as e:  # keep the failure
            rec = {"exception": repr(e), "text": ""}
        rec.update({"generator": gen, "theme_index": idx, "theme": theme, "call": call,
                    "started": started, "finished": now(), "prompt": prompt, "system": SYSTEM})
        qs, bad = extract(rec["text"])
        rec["extracted"] = len(qs)
        rec["unextractable_lines"] = bad
        (logdir / f"theme-{idx:02d}-call-{call}.json").write_text(json.dumps(rec, indent=1))
        for n, q in enumerate(qs, 1):
            out.append({"query_id": f"{gen}-t{idx:02d}-c{call}-q{n:02d}", "generator": gen,
                        "theme_index": idx, "theme": theme, "call": call, **q})
        if len(qs) >= 10:
            break
    return out


def main():
    for gen in GENERATORS:
        if (HERE / f"queries/{gen}.jsonl").exists():
            raise SystemExit(f"queries/{gen}.jsonl exists; refusing to overwrite")
        (HERE / "logs/generation" / gen).mkdir(parents=True, exist_ok=True)
    summary = {"started": now(), "g1_endpoint": G1_ENDPOINT, "g1_model": G1_MODEL,
               "g2_model_alias": G2_MODEL}
    try:
        with urllib.request.urlopen(G1_ENDPOINT + "/models", timeout=30) as r:
            summary["g1_models_listing"] = json.load(r)
    except Exception as e:
        summary["g1_models_listing_error"] = repr(e)
    results = {g: [] for g in GENERATORS}
    with cf.ThreadPoolExecutor(max_workers=5) as ex:
        futs = {}
        for i, th in enumerate(THEMES, 1):
            futs[ex.submit(run_theme, "g2", i, th)] = ("g2", i)
        # G1 is served by one local model: run its themes sequentially in one worker.
        g1 = ex.submit(lambda: [q for i, th in enumerate(THEMES, 1) for q in run_theme("g1", i, th)])
        for f in cf.as_completed(futs):
            results["g2"].extend(f.result())
        results["g1"] = g1.result()
    for gen, qs in results.items():
        qs.sort(key=lambda q: q["query_id"])
        with open(HERE / f"queries/{gen}.jsonl", "w") as fh:
            for q in qs:
                fh.write(json.dumps(q) + "\n")
        summary[f"{gen}_queries"] = len(qs)
    summary["finished"] = now()
    (HERE / "logs/generation/summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k != "g1_models_listing"}, indent=1))


if __name__ == "__main__":
    main()
