"""V3: the commit skill tells a committing role that commitizen's commit-msg stage rejects a bad header; the template
installs that stage (the plugin hook that did it in every session is gone, S3)."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def test_pre_commit_installs_the_commit_msg_stage_commitizen_runs_in() -> None:
    config = (REPO / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert config.splitlines()[0] == "default_install_hook_types: [pre-commit, commit-msg]"
    assert "id: commitizen" in config and "stages: [commit-msg]" in config


def test_contributing_names_the_install_command_that_writes_both_hooks() -> None:
    contributing = (REPO / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "`pre-commit install`" in contributing and "--hook-type" not in contributing


def test_the_commit_skill_says_where_the_commit_msg_stage_runs() -> None:
    skill = (REPO / ".claude" / "skills" / "commit-style" / "SKILL.md").read_text(encoding="utf-8")
    assert (
        "commitizen's commit-msg stage rejects a header that does not match, where the project installed it"
        in skill.lower()
    )
