#!/usr/bin/env python3
"""Context handoff of the manager's session and of a human's session in this project.

Before Claude Code compacts a conversation, the session writes what a fresh context needs to go on into
`docs/handoff/<date>-<time>-handoff.md`; after the compaction it reads the newest one back. The handoff holds the
main points of the conversation (what the user wants and why, what was agreed, what is still open), so that the
conversation can go on, and the state of the work. It is never a copy of the conversation: a transcript read again
fills the next context with talk instead of material, so none is kept. Events:

- PostToolUse: the notices. The first comes at FIRST of the point where Claude Code compacts and asks for a handoff,
  the second at SECOND and asks to bring it up to date; each once per session and compaction.
- PostCompact: the notices start over.
- SessionStart with source `compact`: read the newest handoff and continue from its next steps.

The size of the conversation comes from the status line, which calls record_context; without it there is no
notice, and the reminder after a compaction still works. The compaction point is the auto-compact
window (CLAUDE_CODE_AUTO_COMPACT_WINDOW; else about 967,000 tokens for a 1M window, the window itself below that)
times CLAUDE_AUTOCOMPACT_PCT_OVERRIDE (code.claude.com/docs/en/model-config, "Default auto-compact thresholds").

A role session is left alone: its handoff is its checkpoint (progress.md), which session-start.py gives back after a
compaction, and the manager's handoffs are closed to it (docs/roles/need-to-know.yaml). When the user's own settings
already run a handoff hook (a hook command naming `handoff` in the user's settings.json), this one stays silent, so
that no session is asked twice. The directory is not committed (.gitignore).
"""

from __future__ import annotations

import datetime as dt
import getpass
import json
import os
import sys
import tempfile
from pathlib import Path

FIRST, SECOND = 0.92, 0.97  # shares of the compaction point; with auto-compact at 60 % they are 55 % and 58 %
NATIVE_1M_POINT = 967_000  # where a session with a 1M window compacts by default
FOLDER = Path("docs") / "handoff"


def state_dir() -> Path:
    """Per-user, outside the repository and gone with a reboot: the size of each session and the notices given."""
    return Path(tempfile.gettempdir()) / f"claude-handoff-{getpass.getuser()}"


def record_context(data: dict) -> None:
    """Called by the status line with its input: the tokens in the conversation and the window, per session."""
    sid = data.get("session_id")
    cw = data.get("context_window") or {}
    if not sid or not cw.get("context_window_size"):
        return
    try:
        state_dir().mkdir(parents=True, exist_ok=True)
        size = {"used": cw.get("total_input_tokens") or 0, "window": cw["context_window_size"]}
        (state_dir() / f"{sid}.json").write_text(json.dumps(size), encoding="utf-8")
    except OSError:
        pass


def compaction_point(window: int) -> int:
    """The number of tokens at which Claude Code compacts a conversation with this window."""

    def number(name: str) -> int:
        try:
            return int(os.environ.get(name) or 0)
        except ValueError:
            return 0

    own = number("CLAUDE_CODE_AUTO_COMPACT_WINDOW")
    base = min(own, window) if own else (NATIVE_1M_POINT if window >= 1_000_000 else window)
    pct = number("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE")
    return base * (pct if 1 <= pct <= 100 else 100) // 100


def user_hook() -> bool:
    """Whether the user's own settings already run a handoff hook."""
    home = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    for name in ("settings.json", "settings.local.json"):
        try:
            hooks = json.loads((home / name).read_text(encoding="utf-8")).get("hooks") or {}
        except (OSError, ValueError, AttributeError):
            continue
        for groups in hooks.values():
            for group in groups if isinstance(groups, list) else []:
                if any("handoff" in str(h.get("command", "")) for h in group.get("hooks", [])):
                    return True
    return False


def claim(path: Path) -> bool:
    """True once: the first of two hooks running at the same moment gets the notice."""
    try:
        os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        return True
    except OSError:
        return False


def stamp() -> str:
    """The local date and time a file name carries, as `date +%Y-%m-%d-%H%M` writes it."""
    return dt.datetime.now(dt.UTC).astimezone().strftime("%Y-%m-%d-%H%M")


def say(event: str, text: str, note: str = "") -> None:
    out: dict = {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}
    if note:
        out["systemMessage"] = note
    print(json.dumps(out))


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    sid, event = data.get("session_id") or "", data.get("hook_event_name") or ""
    if not sid or os.environ.get("HARNESS_RUN_DIR") or data.get("agent_id") or user_hook():
        return 0
    folder = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".") / FOLDER
    marks = state_dir()
    if event in ("PostCompact", "SessionStart"):
        for name in (f"{sid}.notice-1", f"{sid}.notice-2", f"{sid}.json"):  # the size is the one before compacting
            (marks / name).unlink(missing_ok=True)
        if event == "SessionStart" and data.get("source") == "compact":
            say(
                event,
                f"The conversation was just compacted. Before you continue, read the newest file in {folder}/ (if "
                "there is one) and continue from its next steps. If you were managing a run, read the HANDOFF.md of "
                "its run directory too.",
            )
        return 0
    if event != "PostToolUse":
        return 0
    try:
        size = json.loads((marks / f"{sid}.json").read_text(encoding="utf-8"))
        used, window = int(size["used"]), int(size["window"])
    except (OSError, ValueError, KeyError, TypeError):
        return 0
    point = compaction_point(window)
    if point <= 0 or used < FIRST * point:
        return 0
    level = 2 if used >= SECOND * point else 1
    marks.mkdir(parents=True, exist_ok=True)
    given = [n for n in range(1, level + 1) if claim(marks / f"{sid}.notice-{n}")]
    if not given:
        return 0
    pct = round(100 * used / point)
    if 1 in given:
        text = (
            f"Context is at {pct}% of the point where Claude Code compacts this conversation. Finish the current "
            f"small step, then write a handoff to {folder / f'{stamp()}-handoff.md'}. Write the main points of the "
            "conversation, not a copy of it, so that the conversation can go on after the compaction: what the user "
            "wants and why, what was agreed and decided, what was asked and is still open. Then the state of the "
            "work: what is done, what is in progress, the open problems, the exact next steps, and the files and "
            "commands that matter. Tell the user in one short line that it is saved and where, then keep working."
            + (" You will be asked once more to bring it up to date before the compaction." if level == 1 else "")
        )
    else:
        text = (
            f"Context is at {pct}% of the compaction point. Bring the newest handoff in {folder}/ up to date with "
            "everything since it was written (new points of the conversation, decisions, results, changed next "
            "steps): edit it in place, keep it to the main points and complete, tell the user in one short line, "
            "then keep working."
        )
    say(event, text, f"context {pct}% of the compaction point: handoff")
    return 0


if __name__ == "__main__":
    sys.exit(main())
