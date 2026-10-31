"""Cases without a session, graded by code (`harness eval --no-sessions`), and a stale case that stops the suite."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml
from harness import cli, evals

ROOT = Path(__file__).resolve().parents[3]
CHECK_OK = "import pathlib, sys\nsys.exit(0 if (pathlib.Path(sys.argv[1]) / 'ok.txt').is_file() else 1)\n"
SESSION = {"session": None, "role_type": "critic", "stage": "attack"}
CODE_CASES = [
    "pipeline-ancestor-deny",
    "pipeline-cited-lines",
    "pipeline-commit-has-pages",
    "pipeline-control-files",
    "pipeline-disjoint-files",
    "pipeline-expected-lines",
    "pipeline-generated-files",
    "pipeline-handoff-pointers",
    "pipeline-job-timeouts",
    "pipeline-lock-with-deps",
    "pipeline-summaries-and-sizes",
    "pipeline-tests-can-fail",
    "pipeline-waiters",
    "pipeline-write-gate-refuses",
]
MODEL_CASES = ["pipeline-critic-unproven-finding", "pipeline-handoff-carries-facts", "pipeline-verifier-planted-defect"]
NO_STAGE = "{}: no stage for role type critic in pipeline default; name `pipeline` and `stage`"


def refuse(*args, **kwargs):
    raise AssertionError("a case without a session is neither staged nor started")


def no_sessions(monkeypatch) -> None:
    """No session starts, and a case without a session is never staged (the suite's lint stages the others)."""
    stage_row = evals.stage_row

    def staged(root: Path, task: dict) -> tuple[str, dict]:
        if task.get("session") is False:
            refuse()
        return stage_row(root, task)

    monkeypatch.setattr(evals, "run_trial", refuse)
    monkeypatch.setattr(evals, "stage_row", staged)


def case(root: Path, name: str, ok: bool = True, **fields) -> Path:
    """A case of root's regression suite: without a session and graded by check_ok.py, unless fields say otherwise."""
    d = root / "evals" / "regression" / name
    (d / "fixture").mkdir(parents=True)
    if ok:
        (d / "fixture" / "ok.txt").write_text("ok\n", encoding="utf-8")
    task = {
        "schema_version": 1,
        "name": name,
        "suite": "regression",
        "session": False,
        "trials": 1,
        "fixture": "fixture",
        "graders": [{"type": "python", "base": "workspace", "script": "evals/graders/check_ok.py", "args": ["."]}],
        "pass_rule": "deterministic_all",
        **fields,
    }
    (d / "task.yaml").write_text(yaml.safe_dump({k: v for k, v in task.items() if v is not None}), encoding="utf-8")
    return d


@pytest.fixture()
def root(tmp_path):
    r = tmp_path / "root"
    (r / "evals" / "graders").mkdir(parents=True)
    (r / "evals" / "graders" / "check_ok.py").write_text(CHECK_OK, encoding="utf-8")
    return r


def test_a_case_without_a_session_is_graded_by_code_on_a_copy_of_its_fixture(root, monkeypatch):
    no_sessions(monkeypatch)
    case(root, "free-a")
    out = evals.run_suite(root, "regression", threshold=1.0)
    trial = root / out["results"] / "free-a" / "trial-1"
    assert (out["ok"], out["pass_rate"], out["tasks"][0]["role_type"]) == (True, 1.0, "none")
    assert out["tasks"][0]["trials"] == [{"trial": 1, "passed": True, "llm_score": None, "llm_skipped": False}]
    assert (trial / "workspace" / "ok.txt").is_file()
    assert json.loads((trial / "grades.json").read_text(encoding="utf-8"))["session"] is False


def test_a_failing_grader_fails_its_case_and_the_threshold(root, monkeypatch):
    no_sessions(monkeypatch)
    case(root, "free-a")
    case(root, "free-b", ok=False)
    out = evals.run_suite(root, "regression", threshold=0.9)
    assert (out["ok"], out["pass_rate"]) == (False, 0.5)
    assert [(t["task"], t["passed"]) for t in out["tasks"]] == [("free-a", 1), ("free-b", 0)]


def test_a_case_without_a_session_has_one_trial_whatever_trials_says(root, monkeypatch):
    no_sessions(monkeypatch)
    case(root, "free-a", trials=3)
    out = evals.run_suite(root, "regression")
    assert [t["trial"] for t in out["tasks"][0]["trials"]] == [1]


def test_without_sessions_the_session_cases_are_left_out_and_named(root, monkeypatch, copy_config):
    no_sessions(monkeypatch)
    copy_config(ROOT, root, ("schemas", "docs/roles"))
    case(root, "free-a")
    case(root, "sess-b", **SESSION)
    case(root, "sess-a", **SESSION)
    out = evals.run_suite(root, "regression", threshold=1.0, sessions=False)
    assert ([t["task"] for t in out["tasks"]], out["skipped"], out["ok"]) == (["free-a"], ["sess-a", "sess-b"], True)


def test_without_sessions_a_suite_of_session_cases_says_so(root, monkeypatch, copy_config):
    no_sessions(monkeypatch)
    copy_config(ROOT, root, ("schemas", "docs/roles"))
    case(root, "sess-a", **SESSION)
    out = evals.run_suite(root, "regression", sessions=False)
    assert out == {"ok": False, "problems": ["no case without a session in evals/regression"]}


def test_a_baseline_run_grades_a_case_without_a_session_and_writes_no_results(root, monkeypatch):
    no_sessions(monkeypatch)
    case(root, "free-a")
    out = evals.run_suite(root, "regression", threshold=1.0, baseline=True)
    assert out["tasks"][0]["trials"] == [{"trial": "baseline", "passed": True, "llm_score": None, "llm_skipped": False}]
    assert not (root / "evals" / "results").exists()


@pytest.mark.parametrize("mode", [{"baseline": True}, {"baseline": False}, {"sessions": False}])
def test_a_session_case_whose_stage_is_gone_stops_the_suite(root, monkeypatch, copy_config, mode):
    monkeypatch.setattr(evals, "run_trial", refuse)
    monkeypatch.setattr(evals, "free_trial", refuse)
    copy_config(ROOT, root, ("schemas", "docs/roles"))
    case(root, "free-a")
    case(root, "stale-stage", **{**SESSION, "stage": "critique"})
    out = evals.run_suite(root, "regression", **mode)
    assert out == {"ok": False, "problems": [NO_STAGE.format("stale-stage")]}


def test_the_repository_suite_without_sessions_grades_its_fourteen_code_cases(tmp_path, monkeypatch, copy_config):
    no_sessions(monkeypatch)
    shutil.copytree(ROOT / "evals", tmp_path / "evals", ignore=shutil.ignore_patterns("results"))
    copy_config(ROOT, tmp_path, ("schemas", "docs/roles"))
    out = evals.run_suite(tmp_path, "regression", threshold=1.0, sessions=False)
    assert ([t["task"] for t in out["tasks"]], out["ok"]) == (CODE_CASES, True)
    assert out["skipped"] == sorted(["cache-share-reader", "reader-quotes-locations", *MODEL_CASES])


def test_every_pipeline_case_is_strict_and_graded_by_code():
    suite = ROOT / "evals" / "regression"
    cases = {p.parent.name: yaml.safe_load(p.read_text(encoding="utf-8")) for p in suite.glob("pipeline-*/task.yaml")}
    assert sorted(cases) == sorted([*CODE_CASES, *MODEL_CASES])
    for name, task in cases.items():
        assert (task["name"], task["pass_rule"]) == (name, "deterministic_all")
        assert "llm" not in [g["type"] for g in task["graders"]]
        if task.get("session") is False:
            assert "role_type" not in task
            assert (suite / name / "fixture" / "expect.json").is_file()
        else:
            assert task["trials"] == 1
            assert (suite / name / "assignment.md").is_file()
            assert (ROOT / "evals" / "baseline" / name / "run").is_dir()


def test_the_repository_suite_passes_all_its_baselines():
    out = evals.run_suite(ROOT, "regression", threshold=1.0, baseline=True)
    failed = {t["task"]: t["trials"] for t in out["tasks"] if not t["passed"]}
    assert (len(out["tasks"]), out["pass_rate"], out["ok"], failed) == (19, 1.0, True, {})


def test_eval_no_sessions_reaches_the_suite(monkeypatch, capsys):
    seen = {}

    def fake(root, suite, **kwargs):
        seen.update(kwargs, suite=suite)
        return {"ok": True}

    monkeypatch.setattr(evals, "run_suite", fake)
    assert cli.main(["eval", "--suite", "regression", "--no-sessions", "--threshold", "1.0"]) == 0
    assert seen == {"suite": "regression", "case": None, "threshold": 1.0, "baseline": False, "sessions": False}
    assert json.loads(capsys.readouterr().out) == {"ok": True}


def test_adr_0028_records_the_pipeline_evals():
    text = (ROOT / "docs" / "decisions" / "0028-pipeline-evals.md").read_text(encoding="utf-8")
    listing = (ROOT / "docs" / "decisions" / "README.md").read_text(encoding="utf-8")
    assert text.startswith("---\nstatus: accepted\n")
    for phrase in ("session: false", "--no-sessions", "pipeline-report", "evals/baseline/pipeline/earlier-run.json"):
        assert phrase in text
    assert "(0028-pipeline-evals.md)" in listing


def test_just_evals_runs_the_session_free_suite_and_the_report():
    lines = (ROOT / "justfile").read_text(encoding="utf-8").splitlines()
    at = lines.index("evals run_dir:")
    assert [line.strip() for line in lines[at + 1 : at + 3]] == [
        "uv run harness eval --suite regression --no-sessions --threshold 1.0",
        "uv run harness pipeline-report {{run_dir}}",
    ]
    assert lines[at + 1].startswith("    ") and lines[at - 1].startswith("# ")
    assert at + 3 == len(lines) or not lines[at + 3].startswith(" ")
