"""The launcher records the trust `claude --bg` needs (harness/trust.py): the flag alone, never over a change Claude
Code makes to the same file meanwhile."""

from __future__ import annotations

import json
from pathlib import Path

from harness import launch, state, trust

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "docs" / "roles" / "stages.yaml").is_file())


def test_the_checkout_records_its_trust_once_and_keeps_everything_else(tmp_path: Path):
    config, root = tmp_path / ".claude.json", tmp_path / "repo"
    root.mkdir()
    config.write_text(json.dumps({"numStartups": 3, "projects": {"/other": {"hasTrustDialogAccepted": True, "x": 1}}}))
    assert trust.record(root, config) is True
    doc = json.loads(config.read_text())
    assert doc["numStartups"] == 3 and doc["projects"]["/other"] == {"hasTrustDialogAccepted": True, "x": 1}
    assert doc["projects"][str(root.resolve())] == {"hasTrustDialogAccepted": True}  # the flag and nothing else
    assert trust.trusted(root, config)
    assert trust.record(root, config) is False  # recorded already: nothing is written


def test_the_record_keeps_what_claude_code_recorded_for_the_project(tmp_path: Path):
    config, root = tmp_path / ".claude.json", tmp_path / "repo"
    root.mkdir()
    config.write_text(
        json.dumps({"projects": {str(root.resolve()): {"allowedTools": ["Bash(ls)"], "lastSessionId": "s"}}})
    )
    trust.record(root, config)
    entry = json.loads(config.read_text())["projects"][str(root.resolve())]
    assert entry["allowedTools"] == ["Bash(ls)"] and entry["lastSessionId"] == "s" and entry["hasTrustDialogAccepted"]


def test_a_machine_where_claude_code_never_ran_is_left_alone(tmp_path: Path):
    assert trust.record(tmp_path, tmp_path / ".claude.json") is False
    assert not (tmp_path / ".claude.json").exists() and trust.trusted(tmp_path, tmp_path / ".claude.json")


def test_the_record_is_given_up_while_claude_code_writes_the_file(tmp_path: Path, monkeypatch):
    config, root = tmp_path / ".claude.json", tmp_path / "repo"
    root.mkdir()
    config.write_text(json.dumps({"projects": {}}))
    real = trust._temporary

    def claude_code_writes_meanwhile(cfg, text):  # the temporary file is written: so is the config
        out = real(cfg, text)
        config.write_text(json.dumps({"projects": {}, "mcpServers": {"new": {}}}) + " ")
        return out

    monkeypatch.setattr(trust, "_temporary", claude_code_writes_meanwhile)
    monkeypatch.setattr(trust.time, "sleep", lambda s: None)
    assert trust.record(root, config, tries=2) is False
    assert json.loads(config.read_text())["mcpServers"] == {"new": {}}  # its change stands
    assert not list(tmp_path.glob(".claude.json.*.harness-tmp"))


def test_two_records_at_once_never_share_a_temporary_file(tmp_path: Path):
    config = tmp_path / ".claude.json"
    config.write_text("{}")
    first, second = trust._temporary(config, "a"), trust._temporary(config, "b")
    assert first != second and first.read_text() == "a" and second.read_text() == "b"


def test_a_record_the_file_system_refuses_is_a_note_and_the_launch_goes_on(tmp_path: Path, monkeypatch):
    home = tmp_path / "config"
    home.mkdir()
    (home / ".claude.json").write_text("{}")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(home))
    home.chmod(0o500)  # as a sandbox keeps a command from writing outside its checkout
    try:
        note = trust.ensure(tmp_path / "repo")
    finally:
        home.chmod(0o700)
    assert note.startswith("trust not recorded") and json.loads((home / ".claude.json").read_text()) == {}


def test_launch_and_resume_record_the_trust_and_refuse_without_a_sandbox(tmp_path: Path, monkeypatch):
    home = tmp_path / "config"
    home.mkdir()
    (home / ".claude.json").write_text(json.dumps({"projects": {}}))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(home))
    root = tmp_path / "repo"
    root.mkdir()
    assert launch.before_start(root) == {"ok": True, "trust": f"trust recorded for {root.resolve()}"}
    assert launch.before_start(root) == {"ok": True}
    monkeypatch.setattr(launch, "sandbox_problem", lambda r, mode="bg": "socat not on PATH")
    refused = launch.before_start(root)
    assert refused["status"] == "no_sandbox" and refused["why"] == "socat not on PATH" and "password" in refused["fix"]


def test_a_wave_refused_for_its_sandbox_records_no_shard(tmp_path: Path, copy_config, monkeypatch):
    """A per_task stage asks for the sandbox before it splits the planner's tasks: a wave refused at its start leaves
    no shard behind, so the next `harness launch` starts the wave instead of answering already_launched. The
    software-factory table keeps a wave of writers (the default table has one writer since ADR-0024)."""
    root = tmp_path / "repo"
    copy_config(ROOT, root)
    brief = tmp_path / "brief.md"
    brief.write_text("# Project brief — demo\n\n## Goal of this run\nNotes.\n", encoding="utf-8")
    run_id = state.create_run(root, "demo", brief, ["context"], pipeline="software-factory")["run_id"]
    table = state.load_table(root, "software-factory")
    assert next(s for s in table["stages"] if s["id"] == "write").get("parallel") == "per_task"
    run_dir = state.runs_root(root) / run_id
    task = {"category": "code", "description": "d", "steps": ["s"], "depends_on": [], "passes": False}
    tasks = {"schema_version": 1, "stage": "plan", "tasks": [{"id": "T001", **task}, {"id": "T002", **task}]}
    (run_dir / "stages" / "plan").mkdir(parents=True, exist_ok=True)
    state.save(root, run_dir / "stages" / "plan" / "tasks.json", tasks, "tasks")
    monkeypatch.setattr(launch, "status", lambda *args: {"ok": True, "status": "ready"})
    monkeypatch.setattr(launch, "sandbox_problem", lambda r, mode="bg": "socat not on PATH")
    out = launch.launch(root, run_id, "write")
    assert out["status"] == "no_sandbox" and out["why"] == "socat not on PATH"
    st = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert not st["stages"]["write"].get("shards") and not (run_dir / "stages" / "write" / "01").exists()


def test_a_background_session_is_checked_with_the_path_of_the_background_service(
    machine_with_a_sandbox, tmp_path: Path, monkeypatch
):
    """Claude Code's background service keeps the PATH it started with, and every background session inherits it."""
    seen = []
    monkeypatch.setattr(launch.doctor, "service_path", lambda: "/service/bin")
    monkeypatch.setattr(launch.doctor, "sandbox_problem", lambda root, path=None: seen.append(path))
    machine_with_a_sandbox(tmp_path, "bg")
    machine_with_a_sandbox(tmp_path, "print")
    assert seen == ["/service/bin", None]
