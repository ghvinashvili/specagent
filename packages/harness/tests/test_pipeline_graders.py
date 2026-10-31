"""The code graders of the pipeline evals: one case per known error class, a hand-over note against its facts."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "evals" / "graders" / "pipeline_plan.py"
NOTE = ROOT / "evals" / "graders" / "pipeline_note.py"
CASES = sorted(p.parents[1] for p in (ROOT / "evals" / "regression").glob("pipeline-*/fixture/expect.json"))
FENCE = "`" * 3
PLANTED = "x.md:1: a defect nobody planted"
FACTS = {
    "role": "planner",
    "task": 3,
    "facts": [
        "uv run pytest -q tests/test_dates.py",
        "4 passed",
        "src/dates.py:14",
        "pyproject.toml:31",
        "7f3c2a1",
        "C12",
    ],
}
GOOD_NOTE = (
    "HANDOFF planner after Task 3 — 2026-10-29 09:47\n"
    "State: Task 3 is committed as 7f3c2a1; the next unit is Task 4, which extends parse_day at src/dates.py:14.\n"
    "Check: uv run pytest -q tests/test_dates.py prints 4 passed.\n"
    "Trap: pyproject.toml:31 pins the old parser; leave it.\n"
    "Open: C12 waits for the critic.\n"
)
LINE_1 = 'line 1 is not "HANDOFF planner after Task 3 — <YYYY-MM-DD HH:MM>"'


def run(*args: object, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, check=False, cwd=cwd)


def workspace(case: Path, tmp_path: Path) -> Path:
    """A copy of the case's fixture, as `harness eval` grades it."""
    return Path(shutil.copytree(case / "fixture", tmp_path / "workspace"))


def test_fourteen_cases_are_graded_by_code():
    assert [c.name for c in CASES] == [
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


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_a_case_passes_and_prints_its_findings_sorted(case, tmp_path):
    ws = workspace(case, tmp_path)
    found = json.loads((ws / "expect.json").read_text(encoding="utf-8"))["found"]
    proc = run(PLAN, ws)
    assert (proc.returncode, proc.stdout.splitlines(), proc.stderr) == (0, sorted(found), "")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_a_case_fails_when_a_finding_is_dropped_or_one_is_added(case, tmp_path):
    ws = workspace(case, tmp_path)
    expect = json.loads((ws / "expect.json").read_text(encoding="utf-8"))
    first = expect["found"][0]
    expect["found"] = [*expect["found"][1:], PLANTED]
    (ws / "expect.json").write_text(json.dumps(expect), encoding="utf-8")
    proc = run(PLAN, ws)
    assert (proc.returncode, proc.stderr.splitlines()) == (1, [f"missing: {PLANTED}", f"unexpected: {first}"])


def test_measure_mode_names_each_input_as_given_and_exits_by_its_findings(tmp_path):
    (tmp_path / "bad.md").write_text(f"# Task 1 — T\n{FENCE}bash\nuv run pytest -q\n{FENCE}\n", encoding="utf-8")
    good = f"# Task 1 — T\n{FENCE}bash\nuv run pytest -q\n{FENCE}\nExpected: `1 passed`.\n"
    (tmp_path / "good.md").write_text(good, encoding="utf-8")
    bad_run = run(PLAN, "--check", "expected-lines", "--root", tmp_path, "bad.md", cwd=tmp_path)
    good_run = run(PLAN, "--check", "expected-lines", "--root", tmp_path, "good.md", cwd=tmp_path)
    assert (bad_run.returncode, bad_run.stdout) == (1, "bad.md:2: a command block without an Expected: line\n")
    assert (good_run.returncode, good_run.stdout) == (0, "")


def test_a_citation_inside_a_fence_is_no_citation(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    text = f"# Task 1 — T\n\n{FENCE}text\n`a.py:2` inside a fence\n{FENCE}\n- [ ] Read `a.py:3`.\n"
    (tmp_path / "t.md").write_text(text, encoding="utf-8")
    proc = run(PLAN, "--check", "cited-lines", "--root", tmp_path, "t.md", cwd=tmp_path)
    assert (proc.returncode, proc.stdout) == (1, "t.md:6: cites a.py:3 past the file's 1 lines\n")


def test_a_glob_of_one_builder_overlaps_the_files_of_the_other(tmp_path):
    rows = [
        "## Task order",
        "| Task | title | builder | depends_on | files | milestone |",
        "|---|---|---|---|---|---|",
        "| 1 | Code | a | — | `src/{x,y}.py` | M1 |",
        "| 2 | Lint | b | — | `src/*.py` | M1 |",
    ]
    (tmp_path / "00-index.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    proc = run(PLAN, "--check", "disjoint-files", "--root", tmp_path, "00-index.md", cwd=tmp_path)
    assert proc.stdout.splitlines() == [
        "00-index.md:4: Task 1 (builder a) and Task 2 (builder b) both list src/x.py",
        "00-index.md:4: Task 1 (builder a) and Task 2 (builder b) both list src/y.py",
    ]


def test_a_python_input_is_read_whole(tmp_path):
    (tmp_path / "test_a.py").write_text("def test_a():\n    assert 1\n", encoding="utf-8")
    proc = run(PLAN, "--check", "tests-can-fail", "--root", tmp_path, "test_a.py", cwd=tmp_path)
    assert (proc.returncode, proc.stdout) == (1, "test_a.py:2: test_a asserts a constant\n")


def test_a_dependency_added_to_a_workspace_member_needs_the_root_lock(tmp_path):
    def added(path: str) -> str:
        head = f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -5,3 +5,4 @@ dependencies = [\n"
        return head + '     "pyyaml>=6",\n+    "httpx>=0.27",\n ]\n'

    lock = 'diff --git a/uv.lock b/uv.lock\n--- a/uv.lock\n+++ b/uv.lock\n@@ -1,3 +1,4 @@\n+name = "httpx"\n'
    (tmp_path / "member.diff").write_text(added("packages/harness/pyproject.toml"), encoding="utf-8")
    (tmp_path / "locked.diff").write_text(added("packages/harness/pyproject.toml") + lock, encoding="utf-8")
    (tmp_path / "other.diff").write_text(added("docs/old-pyproject.toml"), encoding="utf-8")
    runs = [
        run(PLAN, "--check", "lock-with-deps", "--root", tmp_path, diff, cwd=tmp_path)
        for diff in ("member.diff", "locked.diff", "other.diff")
    ]
    assert [(r.returncode, r.stdout) for r in runs] == [
        (1, "member.diff:6: pyproject.toml adds a dependency and uv.lock does not change\n"),
        (0, ""),
        (0, ""),
    ]


def note(tmp_path: Path, text: str) -> subprocess.CompletedProcess:
    (tmp_path / "handoff.md").write_text(text, encoding="utf-8")
    (tmp_path / "facts.json").write_text(json.dumps(FACTS), encoding="utf-8")
    return run(NOTE, tmp_path / "handoff.md", tmp_path / "facts.json")


def test_a_note_that_carries_its_facts_passes(tmp_path):
    proc = note(tmp_path, GOOD_NOTE)
    assert (proc.returncode, proc.stdout) == (0, "")


@pytest.mark.parametrize(
    ("old", "new", "problem"),
    [
        ("after Task 3", "after Task 4", LINE_1),
        ("09:47", "9:47", LINE_1),
        ("committed as 7f3c2a1", "committed (see git log)", 'the fact "7f3c2a1" is not carried'),
    ],
)
def test_a_note_with_a_wrong_line_1_or_a_pointer_instead_of_a_fact_fails(tmp_path, old, new, problem):
    proc = note(tmp_path, GOOD_NOTE.replace(old, new))
    assert (proc.returncode, proc.stdout) == (1, problem + "\n")


def test_a_note_over_forty_lines_fails(tmp_path):
    proc = note(tmp_path, GOOD_NOTE + "More.\n" * 36)
    assert (proc.returncode, proc.stdout) == (1, "41 lines, over 40\n")


def test_the_readme_counts_the_known_error_classes_of_the_skills_example_lessons():
    """R13: evals/regression/README.md names as many classes as the skill's example/lessons.md lists (ten since J6)."""
    lessons = (ROOT / ".claude/skills/running-specagent-pipelines/example/lessons.md").read_text(encoding="utf-8")
    readme = " ".join((ROOT / "evals" / "regression" / "README.md").read_text(encoding="utf-8").split())
    tenth = "the tenth, a settings file that leaves the credentials file readable, is the pre-flight's `blind` check"
    assert lessons.split("## Known error classes", 1)[1].split("\n## ", 1)[0].count("\n- ") == 10
    assert "Eight of the ten known error classes" in readme
    assert tenth in readme
