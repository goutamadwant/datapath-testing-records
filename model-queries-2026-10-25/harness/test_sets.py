"""Small offline checks for measurement paths and process-run completeness."""
import contextlib
import copy
import hashlib
import importlib
import io
import json
import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import analyze
import compare
import measure
from measurement_sets import paths, write_output


class MeasurementSetsTest(unittest.TestCase):
    def test_paths_used_by_measure_and_analyze(self):
        for name in (None, "measure-locked-2026-10-29"):
            with self.subTest(name=name), patch.dict(os.environ, {}, clear=True):
                if name is not None:
                    os.environ["MEASURE_SET"] = name
                importlib.reload(measure)
                importlib.reload(analyze)
                root = measure.HERE
                selected = name or "measure"
                self.assertEqual(measure.OUT, root / "logs" / selected)
                self.assertEqual(analyze.OUT, measure.OUT)
                self.assertEqual(analyze.RESULTS, root / (f"results-{name}.json" if name else "results.json"))
                self.assertEqual(analyze.TABLES, root / "logs" / (f"{name}/tables.md" if name else "tables.md"))
        importlib.reload(measure)
        importlib.reload(analyze)

    def test_invalid_set_names(self):
        for name in ("", "..", "../measure", "/tmp/replay", "a/b"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                paths(pathlib.Path("."), name)

    def test_completeness(self):
        items = [{"query_id": f"item-{i}"} for i in range(417)]
        runs = {(it["query_id"], b): [{"rep": r} for r in (1, 2, 3)]
                for it in items for b in analyze.BUILDS}
        state, problems = analyze.completeness(items, runs)
        self.assertEqual(state, {"expected_process_runs": 2502,
                                 "recorded_process_runs": 2502, "complete": True})
        self.assertEqual(problems, [])
        runs[("item-0", "before")].pop()
        state, problems = analyze.completeness(items, runs)
        self.assertFalse(state["complete"])
        self.assertEqual(state["recorded_process_runs"], 2501)
        self.assertIn("item-0 before", problems[0])
        # The right total alone does not establish completeness.
        runs[("item-0", "before")].append({"rep": 2})
        state, problems = analyze.completeness(items, runs)
        self.assertEqual(state["recorded_process_runs"], 2502)
        self.assertFalse(state["complete"])
        runs[("item-0", "before")][-1] = {"rep": 3}
        runs[("unknown", "after")] = [{"rep": 1}]
        state, problems = analyze.completeness(items, runs)
        self.assertFalse(state["complete"])
        self.assertTrue(any("unknown after" in p for p in problems))

    def test_reduced_inputs_do_not_reduce_expected_runs(self):
        items = [{"query_id": "control"}, {"query_id": "query"}]
        runs = {(it["query_id"], b): [{"rep": r} for r in (1, 2, 3)]
                for it in items for b in analyze.BUILDS}
        state, problems = analyze.completeness(items, runs)
        self.assertEqual(state["expected_process_runs"], 2502)
        self.assertFalse(state["complete"])
        self.assertTrue(any("expected 417" in p for p in problems))

    def test_duplicate_item_ids_are_incomplete(self):
        items = [{"query_id": f"item-{i}"} for i in range(416)]
        items.append(items[0])
        runs = {(it["query_id"], b): [{"rep": r} for r in (1, 2, 3)]
                for it in items for b in analyze.BUILDS}
        state, _ = analyze.completeness(items, runs)
        self.assertFalse(state["complete"])


class MeasurementInvocationTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = pathlib.Path(temporary.name)
        self.out = self.root / "logs/test-set"
        self.plan_time = self.root / "harness/plan_time"
        self.plan_time.mkdir(parents=True)
        self.binaries = {}
        for label in ("before", "after"):
            binary = self.root / f"plan_time_{label}"
            binary.write_bytes(label.encode())
            self.binaries[label] = binary
            (self.plan_time / f"Cargo.lock.{label}").write_text(f"lock {label}\n")
        (self.plan_time / "TOOLCHAIN.expected").write_text("rustc test\n")
        self.items = [{"query_id": "test-item", "sql": "select 1"}]
        self.enterContext(patch.dict(os.environ, {"MEASURE_RESUME": "0"}))
        self.enterContext(patch.multiple(measure, HERE=self.root, OUT=self.out, BIN=self.binaries))
        self.enterContext(patch.object(measure, "load_items", return_value=self.items))
        self.process = self.enterContext(patch.object(measure, "run_one", return_value={"status": "ok"}))

    def invoke(self, resume=False):
        output = io.StringIO()
        with patch.dict(os.environ, {"MEASURE_RESUME": "1" if resume else "0"}), contextlib.redirect_stdout(output):
            measure.main()
        return output.getvalue()

    def manifest(self):
        return json.loads((self.out / "manifest.json").read_text())

    def test_existing_records_refused_by_default(self):
        self.out.mkdir(parents=True)
        for filename in ("classify.jsonl", "runs.jsonl"):
            with self.subTest(filename=filename):
                record = self.out / filename
                record.write_bytes(b"retained record\n")
                with self.assertRaises(SystemExit) as error:
                    measure.main()
                self.assertIn(str(self.out), str(error.exception))
                self.assertIn("choose a new set name or set MEASURE_RESUME=1", str(error.exception))
                self.assertEqual(record.read_bytes(), b"retained record\n")
                self.assertFalse((self.out / "manifest.json").exists())
                record.unlink()
        self.process.assert_not_called()

    def test_fresh_manifest_and_matching_resume_report(self):
        self.assertIn("executed 6 process runs, reused 0 recorded runs", self.invoke())
        manifest = self.manifest()
        self.assertEqual(manifest["binary_sha256"], {
            f"plan_time_{b}": hashlib.sha256(p.read_bytes()).hexdigest() for b, p in self.binaries.items()})
        self.assertEqual(manifest["lockfile_sha256"], {
            f"Cargo.lock.{b}": hashlib.sha256((self.plan_time / f"Cargo.lock.{b}").read_bytes()).hexdigest()
            for b in ("before", "after")})
        self.assertEqual(manifest["toolchain"], "rustc test")
        self.assertEqual(manifest["item_count"], 1)
        self.assertEqual(manifest["start"], manifest["invocations"][0]["start"])
        retained = {name: (self.out / name).read_bytes() for name in ("runs.jsonl", "classify.jsonl")}
        self.process.reset_mock()
        self.assertIn("executed 0 process runs, reused 6 recorded runs", self.invoke(resume=True))
        self.process.assert_not_called()
        for name, data in retained.items():
            self.assertEqual((self.out / name).read_bytes(), data)
        invocations = self.manifest()["invocations"]
        self.assertEqual([(r["executed"], r["reused"]) for r in invocations], [(6, 0), (0, 6)])
        for invocation in invocations:
            self.assertLessEqual(invocation["start"], invocation["end"])

    def test_partial_resume_reports_executed_and_reused(self):
        self.invoke()
        runs = self.out / "runs.jsonl"
        first_record = runs.read_text().splitlines(keepends=True)[0]
        runs.write_text(first_record)
        self.process.reset_mock()
        self.assertIn("executed 5 process runs, reused 1 recorded runs", self.invoke(resume=True))
        self.assertEqual(self.process.call_count, 5)
        self.assertEqual(len(runs.read_text().splitlines()), 6)
        self.assertTrue(runs.read_text().startswith(first_record))
        self.assertEqual(self.manifest()["invocations"][-1]["executed"], 5)

    def test_resume_requires_manifest(self):
        self.out.mkdir(parents=True)
        (self.out / "runs.jsonl").write_text("")
        with self.assertRaisesRegex(SystemExit, "valid manifest.json required"):
            self.invoke(resume=True)
        self.process.assert_not_called()

    def test_resume_refuses_changed_binary_or_lockfile(self):
        self.invoke()
        for target, field in ((self.binaries["before"], "binary_sha256"),
                              (self.binaries["after"], "binary_sha256"),
                              (self.plan_time / "Cargo.lock.before", "lockfile_sha256"),
                              (self.plan_time / "Cargo.lock.after", "lockfile_sha256")):
            with self.subTest(target=target.name):
                original = target.read_bytes()
                retained = {p: p.read_bytes() for p in self.out.iterdir()}
                target.write_bytes(original + b"changed")
                self.process.reset_mock()
                with self.assertRaisesRegex(SystemExit, field + " mismatch"):
                    self.invoke(resume=True)
                self.process.assert_not_called()
                self.assertEqual({p: p.read_bytes() for p in self.out.iterdir()}, retained)
                target.write_bytes(original)


class SyntheticFilesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.out, self.results, self.tables = paths(self.root, "measure")
        for directory in (self.root / "harness", self.root / "queries", self.out,
                          self.root / "logs/generation"):
            directory.mkdir(parents=True, exist_ok=True)
        self.patches = patch.multiple(analyze, HERE=self.root, OUT=self.out,
                                     RESULTS=self.results, TABLES=self.tables)
        self.patches.start()
        self.addCleanup(self.patches.stop)

    def jsonl(self, path, records):
        path.write_text("".join(json.dumps(r) + "\n" for r in records))

    def fixture(self):
        # Minimal synthetic SQL and timings; no measurements or real logs.
        controls = [{"query_id": f"control-{i}", "sql": "select 1",
                     "kind": "synthetic", "note": "test"} for i in range(5)]
        queries = [{"query_id": f"query-{i}", "sql": "select 1",
                    "generator": "g1", "theme_index": 0} for i in range(412)]
        self.jsonl(self.root / "harness/controls.jsonl", controls)
        self.jsonl(self.root / "queries/test.jsonl", queries)
        items = controls + queries
        self.jsonl(self.out / "classify.jsonl",
                   [{"query_id": it["query_id"], "regexp_like_calls": [], "other_regex": {}}
                    for it in items])
        self.jsonl(self.out / "runs.jsonl",
                   [{"query_id": it["query_id"], "build": b, "rep": rep,
                     "status": "ok", "total_ms": 1, "logical_ms": 0.5, "physical_ms": 0.5}
                    for it in items for b in analyze.BUILDS for rep in (1, 2, 3)])
        (self.root / "logs/generation/summary.json").write_text("{}")
        (self.root / "harness/analyze.py").write_text("# synthetic source for hash\n")

    def analyze(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = analyze.main()
        return status, stdout.getvalue(), stderr.getvalue()

    def test_analyze_rejects_wrong_item_count_before_loading_logs(self):
        for count in (0, 2, 416, 418):
            with self.subTest(count=count):
                self.jsonl(self.root / "harness/controls.jsonl", [])
                self.jsonl(self.root / "queries/test.jsonl",
                           [{"query_id": str(i)} for i in range(count)])
                status, _, error = self.analyze()
                self.assertEqual(status, 1)
                self.assertIn(f"loaded {count} items; expected 417", error)
                self.assertFalse(self.results.exists())
                self.assertFalse(self.tables.exists())

    def test_analyze_writes_complete_new_outputs(self):
        self.fixture()
        status, _, error = self.analyze()
        self.assertEqual((status, error), (0, ""))
        validation = json.loads(self.results.read_text())["validation"]
        self.assertEqual(validation["expected_process_runs"], 2502)
        self.assertEqual(validation["recorded_process_runs"], 2502)
        self.assertTrue(validation["complete"])
        self.assertTrue(self.tables.exists())

    def test_analyze_preserves_historical_outputs(self):
        self.fixture()
        self.results.write_bytes(b"historical results\r\n")
        self.tables.write_bytes(b"historical tables\r\n")
        status, output, error = self.analyze()
        self.assertEqual((status, error), (0, ""))
        self.assertEqual(self.results.read_bytes(), b"historical results\r\n")
        self.assertEqual(self.tables.read_bytes(), b"historical tables\r\n")
        regenerated = self.root / "results.regenerated.json"
        self.assertTrue(json.loads(regenerated.read_text())["validation"]["complete"])
        self.assertIn("Queries extracted", (self.root / "logs/tables.regenerated.md").read_text())
        self.assertIn("Historical results.json was left unchanged", output)
        self.assertIn("Historical tables.md was left unchanged", output)

    def test_identical_historical_bytes_need_no_write(self):
        for path in (self.results, self.tables):
            with self.subTest(path=path.name):
                path.write_bytes(b"same bytes\n")
                with patch.object(pathlib.Path, "write_bytes", side_effect=AssertionError("unexpected write")):
                    self.assertEqual(write_output(path, "same bytes\n", preserve=True), path)
                self.assertFalse(path.with_name(f"{path.stem}.regenerated{path.suffix}").exists())

    def test_named_outputs_can_be_replaced(self):
        self.fixture()
        _, results, tables = paths(self.root, "replay")
        results.write_text("old replay")
        tables.parent.mkdir(parents=True)
        tables.write_text("old tables")
        with patch.multiple(analyze, RESULTS=results, TABLES=tables):
            status, _, error = self.analyze()
        self.assertEqual((status, error), (0, ""))
        self.assertTrue(json.loads(results.read_text())["validation"]["complete"])
        self.assertIn("Queries extracted", tables.read_text())
        self.assertFalse(self.results.exists())

    def comparison_fixture(self):
        return {"queries": [{"query_id": f"q{i}", "before": {"reps": 3}, "after": {"reps": 3}}
                            for i in range(412)],
                "controls": [{"query_id": f"c{i}", "before": {"reps": 3}, "after": {"reps": 3}}
                             for i in range(5)],
                "validation": {"result": "PASS"}}

    def test_compare_accepts_full_historical_schema(self):
        self.assertTrue(compare.complete(self.comparison_fixture()))

    def test_compare_refuses_invalid_files_without_writing(self):
        mutations = (
            (lambda r: r["queries"].pop(), "query count is 411; expected 412"),
            (lambda r: r["validation"].update(complete=False), "incomplete"),
            (lambda r: r["validation"].update(recorded_process_runs=2501), "expected 2502"),
            (lambda r: r["validation"].update(expected_process_runs=2496), "expected 2502"),
            (lambda r: r["queries"][0]["before"].update(reps=2), "incomplete repetitions"),
            (lambda r: r["queries"][0].update(query_id="q1"), "417 distinct item IDs"),
        )
        destination = self.root / "COMPARISON-replay.md"
        for filename in ("results.json", "results-replay.json"):
            for mutate, reason in mutations:
                with self.subTest(filename=filename, reason=reason):
                    old = self.comparison_fixture()
                    new = copy.deepcopy(old)
                    mutate(old if filename == "results.json" else new)
                    self.results.write_text(json.dumps(old))
                    (self.root / "results-replay.json").write_text(json.dumps(new))
                    with patch.object(compare, "HERE", self.root), patch("sys.argv", ["compare.py", "replay"]):
                        with self.assertRaises(SystemExit) as error:
                            compare.main()
                    self.assertIn(filename + ":", str(error.exception))
                    self.assertIn(reason, str(error.exception))
                    self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
