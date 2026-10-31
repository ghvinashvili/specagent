"""Read `claude agents --json` and reconcile state.json; print the actions the manager must take.
Every unit that is not running and not done gets exactly one action here (resume with the reason, or max_attempts),
so the retry rule lives in this file and nowhere else."""

from __future__ import annotations

import copy
import datetime as dt
import json
import subprocess
from pathlib import Path

import jsonschema

from . import access, gates, launch, limits, pause, rounds, state

ACTIVE = {"launched", "working", "blocked", "checkpointed"}
NEEDS_ACTION = {"stopped", "failed", "gate_failed"}
IDLE_SECONDS = 180  # a session listed as working whose process is idle and whose log is this old is not working
# A unit's own record (schemas/run-state.schema.json, shard_state); a stage's approval is not part of it.
UNIT_KEYS = ("status", "attempts", "session_ids", "job_ids", "started_at", "finished_at", "last_poll", "last_error",
             "last_checkpoint_at", "gate", "note", "round_start")  # fmt: skip
UNIT_ACTIONS = {"gate", "attention", "timeout", "resume", "max_attempts", "wait_limit", "limit_human"}  # from a unit


def _log_age(session_id: str | None) -> float | None:
    """Seconds since the session's log was last written, or None when there is no log."""
    path = launch.transcript_of(session_id) if session_id else None
    return (dt.datetime.now(dt.UTC).timestamp() - path.stat().st_mtime) if path and path.is_file() else None


def _turn_ended(session_id: str | None) -> bool:
    """True when the session's log ends with a finished turn: Claude Code writes a `turn_duration` entry when a turn
    is over, and nothing the model said or received follows it. Only the end of the log is read."""
    path = launch.transcript_of(session_id) if session_id else None
    if not path or not path.is_file():
        return False
    with path.open("rb") as fh:
        fh.seek(max(0, path.stat().st_size - 65536))
        tail = fh.read().decode("utf-8", errors="replace").splitlines()
    for line in reversed(tail):
        try:
            entry = json.loads(line)
        except ValueError:
            continue  # the first line of the tail may be cut
        if entry.get("type") == "system" and entry.get("subtype") == "turn_duration":
            return True
        if entry.get("type") in ("user", "assistant"):
            return False
    return False


def _minutes_since(iso: str | None) -> float:
    if not iso:
        return 0.0
    return (dt.datetime.now(dt.UTC) - dt.datetime.fromisoformat(iso)).total_seconds() / 60


def _units(ss: dict) -> list[tuple[int | None, dict]]:
    """(shard, record) pairs: the stage itself, or its shards once it was launched as a wave."""
    if ss.get("shards"):
        return [(int(k), v) for k, v in sorted(ss["shards"].items())]
    return [(None, ss)]


def _aggregate(ss: dict) -> None:
    """A sharded stage is done only when every shard passed its gate; one failing shard fails the stage's gate."""
    if not ss.get("shards"):
        return
    records = list(ss["shards"].values())
    statuses = [r["status"] for r in records]
    if all(s == "done" for s in statuses):
        ss["status"], ss["gate"] = "done", "pass"
    elif "gate_failed" in statuses:
        ss["status"], ss["gate"] = "gate_failed", "fail"
    elif "blocked" in statuses:
        ss["status"] = "blocked"
    elif any(s in ("working", "launched", "checkpointed") for s in statuses):
        ss["status"] = "working"
    else:
        ss["status"] = "stopped" if "stopped" in statuses else "failed"
    ss["attempts"] = max(r["attempts"] for r in records)
    ss["session_ids"] = [s for r in records for s in r["session_ids"]]


def _unlock(run_dir: Path, stage_id: str, shard: int | None) -> None:
    lock = launch.lock_path(run_dir, stage_id, shard)
    if lock.exists():
        lock.unlink()


def _result_is_final(stage_dir: Path) -> bool:
    """The session wrote the result it may stop with: the Stop hook lets a role session end its turn only then."""
    try:
        doc = json.loads((stage_dir / "result.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return doc.get("status") in ("complete", "escalated", "failed")


def _result_is_complete(stage_dir: Path) -> bool:
    try:
        return json.loads((stage_dir / "result.json").read_text(encoding="utf-8")).get("status") == "complete"
    except (OSError, json.JSONDecodeError):
        return False


def _retry_message(stage_dir: Path, u: dict) -> str:
    """What the next resume delivers: the failing gate checks, or the print run's error."""
    if u["status"] == "gate_failed" and (stage_dir / "gate.json").exists():
        verdict = json.loads((stage_dir / "gate.json").read_text(encoding="utf-8"))
        failed = [
            c["name"] + (f" ({c['detail']})" if c.get("detail") else "") for c in verdict["checks"] if not c["passed"]
        ]
        return "Gate failed: " + "; ".join(failed) + ". Fix these, then rewrite result.json."
    if u["status"] == "failed" and u.get("last_error"):
        return (
            "The previous run failed (exit "
            + str(u["last_error"]["exit_code"])
            + "): "
            + u["last_error"]["stderr"][-300:]
            + " Produce the result again."
        )
    return "Continue from progress.md."


def gate_now(root: Path, run_id: str, stage_id: str, shard: int | None = None) -> dict:
    """`harness gate`: run the gate of a unit and, when its session is not running, record the verdict in state.json.
    A unit that failed its gate and passes now, because its files were corrected or the gate was, becomes done; the
    other way round it becomes gate_failed and the next poll asks for a resume."""
    verdict = gates.run_gate(root, run_id, stage_id, shard)
    run_dir = state.runs_root(root) / run_id
    with state.locked(run_dir / "state.json"):  # the gate ran without the lock; the file is read again (ADR-0021)
        st = state.load(root, run_dir / "state.json", "run-state")
        ss = st["stages"][stage_id]
        u = launch.unit(ss, shard)
        if st["status"] != "aborted" and u["status"] in ("gate_failed", "done", "checkpointed", "stopped"):
            u["gate"], u["finished_at"] = ("pass" if verdict["passed"] else "fail"), state.now()
            u["status"] = "done" if verdict["passed"] else "gate_failed"
            _unlock(run_dir, stage_id, shard)
            _aggregate(ss)
            if ss["status"] == "done" and not ss.get("finished_at"):
                ss["finished_at"] = state.now()
            st["updated_at"] = state.now()
            state.save(root, run_dir / "state.json", st, "run-state")
    return {**verdict, "unit_status": u["status"]}


def poll(root: Path, run_id: str, listing: list[dict] | None = None) -> dict:
    run_dir = state.runs_root(root) / run_id
    st = state.load(root, run_dir / "state.json", "run-state")
    if st["status"] == "aborted":  # a record: reported as it is, nothing written (docs/decisions/0010)
        return {"ok": True, "run_id": run_id, "status": "aborted", "actions": []}
    held = pause.current(root)
    if held:  # the pause switch: nothing is looked at, gated or written until the human lifts it (ADR-0023)
        return {"ok": True, "run_id": run_id, "status": st["status"], "paused": held, "actions": []}
    before = copy.deepcopy(st)  # what this poll read; _commit merges its findings into the file as it is then
    manifest = state.load(root, run_dir / "manifest.json", "run-manifest")
    rows = listing if listing is not None else launch.listing(root)
    polls = run_dir / "logs" / "polls"
    polls.mkdir(parents=True, exist_ok=True)
    (polls / f"agents-{dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ')}.json").write_text(
        json.dumps(rows), encoding="utf-8"
    )
    by_session = {r.get("sessionId"): r for r in rows}
    by_job = {r.get("id"): r for r in rows if r.get("id")}
    actions: list[dict] = []

    for stage_id, ss in st["stages"].items():
        stage = next(s for s in manifest["stages"] if s["id"] == stage_id)
        for shard, u in _units(ss):
            where = {"stage": stage_id, **({"shard": shard} if shard else {})}
            if u["status"] in ACTIVE:
                # A unit is found by its session id, or by the job id `claude --bg` printed: a background session
                # runs under an id Claude Code assigned, and a resume may continue it as a copy under a new one.
                live = [by_session[s] for s in u["session_ids"] if s in by_session]
                for job in u.get("job_ids", []):
                    row = by_job.get(job)
                    if row and row not in live:
                        live.append(row)
                        if row.get("sessionId") and row["sessionId"] not in u["session_ids"]:
                            u["session_ids"].append(row["sessionId"])
                if u["status"] == "checkpointed" and not live:  # print unit already has its result
                    verdict = gates.run_gate(root, run_id, stage_id, shard)
                    u["gate"], u["status"], u["finished_at"] = (
                        ("pass", "done", state.now()) if verdict["passed"] else ("fail", "gate_failed", state.now())
                    )
                    _unlock(run_dir, stage_id, shard)
                    if verdict["passed"]:
                        actions.append({"action": "gate", **where, "next": verdict["next"]})
                elif not live:
                    u["status"] = "stopped"
                    _unlock(run_dir, stage_id, shard)
                else:
                    row = live[-1]  # session_ids keep launch order, so the last live one is the newest
                    # `status`, `pid` and `waitingFor` exist only while the session's process is alive; a done/stopped row may lack them.
                    u["last_poll"] = {
                        "at": state.now(),
                        "state": row["state"],
                        "status": row.get("status"),
                        "waitingFor": row.get("waitingFor"),
                    }
                    # Claude Code reads a session's last message and lists it as `blocked` when the message asks
                    # something, also when the turn is over (seen live: a reader that ended with "two questions go
                    # to the next stages"). A role session asks through an escalation, never through its last
                    # message, so an idle session without an open prompt whose result is final has finished.
                    # A session whose turn is over can also stay listed as `working` (seen live: a critic that had
                    # written its result and ended its turn was `working`, `idle` for minutes). The end of its log
                    # says whether the turn ended.
                    at_rest = not row.get("waitingFor") and row.get("status") in (None, "idle")
                    finished = row["state"] == "done" or (
                        at_rest
                        and _result_is_final(launch._stage_dir(run_dir, stage_id, shard))
                        and (
                            row["state"] == "blocked"
                            or (row["state"] == "working" and _turn_ended(row.get("sessionId")))
                        )
                    )
                    # A process that is alive, idle and silent although the session is listed as working, without a
                    # final result: no turn is running and none starts by itself (seen live after a restart without a
                    # message). It is treated as stopped, so that the unit gets a resume with a message.
                    age = _log_age(row.get("sessionId"))
                    stalled = (
                        not finished
                        and row["state"] == "working"
                        and row.get("status") == "idle"
                        and age is not None
                        and age > IDLE_SECONDS
                        and _minutes_since(u.get("started_at")) * 60 > IDLE_SECONDS
                    )
                    if stalled:
                        u["status"] = "stopped"
                        _unlock(run_dir, stage_id, shard)
                    elif row["state"] == "working" and not finished:
                        u["status"] = "working"
                    elif row["state"] == "blocked" and not finished:
                        u["status"] = "blocked"
                        actions.append(
                            {
                                "action": "attention",
                                **where,
                                "waitingFor": row.get("waitingFor"),
                                "job_id": row.get("id"),
                            }
                        )
                    elif finished:
                        verdict = gates.run_gate(root, run_id, stage_id, shard)
                        u["gate"], u["finished_at"] = ("pass" if verdict["passed"] else "fail"), state.now()
                        u["status"] = "done" if verdict["passed"] else "gate_failed"
                        _unlock(run_dir, stage_id, shard)
                        if verdict["passed"]:
                            actions.append({"action": "gate", **where, "next": verdict["next"]})
                    elif row["state"] in ("failed", "stopped"):
                        u["status"] = row["state"]
                        _unlock(run_dir, stage_id, shard)
                    if u["status"] in ACTIVE and _minutes_since(u.get("started_at")) > stage["max_minutes"]:
                        actions.append(
                            {"action": "timeout", **where, "job_id": row.get("id"), "max_minutes": stage["max_minutes"]}
                        )
            if u["status"] == "stopped" and _result_is_complete(launch._stage_dir(run_dir, stage_id, shard)):
                # A session that stopped after it wrote a complete result has finished: its work is judged by the
                # gate, not continued with a message (seen live: a finished critic was taken for a stalled one).
                verdict = gates.run_gate(root, run_id, stage_id, shard)
                u["gate"], u["finished_at"] = ("pass" if verdict["passed"] else "fail"), state.now()
                u["status"] = "done" if verdict["passed"] else "gate_failed"
                if verdict["passed"]:
                    actions.append({"action": "gate", **where, "next": verdict["next"]})
            if u["status"] in NEEDS_ACTION:  # the one place that decides what a retry is
                held = limits.decision(launch._stage_dir(run_dir, stage_id, shard), u)
                if held:  # a limit or an API error ended the turn: wait for the reset or hand it to the human; no attempt is spent
                    actions.append({**held, **where})
                elif launch.round_attempts(u) < stage["max_attempts"] and rounds.runs_left(manifest, stage_id, u):
                    actions.append(
                        {
                            "action": "resume",
                            **where,
                            "why": u["status"],
                            "mode": stage["mode"],
                            "message": _retry_message(launch._stage_dir(run_dir, stage_id, shard), u),
                        }
                    )
                else:  # the retries of the round are spent, or the stage's starts in this run (loop.max_runs)
                    runs = (
                        {}
                        if rounds.runs_left(manifest, stage_id, u)
                        else {"max_runs": manifest["loop"]["max_runs"][stage_id]}
                    )
                    actions.append(
                        {"action": "max_attempts", **where, "why": u["status"], "attempts": u["attempts"], **runs}
                    )
        _aggregate(ss)
        if ss["status"] == "done" and not ss.get("finished_at"):
            ss["finished_at"] = state.now()

    access.file_escalations(run_dir)  # a blind session writes escalation.json in its own stage directory
    known = {e["id"]: e for e in st["escalations"]}
    for path in sorted((run_dir / "escalations").glob(state.ESCALATION)):
        esc = state.load(root, path, "escalation")
        known[esc["id"]] = {"id": esc["id"], "stage": esc["stage"], "status": esc["status"]}
        where = {"stage": esc["stage"], **({"shard": esc["shard"]} if esc.get("shard") else {})}
        if esc["status"] == "open":
            actions.append({"action": "escalation", **where, "id": esc["id"], "file": str(path)})
        elif esc["status"] == "answered":
            for a in actions:
                if a["action"] == "resume" and a["stage"] == esc["stage"] and a.get("shard") == esc.get("shard"):
                    a["escalation"] = esc["id"]  # the answer is what the resume delivers
    st["escalations"] = sorted(known.values(), key=lambda e: e["id"])

    stopped = _let_finished_go(st, by_job, by_session)
    written = _commit(root, run_dir, before, st, actions, manifest)
    if written is None:  # aborted while this poll looked: a record, nothing written (docs/decisions/0010)
        return {"ok": True, "run_id": run_id, "status": "aborted", "actions": []}
    out = {"ok": True, "run_id": run_id, "status": written["status"], "actions": actions}
    return {**out, "stopped": stopped} if stopped else out


def _record(ss: dict, shard: int | None) -> dict | None:
    """The record of one unit of a stage as a state file has it: the stage itself, or one of its shards."""
    return ss.get("shards", {}).get(f"{shard:02d}") if shard else ss


def _unit_view(rec: dict) -> dict:
    return {k: rec[k] for k in UNIT_KEYS if k in rec}


def _commit(root: Path, run_dir: Path, before: dict, st: dict, actions: list[dict], manifest: dict) -> dict | None:
    """Write what this poll found into state.json under the file's one lock (ADR-0021). The file is read again: this
    poll's record of a unit is taken only where no other command changed that unit since the poll read it; a unit
    changed meanwhile keeps the other command's record, and this poll's actions for it are dropped (the next poll
    derives them again). Approvals, aggregates and the run's status come from the merged state. The loops are taken
    here, on the state as it is under the lock (harness/rounds.py): a round is saved first and its files move after,
    and a `gate` action of a unit in a loop or of a reviewer whose loop stopped is dropped. Nothing is written to a
    run that was aborted meanwhile; returns None then, else the state written."""
    path = run_dir / "state.json"
    with state.locked(path):
        fresh = state.load(root, path, "run-state")
        if fresh["status"] == "aborted":
            return None
        stale = set()
        for stage_id, ss in st["stages"].items():
            fss, bss = fresh["stages"][stage_id], before["stages"][stage_id]
            for shard, mine in _units(ss):
                seen, now = _record(bss, shard), _record(fss, shard)
                if seen is None or now is None:
                    continue
                if _unit_view(now) != _unit_view(seen):  # another command changed it since this poll read it
                    stale.add((stage_id, shard))
                    continue
                if _unit_view(mine) == _unit_view(seen):
                    continue  # this poll changed nothing here
                for key in UNIT_KEYS:
                    if key in mine:
                        now[key] = mine[key]
                    else:
                        now.pop(key, None)
            _aggregate(fss)
            if fss["status"] == "done" and not fss.get("finished_at"):
                fss["finished_at"] = state.now()
        actions[:] = [
            a for a in actions if a["action"] not in UNIT_ACTIONS or (a["stage"], a.get("shard")) not in stale
        ]
        known = {e["id"]: e for e in fresh["escalations"]} | {e["id"]: e for e in st["escalations"]}
        fresh["escalations"] = sorted(known.values(), key=lambda e: e["id"])
        loop = rounds.process(run_dir, manifest, fresh)
        held = {a["stage"] for a in loop if a["action"] in rounds.STOP_ACTIONS}
        held |= {sid for sid, ss in fresh["stages"].items() if ss["status"] in rounds.LOOPING}
        actions[:] = [a for a in actions if not (a["action"] == "gate" and a["stage"] in held)] + loop
        _settle(fresh, actions)
        state.save(root, path, fresh, "run-state")
        if rounds.move_round(run_dir, fresh):  # the files of the round the saved state holds
            state.save(root, path, fresh, "run-state")
    return fresh


def _settle(st: dict, actions: list[dict]) -> None:
    """The approval actions and the status of a run, as poll derives them from its state and its actions."""
    pending_approval = [s for s, ss in st["stages"].items() if ss["status"] == "done" and ss["approval"] == "pending"]
    for s in pending_approval:
        actions.append({"action": "approval", "stage": s})
    human = ("escalation", "approval", "attention", "max_attempts", "limit_human", *rounds.STOP_ACTIONS)
    if any(a["action"] in human for a in actions):
        st["status"] = "waiting_human"
    elif any(ss["status"] in ACTIVE for ss in st["stages"].values()):
        st["status"] = "running"
    elif all(ss["status"] in ("done", "skipped") for ss in st["stages"].values()):
        st["status"] = "done"
    else:
        st["status"] = "paused"
    st["updated_at"] = state.now()


def _let_finished_go(st: dict, by_job: dict, by_session: dict) -> list[str]:
    """Stop the idle process of every unit whose stage is done and needs no approval, or got it: an idle session
    held about 300 MB until the run was cleaned, and Claude Code woke such sessions again after an update. `claude
    stop` keeps the conversation, and `harness resume` continues it (docs/decisions/0010). A busy session, one a human
    may still ask (approval pending or rejected) and one already stopped are left."""
    stopped: list[str] = []
    for ss in st["stages"].values():
        if ss["status"] != "done" or ss["approval"] not in ("not_required", "approved"):
            continue
        for _, u in _units(ss):
            rows = [by_job[j] for j in u.get("job_ids", []) if j in by_job]
            rows += [by_session[s] for s in u["session_ids"] if s in by_session and by_session[s] not in rows]
            for row in rows:
                if row.get("pid") and row.get("status") == "idle" and row.get("id") and row["id"] not in stopped:
                    try:
                        subprocess.run(
                            ["claude", "stop", row["id"]], capture_output=True, text=True, timeout=30, check=False
                        )
                    except (OSError, subprocess.TimeoutExpired):
                        return stopped
                    stopped.append(row["id"])
    return stopped


def watch(root: Path, run_id: str, every: int = 20, max_minutes: int = 240) -> dict:
    """Poll until the run needs the manager, then return that poll's result. Started in the background right after a
    launch, it keeps a running task in the manager's terminal for as long as role sessions work, and its exit brings
    the manager back with the actions to take. Nothing needs the manager while every unit is working."""
    import time

    deadline = time.monotonic() + max_minutes * 60
    seen: dict = {}
    while True:
        out = poll(root, run_id)
        st = state.load(root, state.runs_root(root) / run_id / "state.json", "run-state")
        now = {
            s + (f"/{k}" if k else ""): u["status"]
            for s, ss in st["stages"].items()
            for k, u in (sorted(ss["shards"].items()) if ss.get("shards") else [("", ss)])
            if u["status"] != "pending"
        }
        for unit, status in now.items():
            if seen.get(unit) != status:
                print(f"{state.now()} {unit}: {status}", flush=True)
        seen = now
        if out["actions"] or out["status"] in ("done", "paused", "waiting_human", "aborted") or out.get("paused"):
            return {**out, "watched": True}
        if time.monotonic() > deadline:
            return {**out, "watched": True, "timed_out": True}
        time.sleep(every)


def poll_all(root: Path) -> dict:
    """`harness poll --all-active`: every open run. A run whose state.json cannot be read is named under `unreadable`
    and left out, as leftovers does; one whose poll raised (a gate that met what it did not expect) is named under
    `failed` with the error; the others are polled all the same."""
    held = pause.current(root)
    if held:  # the pause switch (ADR-0023): no run is polled
        return {"ok": True, "paused": held, "runs": [], "unreadable": [], "failed": []}
    rows = launch.listing(root)
    results, unreadable, failed = [], [], []
    for run_dir in sorted(state.runs_root(root).glob("*-*")):
        if (run_dir / "state.json").exists():
            try:
                st = state.load(root, run_dir / "state.json", "run-state")
            except (OSError, ValueError, jsonschema.ValidationError) as exc:
                why = f"{type(exc).__name__}: {(str(exc).splitlines() or [''])[0][:200]}"
                unreadable.append({"run_id": run_dir.name, "why": why})
                continue
            if st["status"] in ("created", "running", "waiting_human", "paused"):
                try:
                    results.append(poll(root, run_dir.name, rows))
                except Exception as exc:  # noqa: BLE001 — one run's error stops no other run; it is named, not hidden
                    why = f"{type(exc).__name__}: {(str(exc).splitlines() or [''])[0][:200]}"
                    failed.append({"run_id": run_dir.name, "why": why})
    return {"ok": True, "runs": results, "unreadable": unreadable, "failed": failed}
