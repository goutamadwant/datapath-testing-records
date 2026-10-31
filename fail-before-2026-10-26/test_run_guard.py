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
        self.assertNotIn("st12481-shim-both", request["cases"])
        self.assertNotIn("df24917-budget-nohook", request["cases"])
        self.assertFalse(any(r["case"] in ("st12481-shim", "st12481-shim-both", "df24917-budget-nohook")
                             for r in self.records()))

    def test_shim_both_without_disposable_refuses_both_sides_before_clone(self):
        result = self.run_script("st12481-shim-both")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        records = self.records()
        self.assertEqual([r["side"] for r in records], ["before", "after"])
        for record in records:
            self.assertIn("safety guard before clone", record["setup_error"])
        self.assertIn("applied on the after side", records[1]["transplant"])
        self.assertFalse(self.trace.exists(), "clone or build command reached")

    def test_nohook_explicit_setup_failure_records_both_sides(self):
        result = self.run_script("df24917-budget-nohook")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        request = json.loads((self.root / "logs/requested.json").read_text())[0]
        self.assertEqual(request["cases"], ["df24917-budget-nohook"])
        records = self.records()
        self.assertEqual([r["side"] for r in records], ["before", "after"])
        for record in records:
            self.assertIn("clone", record["setup_error"])
            self.assertIn(f"df24917-budget-nohook-{record['side']}.patch applied",
                          record["transplant"])
            self.assertNotIn("merge commit as is", record["transplant"])
        self.assertNotIn("cargo", self.trace.read_text())

    def test_unknown_case_lists_nohook(self):
        result = self.run_script("unknown")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("df24917-budget-nohook", result.stderr)
        self.assertIn("st12481-shim", result.stderr)

    def isolated(self, body):
        # Load definitions only, in a temporary runner directory; never touch the real host path.
        self.runner.write_text(SOURCE.split('\nALL="', 1)[0] + "\n" + body)
        return self.run_script()

    def test_nohook_applies_patch_and_runs_same_command_on_each_commit(self):
        result = self.isolated('''
df_tree() { echo "tree $*"; }
df_transplant() { echo "transplant $*"; }
run_one() { printf 'run %s\\n' "$*"; }
setup_error() { exit 9; }
case_df24917-budget-nohook
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        before = "408527ae58b5b706f5c02df8c37e096122cd8c78"
        after = "3dfa245d61dde362e2c077761783bc735931659c"
        command = ("cargo test --locked --profile ci --no-fail-fast "
                   "-p datafusion-optimizer -p datafusion-physical-expr --lib "
                   "test_constant_regex_planning_budget_without_hook")
        expected = []
        for side, commit in (("before", before), ("after", after)):
            patch = f"df24917-budget-nohook-{side}.patch"
            expected.extend([
                f"tree {commit}",
                f"transplant patch {patch} {after}",
                f"run df24917-budget-nohook {side} {before} {after} patches/{patch} "
                f"applied (hook-free test-module hunks only) - {command}",
            ])
        self.assertEqual(result.stdout.splitlines(), expected)
        self.assertFalse(self.trace.exists(), "external command reached")

    def test_guard_requires_both_conditions(self):
        hazard = shlex.quote(str(self.root / "host-path"))
        for explicit, disposable, expected in ((0, "1", 1), (1, "", 1), (1, "0", 1), (1, "1", 0)):
            with self.subTest(explicit=explicit, disposable=disposable):
                result = self.isolated(f"ST_REFUSE_IF_EXISTS={hazard}\nEXPLICIT_CASES={explicit}\n"
                                       f"FAILBEFORE_DISPOSABLE={shlex.quote(disposable)}\nst12481_guard\n")
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertIn("host-deletion hazard", result.stderr)

    def test_shim_both_copies_only_before_and_patches_both_commits(self):
        result = self.isolated('''
st_tree() { echo "tree $*"; }
st_copy() { echo "copy $*"; }
step() { echo "step $*"; }
run_one() { printf 'run %s\\n' "$*"; }
setup_error() { exit 9; }
case_st12481-shim-both
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0], "tree st12481 7ba68325cb7ea1bf1a28f56c4f9c20695d221df3")
        self.assertEqual(lines[1], "copy 0e4cf52896ee3604a8e7899d7736ffd914ee6ce7 "
                         "seatunnel-e2e/seatunnel-e2e-common/src/test/java/org/apache/"
                         "seatunnel/e2e/common/container/flink/AbstractTestFlinkContainerTest.java")
        self.assertEqual(lines[4], "tree st12481 0e4cf52896ee3604a8e7899d7736ffd914ee6ce7")
        self.assertEqual(lines[2], lines[5])
        self.assertIn("apply patches/st12481-flink-test-drop-override.patch", lines[2])
        self.assertIn("run st12481-shim-both before", lines[3])
        self.assertIn("run st12481-shim-both after", lines[6])
        self.assertIn("applied on the after side to the merge commit's own committed test", lines[6])
        self.assertEqual(lines[3].split(" ./mvnw ", 1)[1], lines[6].split(" ./mvnw ", 1)[1])
        self.assertFalse(self.trace.exists(), "external command reached")

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
