"""Tell a human outside the terminal that a run needs them. `after_poll` sends one line each time an action that
needs the human appears, through the operator's command in HARNESS_NOTIFY_CMD (the line arrives on its standard
input). No channel is built in: the command is whatever the operator uses (mail, chat webhook, desktop notifier)."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path

from . import state
from .rounds import STOP_ACTIONS

HUMAN_ACTIONS = {"escalation", "approval", "attention", "max_attempts", "timeout", "limit_human", *STOP_ACTIONS}


def send(root: Path, kind: str, line: str) -> bool:
    command, sent = os.environ.get("HARNESS_NOTIFY_CMD"), False
    if command:
        try:
            sent = (
                subprocess.run(
                    shlex.split(command), input=line + "\n", text=True, capture_output=True, timeout=20, check=False
                ).returncode
                == 0
            )
        except (OSError, subprocess.TimeoutExpired):
            sent = False
    log = state.runs_root(root) / "_audit" / "notify.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": state.now(), "kind": kind, "line": line, "sent": sent}) + "\n")
    return sent


def _seen(path: Path) -> set[str] | None:
    """The keys logs/notified.json holds; an empty set when there is no file, None when the file holds no list of
    keys (empty, cut, not JSON). Such a file counts as empty and is written again: at worst a line is sent twice,
    while a raise here would hide every later action of the run (02/F09)."""
    if not path.exists():
        return set()
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return {k for k in doc if isinstance(k, str)} if isinstance(doc, list) else None


def _key(action: dict) -> str:
    return ":".join(str(action.get(k, "")) for k in ("action", "stage", "shard", "id"))


def after_poll(root: Path, out: dict) -> dict:
    """Called on the result of every `harness poll`; returns it unchanged. logs/notified.json holds the actions that
    need the human in the last poll that announced them, and `done` once the run finished: an action is announced
    when it appears, and forgotten when a poll no longer prints it, so the next time the unit needs the human is
    announced again (02/F10). The file is read, changed and written under its one lock, through a temporary file of
    its own (ADR-0021); the lines are sent after the lock is let go. A paused or aborted result announces nothing."""
    for result in out.get("runs", [out]):
        if result.get("paused") or result.get("status") == "aborted":
            continue
        run_dir = state.runs_root(root) / result["run_id"]
        seen_file = run_dir / "logs" / "notified.json"
        human = [a for a in result.get("actions", []) if a["action"] in HUMAN_ACTIONS]
        with state.locked(seen_file):
            found = _seen(seen_file)
            seen = found or set()
            new = list({_key(a): a for a in human if _key(a) not in seen}.values())
            done = result.get("status") == "done" and "done" not in seen
            keep = {_key(a) for a in human} | ({"done"} & seen) | ({"done"} if done else set())
            if keep != seen or found is None:
                state.write_atomic(seen_file, json.dumps(sorted(keep)))
        for action in new:
            where = action.get("stage", "") + (f"/{action['shard']:02d}" if action.get("shard") else "")
            line = f"[{result['run_id']}] {action['action']} at {where}: see {run_dir / 'HANDOFF.md'}"
            send(root, action["action"], line)
        if done:
            send(root, "done", f"[{result['run_id']}] run finished: see {run_dir / 'HANDOFF.md'}")
    return out
