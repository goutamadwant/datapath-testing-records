"""Offline safety checks: python3 test_run_guard.py."""
import json
import os
import pathlib
import shlex
import subprocess
import tempfile
import unittest


SOURCE = pathlib.Path(__file__).with_name("run.sh").read_text()


class RunGuardTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = pathlib.Path(temporary.name)
        self.runner = self.root / "run.sh"
        self.runner.write_text(SOURCE)
        commands = self.root / "bin"
        commands.mkdir()
        for name in ("git", "cargo", "java", "mvn", "mvnw"):
            command = commands / name
            command.write_text(f'#!/bin/sh\necho "{name} $*" >> "$COMMAND_TRACE"\nexit 73\n')
            command.chmod(0o755)
        self.trace = self.root / "commands"
        self.env = {**os.environ, "PATH": f"{commands}{os.pathsep}{os.environ['PATH']}",
                    "COMMAND_TRACE": str(self.trace), "FAILBEFORE_WORK": str(self.root / "work"),
                    "JAVA8_HOME": str(self.root / "no-jdk"),
                    "DATAFUSION_REPO": str(self.root / "df"),
                    "SEATUNNEL_REPO": str(self.root / "st")}
        self.env.pop("FAILBEFORE_DISPOSABLE", None)

    def run_script(self, *args):
        return subprocess.run(["bash", str(self.runner), *args], env=self.env,
                              capture_output=True, text=True, timeout=30)

    def records(self):
        return [json.loads(line) for line in (self.root / "logs/runs.jsonl").read_text().splitlines()]

    def test_explicit_case_without_disposable_refuses_before_clone(self):
        result = self.run_script("st12481-shim")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        for text in ("host-deletion hazard", "/tmp/seatunnel_mnt", "FAILBEFORE_DISPOSABLE=1",
                     "disposable filesystem environment without host-path mounts"):
            self.assertIn(text, result.stderr)
        requests = json.loads((self.root / "logs/requested.json").read_text())
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["cases"], ["st12481-shim"])
        records = self.records()
        self.assertEqual(len(records), 2)
        self.assertEqual({r["side"] for r in records}, {"before", "after"})
        for record in records:
            self.assertEqual(record["invocation"], requests[0]["invocation"])
            self.assertIn("safety guard before clone", record["setup_error"])
            self.assertNotEqual(record["exit_code"], 0)
            self.assertIn("FileUtils.deleteFile", (self.root / record["log"]).read_text())
        self.assertFalse(self.trace.exists(), "clone or build command reached")
        self.assertIn("0/2 requested sides ran", result.stdout)

    def test_default_matrix_excludes_shim_even_with_disposable_variable(self):
        self.env["FAILBEFORE_DISPOSABLE"] = "1"
        result = self.run_script()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        request = json.loads((self.root / "logs/requested.json").read_text())[0]
        self.assertEqual(len(request["cases"]), 10)
        self.assertNotIn("st12481-shim", request["cases"])
        self.assertFalse(any(r["case"] == "st12481-shim" for r in self.records()))

    def isolated(self, body):
        # Load definitions only, in a temporary runner directory; never touch the real host path.
        self.runner.write_text(SOURCE.split('\nALL="', 1)[0] + "\n" + body)
        return self.run_script()

    def test_guard_requires_both_conditions(self):
        hazard = shlex.quote(str(self.root / "host-path"))
        for explicit, disposable, expected in ((0, "1", 1), (1, "", 1), (1, "0", 1), (1, "1", 0)):
            with self.subTest(explicit=explicit, disposable=disposable):
                result = self.isolated(f"ST_REFUSE_IF_EXISTS={hazard}\nEXPLICIT_CASES={explicit}\n"
                                       f"FAILBEFORE_DISPOSABLE={shlex.quote(disposable)}\nst12481_guard\n")
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertIn("host-deletion hazard", result.stderr)

    def test_path_created_after_initial_guard_refuses_before_execution(self):
        hazard = shlex.quote(str(self.root / "host-path"))
        result = self.isolated(f"""
ST_REFUSE_IF_EXISTS={hazard}
EXPLICIT_CASES=1
FAILBEFORE_DISPOSABLE=1
st12481_guard || exit 9
mkdir "$ST_REFUSE_IF_EXISTS"
begin_side
TREE=$WORK
JAVA_HOME=$HERE
run_one st12481-shim before a b test module cargo test
""")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        records = self.records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["setup_error"], "st12481-shim safety guard before execution")
        self.assertIn("exists; unfixed teardown would delete it", (self.root / records[0]["log"]).read_text())
        self.assertNotIn("cargo", self.trace.read_text())
        self.assertTrue((self.root / "host-path").is_dir())

    def test_dangling_symlink_is_also_refused(self):
        hazard = self.root / "host-path"
        hazard.symlink_to(self.root / "missing")
        result = self.isolated(f"ST_REFUSE_IF_EXISTS={shlex.quote(str(hazard))}\n"
                               "EXPLICIT_CASES=1\nFAILBEFORE_DISPOSABLE=1\nst12481_guard\n")
        self.assertEqual(result.returncode, 1)
        self.assertTrue(hazard.is_symlink())


if __name__ == "__main__":
    unittest.main()
