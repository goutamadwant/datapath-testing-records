"""Paths for the historical measurement and named replays."""
import os
import re
import hashlib
import json


BUILDS = ("before", "after")
REPS = 3
EXPECTED_CONTROLS = 5
EXPECTED_QUERIES = 412
EXPECTED_ITEMS = EXPECTED_CONTROLS + EXPECTED_QUERIES
EXPECTED_PROCESS_RUNS = EXPECTED_ITEMS * len(BUILDS) * REPS


class InputIdentityError(ValueError):
    pass


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def inputs_sha256(items):
    """Hash the full loaded records in measurement order, including all metadata."""
    return hashlib.sha256(canonical_json(items)).hexdigest()


def input_records(items):
    """Positions are zero-based: controls first, then queries in file order."""
    return [{"id": item["query_id"], "sha256": hashlib.sha256(canonical_json(item)).hexdigest(),
             "position": position} for position, item in enumerate(items)]


def write_inputs(logs, items):
    (logs / "inputs.jsonl").write_bytes(
        b"".join(canonical_json(record) + b"\n" for record in input_records(items)))


def validate_inputs(logs, items, manifest=None):
    """Reject unbound or changed workloads before retained records can be used."""
    prefix = f"input-identity error for {logs}"
    try:
        if manifest is None:
            manifest = json.loads((logs / "manifest.json").read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or manifest.get("inputs_file") != "inputs.jsonl":
            raise ValueError("manifest.json must bind inputs.jsonl")
        digest = manifest["inputs_sha256"]
        recorded = [json.loads(line) for line in
                    (logs / "inputs.jsonl").read_text(encoding="utf-8").splitlines()]
        if any(not isinstance(record, dict) or not {"id", "sha256", "position"} <= record.keys()
               for record in recorded):
            raise ValueError("invalid inputs.jsonl record")
    except (OSError, ValueError, KeyError) as error:
        raise InputIdentityError(f"{prefix}: {error}") from error
    current_digest = inputs_sha256(items)
    current = input_records(items)
    for position in range(max(len(recorded), len(current))):
        old = recorded[position] if position < len(recorded) else None
        new = current[position] if position < len(current) else None
        if old != new:
            item_id = (old if old is not None else new)["id"]
            detail = f" (current id {new['id']})" if old and new and old["id"] != new["id"] else ""
            raise InputIdentityError(f"{prefix}: item {item_id} at position {position} differs{detail}; "
                                     "changed workloads require a fresh set")
    if current_digest != digest:
        raise InputIdentityError(f"{prefix}: inputs_sha256 mismatch with manifest.json; "
                                 "changed workloads require a fresh set")


def check_fresh(logs, resume):
    if not resume and any((logs / name).exists() for name in
                          ("classify.jsonl", "runs.jsonl", "manifest.json", "inputs.jsonl")):
        raise SystemExit(f"{logs} already contains measurement records; choose a new set name "
                         "or set MEASURE_RESUME=1")


def prepare_manifest(root, logs, binaries, items, started, resume):
    """Bind a set to inputs, binary bytes, committed lockfiles and the declared compiler."""
    check_fresh(logs, resume)
    manifest_path = logs / "manifest.json"
    manifest = None
    if resume:
        try:
            manifest = json.loads(manifest_path.read_text())
            if not isinstance(manifest, dict) or not isinstance(manifest["invocations"], list):
                raise ValueError("invalid manifest structure")
        except (OSError, ValueError, KeyError) as error:
            raise SystemExit(f"cannot resume {logs}: valid manifest.json required ({error})")
        try:
            validate_inputs(logs, items, manifest)
        except InputIdentityError as error:
            raise SystemExit(str(error)) from error
    plan_time = root / "harness/plan_time"
    try:
        identity = {
            "binary_sha256": {f"plan_time_{label}": hashlib.sha256(path.read_bytes()).hexdigest()
                              for label, path in binaries.items()},
            "lockfile_sha256": {f"Cargo.lock.{label}": hashlib.sha256(
                (plan_time / f"Cargo.lock.{label}").read_bytes()).hexdigest() for label in BUILDS},
            "toolchain": (plan_time / "TOOLCHAIN.expected").read_text().strip(),
            "item_count": len(items),
        }
    except OSError as error:
        raise SystemExit(f"cannot measure {logs}: {error}; run ./run.sh build first")
    if resume:
        for key, value in identity.items():
            if manifest.get(key) != value:
                raise SystemExit(f"cannot resume {logs}: {key} mismatch with manifest.json")
        return manifest
    manifest = {**identity, "inputs_sha256": inputs_sha256(items), "inputs_file": "inputs.jsonl",
                "inputs_binding": "recorded at first run", "start": started, "invocations": []}
    logs.mkdir(parents=True, exist_ok=True)
    write_inputs(logs, items)
    save_manifest(logs, manifest)
    return manifest


def save_manifest(logs, manifest):
    (logs / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def write_output(path, content, preserve=False):
    """Keep historical bytes intact and save differing output beside them."""
    data = content.encode("utf-8")
    destination = path
    if preserve and path.exists():
        if path.read_bytes() == data:
            return path
        destination = path.with_name(f"{path.stem}.regenerated{path.suffix}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    if destination != path:
        print(f"Historical {path.name} was left unchanged; wrote {destination.name}")
    return destination


def set_name(value=None):
    name = os.environ.get("MEASURE_SET", "measure") if value is None else value
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", name):
        raise ValueError("MEASURE_SET must contain only letters, digits, underscores or hyphens")
    return name


def paths(root, name=None):
    name = set_name(name)
    logs = root / "logs" / name
    results = root / ("results.json" if name == "measure" else f"results-{name}.json")
    tables = root / "logs/tables.md" if name == "measure" else logs / "tables.md"
    return logs, results, tables
