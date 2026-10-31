"""Fixtures the harness tests share."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
import yaml

SKIP = shutil.ignore_patterns("worktrees", "__pycache__", "agent-memory*", "settings.local.json")
REPO = next(
    p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file() and (p / "schemas").is_dir()
)


@pytest.fixture(autouse=True)
def own_claude_config(tmp_path_factory, monkeypatch):
    """No test reads or writes the developer's ~/.claude.json: the launcher records a checkout's trust there
    (harness/trust.py). A test that needs that file sets its own directory."""
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path_factory.mktemp("claude-config")))


@pytest.fixture(autouse=True)
def machine_with_a_sandbox(monkeypatch):
    """launch and resume ask whether the sandbox of a role session can start (launch.sandbox_problem); a test machine
    without socat would refuse every launch, so the question is answered here. A test that asks for this fixture gets
    the real question back."""
    from harness import launch

    real = launch.sandbox_problem
    monkeypatch.setattr(launch, "sandbox_problem", lambda root, mode="bg": None)
    return real


@pytest.fixture(autouse=True)
def no_role_session(monkeypatch):
    """A test runs as no role session, also when a role session runs the suite: the CLI refuses every command a role
    session may not run (cli.ROLE_COMMANDS), and a test that wants HARNESS_ROLE sets it itself."""
    for key in [k for k in os.environ if k.startswith("HARNESS_")]:
        monkeypatch.delenv(key)


@pytest.fixture()
def copy_config():
    """Copy the repository's tables, schemas and configuration into a test's own root.

    Inside a role session the sandbox puts entries into `.claude/` that nobody may read (`output-styles`,
    `routines`, `commands`; seen live: the fixtures of two test files failed there with seventeen errors). They are
    no part of the configuration, so a copy that cannot read them leaves them out; any other error still fails."""

    def copy(src: Path, dst: Path, parts: tuple[str, ...] = ("schemas", "docs/roles", ".claude")) -> None:
        for rel in parts:
            try:
                shutil.copytree(src / rel, dst / rel, ignore=SKIP)
            except shutil.Error as exc:
                if not all("Permission denied" in str(entry[2]) for entry in exc.args[0]):
                    raise

    return copy


@pytest.fixture()
def small_config():
    """A configuration a role session may read whole: the repository's schemas, a table of two stages (`read` by a
    reader, then `plan` by a planner) and a policy with a row for each type. Tests of specs/001-chat-depth build their
    runs on it instead of copying docs/roles and .claude, so that a writer runs them without a closed file."""

    def make(root: Path) -> Path:
        shutil.copytree(REPO / "schemas", root / "schemas")
        common = {"mode": "bg", "model": "sonnet", "effort": "high", "output": "output/", "approval": "none",
                  "permission_mode": "acceptEdits", "max_minutes": 30, "max_attempts": 2}  # fmt: skip
        stages = [
            {"id": "read", "role_type": "reader", "inputs": ["brief"], "gate": "read", **common},
            {
                "id": "plan",
                "role_type": "planner",
                "inputs": ["brief"],
                "gate": "plan",
                "depends_on": ["read"],
                **common,
            },
        ]
        roles = root / "docs" / "roles"
        roles.mkdir(parents=True)
        table = {"version": 1, "stages": stages, "no_match": {"action": "escalate", "message": "no table fits"}}
        (roles / "stages.yaml").write_text(yaml.safe_dump(table), encoding="utf-8")
        policy = {"schema_version": 1, "defaults": {}, "types": {"reader": {}, "planner": {}}}
        (roles / "need-to-know.yaml").write_text(yaml.safe_dump(policy), encoding="utf-8")
        return root

    return make
