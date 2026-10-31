"""Tests for harness/poll.py: how the listing of `claude agents --json` becomes the state of a unit.
Run from the repository root: `uv run pytest -q packages/harness/tests/test_poll.py`."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest
from harness import poll, state

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "docs" / "roles" / "stages.yaml").is_file())
BRIEF = "# Project brief — demo\n\n## Goal of this run\nNotes.\n\n## Constraints\n- Budget: 10 minutes per stage\n"


@pytest.fixture()
def launched(tmp_path: Path, copy_config):
    """A copy of the repository's tables and schemas with one run whose read stage was launched as job j1."""
    root = tmp_path / "repo"
    copy_config(ROOT, root)
    brief = tmp_path / "brief.md"
    brief.write_text(BRIEF, encoding="utf-8")
    run_id = state.create_run(root, "demo", brief, [])["run_id"]
    run_dir = state.runs_root(root) / run_id
    st = state.load(root, run_dir / "state.json", "run-state")
    unit = st["stages"]["read"]
    unit.update(status="launched", attempts=1, session_ids=["s1"], job_ids=["j1"], started_at=state.now())
    state.save(root, run_dir / "state.json", st, "run-state")
    (run_dir / "stages/read/output").mkdir(parents=True)
    return root, run_id, run_dir


def result(run_dir: Path, status: str) -> None:
    doc = {
        "schema_version": 1,
        "run_id": run_dir.name,
        "stage": "read",
        "role_type": "reader",
        "status": status,
        "outputs": [],
        "summary": "s",
        "evidence": [],
        "open_questions": [],
    }
    (run_dir / "stages/read/result.json").write_text(json.dumps(doc), encoding="utf-8")


def unit_after(root: Path, run_id: str, run_dir: Path, row: dict) -> tuple[dict, list[dict]]:
    out = poll.poll(root, run_id, listing=[{"id": "j1", "sessionId": "s1", **row}])
    return state.load(root, run_dir / "state.json", "run-state")["stages"]["read"], out["actions"]


def test_a_session_waiting_at_a_prompt_is_blocked(launched):
    root, run_id, run_dir = launched
    result(run_dir, "partial")
    unit, actions = unit_after(
        root, run_id, run_dir, {"state": "blocked", "status": "waiting", "waitingFor": "permission prompt"}
    )
    assert unit["status"] == "blocked" and not (run_dir / "stages/read/gate.json").exists()
    assert [a["action"] for a in actions] == ["attention"] and actions[0]["waitingFor"] == "permission prompt"


def test_an_idle_session_listed_as_blocked_without_a_final_result_stays_blocked(launched):
    root, run_id, run_dir = launched
    result(run_dir, "partial")
    unit, actions = unit_after(root, run_id, run_dir, {"state": "blocked", "status": "idle"})
    assert unit["status"] == "blocked" and [a["action"] for a in actions] == ["attention"]


def test_an_idle_session_listed_as_blocked_with_a_final_result_has_finished(launched):
    # Claude Code lists a finished session as blocked when its last message asks something; the gate runs all the same
    root, run_id, run_dir = launched
    result(run_dir, "complete")
    unit, _ = unit_after(root, run_id, run_dir, {"state": "blocked", "status": "idle"})
    assert unit["status"] == "gate_failed" and unit["gate"] == "fail"  # the gate ran; this result has no notes
    assert json.loads((run_dir / "stages/read/gate.json").read_text(encoding="utf-8"))["passed"] is False


def test_harness_gate_records_its_verdict_for_a_unit_that_is_not_running(launched):
    root, run_id, run_dir = launched
    result(run_dir, "complete")
    unit_after(root, run_id, run_dir, {"state": "done"})  # gate_failed: no notes yet
    put_notes = run_dir / "stages/read/output"
    (put_notes / "notes.md").write_text(
        '## a.md\n\n- A fact. Quote: "nothing to check here" `missing.md:1`\n\n## Contradictions\n\nnone\n\n'
        "## Probes\n\nnone: the material is a text.\n\n"
        "## Coverage\n\n| Source | Coverage |\n| --- | --- |\n| a.md | read completely |\n",
        encoding="utf-8",
    )
    (put_notes / "questions.md").write_text("none\n", encoding="utf-8")
    out = poll.gate_now(root, run_id, "read")
    unit = state.load(root, run_dir / "state.json", "run-state")["stages"]["read"]
    assert out["passed"] and out["unit_status"] == "done" and unit["status"] == "done" and unit["gate"] == "pass"
    st = state.load(root, run_dir / "state.json", "run-state")  # a running unit is gated without being touched
    st["stages"]["read"]["status"] = "working"
    state.save(root, run_dir / "state.json", st, "run-state")
    assert poll.gate_now(root, run_id, "read")["unit_status"] == "working"


def test_a_file_the_sandbox_left_in_the_escalations_directory_is_not_an_escalation(launched):
    # seen live: the Bash sandbox leaves an empty read-only `.mcp.json` in every directory a session may write to
    root, run_id, run_dir = launched
    (run_dir / "escalations").mkdir(exist_ok=True)
    (run_dir / "escalations/.mcp.json").write_text("", encoding="utf-8")
    result(run_dir, "partial")
    unit, actions = unit_after(root, run_id, run_dir, {"state": "working", "status": "busy"})
    assert unit["status"] == "working" and actions == []
    assert state.list_escalations(root, run_id, None)["escalations"] == []


def test_an_idle_silent_session_listed_as_working_gets_a_resume(launched, monkeypatch):
    # seen live: a session restarted without a message sits idle and is still listed as working
    root, run_id, run_dir = launched
    result(run_dir, "partial")
    st = state.load(root, run_dir / "state.json", "run-state")
    st["stages"]["read"]["started_at"] = (dt.datetime.now(dt.UTC) - dt.timedelta(minutes=10)).isoformat(
        timespec="seconds"
    )
    state.save(root, run_dir / "state.json", st, "run-state")
    row = {"state": "working", "status": "idle"}
    monkeypatch.setattr(poll, "_log_age", lambda session_id: 30.0)  # it wrote half a minute ago: between two steps
    unit, actions = unit_after(root, run_id, run_dir, row)
    assert unit["status"] == "working" and actions == []
    monkeypatch.setattr(poll, "_log_age", lambda session_id: 900.0)
    unit, actions = unit_after(root, run_id, run_dir, row)
    assert unit["status"] == "stopped" and [(a["action"], a["why"]) for a in actions] == [("resume", "stopped")]
    unit, _ = unit_after(root, run_id, run_dir, {"state": "working", "status": "busy"})  # a long command is not idle
    assert unit["status"] == "stopped"  # a stopped unit stays so until it is resumed


def test_a_done_session_is_gated(launched):
    root, run_id, run_dir = launched
    result(run_dir, "complete")
    unit, _ = unit_after(root, run_id, run_dir, {"state": "done"})
    assert unit["status"] == "gate_failed" and (run_dir / "stages/read/gate.json").exists()


def test_a_session_listed_as_working_whose_turn_is_over_and_whose_result_is_final_has_finished(launched, monkeypatch):
    # seen live: a critic that had written its result and ended its turn stayed `working`, `idle` in the listing
    root, run_id, run_dir = launched
    config = run_dir.parent / "config"
    log = config / "projects" / "p" / "s1.jsonl"
    log.parent.mkdir(parents=True)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
    row = {"state": "working", "status": "idle"}
    result(run_dir, "complete")
    log.write_text(json.dumps({"type": "assistant"}) + "\n", encoding="utf-8")  # the turn is still running
    unit, actions = unit_after(root, run_id, run_dir, row)
    assert unit["status"] == "working" and actions == []
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "system", "subtype": "turn_duration"}) + "\n")
        fh.write(json.dumps({"type": "worktree-state"}) + "\n")  # bookkeeping after the turn changes nothing
    unit, _ = unit_after(root, run_id, run_dir, row)
    assert unit["status"] == "gate_failed" and (run_dir / "stages/read/gate.json").exists()  # gated, not resumed


def test_a_stopped_unit_with_a_complete_result_is_gated_instead_of_resumed(launched):
    root, run_id, run_dir = launched
    result(run_dir, "complete")
    st = state.load(root, run_dir / "state.json", "run-state")
    st["stages"]["read"]["status"] = "stopped"
    state.save(root, run_dir / "state.json", st, "run-state")
    out = poll.poll(root, run_id, listing=[])
    unit = state.load(root, run_dir / "state.json", "run-state")["stages"]["read"]
    assert unit["status"] == "gate_failed" and unit["gate"] == "fail"  # the gate spoke; this result has no notes
    assert [(a["action"], a["why"]) for a in out["actions"]] == [("resume", "gate_failed")]
    assert "Gate failed" in out["actions"][0]["message"]  # the resume carries the failed checks, not "continue"


def test_a_print_result_written_as_text_is_taken_when_it_matches_the_schema(launched):
    # seen live: the judge's agent file did not list StructuredOutput, the verdict came back as text and was lost
    from harness import launch

    root, run_id, run_dir = launched
    stage_dir = run_dir / "stages" / "read"
    doc = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "read",
        "role_type": "reader",
        "status": "complete",
        "outputs": [],
        "summary": "s",
        "evidence": [],
        "open_questions": [],
    }
    assert launch.structured_result({"structured_output": doc}) == doc
    assert launch.structured_result({"result": json.dumps(doc)}) == doc
    assert launch.structured_result({"result": "Here it is:\n```json\n" + json.dumps(doc) + "\n```"}) == doc
    assert launch.structured_result({"result": "I could not decide."}) is None

    st, unit = {"cost": {"print_total_usd": 0.0, "note": ""}}, {"status": "launched"}
    out = launch.record_print(root, stage_dir, st, unit, {"result": json.dumps(doc), "total_cost_usd": 0.5}, 0, "")
    assert out["ok"] and unit["status"] == "checkpointed" and (stage_dir / "result.json").is_file()
    bad = launch.record_print(
        root, stage_dir, st, unit, {"result": '{"status": "complete"}', "total_cost_usd": 0.25}, 0, ""
    )
    assert not bad["ok"] and unit["status"] == "failed" and "does not match" in bad["why"]
    assert st["cost"]["print_total_usd"] == 0.75  # a run that returned nothing usable was paid for all the same


def test_every_print_stage_can_return_its_result():
    from harness import access

    for path in [ROOT / "docs/roles/stages.yaml", *sorted((ROOT / "docs/roles/pipelines").glob("*.yaml"))]:
        import yaml

        for row in yaml.safe_load(path.read_text(encoding="utf-8"))["stages"]:
            if row["mode"] == "print" and row.get("json_schema"):
                assert "StructuredOutput" in access.tools_flag(ROOT, row["role_type"]).split(","), (
                    path.name,
                    row["id"],
                )
