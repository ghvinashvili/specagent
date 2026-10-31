"""A run takes the model and the effort of the stage table as they are; the session that creates it is recorded and
changes nothing (docs/decisions/0024); an `--effort` flag above the table raises the time limit.
Run: `uv run pytest -q packages/harness/tests/test_model_effort.py`."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from harness import cli, state

APPENDIX = Path(__file__).parent / "fixtures" / "transcripts" / "appendix.jsonl"
BRIEF = "# Project brief — demo\n\n## Goal of this run\nNotes.\n"
SID = "11111111-2222-3333-4444-555555555555"


def row(**extra) -> dict:
    return {"id": "read", "role_type": "reader", "model": "sonnet", "effort": "high", "max_minutes": 30, **extra}


def session(model: str = "claude-opus-5-5", effort: str = "max") -> dict:
    return {"inherited": True, "session_id": SID, "model": model, "effort": effort}


def test_the_table_is_exact_and_the_session_changes_nothing():
    kept = state.choose_stage(row(), session(), None)
    assert (kept["model"], kept["effort"], kept["max_minutes"]) == ("sonnet", "high", 30)
    assert kept["source"] == {"model": "table", "effort": "table", "max_minutes": "table"}
    assert kept["floor"] == {"model": "sonnet", "effort": "high", "max_minutes": 30}
    weak = state.choose_stage(row(model="opus", effort="max"), session("claude-haiku-4-5", "low"), None)
    assert (weak["model"], weak["effort"], weak["max_minutes"]) == ("opus", "max", 30)


@pytest.mark.parametrize(
    ("name", "family"),
    [("claude-opus-5-5", "opus"), ("claude-sonnet-5-5", "sonnet"), ("claude-haiku-4-5", "haiku"),
     ("claude-fable-5-1", "opus"), ("<synthetic>", None), ("gpt-x", None)],
)  # fmt: skip
def test_a_model_is_read_as_its_family_and_fable_counts_as_opus(name: str, family: str | None):
    assert state.family(name) == family


@pytest.mark.parametrize(("effort", "minutes"), [("high", 30), ("xhigh", 60), ("max", 90)])
def test_the_time_limit_follows_an_effort_flag_above_the_table(effort: str, minutes: int):
    assert state.choose_stage(row(), session("claude-sonnet-5-5", "low"), effort)["max_minutes"] == minutes


def test_classifier_and_quarantine_reader_keep_the_table(tmp_path: Path):
    for role_type in state.FIXED_TYPES:
        kept = state.choose_stage(row(role_type=role_type, model="haiku", effort="low"), session(), None)
        assert (kept["model"], kept["effort"], kept["source"]["model"]) == ("haiku", "low", "table")


def test_an_effort_flag_stands_above_everything():
    flagged = state.choose_stage(row(), session(effort="max"), "medium")
    assert (flagged["effort"], flagged["source"]["effort"], flagged["max_minutes"]) == ("medium", "flag", 30)
    fixed = state.choose_stage(row(role_type="classifier"), session(), "xhigh")
    assert (fixed["effort"], fixed["max_minutes"]) == ("xhigh", 60)


def write_log(config: Path, lines: list[dict]) -> None:
    path = config / "projects" / "p" / f"{SID}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(x) + "\n" for x in lines), encoding="utf-8")


def test_the_session_is_read_from_its_transcript_or_named_as_not_found(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "config"))
    assert state.resolve_model_effort(None)["inherited"] is False
    assert "CLAUDE_CODE_SESSION_ID is not set" in state.resolve_model_effort({})["reason"]
    assert "no transcript" in state.resolve_model_effort({"CLAUDE_CODE_SESSION_ID": SID})["reason"]
    lines = [json.loads(x) for x in APPENDIX.read_text(encoding="utf-8").splitlines()]
    last = copy.deepcopy(lines[8])
    last.update(effort="max", perTurnEffort="max")
    last["message"]["model"] = "claude-opus-5-5"
    write_log(tmp_path / "config", [*lines[:8], last, lines[9]])  # the <synthetic> line comes last
    found = state.resolve_model_effort({"CLAUDE_CODE_SESSION_ID": SID})
    assert found == {"inherited": True, "session_id": SID, "model": "claude-opus-5-5", "effort": "max"}


def test_harness_run_records_the_choice_and_its_source_and_prints_it(tmp_path: Path, small_config, monkeypatch, capsys):
    root = small_config(tmp_path / "repo")
    brief = tmp_path / "brief.md"
    brief.write_text(BRIEF, encoding="utf-8")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    assert cli.main(["run", "--slug", "plain", "--brief", str(brief)]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["session"]["inherited"] is False and "not set" in printed["session"]["reason"]
    table = {r["id"]: r for r in state.load_table(root)["stages"]}
    plain = json.loads((Path(printed["run_dir"]) / "manifest.json").read_text(encoding="utf-8"))
    assert all(
        s["model"] == table[s["id"]]["model"] and s["effort"] == table[s["id"]]["effort"] for s in plain["stages"]
    )
    lines = [json.loads(x) for x in APPENDIX.read_text(encoding="utf-8").splitlines()]
    last = copy.deepcopy(lines[8])
    last.update(effort="max")
    last["message"]["model"] = "claude-opus-5-5"
    write_log(tmp_path / "config", [last])
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", SID)
    assert cli.main(["run", "--slug", "hard", "--brief", str(brief), "--effort", "plan=medium"]) == 0
    manifest = json.loads((Path(json.loads(capsys.readouterr().out)["run_dir"]) / "manifest.json").read_text())
    stages = {s["id"]: s for s in manifest["stages"]}
    assert manifest["session"]["inherited"] and manifest["session"]["effort"] == "max"
    assert (stages["read"]["model"], stages["read"]["effort"]) == (table["read"]["model"], table["read"]["effort"])
    assert stages["read"]["source"] == {"model": "table", "effort": "table", "max_minutes": "table"}
    assert stages["read"]["max_minutes"] == table["read"]["max_minutes"]
    assert stages["plan"]["effort"] == "medium" and stages["plan"]["source"]["effort"] == "flag"
    assert all(s["steps"] == "warn" for s in stages.values())  # the policy names no mode: warn
    assert manifest["limits"]["max_minutes_per_stage"] == max(s["max_minutes"] for s in stages.values())
