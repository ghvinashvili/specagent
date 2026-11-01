"""The waiters return within 3.5 minutes, so a role's next call comes inside the prompt cache's 5 minutes (owner,
2026-11-01): exit 3 with the line that says to run the same command again; exit 0 at once when there is work."""

import runpy
import sys
import time
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent
AGAIN = "Run the same command again now: a call within 5 min keeps the prompt cache warm"


def run(monkeypatch, capsys, script, argv):
    clock = [0.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(time, "sleep", lambda s: clock.__setitem__(0, clock[0] + s))
    monkeypatch.setattr(sys, "argv", [script, *argv])
    with pytest.raises(SystemExit) as done:
        runpy.run_path(str(SCRIPTS / script), run_name="__main__")
    return done.value.code, capsys.readouterr().out, clock[0]


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
