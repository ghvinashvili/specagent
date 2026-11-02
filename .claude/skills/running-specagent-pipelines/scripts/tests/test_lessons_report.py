"""lessons_report.py: whether a lesson lowers the error it was written for (owner, 2026-11-02)."""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "lessons_report.py"
LESSONS = """# Lessons
## Read first (main session, 2026-11-01)
1. Read late and narrow.
## Known error classes (from earlier runs; check each task against them)
- A test list is no task.
## Lessons from this run
(planner and builders add one-line rules here, with the finding ids)
- Every task carries its tests in full (C3, C4).
- A name a task creates is grepped first
  in its module at the base commit (B1).
"""


def run_folder(tmp_path: Path) -> Path:
    run = tmp_path / "run"
    run.mkdir()
    (run / "lessons.md").write_text(LESSONS, encoding="utf-8")
    (run / "build-log-a.md").write_text(
        "STATUS: done\nTask 1: done — abc1234\nTask 2: done — def5678\n", encoding="utf-8"
    )
    (run / "critique.md").write_text(
        "## Task 3\n#### C3 — (plan) no tests\nChecklist: lessons.md:8\n"
        "#### C9 — (plan) the tests again\nLesson: lessons.md:8\n#### C10 — (plan) a list again\nChecklist: lessons.md:5\n",
        encoding="utf-8",
    )
    (run / "verify.md").write_text("#### V2 — (code) a second def\nLesson: lessons.md:10\n", encoding="utf-8")
    return run


def report(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True, timeout=60, check=False
    )


def test_a_finding_that_names_a_lesson_and_is_not_its_source_is_a_recurrence_and_flags_it_to_become_code(tmp_path):
    run = run_folder(tmp_path)
    r = report(str(run), "--json")
    assert r.returncode == 0, r.stderr
    [d] = json.loads(r.stdout)["runs"]
    items = {i["line"]: i for i in d["items"]}
    assert d["units"] == 2 and d["lessons"] == {"read first": 1, "carried": 1, "this run": 2}
    assert items[8]["sources"] == ["C3", "C4"] and items[8]["recurrences"] == ["C9"]
    assert items[9]["recurrences"] == ["V2"]  # the continuation line 10 belongs to the item of line 9
    assert d["make_code"] == [5, 8, 9] and d["unmeasured"] == [3]
    assert d["carried"] == {"classes": 1, "recurrences": 1, "per_10_units": 5.0}


def test_the_markdown_names_the_lessons_to_make_code_and_the_unmeasured(tmp_path):
    r = report(str(run_folder(tmp_path)))
    assert "make code (broken twice): lessons.md:5, lessons.md:8, lessons.md:9" in r.stdout
    assert "unmeasured (no finding names them): 1 of 4" in r.stdout


def test_two_runs_follow_a_lesson_across_them_and_a_folder_without_lessons_exits_2(tmp_path):
    first = run_folder(tmp_path)
    second = tmp_path / "second"
    second.mkdir()
    (second / "lessons.md").write_text(LESSONS, encoding="utf-8")
    r = report(str(first), str(second))
    assert (
        "## Across runs (recurrences / units)" in r.stdout
        and "| every task carries its tests in full | 1/2 | 0/0 |" in r.stdout
    )
    assert report(str(tmp_path / "nowhere")).returncode == 2


def test_the_vault_pages_a_transcript_read_are_counted(tmp_path):
    lines = [
        {
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "/h/vault/INDEX.md"}}]},
        },
        {
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "/h/vault/INDEX.md"}}]},
        },
        {
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "/h/repo/README.md"}}]},
        },
    ]
    t = tmp_path / "s.jsonl"
    t.write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")
    r = report(str(run_folder(tmp_path)), "--transcript", str(t), "--json")
    assert json.loads(r.stdout)["vault_reads"] == {"INDEX.md": 2}
