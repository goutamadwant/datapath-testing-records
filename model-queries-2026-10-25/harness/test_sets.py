"""Small offline checks for measurement paths and process-run completeness."""
import contextlib
import copy
import hashlib
import importlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import analyze
import compare
import measure
from classifications import load_classifications
from measurement_sets import inputs_sha256, paths, prepare_manifest, write_output


class MeasurementSetsTest(unittest.TestCase):
    def test_canonical_input_hash_covers_full_records_and_order(self):
        items = [{"sql": "select 'é'", "query_id": "q", "metadata": {"z": 1, "a": 2}}]
        canonical = '[{"metadata":{"a":2,"z":1},"query_id":"q","sql":"select \'é\'"}]'
        self.assertEqual(inputs_sha256(items), hashlib.sha256(canonical.encode("utf-8")).hexdigest())
        self.assertEqual(inputs_sha256(items), inputs_sha256([dict(reversed(list(items[0].items())))]))
        other = {"query_id": "other", "sql": "select 1"}
        self.assertNotEqual(inputs_sha256(items + [other]), inputs_sha256([other] + items))

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
        self.assertEqual(manifest["inputs_sha256"], inputs_sha256(self.items))
        self.assertEqual(manifest["inputs_file"], "inputs.jsonl")
        self.assertEqual(manifest["inputs_binding"], "recorded at first run")
        self.assertEqual(json.loads((self.out / "inputs.jsonl").read_text()), {
            "id": "test-item", "sha256": hashlib.sha256(
                b'{"query_id":"test-item","sql":"select 1"}').hexdigest(), "position": 0})
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

    def test_resume_refuses_changed_sql_without_writing_or_reusing(self):
        self.invoke()
        retained = {p: p.read_bytes() for p in self.out.iterdir()}
        self.items[0]["sql"] = "select 2"
        self.process.reset_mock()
        with self.assertRaisesRegex(SystemExit, "input-identity error.*test-item"):
            self.invoke(resume=True)
        self.process.assert_not_called()
        self.assertEqual({p: p.read_bytes() for p in self.out.iterdir()}, retained)

    def test_fresh_set_executes_changed_sql(self):
        self.invoke()
        self.items[0]["sql"] = "select 2"
        self.process.reset_mock()
        with patch.object(measure, "OUT", self.root / "logs/changed-set"):
            self.assertIn("executed 6 process runs, reused 0 recorded runs", self.invoke())
        self.assertEqual(self.process.call_count, 6)
        self.assertTrue(all(call.args[1] == "select 2" for call in self.process.call_args_list))

    def test_interrupted_classification_never_publishes_partial_file(self):
        self.items.extend([{"query_id": "second-item", "sql": "select 2"}])
        original_factory = tempfile.NamedTemporaryFile
        for during_record in (False, True):
            with self.subTest(during_record=during_record):
                self.out.mkdir(parents=True, exist_ok=True)
                final = self.out / "classify.jsonl"
                final.write_text("retained partial classification\n")

                @contextlib.contextmanager
                def interrupted_file(**kwargs):
                    with original_factory(**kwargs) as fh:
                        class InterruptedWriter:
                            name = fh.name
                            writes = 0

                            def write(self, data):
                                self.writes += 1
                                if self.writes == 2:
                                    if during_record:
                                        fh.write(data[:len(data) // 2])
                                    raise KeyboardInterrupt
                                return fh.write(data)
                        yield InterruptedWriter()

                with patch.object(measure.tempfile, "NamedTemporaryFile", interrupted_file), \
                        contextlib.redirect_stdout(io.StringIO()), self.assertRaises(KeyboardInterrupt):
                    measure.classify_all(self.items)
                self.assertEqual(final.read_text(), "retained partial classification\n")
                self.assertEqual(list(self.out.glob(".classify-*.tmp")), [])
                with contextlib.redirect_stdout(io.StringIO()):
                    measure.classify_all(self.items)
                self.assertEqual(len(load_classifications(final, self.items)), 2)
                self.process.assert_not_called()


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

    def bind_inputs(self, items):
        binaries = {}
        plan_time = self.root / "harness/plan_time"
        plan_time.mkdir(exist_ok=True)
        for label in analyze.BUILDS:
            binary = self.root / f"work/target/release/plan_time_{label}"
            binary.parent.mkdir(parents=True, exist_ok=True)
            binary.write_text('#!/usr/bin/env python3\nimport json\n'
                              'print(json.dumps({"status": "ok", "total_ms": 1, '
                              '"logical_ms": 0.5, "physical_ms": 0.5}))\n')
            binary.chmod(0o755)
            binaries[label] = binary
            (plan_time / f"Cargo.lock.{label}").write_text(f"lock {label}\n")
        (plan_time / "TOOLCHAIN.expected").write_text("rustc test\n")
        prepare_manifest(self.root, self.out, binaries, items, "test start", resume=False)
        return binaries

    def fixture(self):
        # Minimal synthetic SQL and timings; no measurements or real logs.
        controls = [{"query_id": f"control-{i}", "sql": "select 1",
                     "kind": "synthetic", "note": "test"} for i in range(5)]
        queries = [{"query_id": f"query-{i}", "sql": "select 1",
                    "generator": "g1", "theme_index": 0} for i in range(412)]
        self.jsonl(self.root / "harness/controls.jsonl", controls)
        self.jsonl(self.root / "queries/test.jsonl", queries)
        items = controls + queries
        self.binaries = self.bind_inputs(items)
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
                self.bind_inputs([{"query_id": str(i)} for i in range(count)])
                status, _, error = self.analyze()
                self.assertEqual(status, 1)
                self.assertIn(f"loaded {count} items; expected 417", error)
                self.assertFalse(self.results.exists())
                self.assertFalse(self.tables.exists())
                (self.out / "manifest.json").unlink()
                (self.out / "inputs.jsonl").unlink()

    def measure(self, out=None, resume=True):
        output = io.StringIO()
        with patch.multiple(measure, HERE=self.root, OUT=out or self.out, BIN=self.binaries), \
                patch.dict(os.environ, {"MEASURE_RESUME": "1" if resume else "0"}), \
                contextlib.redirect_stdout(output):
            measure.main()
        return output.getvalue()

    def snapshot(self):
        return {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def test_unchanged_resume_analysis_and_changed_query(self):
        self.fixture()
        with patch.object(measure, "run_one") as process:
            self.assertIn("executed 0 process runs, reused 2502 recorded runs", self.measure())
            process.assert_not_called()
        self.assertEqual(self.analyze()[0], 0)

        query_file = self.root / "queries/test.jsonl"
        queries = [json.loads(line) for line in query_file.read_text().splitlines()]
        queries[0]["sql"] = "select 2"
        self.jsonl(query_file, queries)
        retained = self.snapshot()
        with patch.object(measure, "run_one") as process, \
                patch.object(measure, "classify_all") as classify, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaisesRegex(SystemExit, "input-identity error.*query-0"):
                self.measure()
            process.assert_not_called()
            classify.assert_not_called()
            self.assertNotIn("reused", output.getvalue())
        status, output, error = self.analyze()
        self.assertEqual(status, 1)
        self.assertIn("input-identity error", error)
        self.assertIn("query-0", error)
        self.assertEqual(output, "")
        self.assertEqual(self.snapshot(), retained)

        fresh = self.root / "logs/changed-set"
        timing = {"status": "ok", "total_ms": 2, "logical_ms": 1, "physical_ms": 1}
        with patch.object(measure, "run_one", return_value=timing) as process:
            self.assertIn("executed 2502 process runs, reused 0 recorded runs",
                          self.measure(out=fresh, resume=False))
            self.assertEqual(process.call_count, 2502)
            self.assertEqual(sum(call.args[1] == "select 2" for call in process.call_args_list), 6)
        self.assertNotEqual(json.loads((fresh / "manifest.json").read_text())["inputs_sha256"],
                            json.loads((self.out / "manifest.json").read_text())["inputs_sha256"])
        with patch.multiple(analyze, OUT=fresh, RESULTS=self.root / "results-changed-set.json",
                            TABLES=fresh / "tables.md"):
            self.assertEqual(self.analyze()[0], 0)
        result = json.loads((self.root / "results-changed-set.json").read_text())
        self.assertEqual(result["queries"][0]["sql"], "select 2")
        self.assertEqual(result["queries"][0]["before"]["time_ms"], 2)

    def test_partial_classification_resume_and_results_commands(self):
        self.fixture()
        # Execute the documented shell commands against a standalone temporary copy.
        source = pathlib.Path(__file__).resolve().parent
        for path in source.glob("*.py"):
            shutil.copy2(path, self.root / "harness" / path.name)
        shutil.copy2(source.parent / "run.sh", self.root / "run.sh")
        classification = self.out / "classify.jsonl"
        complete = classification.read_text().splitlines(keepends=True)
        runs = self.out / "runs.jsonl"
        retained = runs.read_text().splitlines(keepends=True)[:-2]
        env = {**os.environ, "MEASURE_SET": "measure", "MEASURE_RESUME": "1",
               "RUN_WORK": str(self.root / "work"), "PYTHONDONTWRITEBYTECODE": "1"}
        for interruption in ("between records", "during record"):
            with self.subTest(interruption=interruption):
                partial = complete[0] + (complete[1][:20] if interruption == "during record" else "")
                classification.write_text(partial)
                runs.write_text("".join(retained))
                bad = subprocess.run(["./run.sh", "results"], cwd=self.root, env=env,
                                     capture_output=True, text=True, timeout=30)
                self.assertEqual(bad.returncode, 1, bad.stdout + bad.stderr)
                self.assertIn("classification completeness error", bad.stderr)
                self.assertNotIn("KeyError", bad.stderr)
                resumed = subprocess.run(["./run.sh", "measure"], cwd=self.root, env=env,
                                         capture_output=True, text=True, timeout=30)
                self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
                self.assertIn("regenerating all 417 classifications before planning", resumed.stdout)
                self.assertIn("executed 2 process runs, reused 2500 recorded runs", resumed.stdout)
                items = [json.loads(line) for path in
                         (self.root / "harness/controls.jsonl", self.root / "queries/test.jsonl")
                         for line in path.read_text().splitlines()]
                self.assertEqual(len(load_classifications(classification, items)), 417)
                self.assertEqual(len(classification.read_text().splitlines()), 417)
                lines = runs.read_text().splitlines(keepends=True)
                self.assertEqual(lines[:2500], retained)
                records = [json.loads(line) for line in lines]
                keys = {(r["query_id"], r["build"], r["rep"]) for r in records}
                self.assertEqual(len(records), 2502)
                self.assertEqual(len(keys), 2502)
                results = subprocess.run(["./run.sh", "results"], cwd=self.root, env=env,
                                         capture_output=True, text=True, timeout=30)
                self.assertEqual(results.returncode, 0, results.stdout + results.stderr)
                self.assertTrue(json.loads(self.results.read_text())["validation"]["complete"])

    def test_invalid_classification_is_rejected_and_regenerated(self):
        self.fixture()
        path = self.out / "classify.jsonl"
        original = path.read_text()
        records = original.splitlines(keepends=True)
        for invalid in (None, records[0], records[0] + '{"query_id":', original + records[0],
                        original.replace('"query-0"', '"unexpected"'),
                        original.replace(records[0], '[]\n'), original + '\n',
                        original.replace('"regexp_like_calls": []', '"regexp_like_calls": null', 1)):
            with self.subTest(invalid=invalid[:80] if invalid else "missing"):
                if invalid is None:
                    path.unlink()
                else:
                    path.write_text(invalid)
                retained_runs = (self.out / "runs.jsonl").read_bytes()
                status, _, diagnostic = self.analyze()
                self.assertEqual(status, 1)
                self.assertIn("classification completeness error", diagnostic)
                with patch.object(measure, "run_one") as process:
                    self.assertIn("regenerating all 417 classifications", self.measure())
                    process.assert_not_called()
                with patch.object(measure, "HERE", self.root):
                    items = measure.load_items()
                self.assertEqual(len(load_classifications(path, items)), 417)
                self.assertEqual((self.out / "runs.jsonl").read_bytes(), retained_runs)
                self.assertEqual(self.analyze()[0], 0)

    def test_control_metadata_and_order_changes_are_rejected(self):
        self.fixture()
        path = self.root / "harness/controls.jsonl"
        original = path.read_bytes()
        for change in ("sql", "note", "order", "removed"):
            with self.subTest(change=change):
                controls = [json.loads(line) for line in original.splitlines()]
                if change == "order":
                    controls[0], controls[1] = controls[1], controls[0]
                elif change == "removed":
                    controls.pop(0)
                else:
                    controls[0][change] = "changed"
                self.jsonl(path, controls)
                retained = self.snapshot()
                with self.assertRaisesRegex(SystemExit, "input-identity error.*control-0"):
                    self.measure()
                status, _, error = self.analyze()
                self.assertEqual(status, 1)
                self.assertIn("input-identity error", error)
                self.assertIn("control-0", error)
                self.assertEqual(self.snapshot(), retained)
        path.write_bytes(original)

    def test_missing_input_binding_fails_without_writing(self):
        self.fixture()
        for filename in ("inputs.jsonl", "manifest.json"):
            path = self.out / filename
            original = path.read_bytes()
            path.unlink()
            retained = self.snapshot()
            status, _, error = self.analyze()
            self.assertEqual(status, 1)
            self.assertIn("input-identity error", error)
            self.assertEqual(self.snapshot(), retained)
            path.write_bytes(original)

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

    def test_named_outputs_are_preserved(self):
        self.fixture()
        _, results, tables = paths(self.root, "replay")
        results.write_text("old replay")
        tables.parent.mkdir(parents=True)
        tables.write_text("old tables")
        with patch.multiple(analyze, RESULTS=results, TABLES=tables):
            status, _, error = self.analyze()
        self.assertEqual((status, error), (0, ""))
        self.assertEqual(results.read_text(), "old replay")
        regenerated = results.with_name("results-replay.regenerated.json")
        self.assertTrue(json.loads(regenerated.read_text())["validation"]["complete"])
        self.assertEqual(tables.read_text(), "old tables")
        self.assertIn("Queries extracted", tables.with_name("tables.regenerated.md").read_text())
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
