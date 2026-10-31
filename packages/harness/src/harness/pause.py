"""harness/pause.py — the one pause switch of a runs root (docs/decisions/0023-one-pause-switch.md).

While `<runs root>/_pause.json` exists, `harness launch`, `harness resume`, `harness loop tick`, `harness poll` and
ops/night-tick.sh start, resume or change nothing: no session, no loop iteration and no night session starts, and no
state is written, so the same work goes on once the switch is lifted. Sessions that run when it is set are left as
they are. Only the human sets and lifts it (`harness pause set --reason "<words>"`, `harness pause lift`); a role
session can do neither. `harness abort` stays per run and final."""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import state

FLAG = "_pause.json"
HINT = "the human lifts the switch with `harness pause lift`"


def flag_path(root: Path) -> Path:
    """Where the switch lives: in the runs root of the checkout, beside its runs and loops."""
    return state.runs_root(root, create=False) / FLAG


def current(root: Path) -> dict | None:
    """The switch as the human set it ({"at", "reason"}), or None while it is not set. A flag that cannot be read
    still pauses: only the human lifts it."""
    try:
        doc = json.loads(flag_path(root).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        return {"at": None, "reason": f"the flag cannot be read ({type(exc).__name__}); {HINT}"}
    return doc if isinstance(doc, dict) else {"at": None, "reason": f"the flag holds no object; {HINT}"}


def refusal(root: Path) -> dict | None:
    """The answer of a command the switch stops before it does anything, or None while the switch is not set."""
    held = current(root)
    return None if held is None else {"ok": False, "status": "paused", "paused": held, "hint": HINT}


def _role_refusal() -> dict | None:
    """A role session neither sets nor lifts the switch: it writes an escalation (docs/decisions/0010)."""
    role = os.environ.get("HARNESS_ROLE")
    if not role:
        return None
    why = "only the human sets or lifts the pause switch; a role session writes an escalation"
    return {"ok": False, "status": "role_session", "role": role, "command": "pause", "why": why}


def set_flag(root: Path, reason: str) -> dict:
    """`harness pause set`: set the switch with the human's reason. Set again, it keeps its first time and reason."""
    refused = _role_refusal()
    if refused:
        return refused
    if not reason.strip():
        return {"ok": False, "status": "no_reason", "why": 'the switch keeps the human\'s reason: --reason "<words>"'}
    held = current(root)
    if held is not None:
        return {"ok": True, "paused": held, "already": True}
    doc = {"at": state.now(), "reason": reason.strip()}
    path = flag_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    state.write_atomic(path, json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return {"ok": True, "paused": doc}


def lift(root: Path) -> dict:
    """`harness pause lift`: remove the switch; the work goes on from the state it was left in."""
    refused = _role_refusal()
    if refused:
        return refused
    held = current(root)
    flag_path(root).unlink(missing_ok=True)
    return {"ok": True, "lifted": held is not None, "was": held}
