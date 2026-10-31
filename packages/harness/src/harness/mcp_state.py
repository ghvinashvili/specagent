"""`harness mcp-state`: a stdio MCP server that exposes run state read-only to the manager session.
Tools (namespaced with the harness_ prefix):
  harness_list_runs()                       -> [{run_id, status, current_stage, updated_at}]
  harness_get_run(run_id)                   -> state.json + manifest.json
  harness_open_escalations(run_id=None)     -> [{run_id, id, stage, question, file}]
  harness_stage_result(run_id, stage)       -> result.json or null
The repository root is CLAUDE_PROJECT_DIR, read from the server's own environment (Claude Code sets it for stdio
servers); the runs root is the one state.runs_root() finds. It never writes, and it reads nothing outside the runs
root: a run id or a stage that names another place is refused, and a file reached through a link that leads out of
the runs root is not read."""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import state

STAGE = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9._-]*(/[0-9]{2})?$")  # a stage id, or a stage and its shard: write/01


def _runs(root: Path) -> Path:
    return state.runs_root(root, create=False)


def _run_dir(root: Path, run_id: str) -> Path:
    """The folder of a run directly under the runs root. Any other name is refused, so no tool reads outside it."""
    base = _runs(root)
    if (
        not run_id
        or "/" in run_id
        or "\\" in run_id
        or run_id in (".", "..")
        or (base / run_id).resolve().parent != base.resolve()
    ):
        raise ValueError(f"no run {run_id!r}: a run id names a folder directly under {base}")
    return base / run_id


def _json(root: Path, path: Path) -> object | None:
    """A JSON file of the runs root as it is, or None when it is missing, cannot be read, or is reached through a link
    that leads out of the runs root."""
    try:
        if not path.resolve().is_relative_to(_runs(root).resolve()):
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, RuntimeError, ValueError):  # RuntimeError: Path.resolve met a loop of links
        return None


def list_runs(root: Path) -> list[dict]:
    """Every run whose state.json can be read, oldest first: its id, status, current stage and last poll."""
    out = []
    for path in sorted(_runs(root).glob("*-*/state.json")):
        doc = _json(root, path)
        if isinstance(doc, dict):
            keys = ("status", "current_stage", "updated_at")
            out.append({"run_id": path.parent.name, **{k: doc.get(k) for k in keys}})
    return out


def get_run(root: Path, run_id: str) -> dict | None:
    """The state.json and manifest.json of one run, or None when the run has no state."""
    run_dir = _run_dir(root, run_id)
    if not (run_dir / "state.json").is_file():
        return None
    return {"state": _json(root, run_dir / "state.json"), "manifest": _json(root, run_dir / "manifest.json")}


def open_escalations(root: Path, run_id: str | None = None) -> list[dict]:
    """The open escalations of one run, or of every run."""
    dirs = [_run_dir(root, run_id)] if run_id else sorted(p.parent for p in _runs(root).glob("*-*/state.json"))
    out = []
    for run_dir in dirs:
        for path in sorted((run_dir / "escalations").glob(state.ESCALATION)):
            doc = _json(root, path)
            if isinstance(doc, dict) and doc.get("status") == "open":
                keys = ("id", "stage", "question")
                out.append({"run_id": run_dir.name, **{k: doc.get(k) for k in keys}, "file": str(path)})
    return out


def stage_result(root: Path, run_id: str, stage: str) -> object | None:
    """The result.json of a stage (`write/01` for a shard), or None while it has none."""
    run_dir = _run_dir(root, run_id)
    if not STAGE.match(stage) or ".." in stage:
        raise ValueError(f"no stage {stage!r}: a stage is its id, or its id and a shard as write/01")
    return _json(root, run_dir / "stages" / stage / "result.json")


def serve(root: Path) -> int:
    """Serve the four tools over stdio until the client closes the stream; returns the exit code."""
    from mcp.server.mcpserver import MCPServer  # the SDK is imported by this command only
    from mcp.server.mcpserver.exceptions import ToolError

    server = MCPServer("harness-state", instructions="Run state of this checkout's harness runs, read-only.")

    def asked(fn, *args):
        try:
            return fn(root, *args)
        except ValueError as exc:  # a refused run id or stage: the reason reaches the client, no traceback is logged
            raise ToolError(str(exc)) from exc

    def harness_list_runs() -> list[dict]:
        return asked(list_runs)

    def harness_get_run(run_id: str) -> dict | None:
        return asked(get_run, run_id)

    def harness_open_escalations(run_id: str | None = None) -> list[dict]:
        return asked(open_escalations, run_id)

    def harness_stage_result(run_id: str, stage: str) -> object | None:
        return asked(stage_result, run_id, stage)

    server.add_tool(harness_list_runs, description=list_runs.__doc__)
    server.add_tool(harness_get_run, description=get_run.__doc__)
    server.add_tool(harness_open_escalations, description=open_escalations.__doc__)
    server.add_tool(harness_stage_result, description=stage_result.__doc__)
    server.run("stdio")
    return 0
