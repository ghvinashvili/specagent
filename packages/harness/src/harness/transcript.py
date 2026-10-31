"""harness/transcript.py — the one module that reads a session's transcript, the Claude Code session log
`<config dir>/projects/<dir>/<session id>.jsonl` (launch.transcript_of finds it).

The format is not documented. Every key read here appears in the real lines of the appendix of
specs/001-chat-depth/spec.md, and the tests hold fixture lines built from them: when a version of Claude Code
changes the format, a test fails instead of a gate going quiet (risk 1 of that spec). A gate reads what a session
did from here; a role session cannot read its own transcript (`~/.claude/projects/**` is in `home_deny`).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

EXIT = re.compile(r"\AExit code (\d+)")  # the result of a Bash call that ran and ended with another code than 0
NOTIFICATION = re.compile(r"<task-notification>(.*?)</task-notification>", re.DOTALL)
NOTICE_ID = re.compile(r"<tool-use-id>([^<\s]+)</tool-use-id>")
NOTICE_EXIT = re.compile(r"exit code (\d+)")
EDITS = ("Edit", "Write")
SYNTHETIC = "<synthetic>"  # a line Claude Code writes itself (an API error, "No response requested."): no model


def _lines(path: Path):
    """Every line of the log that parses as a JSON object; a cut or foreign line is skipped."""
    for raw in path.open(encoding="utf-8", errors="replace"):
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        if isinstance(entry, dict):
            yield entry


def _blocks(entry: dict) -> list[dict]:
    content = (entry.get("message") or {}).get("content")
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []


def _text(content: object) -> str:
    """The text of a tool result or a message: a string, or the text parts of a list of blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(b.get("text", "")) for b in content if isinstance(b, dict))
    return ""


def _call(block: dict, entry: dict, seq: int) -> dict | None:
    """The event of a tool_use block, before its result is known; None for a tool no rule looks at."""
    name, given = block.get("name"), block.get("input") or {}
    base = {"seq": seq, "id": block.get("id"), "tool": name, "ts": entry.get("timestamp"), "cwd": entry.get("cwd")}
    if name == "Read":
        asked = {"offset": given.get("offset"), "limit": given.get("limit")}
        return {**base, "file": str(given.get("file_path", "")), **asked, "ok": False, "start": None, "lines": None}
    if name == "Bash":
        command = str(given.get("command", ""))
        ended = {"denied": False, "exit_code": None, "output": ""}
        return {**base, "command": command, "background": bool(given.get("run_in_background")), **ended}
    if name in EDITS:
        return {**base, "file": str(given.get("file_path", "")), "ok": False}
    return None


def _settle(event: dict, block: dict, entry: dict) -> None:
    """Fill in how a call ended from its tool_result block and the line that carries it."""
    text = _text(block.get("content"))
    error = bool(block.get("is_error"))
    refused = "toolDenialKind" in entry  # a denied call was not run (spec.md:38)
    if event["tool"] == "Bash":
        found = EXIT.match(text)
        event["output"] = text
        if refused or (error and not found):
            event["denied"] = True  # refused by a rule, a hook or the sandbox: the command did not run
        elif not event["background"]:
            event["exit_code"] = int(found.group(1)) if found else 0
        return
    event["ok"] = not error and not refused
    shown = entry.get("toolUseResult")
    file = shown.get("file") if isinstance(shown, dict) else None
    if event["tool"] == "Read" and isinstance(file, dict):
        event["start"], event["lines"] = file.get("startLine"), file.get("numLines")


def events(path: Path) -> list[dict]:
    """The Read, Bash, Edit and Write calls of a session, in the order it made them.

    Shapes (every event has seq, id, tool, ts, cwd):
      Read   file, offset, limit (as asked), ok, start and lines (what the result shows it returned, or None)
      Bash   command, background, denied (the command did not run), exit_code (None while unknown), output
      Edit / Write   file, ok
    A background command's exit code comes from the task notification that names its tool use, when the log has one.
    A continued copy carries the earlier conversation in its own log: its first lines are the calls it continues."""
    out: list[dict] = []
    by_id: dict[str, dict] = {}
    for entry in _lines(path):
        for block in _blocks(entry):
            if block.get("type") == "tool_use":
                event = _call(block, entry, len(out))
                if event:
                    out.append(event)
                    by_id[str(block.get("id"))] = event
            elif block.get("type") == "tool_result" and str(block.get("tool_use_id")) in by_id:
                _settle(by_id[str(block["tool_use_id"])], block, entry)
        if entry.get("type") == "user":
            _notices(entry, by_id)
    return out


def _notices(entry: dict, by_id: dict[str, dict]) -> None:
    """A task notification (`<task-notification>` with `<tool-use-id>` and "exit code N" in its summary) gives a
    background command the exit code its call result did not have."""
    message = entry.get("message") or {}
    for found in NOTIFICATION.finditer(_text(message.get("content"))):
        tool_use = NOTICE_ID.search(found.group(1))
        code = NOTICE_EXIT.search(found.group(1))
        event = by_id.get(tool_use.group(1)) if tool_use else None
        if event and event["tool"] == "Bash" and event["background"] and code:
            event["exit_code"] = int(code.group(1))


def model_and_effort(path: Path) -> dict:
    """The model and the effort a session runs on now: `message.model` of its last response that is not
    `<synthetic>`, and the top-level `effort` of its last line that carries one (a tool result and a `<synthetic>`
    line carry none). Either is None when the log holds none."""
    model = effort = None
    for entry in _lines(path):
        if entry.get("effort"):
            effort = str(entry["effort"])
        found = (entry.get("message") or {}).get("model") if entry.get("type") == "assistant" else None
        if found and found != SYNTHETIC:
            model = str(found)
    return {"model": model, "effort": effort}
