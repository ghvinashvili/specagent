"""The waiters return within 3.5 minutes, so a role's next call comes inside the prompt cache's 5 minutes (owner,
2026-11-01): exit 3 with the line that says to run the same command again; exit 0 at once when there is work."""

import ast
import runpy
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent
AGAIN = "Run the same command again now: a call within 5 min keeps the prompt cache warm"


def run_captured(monkeypatch, capsys, script, argv):
    """A waiter script run to its exit: (exit code, what it printed on stdout and stderr, the clock it saw)."""
    clock = [0.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(time, "sleep", lambda s: clock.__setitem__(0, clock[0] + s))
    monkeypatch.setattr(sys, "argv", [script, *argv])
    with pytest.raises(SystemExit) as done:
        runpy.run_path(str(SCRIPTS / script), run_name="__main__")
    return done.value.code, capsys.readouterr(), clock[0]


def run(monkeypatch, capsys, script, argv):
    code, captured, clock = run_captured(monkeypatch, capsys, script, argv)
    return code, captured.out, clock


@pytest.mark.parametrize(
    "script, files, argv",
    [
        ("wait_for_log.py", {"log.md": "a\n"}, ["log.md", "1"]),
        (
            "wait_for_ready.py",
            {"c.md": "STATUS: reviewed through Task 1\n", "r.md": ""},
            ["--critique", "c.md", "--response", "r.md", "2"],
        ),
        ("wait_for_task.py", {"plan.md": "### Task 1\n", "r.md": ""}, ["--plan", "plan.md", "--response", "r.md", "1"]),
    ],
)
def test_a_waiter_with_nothing_to_take_returns_within_3_5_minutes_with_the_line_to_run_it_again(
    tmp_path, monkeypatch, capsys, script, files, argv
):
    monkeypatch.chdir(tmp_path)
    for name, text in files.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    code, out, waited = run(monkeypatch, capsys, script, argv)
    assert code == 3, out
    assert AGAIN in out
    assert waited <= 210


def test_a_waiter_with_work_exits_0_at_once(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "log.md").write_text("a\nb\n", encoding="utf-8")
    code, out, waited = run(monkeypatch, capsys, "wait_for_log.py", ["log.md", "1"])
    assert (code, waited) == (0, 0.0)
    assert "2 lines now" in out


@pytest.mark.parametrize(
    "script, files, argv, line",
    [
        (
            "wait_for_ready.py",
            {"c.md": "STATUS: reviewed through Task 2\n", "r.md": "ok\n"},
            ["--critique", "c.md", "--response", "r.md", "2"],
            "Task 2 ready",
        ),
        (
            "wait_for_task.py",
            {"plan.md": "### Task 1\n### Task 2\n", "r.md": ""},
            ["--plan", "plan.md", "--response", "r.md", "0"],
            "complete through Task 1",
        ),
    ],
)
def test_the_ready_and_task_waiters_with_work_exit_0_at_once(tmp_path, monkeypatch, capsys, script, files, argv, line):
    monkeypatch.chdir(tmp_path)
    for name, text in files.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    code, out, waited = run(monkeypatch, capsys, script, argv)
    assert (code, waited) == (0, 0.0), out
    assert line in out


INDEX = (
    "# Plan: demo — index\n\n## Commands\n| 2 | not a task row | a | — |\n\n## Task order\n"
    "| Task | title | builder | depends_on | files | milestone |\n| --- | --- | --- | --- | --- | --- |\n"
    "| 1 | One | a | — | `a.py` | M1 |\n| 2 | Two | b | — | `b.py` | M1 |\n| 3 | Three | a | 1 | `c.py` | M1 |\n"
    "| 4 | Four | b | 2 | `d.py` | M2 |\n| 5 | Five | a | 2, 3 | `e.py` | M2 |\n"
)
CRITIQUE = (
    "STATUS: reviewed through Task 5\n## Shared\n#### C9 — shared\n### Task 2\n#### C1 — on b's task\n"
    "### Task 3\n#### C3 — on a's task\n### Task 4\n#### C2 — on b's later task\n"
)


@pytest.mark.parametrize(
    "task, lane, line",
    [
        (3, ["--index", "i.md", "--lane", "a"], "Task 3 ready"),  # b's open C1 does not hold a's Task 3
        (5, ["--index", "i.md", "--lane", "a"], "not ready: unanswered C1"),  # Task 5 depends on b's Task 2
        (3, [], "not ready: unanswered C1"),  # without the index every task 1..N counts
    ],
)
def test_a_builder_s_task_is_held_by_its_own_lane_and_its_depends_on_only(
    tmp_path, monkeypatch, capsys, task, lane, line
):
    """A project's run of 2026-11-02: a builder waited 107 minutes on the other lane's open ids."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "i.md").write_text(INDEX, encoding="utf-8")
    (tmp_path / "c.md").write_text(CRITIQUE, encoding="utf-8")
    (tmp_path / "r.md").write_text("C9: fixed\nC3: fixed\n", encoding="utf-8")
    argv = ["--critique", "c.md", "--response", "r.md", "--once", *lane, str(task)]
    code, out, _ = run(monkeypatch, capsys, "wait_for_ready.py", argv)
    assert out.strip() == line and code == (0 if "ready" == line.split()[-1] else 3)
    (tmp_path / "r.md").write_text("C3: fixed\n", encoding="utf-8")  # a shared id holds every lane
    assert run(monkeypatch, capsys, "wait_for_ready.py", argv)[1].strip().startswith("not ready: unanswered")


def test_an_index_without_a_lane_is_a_usage_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    for name in ("i.md", "c.md", "r.md"):
        (tmp_path / name).write_text("", encoding="utf-8")
    argv = ["--critique", "c.md", "--response", "r.md", "--index", "i.md", "1"]
    assert run(monkeypatch, capsys, "wait_for_ready.py", argv)[0] == 2


PLANNER_COLUMN = (
    "## Task order\n| Task | title | planner | builder | depends_on | files |\n| --- | --- | --- | --- | --- | --- |\n"
    "| 1 | One | p | a | — | `a.py` |\n| 2 | Two | p | b | — | `b.py` |\n| 3 | Three | p | a | 1 | `c.py` |\n"
)
RANGE_CELL = (
    "## Task order\n| Task | title | builder | depends_on | files |\n| --- | --- | --- | --- | --- |\n"
    "| 1 | One | b | — | `a.py` |\n| 2 | Two | b | — | `b.py` |\n| 3 | Three | b | — | `c.py` |\n"
    "| 4 | Four | b | — | `d.py` |\n| 5 | Five | a | 1-4 | `e.py` |\n"
)
LONG_BUILDER = (
    "## Task order\n| Task | title | builder | depends_on |\n| --- | --- | --- | --- |\n"
    "| 1 | One | Builder A | — |\n| 2 | Two | builder: b | — |\n| 3 | Three | `builder a` | — |\n"
)
OPEN_IDS = (
    "STATUS: reviewed through Task 5\n### Task 1\n#### C1 — on the first task\n### Task 2\n#### C2 — on the second\n"
)


def waiter_argv(tmp_path, index, critique=OPEN_IDS):
    """The files of one check of the index's reading (the response answers only C99) and the arguments that name them."""
    (tmp_path / "c.md").write_text(critique, encoding="utf-8")
    (tmp_path / "r.md").write_text("C99: none\n", encoding="utf-8")
    if index is not None:
        (tmp_path / "i.md").write_text(index, encoding="utf-8")
    return ["--critique", "c.md", "--response", "r.md", "--once", "--index", "i.md"]


@pytest.mark.parametrize(
    "index, lane, task, line",
    [
        (PLANNER_COLUMN, "a", 3, "not ready: unanswered C1"),  # the builder is the column named builder, not the third
        (RANGE_CELL, "a", 5, "not ready: unanswered C1, C2"),  # `1-4` is Tasks 1, 2, 3 and 4
        (LONG_BUILDER, "a", 3, "not ready: unanswered C1"),  # `Builder A` and `builder a` are lane a, `builder: b` is b
    ],
)
def test_the_index_is_read_by_its_header_and_a_range_in_depends_on_holds_each_task_of_it(
    tmp_path, monkeypatch, capsys, index, lane, task, line
):
    """V15 of the verifier: the table was read by the position of its cells and `depends_on` by its digits, so a
    `planner` column or a range `1-4` released Task N while the ids of the tasks it waits for were open."""
    monkeypatch.chdir(tmp_path)
    argv = [*waiter_argv(tmp_path, index), "--lane", lane, str(task)]
    code, out, _ = run(monkeypatch, capsys, "wait_for_ready.py", argv)
    assert (code, out.strip()) == (3, line)


def test_a_task_is_held_by_the_ids_of_its_lane_up_to_itself_with_or_without_a_depends_on(tmp_path, monkeypatch, capsys):
    """V16 of the verifier: with the lane's earlier tasks dropped from the set that holds Task N (`mine = {n}`) every
    test passed, because no case filed an id on a task of the lane that Task N does not depend on. A builder works its
    lane in the index's order, so an open id on an earlier task of the lane, or on Task N itself, holds Task N even
    when Task N lists no depends_on; an id on a later task of the lane, or on the other lane's task, holds nothing."""
    monkeypatch.chdir(tmp_path)
    # lane a: Tasks 1, 3, 5; Task 3 waits on none
    index = INDEX.replace("| 3 | Three | a | 1 |", "| 3 | Three | a | — |")
    assert index != INDEX
    critique = (
        "STATUS: reviewed through Task 5\n### Task 1\n#### C7 — on an earlier task of lane a\n### Task 2\n"
        "#### C8 — on lane b's task\n### Task 3\n#### C6 — on Task 3 itself\n### Task 5\n#### C5 — on a later task of lane a\n"
    )
    argv = [*waiter_argv(tmp_path, index, critique), "--lane", "a", "3"]
    for response, code, line in [
        ("C99: none\n", 3, "not ready: unanswered C6, C7"),
        ("C6: fixed\n", 3, "not ready: unanswered C7"),
        ("C7: fixed\n", 3, "not ready: unanswered C6"),
        ("C6: fixed\nC7: fixed\n", 0, "Task 3 ready"),  # C8 and C5 are still open and hold nothing
    ]:
        (tmp_path / "r.md").write_text(response, encoding="utf-8")
        assert run(monkeypatch, capsys, "wait_for_ready.py", argv)[:2] == (code, line + "\n")


@pytest.mark.parametrize(
    "index, critique, lane, task, reasons",
    [
        (None, OPEN_IDS, "a", 3, ["--index i.md", "no such file"]),
        (None, "STATUS: reviewed through Task 0\n", "a", 3, ["--index i.md", "no such file"]),  # at the first call
        ("# Plan\n\nno table here\n", OPEN_IDS, "a", 3, ["i.md", "no task table"]),
        ("## Task order\n| Task | builder |\n| --- | --- |\n| 1 | a |\n", OPEN_IDS, "a", 1, ["no task table"]),
        (INDEX, OPEN_IDS, "c", 3, ["Task 3", "lane c"]),  # no task of lane c
        (INDEX, OPEN_IDS, "a", 4, ["Task 4", "lane a"]),  # Task 4 is b's
        (INDEX, OPEN_IDS, "a", 9, ["Task 9", "lane a"]),  # no such task
    ],
)
def test_an_index_the_waiter_cannot_use_stops_it_with_exit_2_and_the_reason_at_the_first_call(
    tmp_path, monkeypatch, capsys, index, critique, lane, task, reasons
):
    """V15 of the verifier: a missing index, one without a task table, or a Task N outside the lane counted N alone and
    printed `Task N ready`; the gate holds or stops with an error."""
    monkeypatch.chdir(tmp_path)
    argv = [*waiter_argv(tmp_path, index, critique), "--lane", lane, str(task)]
    code, captured, _ = run_captured(monkeypatch, capsys, "wait_for_ready.py", argv)
    assert code == 2 and captured.out == ""
    assert all(reason in captured.err for reason in reasons), captured.err


def test_the_waiter_copied_alone_into_a_run_folder_reads_an_index(tmp_path, monkeypatch):
    """SKILL.md has the waiters copied into the run folder and run from there with `python3 -I`; a script that imports
    its sibling `duty_list.py` fails in that folder (V15 of the verifier asked for the duty list's reader)."""
    monkeypatch.chdir(tmp_path)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    shutil.copy(SCRIPTS / "wait_for_ready.py", run_dir / "_wait_for_ready.py")
    argv = [*waiter_argv(tmp_path, PLANNER_COLUMN), "--lane", "a", "3"]
    done = subprocess.run(
        [sys.executable, "-I", str(run_dir / "_wait_for_ready.py"), *argv], capture_output=True, text=True, check=False
    )
    assert (done.returncode, done.stdout.strip(), done.stderr) == (3, "not ready: unanswered C1", "")


READER = ("CODE_SPAN", "SEPARATOR", "RANGE", "numbers", "cells", "task_table")


def reader_sources(path):
    """The source text of the index reader's definitions in a script, by name."""
    text = path.read_text(encoding="utf-8")
    found = {}
    for node in ast.parse(text).body:
        if isinstance(node, ast.FunctionDef):
            found[node.name] = ast.get_source_segment(text, node)
        elif isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            found[node.targets[0].id] = ast.get_source_segment(text, node)
    return {name: found.get(name) for name in READER}


def test_the_index_reader_copied_into_wait_for_ready_is_the_one_of_duty_list_character_for_character():
    """The waiter holds a copy of the duty list's reader because it runs alone from the run folder; a copy that drifts
    reads an index differently from the duty list and the monitor, which is how V15's three cases got through."""
    original, copy = reader_sources(SCRIPTS / "duty_list.py"), reader_sources(SCRIPTS / "wait_for_ready.py")
    assert None not in original.values()
    assert copy == original
