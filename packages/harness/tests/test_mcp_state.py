"""`harness mcp-state` (05/F31): the stdio MCP server that .mcp.json defines for the manager, run as Claude Code runs
it (a process on stdio, the initialize handshake) and talked to with the SDK's own client. It serves its four tools
read-only, refuses a run id or a stage that names a place outside the runs root, and follows no link out of it."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from harness import mcp_state
from mcp import Client
from mcp.client.stdio import StdioServerParameters

TOOLS = ["harness_get_run", "harness_list_runs", "harness_open_escalations", "harness_stage_result"]
RUN = "20261004-000000-demo"


def runs_root(tmp_path: Path) -> Path:
    """A checkout and two runs beside it. One has a state, a manifest, an open, an answered and a cut escalation, the
    result of a stage and of a shard; the other has a cut state.json."""
    (tmp_path / "repo").mkdir()
    run = tmp_path / "repo-runs" / RUN
    (run / "escalations").mkdir(parents=True)
    (run / "stages" / "read").mkdir(parents=True)
    (run / "stages" / "write" / "01").mkdir(parents=True)
    state = {"status": "waiting_human", "current_stage": "read", "updated_at": "2026-10-04T00:00:00+00:00"}
    (run / "state.json").write_text(json.dumps(state), encoding="utf-8")
    (run / "manifest.json").write_text(json.dumps({"run_id": RUN}), encoding="utf-8")
    for n, status in (("001", "open"), ("002", "answered")):
        doc = {"id": n, "stage": "read", "question": "Which of the two?", "status": status}
        (run / "escalations" / f"{n}.json").write_text(json.dumps(doc), encoding="utf-8")
    (run / "escalations" / "003.json").write_text('{"id": "003", "stage": "read", "status": "op', encoding="utf-8")
    (run / "stages" / "read" / "result.json").write_text(json.dumps({"status": "complete"}), encoding="utf-8")
    (run / "stages" / "write" / "01" / "result.json").write_text(json.dumps({"status": "partial"}), encoding="utf-8")
    cut = tmp_path / "repo-runs" / "20261004-000001-cut"
    cut.mkdir()
    (cut / "state.json").write_text('{"status": "running", "stag', encoding="utf-8")
    return tmp_path / "repo"


async def session(root: Path, calls: list[tuple[str, dict]]) -> tuple[list[str], list]:
    params = StdioServerParameters(command=sys.executable, args=["-m", "harness.cli", "mcp-state"],
                                   env={**os.environ, "CLAUDE_PROJECT_DIR": str(root)})  # fmt: skip
    async with Client(params, mode="legacy") as client:  # the initialize handshake, as Claude Code 2.1.289 speaks it
        names = sorted(t.name for t in (await client.list_tools()).tools)
        return names, [await client.call_tool(name, args) for name, args in calls]


def test_the_server_lists_its_four_tools_and_answers_each_read_only(tmp_path):
    root = runs_root(tmp_path)
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*"))
    calls = [("harness_list_runs", {}), ("harness_get_run", {"run_id": RUN}), ("harness_open_escalations", {}),
             ("harness_open_escalations", {"run_id": RUN}),
             ("harness_stage_result", {"run_id": RUN, "stage": "read"}),
             ("harness_stage_result", {"run_id": RUN, "stage": "write/01"}),
             ("harness_stage_result", {"run_id": RUN, "stage": "plan"}),
             ("harness_get_run", {"run_id": "20261004-000009-gone"})]  # fmt: skip
    names, results = asyncio.run(session(root, calls))
    assert names == TOOLS and not any(r.is_error for r in results)
    listed, got, escalations, of_one, result, shard, missing, gone = (r.structured_content["result"] for r in results)
    assert listed == [{"run_id": RUN, "status": "waiting_human", "current_stage": "read",
                       "updated_at": "2026-10-04T00:00:00+00:00"}]  # fmt: skip
    assert got["state"]["status"] == "waiting_human" and got["manifest"] == {"run_id": RUN}
    assert [(e["run_id"], e["id"]) for e in escalations] == [(RUN, "001")] and escalations[0]["file"].endswith(
        "001.json"
    )
    assert of_one == escalations
    assert result == {"status": "complete"} and shard == {"status": "partial"} and missing is None and gone is None
    assert sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*")) == before  # it never writes
    fresh = tmp_path / "fresh"  # a checkout whose runs root does not exist yet
    fresh.mkdir()
    assert mcp_state.list_runs(fresh) == [] and mcp_state.open_escalations(fresh) == []
    assert mcp_state.get_run(fresh, RUN) is None and not (tmp_path / "fresh-runs").exists()  # looking makes none


def test_a_run_id_or_a_stage_that_leaves_the_runs_root_is_refused(tmp_path):
    root = runs_root(tmp_path)
    (tmp_path / "state.json").write_text("{}", encoding="utf-8")  # what `..` would reach
    outside = tmp_path / "outside"  # what two links under the runs root lead to
    (outside / "escalations").mkdir(parents=True)
    (outside / "state.json").write_text(json.dumps({"status": "running", "updated_at": "t"}), encoding="utf-8")
    doc = {"id": "009", "stage": "read", "question": "From outside?", "status": "open"}
    (outside / "escalations" / "009.json").write_text(json.dumps(doc), encoding="utf-8")
    (outside / "result.json").write_text(json.dumps({"from": "outside"}), encoding="utf-8")
    runs = tmp_path / "repo-runs"
    (runs / "20261004-000002-link").symlink_to(outside, target_is_directory=True)
    (runs / RUN / "stages" / "linked").mkdir()
    (runs / RUN / "stages" / "linked" / "result.json").symlink_to(outside / "result.json")
    refused = [("harness_get_run", {"run_id": ".."}), ("harness_get_run", {"run_id": "../repo-runs"}),
               ("harness_get_run", {"run_id": ""}), ("harness_get_run", {"run_id": "/etc"}),
               ("harness_get_run", {"run_id": "a\\b"}), ("harness_get_run", {"run_id": "20261004-000002-link"}),
               ("harness_get_run", {"run_id": "x" * 300}),  # longer than a file name: an error, and the server goes on
               ("harness_open_escalations", {"run_id": "a/b"}),
               ("harness_stage_result", {"run_id": RUN, "stage": "../../x"}),
               ("harness_stage_result", {"run_id": RUN, "stage": "write/1"}),
               ("harness_stage_result", {"run_id": RUN, "stage": "/etc"})]  # fmt: skip
    not_followed = [("harness_list_runs", {}), ("harness_open_escalations", {}),
                    ("harness_stage_result", {"run_id": RUN, "stage": "linked"})]  # fmt: skip
    _, results = asyncio.run(session(root, refused + not_followed))
    texts = [r.content[0].text for r in results[: len(refused)]]
    assert all(r.is_error for r in results[: len(refused)])
    assert "no run '..'" in texts[0] and any("no stage '../../x'" in t for t in texts)
    assert not any(r.is_error for r in results[len(refused) :])
    listed, escalations, linked = (r.structured_content["result"] for r in results[len(refused) :])
    assert [r["run_id"] for r in listed] == [RUN] and [(e["run_id"], e["id"]) for e in escalations] == [(RUN, "001")]
    assert linked is None  # a link out of the runs root is not followed
