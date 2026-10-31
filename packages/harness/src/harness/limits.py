"""Usage limits and API errors of role sessions. The StopFailure hook writes one line per failed turn into the unit's
logs/stop-failure.jsonl; this module turns the newest line into a decision for `poll`: wait until a time, hand the unit
to the human, or nothing (the ordinary retry applies)."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

import jsonschema

from . import launch, state

HUMAN = {
    "authentication_failed",
    "oauth_org_not_allowed",
    "account_on_hold",
    "billing_error",
    "cloud_credential_error",
    "model_not_found",
    "invalid_request",
}
FALLBACK_MINUTES = {
    "rate_limit": 60,
    "overloaded": 10,
    "server_error": 10,
}  # used when the message carries no reset time
RESETS = re.compile(r"resets\s+(?:(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)", re.IGNORECASE)
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def reset_time(text: str, at: dt.datetime) -> dt.datetime | None:
    """`resets 3:45pm` or `resets Mon 12:00am` as the next such moment after `at`, in the machine's time zone."""
    m = RESETS.search(text or "")
    if not m:
        return None
    local = at.astimezone()
    hour = int(m.group(2)) % 12 + (12 if m.group(4).lower() == "pm" else 0)
    target = local.replace(hour=hour, minute=int(m.group(3) or 0), second=0, microsecond=0)
    if m.group(1):
        target += dt.timedelta(days=(DAYS.index(m.group(1).lower()) - target.weekday()) % 7)
    if target <= local:
        target += dt.timedelta(days=7 if m.group(1) else 1)
    return target.astimezone(dt.UTC)


def last_failure(stage_dir: Path, since: str | None) -> dict | None:
    log = stage_dir / "logs" / "stop-failure.jsonl"
    lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    if not lines:
        return None
    record = json.loads(lines[-1])
    if since and dt.datetime.fromisoformat(record["at"]) < dt.datetime.fromisoformat(since):
        return None  # older than the unit's last start: that failure was already handled
    return record


def decision(stage_dir: Path, u: dict, now: dt.datetime | None = None) -> dict | None:
    record = last_failure(stage_dir, u.get("started_at"))
    if not record:
        return None
    error = record.get("error", "unknown")
    if error in HUMAN:
        return {
            "action": "limit_human",
            "error": error,
            "detail": str(record.get("error_details") or record.get("last_assistant_message") or "")[:300],
        }
    if error not in FALLBACK_MINUTES:
        return None
    at = dt.datetime.fromisoformat(record["at"])
    text = f"{record.get('last_assistant_message') or ''} {record.get('error_details') or ''}"
    until = reset_time(text, at) or at + dt.timedelta(minutes=FALLBACK_MINUTES[error])
    if until <= (now or dt.datetime.now(dt.UTC)):
        return None  # the window is over: poll prints the ordinary resume
    return {"action": "wait_limit", "error": error, "resets_at": until.isoformat(timespec="seconds")}


def report(root: Path, run_id: str | None = None) -> dict:
    """`harness limits`: the units a limit holds, of every run or of one. A run whose state.json cannot be read is
    named under `unreadable` and left out, as leftovers does; the others are reported all the same."""
    waiting, unreadable = [], []
    for run_dir in sorted(state.runs_root(root).glob("*-*")):
        if not (run_dir / "state.json").exists() or (run_id and run_dir.name != run_id):
            continue
        try:
            st = state.load(root, run_dir / "state.json", "run-state")
        except (OSError, ValueError, jsonschema.ValidationError) as exc:
            why = f"{type(exc).__name__}: {(str(exc).splitlines() or [''])[0][:200]}"
            unreadable.append({"run_id": run_dir.name, "why": why})
            continue
        for stage_id, ss in st["stages"].items():
            units = [(int(k), v) for k, v in sorted(ss["shards"].items())] if ss.get("shards") else [(None, ss)]
            for shard, u in units:
                held = decision(launch._stage_dir(run_dir, stage_id, shard), u)
                if held and u["status"] in ("stopped", "failed", "gate_failed"):
                    waiting.append(
                        {"run_id": run_dir.name, "stage": stage_id, **({"shard": shard} if shard else {}), **held}
                    )
    return {"ok": True, "waiting": waiting, "unreadable": unreadable}
