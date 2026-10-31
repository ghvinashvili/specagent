"""harness/transcript.py on recorded transcript lines: the ten lines of the appendix of specs/001-chat-depth/spec.md
(tests/fixtures/transcripts/appendix.jsonl, verbatim) and copies of them with one field changed.
Run: `uv run pytest -q packages/harness/tests/test_transcript.py`."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from harness import transcript

FIXTURE = Path(__file__).parent / "fixtures" / "transcripts" / "appendix.jsonl"
LINES = [json.loads(x) for x in FIXTURE.read_text(encoding="utf-8").splitlines()]
READ, READ_OK, BASH, BASH_OK, FAIL, FAIL_RESULT, DENIED, DENIED_RESULT, EDIT, SYNTHETIC = LINES


def log(tmp_path: Path, *entries: dict, name: str = "s.jsonl") -> Path:
    path = tmp_path / name
    path.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")
    return path


def call(entry: dict, **given) -> dict:
    """A copy of an assistant line whose tool_use input has the given fields."""
    out = copy.deepcopy(entry)
    out["message"]["content"][0]["input"].update(given)
    return out


def answer(tool_use_id: str, text: str, error: bool = False, **top) -> dict:
    """A user line carrying one tool result, in the shape of the appendix's result lines."""
    block = {"tool_use_id": tool_use_id, "type": "tool_result", "content": text, "is_error": error}
    return {"type": "user", "message": {"role": "user", "content": [block]}, "cwd": "/repo", **top}


def test_the_appendix_gives_one_event_per_call_in_the_order_of_the_log():
    events = transcript.events(FIXTURE)
    assert [e["tool"] for e in events] == ["Read", "Bash", "Bash", "Bash", "Edit"]
    assert [e["seq"] for e in events] == [0, 1, 2, 3, 4]
    read, ok, failed, denied, edit = events
    assert read["file"].endswith("/stages/write/01/input/plan/plan.md") and read["ok"]
    assert (read["offset"], read["limit"], read["start"], read["lines"]) == (None, None, 1, 157)
    assert ok["exit_code"] == 0 and not ok["denied"] and ok["command"].startswith("git branch --show-current")
    assert failed["exit_code"] == 1 and failed["output"].startswith("Exit code 1")
    assert denied["denied"] and denied["exit_code"] is None  # toolDenialKind: the command did not run
    assert edit["file"].endswith("/packages/harness/src/harness/stagemap.py") and not edit["ok"]  # no result line
    assert {e["cwd"] for e in events} == {"/home/tite/Desktop/aft-exp"}  # as the copied lines carry it


def test_a_read_with_offset_and_limit_keeps_what_it_asked_and_what_it_got(tmp_path: Path):
    asked = call(READ, offset=401, limit=100)
    got = copy.deepcopy(READ_OK)
    got["toolUseResult"]["file"].update(startLine=401, numLines=100)
    (event,) = transcript.events(log(tmp_path, asked, got))
    assert (event["offset"], event["limit"], event["start"], event["lines"]) == (401, 100, 401, 100)


def test_an_edit_and_a_write_are_ok_only_with_a_result_that_is_no_error(tmp_path: Path):
    tool_id = EDIT["message"]["content"][0]["id"]
    write = copy.deepcopy(EDIT)
    write["message"]["content"][0].update(name="Write", id="w1")
    events = transcript.events(
        log(tmp_path, EDIT, answer(tool_id, "The file was updated."), write, answer("w1", "x", True))
    )
    assert [(e["tool"], e["ok"]) for e in events] == [("Edit", True), ("Write", False)]


def test_a_refused_call_is_not_a_run_whatever_its_text(tmp_path: Path):
    tool_id = BASH["message"]["content"][0]["id"]
    refused = answer(tool_id, "This session is isolated in the worktree ...", True)  # a hook's refusal, no Exit code
    (event,) = transcript.events(log(tmp_path, BASH, refused))
    assert event["denied"] and event["exit_code"] is None


def test_a_background_command_has_no_exit_code_until_its_notification(tmp_path: Path):
    started = call(BASH, command="python3 slow.py", run_in_background=True)
    tool_id = started["message"]["content"][0]["id"]
    running = answer(tool_id, "Command running in background with ID: b1. Output is being written to: /tmp/b1.output")
    (event,) = transcript.events(log(tmp_path, started, running))
    assert event["background"] and event["exit_code"] is None and not event["denied"]
    notice = (
        f"<task-notification>\n<task-id>b1</task-id>\n<tool-use-id>{tool_id}</tool-use-id>\n"
        '<status>failed</status>\n<summary>Background command "slow" failed with exit code 3</summary>\n'
        "</task-notification>"
    )  # the text a session received in the planner's trial, 2026-10-03
    (event,) = transcript.events(log(tmp_path, started, running, {"type": "user", "message": {"content": notice}}))
    assert event["exit_code"] == 3


def test_a_continued_copy_carries_the_calls_of_the_session_it_continues(tmp_path: Path):
    original = log(tmp_path, READ, READ_OK, BASH, BASH_OK, name="original.jsonl")
    later = call(FAIL)
    later["sessionId"] = later["session_id"] = "9e1e3b52-8666-4bf1-8bb6-531439eb3e0a"
    copied = log(tmp_path, READ, READ_OK, BASH, BASH_OK, later, FAIL_RESULT, name="copy.jsonl")
    first, second = transcript.events(original), transcript.events(copied)
    assert [e["id"] for e in second[: len(first)]] == [e["id"] for e in first] and len(second) == 3


def test_model_and_effort_skip_the_synthetic_line_and_lines_without_effort(tmp_path: Path):
    assert transcript.model_and_effort(FIXTURE) == {"model": "claude-sonnet-5-5", "effort": "high"}
    raised = copy.deepcopy(EDIT)
    raised.update(effort="max", perTurnEffort="max")
    raised["message"]["model"] = "claude-opus-5-5"
    found = transcript.model_and_effort(log(tmp_path, *LINES[:-1], raised, DENIED_RESULT, SYNTHETIC))
    assert found == {"model": "claude-opus-5-5", "effort": "max"}
    assert transcript.model_and_effort(log(tmp_path, SYNTHETIC, name="only.jsonl")) == {"model": None, "effort": None}


def test_a_line_that_is_no_json_object_is_skipped(tmp_path: Path):
    path = log(tmp_path, READ, READ_OK)
    with path.open("a", encoding="utf-8") as fh:
        fh.write('{"type": "assistant", "message": {"content": [{"type": "tool_use"\n[1, 2]\n')
    assert [e["tool"] for e in transcript.events(path)] == ["Read"]
    empty = log(tmp_path, name="empty.jsonl")
    assert transcript.events(empty) == [] and transcript.model_and_effort(empty) == {"model": None, "effort": None}
