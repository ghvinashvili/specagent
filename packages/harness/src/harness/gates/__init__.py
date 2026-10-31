"""Deterministic gates between stages. A gate reads files only; it never asks a model. A sharded stage is gated per shard."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import ModuleType

import jsonschema

from .. import access, state  # this module is the package harness.gates; access and state are one level up
from . import _common, steps


def _writes_files(root: Path, run_dir: Path, stage_id: str) -> bool:
    """Whether the stage's type can write a file (access.writes_files). A type that cannot, one whose agent file lists
    tools, none of them Write or Bash (judge, comparator, quarantine reader, classifier), returns its result as
    structured output only: it has no document in which to account for its material, and its own gate checks its
    structured result (seen 2026-10-03: a judge failed its gate on 39 files it had no way to account for). Whatever
    cannot be read counts as writing, so the check stays: a run without a manifest, a stage the manifest does not
    name, a type without an agent file, and a type whose agent file lists no tools."""
    role_type = _manifest_stage(run_dir, stage_id).get("role_type")
    return not role_type or access.writes_files(root, role_type)


def common_checks(root: Path, run_dir: Path, stage_dir: Path, stage_id: str) -> list[dict]:
    checks = []
    result = _common.stage_file(stage_dir, "result.json")  # None for a link: its target is not this stage's result
    ok = result is not None
    checks.append({"name": "result.json exists", "passed": ok})
    if result is not None:
        try:
            doc = json.loads(result.read_text(encoding="utf-8"))
            jsonschema.validate(doc, state.schema(root, "stage-result"))
            checks.append({"name": "result.json valid against stage-result.schema.json", "passed": True})
            checks.append({"name": "result.stage matches", "passed": doc.get("stage") == stage_id})
            checks.append(
                {
                    "name": "result.status is complete",
                    "passed": doc.get("status") == "complete",
                    "detail": str(doc.get("status")),
                }
            )
            for out in doc.get("outputs", []):
                if out["kind"] == "code":
                    continue  # a path in the repository, on the stage's branch: the stage's own gate checks it there
                p = state.output_file(run_dir, stage_dir, out["path"])
                checks.append(
                    {
                        "name": f"output exists: {out['path']}",
                        "passed": p is not None and p.stat().st_size > 0,
                        **(
                            {}
                            if p
                            else {"detail": "no such file in the stage directory; write the path as output/<file>"}
                        ),
                    }
                )
        except (json.JSONDecodeError, jsonschema.ValidationError) as exc:
            checks.append(
                {
                    "name": "result.json valid against stage-result.schema.json",
                    "passed": False,
                    "detail": str(exc)[:300],
                }
            )
    if _common.material_files(stage_dir) and _writes_files(root, run_dir, stage_id):  # a type that writes: a file
        # of its material is used or said to hold nothing
        missed = _common.unaccounted_material(stage_dir)
        checks.append(
            {
                "name": "every file of the material is accounted for",
                "passed": not missed,
                **(
                    {"detail": "; ".join(missed[:3]) + " — name each in Coverage or head a section with it"}
                    if missed
                    else {}
                ),
            }
        )
    return checks


def _manifest_stage(run_dir: Path, stage_id: str) -> dict:
    try:
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return next((s for s in manifest.get("stages", []) if s.get("id") == stage_id), {})


def steps_mode(run_dir: Path, stage_id: str) -> str:
    """The mode the run fixed for the stage when it was created (manifest `steps`); `warn` for a run made before."""
    return _manifest_stage(run_dir, stage_id).get("steps") or "warn"


def last_session(run_dir: Path, stage_dir: Path) -> str | None:
    """The newest session id of the unit (stage or shard) in state.json: a continued copy carries the conversation
    it continues, an attempt started afresh does the steps again."""
    try:
        st = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    parts = stage_dir.relative_to(run_dir / "stages").parts
    unit = st.get("stages", {}).get(parts[0], {})
    if len(parts) > 1:
        unit = unit.get("shards", {}).get(parts[1], {})
    return (unit.get("session_ids") or [None])[-1]


def new_checks(
    root: Path, run_dir: Path, stage_dir: Path, module: ModuleType, gate: list[dict], repo: Path | None = None
) -> list[dict]:
    """The checks of specs/001-chat-depth for one unit: its transcript found, every `path:line` exists, every evidence
    command was run, the gate module's `content_checks`, and one check per step of its type's method. `gate` is what
    the stage's own checks said in this run; an `output:` rule reads it. `repo` is where git looks (`--repo`)."""
    from .. import launch, transcript  # launch imports this package

    repo = repo or root
    session = last_session(run_dir, stage_dir)
    path = launch.transcript_of(session) if session else None
    events = transcript.events(path) if path else None
    out = [_common.locator_check(repo, run_dir, stage_dir)]
    if session and events is None:
        out.append(_common.check("the session's transcript was found", False, f"no transcript of session {session}"))
    if events is not None:
        out.append(_common.evidence_check(stage_dir, events))
    out += getattr(module, "content_checks", lambda *a: [])(repo, run_dir, stage_dir, events)
    role_type = _manifest_stage(run_dir, stage_dir.relative_to(run_dir / "stages").parts[0]).get("role_type")
    if role_type:
        seen = {c["name"]: c["passed"] for c in gate + out}
        ctx = steps.context(repo, run_dir, stage_dir, events, seen)
        out += steps.step_checks(steps.agent_steps(root, role_type), ctx)
    return out


def _evaluate(root: Path, run_id: str, stage_id: str, shard: int | None, session: bool) -> tuple:
    """(checks that decide, advisory checks, mode): the stage's own checks always decide; the new checks decide in
    `enforce` and are advisory in `warn`. Both entry points, the verdict and the preview, go through here."""
    run_dir = state.runs_root(root) / run_id
    stage_dir = run_dir / "stages" / stage_id / (f"{shard:02d}" if shard else "")
    module = importlib.import_module(f"harness.gates.{stage_id}")
    checks = common_checks(root, run_dir, stage_dir, stage_id)
    checks += (getattr(module, "session_checks", module.checks) if session else module.checks)(root, run_dir, stage_dir)
    new = new_checks(root, run_dir, stage_dir, module, checks)
    mode = steps_mode(run_dir, stage_id)
    return (checks + new, [], mode) if mode == "enforce" else (checks, new, mode)


def preview(root: Path, run_id: str, stage_id: str, shard: int | None) -> dict:
    """What the gate would say now, without recording anything: the stop hook of a role session asks this before
    the session may end with `complete`, so that work the gate refuses is repaired by its author while the session
    is still warm, instead of after a stop, a poll and a resume. A gate module names in `session_checks` the part of
    its checks a session can be held to; the commands a gate runs outside any session (the whole test suite) stay
    with `run_gate`, which remains the verdict."""
    checks, _, _ = _evaluate(root, run_id, stage_id, shard, session=True)
    failing = [c for c in checks if not c["passed"]]
    return {"ok": not failing, "stage": stage_id, "failing": failing, **({"shard": shard} if shard else {})}


def run_gate(root: Path, run_id: str, stage_id: str, shard: int | None) -> dict:
    run_dir = state.runs_root(root) / run_id
    stage_dir = run_dir / "stages" / stage_id / (f"{shard:02d}" if shard else "")
    checks, advisory, mode = _evaluate(root, run_id, stage_id, shard, session=False)
    passed = all(c["passed"] for c in checks)
    escalated = _common.result(stage_dir).get("status") == "escalated"  # a link is not read (stage_file)
    verdict = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": stage_id,
        "gate": stage_id,
        "passed": passed,
        "checked_at": state.now(),
        "checks": checks,
        "next": "advance" if passed else ("escalate" if escalated else "retry"),
        "steps_mode": mode,
    }
    if advisory:  # warn: recorded for the human (HANDOFF.md, harness steps), not counted in `passed`
        verdict["advisory"] = advisory
    if shard:
        verdict["shard"] = shard
    state.save(root, stage_dir / "gate.json", verdict, "gate-verdict")
    return verdict


def review(root: Path, run_dir: Path, repo: Path | None = None) -> dict:
    """`harness steps`: the checks of specs/001-chat-depth over every unit of a run that had a session, from its
    state.json, its stages' files and its sessions' transcripts. Writes nothing, asks no model. The stage's own checks
    are its session checks (no test suite), which is what an `output:` rule reads."""
    from .. import launch

    try:
        st = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "status": "no_run", "why": str(exc)}
    rows, missing = [], []
    for stage in manifest["stages"]:
        ss = st["stages"].get(stage["id"], {})
        units = sorted(ss["shards"].items()) if ss.get("shards") else [("", ss)]
        module = importlib.import_module(f"harness.gates.{stage['id']}")
        for shard, unit in units:
            if not unit.get("session_ids"):
                continue  # never launched
            stage_dir = run_dir / "stages" / stage["id"] / shard if shard else run_dir / "stages" / stage["id"]
            gate = common_checks(root, run_dir, stage_dir, stage["id"])
            gate += getattr(module, "session_checks", module.checks)(root, run_dir, stage_dir)
            label = stage["id"] + (f"/{shard}" if shard else "")
            if launch.transcript_of(unit["session_ids"][-1]) is None:
                missing.append({"unit": label, "session": unit["session_ids"][-1]})
            for c in new_checks(root, run_dir, stage_dir, module, gate, repo):
                rows.append({"type": stage["role_type"], "unit": label, **c})
    rows.sort(key=lambda r: (r["type"], _step_number(r["name"]), r["unit"]))
    failed = [r for r in rows if not r["passed"]]
    return {"ok": True, "run": run_dir.name, "checks": len(rows), "failed": len(failed), "no_transcript": missing,
            "rows": rows}  # fmt: skip


def _step_number(name: str) -> int:
    """Rows of one type: the run-wide checks first, then the steps in their order."""
    head = name.split(":", 1)[0]
    return int(head.split()[1]) if head.startswith("step ") and head.split()[1].isdigit() else 0
