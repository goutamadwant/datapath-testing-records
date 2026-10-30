"""Offline checks: python3 test_safety.py."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
GUARDED = (
    "harness/run_part_c.sh",
    "replay-2026-10-26/harness/historical-part-c/part_c.sh",
)


def shell_for(path):
    words = shlex.split(path.read_text().splitlines()[0][2:])
    shell = Path(words[-1]).name
    if shell not in ("sh", "bash"):
        raise AssertionError(f"unsupported shell in {path}: {words}")
    return shell


class SafetyTest(unittest.TestCase):
    def test_historical_scripts_refuse_before_work(self):
        for script in GUARDED:
            for value in (None, "0"):
                with self.subTest(script=script, value=value), tempfile.TemporaryDirectory() as tmp:
                    env = dict(os.environ)
                    env.pop("REPLAY_HISTORICAL_DESTRUCTIVE", None)
                    if value is not None:
                        env["REPLAY_HISTORICAL_DESTRUCTIVE"] = value
                    for name in ("REPLAY_BUNDLE", "REPLAY_WORK", "HOME", "TMPDIR"):
                        env[name] = tmp
                    path = ROOT / script
                    result = subprocess.run(
                        [shell_for(path), str(path)], cwd=tmp, env=env,
                        capture_output=True, text=True, timeout=10,
                    )
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    for phrase in (
                        script, "retired historical Part C script",
                        "removes Docker containers", "deletes directories under its work path",
                        "kept for inspection", "REPLAY_HISTORICAL_DESTRUCTIVE=1",
                    ):
                        self.assertIn(phrase, result.stderr)
                    self.assertEqual(list(Path(tmp).iterdir()), [])
                    print(f"PASS guard {script} (variable {value or 'unset'})")

    def test_shell_syntax(self):
        scripts = sorted(
            p for p in ROOT.rglob("*.sh")
            if not p.is_relative_to(ROOT / "replay-clean/out")
        )
        self.assertTrue(scripts)
        for path in scripts:
            with self.subTest(script=str(path.relative_to(ROOT))):
                shell = shell_for(path)
                result = subprocess.run(
                    [shell, "-n", str(path)], capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                print(f"PASS {shell} -n {path.relative_to(ROOT)}")

    def test_all_selects_fresh_mode(self):
        source = (ROOT / "model-queries-2026-10-25/run.sh").read_text()
        # Replace the build function in a temporary copy to exercise dispatch without a build.
        marker = '\ncase "${1:-}" in\n'
        self.assertEqual(source.count(marker), 1)
        source = source.replace(marker, '\nbuild() { printf "build:%s\\n" "$MEASURE_RESUME"; }\n' + marker)
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            runner = work / "run.sh"
            runner.write_text(source)
            commands = work / "bin"
            commands.mkdir()
            python = commands / "python3"
            python.write_text('#!/bin/sh\nprintf "%s:%s\\n" "$1" "$MEASURE_RESUME"\n')
            python.chmod(0o755)
            env = {**os.environ, "PATH": f"{commands}{os.pathsep}{os.environ['PATH']}",
                   "RUN_WORK": str(work / "work"), "MEASURE_RESUME": "1"}
            result = subprocess.run(
                ["sh", str(runner), "all"], cwd=tmp, env=env,
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout.splitlines(), [
                "build:0", "harness/measure.py:0", "harness/analyze.py:0",
            ])
            print("PASS all selects fresh mode with MEASURE_RESUME=1 inherited")


if __name__ == "__main__":
    unittest.main(verbosity=2)
