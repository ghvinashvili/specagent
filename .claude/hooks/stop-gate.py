#!/usr/bin/env python3
"""Stop hook: a role session may stop only with a result.json that is valid against the schema and final
(complete, escalated or failed), or with an open escalation for its stage. A `partial` result is a checkpoint, not an end.

A session that says `complete` is also held to its own stage's gate: the hook asks `harness gate --preview` which
checks would fail and sends the session back with their names while it still has its context, instead of letting it
stop, be polled, fail the gate and be resumed. The hook holds a unit at most MAX_HOLDS times, counted where the session
cannot write (`<run>/logs/stop-gate/`); after that, and whenever the preview cannot be had, the stop is allowed and the
gate outside the session gives the verdict.

The schemas and the harness are the main checkout's (CLAUDE_PROJECT_DIR, mapped to the main checkout when it is a
checkout), so the preview asks the gate of the session's own run. A file of the stage that is a link is not read. A
crash of this hook lets the stop through and is logged: exit 2 would keep the session working, and the gate outside
decides (docs/decisions/0020)."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

FINAL = {"complete", "escalated", "failed"}
MAX_HOLDS = 3
PREVIEW_SECONDS = 120


def main_checkout(path: Path) -> Path:
    """The main checkout of a checkout under `.claude/worktrees/`; else the path itself."""
    return path.parents[2] if path.parent.name == "worktrees" and path.parents[1].name == ".claude" else path


def _jsonschema():
    """python3's own jsonschema, or the workspace's when the workspace was made from the same Python (ops/bootstrap.py
    makes it so): a fresh machine has the workspace, not always python3-jsonschema. None when neither has it."""
    try:
        import jsonschema
    except ImportError:
        v = sys.version_info
        main = main_checkout(Path(os.environ.get("CLAUDE_PROJECT_DIR") or "."))
        sys.path.append(str(main / ".venv" / "lib" / f"python{v[0]}.{v[1]}" / "site-packages"))
        try:
            import jsonschema
        except ImportError:
            return None
    return jsonschema


def schema_errors(root: Path, doc: dict, name: str = "stage-result") -> str | None:
    jsonschema = _jsonschema()
    if jsonschema is None:
        return None  # parse-only where jsonschema is not installed
    schema = json.loads((root / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft7Validator(schema).iter_errors(doc), key=lambda e: list(e.path))
    return "; ".join(f"{'/'.join(map(str, e.path)) or '$'}: {e.message}" for e in errors[:5]) or None


def open_escalation(root: Path, path: Path, stage: str, shard: int | None) -> bool:
    """A blind session's question in its stage directory, not yet filed by `harness poll`: it lets the session stop
    only when it is an open escalation of this stage (and shard), valid against schemas/escalation.schema.json. A
    withdrawn, empty or broken file, or a link, does not."""
    if path.is_symlink() or not path.is_file():
        return False
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(doc, dict) or (doc.get("status"), doc.get("stage"), doc.get("shard")) != ("open", stage, shard):
        return False
    return schema_errors(root, doc, "escalation") is None


def failing_checks(root: Path, run_dir: Path, stage: str, shard: int | None) -> list[dict] | None:
    """The checks the stage's gate would fail now, or None when nobody could be asked. The harness is reached
    through the interpreter that launched the session (HARNESS_PYTHON), the project's environment, or `uv`."""
    python = os.environ.get("HARNESS_PYTHON", "")
    own = root / ".venv" / "bin" / "harness"
    uv = shutil.which("uv")
    if python and Path(python).is_file():
        cmd = [python, "-m", "harness.cli"]
    elif own.is_file():
        cmd = [str(own)]
    elif uv:
        cmd = [uv, "run", "harness"]
    else:
        return None
    cmd += ["gate", "--preview", "--run", run_dir.name, "--stage", stage, *(["--shard", str(shard)] if shard else [])]
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root)}
    try:
        res = subprocess.run(
            cmd, cwd=root, env=env, capture_output=True, text=True, check=False, timeout=PREVIEW_SECONDS
        )
        return json.loads(res.stdout)["failing"]
    except Exception as exc:  # noqa: BLE001 — no verdict here is not a verdict; the gate outside the session decides
        note(run_dir, stage, shard, f"no answer from `gate --preview`: {type(exc).__name__}: {str(exc)[:200]}")
        return None


def note(run_dir: Path, stage: str, shard: int | None, text: str) -> None:
    """One line per decision of the hold in `<stage dir>/logs/stop-gate.log`: what was asked for, and when."""
    import datetime as dt

    log = run_dir / "stages" / stage / (f"{shard:02d}" if shard else "") / "logs" / "stop-gate.log"
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as fh:
            fh.write(f"{dt.datetime.now(dt.UTC).isoformat(timespec='seconds')} {text}\n")
    except OSError:
        pass


def holds_file(run_dir: Path, stage: str, shard: int | None) -> Path:
    """Where the hook counts its holds of a unit: in the run's logs, which the session can neither read nor write."""
    return run_dir / "logs" / "stop-gate" / (f"{stage}-{shard:02d}.holds" if shard else f"{stage}.holds")


def held(root: Path, run_dir: Path, stage: str, shard: int | None) -> str | None:
    """Why a session that says `complete` may not stop yet, or None."""
    count = holds_file(run_dir, stage, shard)
    try:
        holds = int(count.read_text(encoding="utf-8").strip() or 0) if count.is_file() else 0
    except ValueError:
        holds = 0
    if os.environ.get("HARNESS_STOP_GATE") == "off" or holds >= MAX_HOLDS:
        return None
    failing = failing_checks(root, run_dir, stage, shard)
    if not failing:
        if failing is not None:
            note(run_dir, stage, shard, "the gate would pass: stop allowed")
        return None
    count.parent.mkdir(parents=True, exist_ok=True)
    count.write_text(str(holds + 1), encoding="utf-8")
    names = "; ".join(c["name"] + (f" ({c['detail']})" if c.get("detail") else "") for c in failing)
    note(run_dir, stage, shard, f"held ({holds + 1} of {MAX_HOLDS}): {names}")
    return (
        f"the gate of stage {stage} would refuse this work: {names}. Do what is missing (your instruction and your "
        "assignment say what each of these is), update result.json, then stop. What cannot be done is an escalation, "
        "not a `complete`"
    )


def main() -> int:
    data = json.load(sys.stdin)
    run_dir = os.environ.get("HARNESS_RUN_DIR")
    stage = os.environ.get("HARNESS_STAGE")
    if not run_dir or not stage or os.environ.get("HARNESS_MODE") == "print":
        return 0
    shard_env = os.environ.get("HARNESS_SHARD", "")
    shard = int(shard_env) if shard_env else None
    stage_dir = Path(run_dir) / "stages" / stage / shard_env
    root = main_checkout(Path(os.environ["CLAUDE_PROJECT_DIR"]).resolve())
    escalations = Path(run_dir) / "escalations"
    for path in sorted(escalations.glob("[0-9][0-9][0-9].json")) if escalations.exists() else []:
        try:
            esc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001, S112 — an unreadable escalation file is not this stage's open question
            continue
        if (
            esc.get("stage") == stage and esc.get("shard") == shard and esc.get("status") == "open"
        ):  # a shard's escalation frees that shard only
            return 0
    if open_escalation(root, stage_dir / "escalation.json", stage, shard):  # a blind session's, not yet filed
        return 0
    result = stage_dir / "result.json"
    advice = (
        f"Rewrite {result} following schemas/stage-result.schema.json with status complete, escalated or failed, "
        f"or write an escalation with status open in {escalations}/ for stage {stage}, then stop."
    )
    if result.is_symlink():
        reason = f"{result} is a link; write the file itself"
    elif result.exists():
        try:
            doc = json.loads(result.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            reason = f"{result} is not valid JSON: {exc}"
        else:
            invalid = schema_errors(root, doc)
            if invalid:
                reason = f"{result} fails schemas/stage-result.schema.json: {invalid}"
            elif doc.get("stage") == stage and doc.get("status") in FINAL:
                reason = held(root, Path(run_dir), stage, shard) if doc["status"] == "complete" else None
                if not reason:
                    return 0
                advice = ""
            else:
                reason = f"{result} has stage={doc.get('stage')!r} status={doc.get('status')!r} (partial is a checkpoint, not an end)"
    else:
        reason = f"{result} does not exist"
    blocks = data.get("stop_hook_active") and " (stop hook already active)" or ""
    print(json.dumps({"decision": "block", "reason": f"Stop gate{blocks}: {reason}. {advice}".strip()}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - a crash lets the stop through (exit 2 would keep the session working)
        run, stage, shard = (
            os.environ.get("HARNESS_RUN_DIR"),
            os.environ.get("HARNESS_STAGE"),
            os.environ.get("HARNESS_SHARD"),
        )
        if run and stage:
            number = int(shard) if shard and shard.isdigit() else None
            note(Path(run), stage, number, f"the hook crashed: {type(exc).__name__}: {exc}")
        sys.exit(0)
