"""Hash, verify and record resolved harness lockfiles using the standard library."""
import hashlib
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent / "plan_time"
LABELS = ("before", "after", "issuedate")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(label):
    path = HERE / f"Cargo.lock.{label}"
    manifest = HERE / "lockfiles.sha256"
    entries = []
    for line in manifest.read_text().splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]{64})  (Cargo\.lock\.(?:before|after|issuedate))", line)
        if not match:
            raise ValueError("invalid line in harness/plan_time/lockfiles.sha256")
        if match[2] == path.name:
            entries.append(match[1].lower())
    if len(entries) != 1:
        raise ValueError(f"expected exactly one sha256 entry for {path.name}")
    actual = sha256(path)
    if actual != entries[0]:
        raise ValueError(f"sha256 mismatch for {path.name}: expected {entries[0]}, got {actual}")
    return actual


def record():
    paths = [HERE / f"Cargo.lock.{label}" for label in LABELS]
    text = "".join(f"{sha256(p)}  {p.name}\n" for p in paths if p.is_file())
    temporary = HERE / "lockfiles.sha256.tmp"
    temporary.write_text(text)
    temporary.replace(HERE / "lockfiles.sha256")
    print(text, end="")


def main():
    try:
        if sys.argv[1:] == ["record"]:
            record()
        elif len(sys.argv) == 3 and sys.argv[1] == "hash":
            print(sha256(pathlib.Path(sys.argv[2])))
        elif len(sys.argv) == 3 and sys.argv[1] == "verify" and sys.argv[2] in LABELS:
            print(verify(sys.argv[2]))
        else:
            raise ValueError("usage: lockfiles.py hash PATH | verify LABEL | record")
    except (OSError, ValueError) as e:
        raise SystemExit(f"lockfiles.py: {e}")


if __name__ == "__main__":
    main()
