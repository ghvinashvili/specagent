#!/usr/bin/env python3
"""SessionStart hook: inject run context into a role session. Outside a harness run: set up a fresh checkout."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _ops(root: Path, name: str):
    """A script of ops/ as a module (they use the standard library only), or None when the checkout has none."""
    import importlib.util

    path = root / "ops" / f"{name}.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(f"ops_{name.replace('-', '_')}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sandbox(root: Path) -> tuple[str | None, str | None]:
    """A role session starts only inside the sandbox (its settings hold `sandbox.failIfUnavailable`). Where this
    machine lacks it, the user-space way sets it up in the background, without a password (`ops/machine-setup.py
    --auto`), and refreshes its copies when the system's bubblewrap changed or a day has passed; where only the
    administrator can (or the user-space way failed lately, or the human declined it), the session is told the one
    command that asks for the password, with the reason, to offer to the human.
    Returns (a message for the human, a note for the session)."""
    machine = _ops(root, "machine-setup")
    if machine is None:
        return None, None
    f = machine.facts(root)
    if not f["linux"] or not f["sandbox_enabled"]:
        return None, None
    way = machine.user_plan(f)
    work = (way["bwrap"] or way["socat"]) and not way["why_not"]
    if work or machine.refresh_due(f):
        machine.RECORDS.mkdir(parents=True, exist_ok=True)
        with open(machine.RECORDS / "user-space.log", "a", encoding="utf-8") as log:
            subprocess.Popen(
                [sys.executable, str(root / "ops" / "machine-setup.py"), "--auto"],
                cwd=root,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        if not work:  # a refresh: nothing to tell
            return None, None
        message = (
            "Setting up the sandbox of role sessions on this machine as this user, without a password: a copy of "
            f"bubblewrap and socat in {machine.USER_BIN} (log: {machine.RECORDS / 'user-space.log'})."
        )
        return message, None
    if f["socat"] and f["nested_ok"]:
        return None, None
    changes = machine.plan(f)["changes"]
    if not changes:
        return None, None
    reason = f" Without a password it cannot be done here: {way['why_not']}." if way["why_not"] else ""
    return None, (
        "The sandbox of role sessions cannot run on this machine, so no role session starts." + reason + " "
        "`python3 ops/machine-setup.py` sets it up once for the whole machine and asks for the administrator's password "
        "in the system's own window; nothing has to be typed. It " + "; it ".join(changes) + ". Tell the human this in "
        "one or two sentences at the start of your first answer, what is given up included, and with their "
        "yes run it (Bash, timeout 600000). A session that no human answers leaves it."
    )


def set_up(root: Path) -> dict | None:
    """A fresh checkout sets itself up (ops/bootstrap.py) in the background, so that nobody installs anything by hand,
    and so does the sandbox of role sessions where this user can (sandbox); what needs the administrator is told to
    the session, which asks the human. Nothing is written to ~/.claude.json here: Claude Code writes that file while a
    session starts, and the launcher records the trust a role session needs (harness/trust.py)."""
    out: dict = {}
    messages = [m for m in [start_setup(root)] if m]
    try:
        message, note = sandbox(root)
    except Exception:  # noqa: BLE001 - a probe that fails tells nothing; doctor names the problem
        message, note = None, None
    if message:
        messages.append(message)
    if messages:
        out["systemMessage"] = " ".join(messages)
    if note:
        out["hookSpecificOutput"] = {"hookEventName": "SessionStart", "additionalContext": note}
    return out or None


def turn_hooks_on(root: Path) -> None:
    """The versioned git hooks are on in every session, set up or not (ADR-0029): bootstrap's git_hooks points
    core.hooksPath at .githooks/ once per checkout, a worktree made after the setup included, and keeps a hooks folder
    the checkout names itself."""
    bootstrap = _ops(root, "bootstrap") if (root / ".githooks").is_dir() else None
    if bootstrap is None or not hasattr(bootstrap, "git_hooks"):
        return
    (root / ".claude").mkdir(exist_ok=True)
    with open(root / ".claude" / "bootstrap.log", "a", encoding="utf-8") as log:
        try:
            bootstrap.git_hooks(log)
        except OSError as exc:  # no git on this machine: the session starts all the same
            log.write(f"hooks: {exc}\n")


def start_setup(root: Path) -> str | None:
    """Turn the git hooks on, then start ops/bootstrap.py in the background when uv or the workspace is missing. uv
    that the setup put into ~/.local/bin, which a terminal opened before it does not have on PATH, is added to the PATH
    of this session's shell commands."""
    turn_hooks_on(root)
    local_uv = Path.home() / ".local" / "bin" / "uv"
    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if env_file and shutil.which("uv") is None and local_uv.exists():
        with open(env_file, "a", encoding="utf-8") as f:
            f.write(f'export PATH="{local_uv.parent}:$PATH"\n')
    if (shutil.which("uv") or local_uv.exists()) and (root / ".venv").is_dir():
        return None
    bootstrap = root / "ops" / "bootstrap.py"
    if not bootstrap.is_file():
        return None
    subprocess.Popen(
        [sys.executable, str(bootstrap)],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return (
        "Setting up this checkout in the background (uv, the workspace, `just`, the git hooks, the plugins, the "
        "language servers, the sandbox, the first code graph, graphify's skill, the user-level pipeline skill link; "
        "graphify's skill install appends a block to ~/.claude/CLAUDE.md); the log is "
        f"{root / '.claude' / 'bootstrap.log'}. Run `python3 ops/bootstrap.py --wait` to wait for it."
    )


def main() -> int:
    data = json.load(sys.stdin)
    run_dir = os.environ.get("HARNESS_RUN_DIR")
    stage = os.environ.get("HARNESS_STAGE")
    if not run_dir or not stage:
        note = set_up(Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd()))
        if note:
            print(json.dumps(note))
        return 0
    stage_dir = Path(run_dir) / "stages" / stage / os.environ.get("HARNESS_SHARD", "")
    lines = [
        f"Harness run {Path(run_dir).name}, stage {stage}, session source: {data.get('source')}.",
        f"prompt: {stage_dir / 'prompt.md'}",
        f"progress (your checkpoint): {stage_dir / 'progress.md'}",
        f"result: {stage_dir / 'result.json'} (schema: schemas/stage-result.schema.json)",
        f"output directory: {stage_dir / 'output'}",
        f"task list, when your type writes or updates one: {stage_dir / 'tasks.json'} (beside result.json, not in output/)",
        f"inputs from earlier stages (read-only copies): {stage_dir / 'input'}",
    ]
    if os.environ.get("HARNESS_BLIND") == "1":  # a reviewing type does not see the run's escalation directory
        lines.append(f"a question for the human: {stage_dir / 'escalation.json'} (the escalate skill)")
    else:
        lines.append(f"escalations: {Path(run_dir) / 'escalations'}")
    skeleton = {
        "schema_version": 1,
        "run_id": Path(run_dir).name,
        "stage": stage,
        "role_type": os.environ.get("HARNESS_ROLE", ""),
        "status": "partial",
        "outputs": [],
        "summary": "",
        "evidence": [],
        "open_questions": [],
    }
    lines += [
        "Write every file with the Write or Edit tool, not through the shell: the schema check runs there.",
        "Nobody can approve a permission prompt in this session. Keep each Bash call to one plain command.",
        "result.json keeps these fields; fill the rest and set status to complete, escalated or failed at the end:",
        json.dumps(skeleton),
        (
            'An entry of `outputs` is {"path": "output/<file>", "kind": "<kind>"}: the path as seen from your stage '
            "directory. For code on your branch the kind is `code` and the path is the file's path in the repository."
        ),
    ]
    progress = stage_dir / "progress.md"
    if progress.exists():
        lines.append("Tail of progress.md:\n" + progress.read_text(encoding="utf-8")[-4000:])
    if data.get("source") == "compact":
        lines.append("Context was compacted. Re-read progress.md before continuing.")
    out = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(lines),
            "sessionTitle": f"{Path(run_dir).name}/{stage}",
        }
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
