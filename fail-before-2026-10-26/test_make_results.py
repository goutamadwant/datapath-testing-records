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
