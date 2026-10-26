#!/usr/bin/env python3
"""Checks for the outcome parser: python3 -I test_make_results.py"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import make_results as mr  # noqa: E402

OK = "test a::b ... ok\n\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 9 filtered out; finished in 0.01s\n"
IGN = "test a::b ... ignored\n\ntest result: ok. 0 passed; 0 failed; 1 ignored; 0 measured; 9 filtered out; finished in 0.00s\n"
BAD = "test a::b ... ok\n\ntest result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 9 filtered out; finished in 0.01s\n"
NOSUM = "test a::b ... ok\n"
FAILED = "test a::b ... FAILED\n\ntest result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 9 filtered out; finished in 5.01s\n"

assert mr.cargo_outcome(OK, "b")[0] == "PASS"
assert mr.cargo_outcome(OK, "other")[0] == "UNKNOWN", "a passing run of a different test is not PASS"
assert mr.cargo_outcome(IGN, "b")[0] == "NO_TESTS_RUN", "an ignored-only run is not PASS"
assert mr.cargo_outcome(BAD, "b")[0] == "UNKNOWN", "summary/per-test disagreement is not PASS"
assert mr.cargo_outcome(NOSUM, "b")[0] == "UNKNOWN", "no summary line is not PASS"
assert mr.cargo_outcome(FAILED, "b")[0] == "FAIL"
assert mr.cargo_outcome("error[E0433]: failed\nerror: could not compile `x`\n", "b")[0] == "COMPILE_ERROR"
assert mr.expected_cargo_test("cargo test --locked --profile ci -p datafusion --test core_integration my_test") == "my_test"
assert mr.expected_cargo_test("cargo test --locked --profile ci -p x --lib my_test -- --nocapture") == "my_test"
assert mr.expected_maven_tests("./mvnw -pl m -Dtest=A,B#c clean package") == ["A", "B#c"]
assert mr.expected_cargo_test(
    "cargo test --locked --profile ci --no-fail-fast -p a -p b --lib my_test"
) == "my_test", "several -p values are skipped"

# SETUP_ERROR: a record with setup_error is never parsed as a test run, whatever its log says
SETUP_LOG = (
    "# case: c\n# command (not run): cargo test -p x --lib t\n"
    "# setup error: step failed: apply patches/p.patch (exit 1)\n# setup output:\n"
    "#   $ apply patches/p.patch\n#   error: patch failed: a.rs:10\n# end: x\n# exit code: 1\n"
)
rec = {"command": "cargo test -p x --lib t", "setup_error": "apply patches/p.patch"}
outcome, tests, detail, expected = mr.derive(rec, SETUP_LOG + OK, None)
assert outcome == "SETUP_ERROR" and tests == [] and expected == "t"
assert detail[0] == "setup step failed: apply patches/p.patch"
assert "error: patch failed: a.rs:10" in detail, detail
assert mr.derive({"command": "cargo test -p x --lib b"}, OK, None)[0] == "PASS"
rec_mvn = {"command": "./mvnw -pl m -Dtest=A clean package", "setup_error": "find JDK 8"}
assert mr.derive(rec_mvn, "# setup output:\n", None)[:2] == ("SETUP_ERROR", [])


# comparisons
def run(case, side, outcome, inv=None):
    r = {"case": case, "side": side, "outcome": outcome}
    if inv:
        r["invocation"] = inv
    return r


def req(inv, *cases):
    return {"invocation": inv, "sides": [{"case": c, "side": s} for c in cases for s in ("before", "after")]}


# historical records without requests: unchanged rule
c = mr.compare([run("a", "before", "FAIL"), run("a", "after", "PASS"), run("b", "before", "PASS")], [])
assert c["a"] == {"before": "FAIL", "after": "PASS", "comparison": "complete"}
assert c["b"] == {"before": "PASS", "comparison": "incomplete"}
# a requested side without a record from that invocation is missing
c = mr.compare([run("a", "before", "FAIL", "i1")], [req("i1", "a")])
assert c["a"]["comparison"] == "incomplete" and c["a"]["missing"] == ["after (invocation i1)"]
# a requested case with no record at all appears as incomplete
c = mr.compare([], [req("i1", "z")])
assert c["z"] == {"missing": ["before (invocation i1)", "after (invocation i1)"], "comparison": "incomplete"}
# both sides recorded in the requesting invocation: complete
c = mr.compare([run("a", "before", "FAIL", "i1"), run("a", "after", "PASS", "i1")], [req("i1", "a")])
assert c["a"] == {"before": "FAIL", "after": "PASS", "comparison": "complete"}
# a setup error leaves the case incomplete even though both sides have records
c = mr.compare([run("a", "before", "SETUP_ERROR", "i1"), run("a", "after", "PASS", "i1")], [req("i1", "a")])
assert c["a"]["comparison"] == "incomplete"
# records from an older invocation do not satisfy the latest request
c = mr.compare(
    [run("a", "before", "FAIL", "i1"), run("a", "after", "PASS", "i1"), run("a", "before", "FAIL", "i2")],
    [req("i1", "a"), req("i2", "a")],
)
assert c["a"]["comparison"] == "incomplete" and c["a"]["missing"] == ["after (invocation i2)"]
# a later complete invocation supersedes an earlier incomplete one
c = mr.compare(
    [run("a", "before", "FAIL", "i1"), run("a", "before", "FAIL", "i2"), run("a", "after", "PASS", "i2")],
    [req("i1", "a"), req("i2", "a")],
)
assert c["a"]["comparison"] == "complete" and "missing" not in c["a"]

skipped = pathlib.Path(__file__).resolve().parent / "_tmp_surefire"
skipped.mkdir(exist_ok=True)
(skipped / "TEST-x.xml").write_text(
    '<testsuite><testcase classname="p.A" name="m" time="0"><skipped/></testcase></testsuite>'
)
try:
    assert mr.maven_outcome("BUILD SUCCESS", skipped, "m", ["A"])[0] == "NO_TESTS_RUN"
    (skipped / "TEST-x.xml").write_text(
        '<testsuite><testcase classname="p.A" name="m" time="0"/></testsuite>'
    )
    assert mr.maven_outcome("BUILD SUCCESS", skipped, "m", ["A"])[0] == "PASS"
    assert mr.maven_outcome("BUILD SUCCESS", skipped, "m", ["A#other"])[0] == "UNKNOWN"
    assert mr.maven_outcome("BUILD SUCCESS", skipped, "m", ["B"])[0] == "UNKNOWN"
finally:
    for f in skipped.iterdir():
        f.unlink()
    skipped.rmdir()
print("ok")
