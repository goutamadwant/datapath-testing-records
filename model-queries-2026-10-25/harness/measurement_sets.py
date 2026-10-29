"""Paths for the historical measurement and named replays."""
import os
import re


BUILDS = ("before", "after")
REPS = 3
EXPECTED_CONTROLS = 5
EXPECTED_QUERIES = 412
EXPECTED_ITEMS = EXPECTED_CONTROLS + EXPECTED_QUERIES
EXPECTED_PROCESS_RUNS = EXPECTED_ITEMS * len(BUILDS) * REPS


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
