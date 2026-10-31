"""`harness limits` beside a run whose state.json cannot be read (02/F26): the run is named and left out, the others
are reported. Built on the small configuration, so a role session runs it as the write gate does."""

from __future__ import annotations

import json

from harness import launch, limits, state

BRIEF = "# Project brief — demo\n\n## Goal of this run\nNotes.\n\n## Constraints\n- Budget: 10 minutes per stage\n"


def test_limits_names_a_run_it_cannot_read_and_reports_the_others(tmp_path, small_config, monkeypatch):
    monkeypatch.setattr(state, "claude_version", lambda: "test")
    root = small_config(tmp_path / "repo")
    brief = tmp_path / "brief.md"
    brief.write_text(BRIEF, encoding="utf-8")
    run_id = state.create_run(root, "demo", brief, [])["run_id"]
    run_dir = state.runs_root(root) / run_id
    st = state.load(root, run_dir / "state.json", "run-state")
    st["stages"]["read"].update(status="stopped", attempts=1, started_at="2026-10-04T00:00:00+00:00")
    state.save(root, run_dir / "state.json", st, "run-state")
    failure = {"at": "2026-10-04T00:01:00+00:00", "error": "billing_error", "error_details": "spend limit"}
    stage_dir = launch._stage_dir(run_dir, "read", None)
    (stage_dir / "logs").mkdir(parents=True)
    (stage_dir / "logs" / "stop-failure.jsonl").write_text(json.dumps(failure) + "\n", encoding="utf-8")
    bad = state.runs_root(root) / "20261004-000000-bad"
    bad.mkdir()
    (bad / "state.json").write_text('{"status": "running", "stag', encoding="utf-8")
    out = limits.report(root)
    assert [(w["run_id"], w["action"]) for w in out["waiting"]] == [(run_id, "limit_human")]
    assert [u["run_id"] for u in out["unreadable"]] == ["20261004-000000-bad"]
    assert out["unreadable"][0]["why"].startswith("JSONDecodeError")
