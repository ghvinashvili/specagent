"""Resume one unit of a stage (the stage, or one shard). Background units: `claude --resume <session-id> --bg "<message>"`,
always with a message, because a session that is only restarted does not continue by itself; when Claude Code continues
as a copy under a new id, the copy's session id is recorded so that `poll` keeps following it.
Print units: a new `claude -p --resume <session-id>` call with the same schema flags, run to completion here."""

from __future__ import annotations

import copy
import json
import os
import subprocess
from pathlib import Path

from . import access, launch, pause, rounds, state, work
from .gates._common import text as plain_text


def _answer_message(root: Path, run_dir: Path, escalation_id: str) -> str:
    esc = state.load(root, run_dir / "escalations" / f"{escalation_id}.json", "escalation")
    if esc["status"] != "answered":
        raise SystemExit(f"escalation {escalation_id} is {esc['status']}, not answered")
    ans = esc["answer"]
    return (
        f"Escalation {escalation_id} answered by {ans['answered_by']} at {ans['answered_at']}.\n"
        f"Question: {esc['question']}\nAnswer: {ans['text']}\n"
        f"Continue from progress.md and rewrite result.json when done."
    )


RECHECK = (
    "Round {n}. The work this stage checks changed since your last result: it was sent back and done again. Your "
    "earlier output and result are under rounds/{k}/ in your stage directory; input/ holds the current files, and "
    "the Material of your system prompt was rebuilt from them. Check the work again from the start, as your method "
    "says, not only the findings of the round before, and write a new result.json."
)


def _loop_refusal(
    root: Path, run_id: str, manifest: dict, st: dict, stage_id: str, u: dict, rework: bool
) -> dict | None:
    """Why this resume may not start: a unit in a loop needs --rework and --rework needs a unit in a loop; no round is
    resumed while its files are moving; every start of a stage stops at its max_runs; a loop resume waits for the
    stages before it (harness/rounds.py)."""
    looping = u["status"] in rounds.LOOPING
    if looping != rework:
        hint = "the unit answers a loop: add --rework" if looping else "--rework is for a unit in rework or recheck"
        return {"ok": False, "status": "in_rework" if looping else "not_in_rework", "unit_status": u["status"],
                "hint": hint}  # fmt: skip
    if rework and st.get("loop", {}).get("moving"):
        return {"ok": False, "status": "round_moving", "hint": "run `harness poll`: it keeps the round's files first"}
    if not rounds.runs_left(manifest, stage_id, u):
        runs = manifest["loop"]["max_runs"][stage_id]
        return {"ok": False, "status": "max_runs", "attempts": u["attempts"], "max_runs": runs}
    if not rework:
        return None
    ready = launch.status(root, run_id, stage_id)
    return None if ready["ok"] else ready


def _loop_message(stage_dir: Path, u: dict) -> str:
    """What a loop resume delivers: the findings written for the reworking stage (never read through a link: resume
    runs outside the sandbox), or the instruction to check again. "" when rework.md is missing."""
    if u["status"] == "rework":
        return plain_text(stage_dir, rounds.REWORK)
    k = rounds.last_round(stage_dir)
    return RECHECK.format(n=k + 1, k=k)


def resume(
    root: Path,
    run_id: str,
    stage_id: str,
    shard: int | None = None,
    escalation: str | None = None,
    message: str | None = None,
    rework: bool = False,
) -> dict:
    held = pause.refusal(root)
    if held:  # the pause switch: no session resumes (ADR-0023)
        return held
    run_dir = state.runs_root(root) / run_id
    manifest = state.load(root, run_dir / "manifest.json", "run-manifest")
    st = state.load(root, run_dir / "state.json", "run-state")
    before = copy.deepcopy(st)  # what this resume read; launch.commit carries its own changes into the file
    frozen = state.check_frozen(root, st)
    if frozen:
        return frozen
    stage = next(s for s in manifest["stages"] if s["id"] == stage_id)
    row = launch._row(root, stage_id, manifest.get("pipeline", "default"))
    ss = st["stages"][stage_id]
    u = launch.unit(ss, shard)
    if u["attempts"] == 0:
        return {"ok": False, "status": "not_launched", "hint": "use `harness launch`"}
    refused = _loop_refusal(root, run_id, manifest, st, stage_id, u, rework)
    if refused:
        return refused
    if not rework and launch.round_attempts(u) >= stage["max_attempts"]:
        return {"ok": False, "status": "max_attempts", "attempts": u["attempts"]}
    if not (root / ".claude" / "agents" / f"{stage['role_type']}.md").is_file():  # Claude Code would resume the
        why = f".claude/agents/{stage['role_type']}.md is gone, and a session resumed without it gets every tool"
        return {"ok": False, "status": "agent_file_missing", "why": why}  # session with the default tools (cc#2)
    start = launch.before_start(root, stage["mode"])
    if not start["ok"]:
        return start
    session_id = u["session_ids"][-1]  # newest known id: the manifest's, or a copy from an earlier resume
    stage_dir = launch._stage_dir(run_dir, stage_id, shard)
    text = (
        _loop_message(stage_dir, u)
        if rework
        else message or (_answer_message(root, run_dir, escalation) if escalation else "Continue from progress.md.")
    )
    if not text:
        return {"ok": False, "status": "rework_missing", "why": f"{stage_dir / rounds.REWORK} is no plain file"}
    env = state.session_env(run_dir, stage_id, stage["role_type"], stage["mode"], shard)
    if stage["mode"] != "bg":  # a background session reads these from its settings (launch.session_flags)
        env.update(access.env_extra(access.load_policy(root), row, stage_dir))
    launch.own_logs(stage_dir)
    try:  # the work a unit reviews may have changed since it was launched: its checkout and patch follow it
        table = state.load_table(root, manifest.get("pipeline", "default"))
        by_id = {s["id"]: s for s in table["stages"]}
        name, policy = launch.worktree_name(run_id, stage_id, shard), access.load_policy(root)
        if rework and u["status"] == "recheck":  # the inputs and the work of the new round, then the Material
            launch.stage_inputs(root, policy, by_id, run_dir, row, stage_dir, name)
            launch.write_pack(root, policy, row, stage_dir, again=True)
        else:  # its checkout follows the work, and the index names the patch written again (launch.prepare_work)
            launch.prepare_work(root, policy, by_id, run_dir, row, stage_dir, name)
    except work.WorkConflict as e:
        return {"ok": False, "status": "work_conflict", "files": e.files, "branches": e.branches, "why": str(e)}
    except access.AccessError as e:
        return {"ok": False, "status": "access_refused", "why": str(e)}

    if stage["mode"] == "print":
        # A -p session is resumable by its id (`claude -p --resume <id> "<prompt>"`); the run happens here, to completion.
        cmd = [
            "claude",
            "-p",
            "--resume",
            session_id,
            *launch.session_flags(run_dir, stage, session_id, root, row, stage_dir),  # the pack file is already there
            *launch.print_flags(root, row, stage, manifest),
            text,
        ]
        outcome = launch.run_print(root, cmd, env, stage_dir, st, u)
        job_id = None
    else:
        # A stopped session continues only when it is given a message. `claude respawn <job-id>` restarts the process
        # and leaves the conversation where it stopped: the session then sits idle and is listed as working (seen
        # live). So a unit is always resumed with `claude --resume <session-id> --bg "<text>"`, which continues under
        # the same id, or as a copy under a new id with a `note:` line (v2.1.257+). `--add-dir` and `--settings` are not
        # restored by `--resume`, so they are passed again, as they are now: a configuration change a human accepted
        # with `harness refreeze` reaches the session this way. `--permission-mode` is restored; passing it is harmless.
        cmd, job_id = (
            [
                "claude",
                "--resume",
                session_id,
                *launch.session_flags(run_dir, stage, session_id, root, row, stage_dir),
                "--bg",
                text,
            ],
            None,
        )
        res = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True, check=False)
        with (stage_dir / "logs" / "launch.txt").open("a", encoding="utf-8") as fh:
            fh.write("\n--- resume ---\n" + " ".join(cmd[:3]) + "\n" + res.stdout + res.stderr)
        if res.returncode != 0:
            return {"ok": False, "status": "resume_failed", "stderr": res.stderr[-2000:]}
        m = launch.BG_ID.search(res.stdout)
        if m:
            job_id = m.group(1)
        live_id = launch.session_of(root, job_id) or session_id
        if live_id not in u["session_ids"]:
            u["session_ids"].append(live_id)
        if live_id != session_id:  # a copy under a new id: poll follows it from now on
            u["note"] = f"continued as a copy {live_id}; " + res.stdout.strip()[-200:]
        session_id = live_id
        u["status"] = "launched"
        outcome = {"ok": True, "note": res.stdout.strip()[-300:]}

    if rework:  # a loop resume starts a round: its retries count from here (launch.round_attempts)
        u["round_start"] = u["attempts"]
    u["attempts"] += 1
    u["started_at"] = state.now()
    if job_id and job_id not in u.get("job_ids", []):
        u.setdefault("job_ids", []).append(job_id)
    if shard:
        ss["status"] = u["status"]
        ss["attempts"] = max(x["attempts"] for x in ss["shards"].values())
        if session_id not in ss["session_ids"]:
            ss["session_ids"].append(session_id)
    if escalation:
        for e in st["escalations"]:
            if e["id"] == escalation:
                e["status"] = "answered"
    st["status"], st["updated_at"] = "running", state.now()
    if launch.commit(root, run_dir, before, st, stage_id, shard) is None:
        return launch.aborted_meanwhile(run_id, session_id, job_id)
    if outcome["ok"]:
        launch.lock_path(run_dir, stage_id, shard).write_text(
            json.dumps({"session_id": session_id, "pid": os.getpid(), "started_at": state.now()}), encoding="utf-8"
        )
    return {
        **outcome,
        **({"trust": start["trust"]} if "trust" in start else {}),
        "stage": stage_id,
        "shard": shard,
        "mode": stage["mode"],
        "session_id": session_id,
        "job_id": job_id,
        "via": cmd[1] if stage["mode"] == "bg" else "-p --resume",
        "attempts": u["attempts"],
    }
