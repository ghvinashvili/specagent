"""The suite's lint, its minutes and its cost cap, the gate's workflow lines and the nightly script."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml
from harness import evals

ROOT = Path(__file__).resolve().parents[3]
NO_STAGE = "{}: no stage for role type critic in pipeline default; name `pipeline` and `stage`"
CODE = {"session": False, "role_type": None, "stage": None, "brief": None}
CAP_PROBLEM = "cost cap: b not started, $6.00 more would pass $4.00 (spent $3.00)"
GATE = "      - run: uv run harness eval --suite regression --baseline --threshold 1.0"
FAKE_UV = """#!/usr/bin/env bash
echo "$PWD|${HARNESS_EVAL_MAX_USD:-}|$*" >> "$NIGHTLY_LOG"
if [ "$2" = python ]; then echo 115; exit 0; fi
exit 3
"""
FAKE_TIMEOUT = """#!/usr/bin/env bash
echo "$*" >> "$NIGHTLY_LOG"
shift 3
exec "$@"
"""


def refuse(*args, **kwargs):
    raise AssertionError("nothing is graded or staged here")


def write_case(root: Path, name: str, **fields) -> Path:
    """A session case of root's regression suite (critic, stage attack) with its fixture and brief, unless fields
    say otherwise; a field set to None is left out."""
    d = root / "evals" / "regression" / name
    (d / "fixture").mkdir(parents=True)
    (d / "fixture" / "brief.md").write_text("# Brief\n", encoding="utf-8")
    task = {
        "schema_version": 1,
        "name": name,
        "suite": "regression",
        "role_type": "critic",
        "stage": "attack",
        "trials": 1,
        "timeout_minutes": 15,
        "max_budget_usd": 1,
        "fixture": "fixture",
        "brief": "fixture/brief.md",
        "graders": [{"type": "file_exists", "path": "stages/attack/output/critique.md"}],
        "pass_rule": "deterministic_all",
        **fields,
    }
    (d / "task.yaml").write_text(yaml.safe_dump({k: v for k, v in task.items() if v is not None}), encoding="utf-8")
    return d


@pytest.fixture()
def root(tmp_path, copy_config):
    r = tmp_path / "root"
    copy_config(ROOT, r, ("schemas", "docs/roles"))
    return r


@pytest.fixture()
def started(monkeypatch):
    """The names of the cases run_suite hands to suite_case, each answered as one passed trial."""
    names = []

    def fake(root, case_dir, task, results_dir, baseline, llm):
        names.append(task["name"])
        return {"task": task["name"], "trials": [{"trial": 1, "passed": True}], "passed": 1}

    monkeypatch.setattr(evals, "suite_case", fake)
    return names


def cap_cases(root: Path) -> None:
    write_case(root, "a", max_budget_usd=3)
    write_case(root, "b", trials=3, max_budget_usd=2)
    write_case(root, "c", max_budget_usd=1)
    write_case(root, "c1", **CODE)


def test_a_case_whose_stage_is_gone_is_named_and_one_whose_stage_exists_is_not(root):
    write_case(root, "stale", stage="critique")
    write_case(root, "fresh")
    assert evals.stale_cases(root, "regression") == [NO_STAGE.format("stale")]


def test_a_case_whose_pipeline_has_no_stage_table_is_named(root):
    write_case(root, "gone-pipeline", pipeline="retired")
    assert evals.stale_cases(root, "regression") == ["gone-pipeline: pipeline retired has no stage table"]


def test_a_file_a_case_names_that_is_gone_is_named_against_its_own_base(root):
    (root / "evals" / "rubrics").mkdir(parents=True)
    (root / "evals" / "rubrics" / "kept.md").write_text("# Kept\n", encoding="utf-8")
    (root / "evals" / "graders").mkdir(parents=True)
    (root / "evals" / "graders" / "kept.py").write_text("", encoding="utf-8")
    kept = [
        {"type": "llm", "rubric": "evals/rubrics/kept.md"},
        {"type": "python", "script": "evals/graders/kept.py"},
        {"type": "json_schema", "path": "stages/attack/result.json", "schema": "schemas/stages.schema.json"},
    ]
    gone = [
        {"type": "llm", "rubric": "evals/rubrics/gone.md"},
        {"type": "python", "script": "evals/graders/gone.py"},
        {"type": "json_schema", "path": "stages/attack/result.json", "schema": "schemas/gone.schema.json"},
        {"type": "file_exists", "path": "stages/attack/output/gone.md"},
    ]
    write_case(root, "kept-files", graders=kept)
    write_case(root, "gone-files", fixture="fixture-old", brief="fixture/old-brief.md", graders=gone)
    assert evals.stale_cases(root, "regression") == [
        "gone-files: brief fixture/old-brief.md does not exist",
        "gone-files: fixture fixture-old does not exist",
        "gone-files: rubric evals/rubrics/gone.md does not exist",
        "gone-files: schema schemas/gone.schema.json does not exist",
        "gone-files: script evals/graders/gone.py does not exist",
    ]


def test_a_case_without_a_session_is_never_staged(root, monkeypatch):
    monkeypatch.setattr(evals, "stage_row", refuse)
    write_case(root, "free", **{**CODE, "pipeline": "retired"})
    assert evals.stale_cases(root, "regression") == []


def test_the_case_option_selects_the_case_it_names(root):
    write_case(root, "stale-b", stage="critique")
    write_case(root, "stale-a", stage="critique")
    assert evals.stale_cases(root, "regression", "stale-b") == [NO_STAGE.format("stale-b")]
    assert evals.stale_cases(root, "regression") == [NO_STAGE.format("stale-a"), NO_STAGE.format("stale-b")]


def test_this_repository_has_no_stale_case():
    assert (evals.stale_cases(ROOT, "regression"), evals.stale_cases(ROOT, "capability")) == ([], [])


@pytest.mark.parametrize("mode", [{}, {"baseline": True}, {"sessions": False}])
def test_a_stale_case_stops_the_suite_before_a_trial_in_every_mode(root, monkeypatch, mode):
    monkeypatch.setattr(evals, "suite_case", refuse)
    write_case(root, "free", **CODE)
    write_case(root, "stale", stage="critique")
    out = evals.run_suite(root, "regression", threshold=1.0, **mode)
    assert out == {"ok": False, "problems": [NO_STAGE.format("stale")]}
    assert not (root / "evals" / "results").exists()


def test_suite_minutes_count_trials_sessions_and_minutes_of_each_session_case(root):
    write_case(root, "s1", trials=3, timeout_minutes=15)
    write_case(root, "s2", sessions=2, timeout_minutes=15)
    write_case(root, "s3", trials=None, timeout_minutes=10)
    write_case(root, "code", **{**CODE, "timeout_minutes": 99})
    tasks = [task for _, task in evals.load_cases(root, "regression", None)]
    assert [evals.case_minutes(task) for task in tasks] == [0, 45, 30, 10]
    assert (evals.suite_minutes(root, "regression"), evals.suite_minutes(root, "regression", "s2")) == (85, 30)


def test_within_cap_starts_what_fits_in_case_order_and_names_the_rest():
    cases = [
        (Path("c1"), {"name": "c1", "session": False, "max_budget_usd": 9}),
        (Path("a"), {"name": "a", "max_budget_usd": 3}),
        (Path("b"), {"name": "b", "trials": 3, "max_budget_usd": 2}),
        (Path("c"), {"name": "c", "max_budget_usd": 1}),
    ]
    chosen, problems, spent = evals.within_cap(cases, 4.0)
    assert ([task["name"] for _, task in chosen], problems, spent) == (["c1", "a", "c"], [CAP_PROBLEM], 4.0)
    budgets = [evals.case_budget(task) for _, task in cases]
    assert budgets + [evals.case_budget({"sessions": 2, "trials": 2, "max_budget_usd": 1.5})] == [0, 3, 6, 1, 6]
    assert evals.case_budget({"name": "no-budget"}) == 0


def test_the_cost_cap_leaves_out_what_would_pass_it_and_fails_the_suite(root, monkeypatch, started):
    monkeypatch.setenv("HARNESS_EVAL_MAX_USD", "4")
    cap_cases(root)
    out = evals.run_suite(root, "regression", threshold=1.0)
    assert started == ["a", "c", "c1"]
    assert (out["ok"], out["pass_rate"], out["max_usd"], out["spent_usd"]) == (False, 1.0, 4.0, 4.0)
    assert out["problems"] == [CAP_PROBLEM]


def test_a_cap_that_leaves_no_case_fails_before_a_trial(root, monkeypatch, started):
    monkeypatch.setenv("HARNESS_EVAL_MAX_USD", "0.5")
    write_case(root, "a")
    out = evals.run_suite(root, "regression", threshold=1.0)
    assert (started, out) == (
        [],
        {"ok": False, "problems": ["cost cap: a not started, $1.00 more would pass $0.50 (spent $0.00)"]},
    )


@pytest.mark.parametrize(
    ("cap", "mode", "names"),
    [
        ("4", {"baseline": True}, ["a", "b", "c", "c1"]),
        ("4", {"sessions": False}, ["c1"]),
        (None, {}, ["a", "b", "c", "c1"]),
    ],
)
def test_the_cost_cap_is_off_in_a_baseline_run_a_run_without_sessions_and_without_the_variable(
    root, monkeypatch, started, cap, mode, names
):
    monkeypatch.delenv("HARNESS_EVAL_MAX_USD", raising=False)
    if cap is not None:
        monkeypatch.setenv("HARNESS_EVAL_MAX_USD", cap)
    cap_cases(root)
    out = evals.run_suite(root, "regression", threshold=1.0, **mode)
    assert (started, out["ok"]) == (names, True)
    assert not {"max_usd", "spent_usd", "problems"} & set(out)


def test_ci_runs_the_tests_and_the_gate_on_every_push():
    lines = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8").splitlines()
    assert lines[1:5] == ["on:", "  pull_request:", "  push:", '    branches: ["**"]']
    assert lines[15:18] == [
        "      - run: uv run ruff check . && uv run ruff format --check .",
        "      - run: uv run pytest -q",
        GATE,
    ]


def test_no_workflow_starts_a_session_case():
    jobs = yaml.safe_load((ROOT / ".github" / "workflows" / "evals.yml").read_text(encoding="utf-8"))["jobs"]
    assert sorted(jobs) == ["instruction-version"]
    for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if "harness eval" in line:
                assert "--baseline" in line or "--no-sessions" in line, f"{path.name}: {line.strip()}"


@pytest.mark.parametrize(("cap", "shown"), [(None, "20"), ("7", "7")])
def test_the_nightly_script_runs_the_suite_under_its_minutes_and_the_cap(tmp_path, cap, shown):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, text in (("uv", FAKE_UV), ("timeout", FAKE_TIMEOUT)):
        (bin_dir / name).write_text(text, encoding="utf-8")
        (bin_dir / name).chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k != "HARNESS_EVAL_MAX_USD"}
    env |= {"PATH": f"{bin_dir}{os.pathsep}{env['PATH']}", "NIGHTLY_LOG": str(tmp_path / "calls.log")}
    if cap is not None:
        env["HARNESS_EVAL_MAX_USD"] = cap
    proc = subprocess.run(
        ["bash", str(ROOT / "evals" / "nightly.sh")], cwd=tmp_path, env=env, capture_output=True, text=True, check=False
    )
    measure, timeout, run = (tmp_path / "calls.log").read_text(encoding="utf-8").splitlines()
    assert (proc.returncode, proc.stderr) == (3, f"nightly: cap ${shown}, timeout 125 min\n")
    assert measure.startswith(f"{ROOT}|{cap or ''}|run python -c ") and "suite_minutes" in measure
    assert timeout == "-k 10 125m uv run harness eval --suite regression --threshold 1.0"
    assert run == f"{ROOT}|{shown}|run harness eval --suite regression --threshold 1.0"
