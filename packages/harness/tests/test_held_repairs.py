"""Four repairs of wave 1 that no test held (R9 of run 20261009-022929-fix-w1-revise): each test passes with the
repair and fails on a copy of the hook with the repair taken out (output/trial/mutants.py of the plan stage)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[3] / ".claude" / "hooks"
SCHEMAS = Path(__file__).resolve().parents[3] / "schemas"


def answer(name: str, payload: dict, env: dict) -> str:
    """What a PreToolUse hook decided: `deny`, `allow` (it printed nothing), or `exit <code>`."""
    res = subprocess.run(
        [sys.executable, str(HOOKS / name)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": "/usr/bin:/bin", **env},
    )
    if res.returncode:
        return f"exit {res.returncode}"
    return json.loads(res.stdout)["hookSpecificOutput"]["permissionDecision"] if res.stdout.strip() else "allow"


def test_validate_json_takes_its_schemas_from_the_main_checkout_when_the_project_directory_is_a_checkout(
    tmp_path: Path,
):
    """Item 7e: a checkout's own copy of a schema (here one that accepts anything) is not the one a run's file is held
    to; the main checkout's is."""
    root = tmp_path / "repo"
    (root / "schemas").mkdir(parents=True)
    shutil.copy(SCHEMAS / "stage-result.schema.json", root / "schemas" / "stage-result.schema.json")
    checkout = root / ".claude" / "worktrees" / "r1-write"
    (checkout / "schemas").mkdir(parents=True)
    (checkout / "schemas" / "stage-result.schema.json").write_text("{}", encoding="utf-8")
    target = tmp_path / "runs" / "20261009-000000-r1" / "stages" / "plan" / "result.json"
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Write",
               "tool_input": {"file_path": str(target), "content": '{"schema_version": 1}'}}  # fmt: skip
    assert answer("validate-json.py", payload, {"CLAUDE_PROJECT_DIR": str(checkout)}) == "deny"


def test_guard_inbox_finds_the_inbox_of_the_main_checkout_when_the_project_directory_is_a_checkout(tmp_path: Path):
    """Item 7e: without the mapping the hook looked for the inbox beside the checkout and let the real one through."""
    checkout = tmp_path / "template" / ".claude" / "worktrees" / "w1"
    checkout.mkdir(parents=True)
    inbox = tmp_path / "template-runs" / "_inbox" / "upload"
    inbox.mkdir(parents=True)
    (inbox / "note.txt").write_text("UNTRUSTED\n", encoding="utf-8")
    payload = {
        "tool_name": "Read",
        "tool_input": {"file_path": str(inbox / "note.txt")},
        "hook_event_name": "PreToolUse",
    }
    assert answer("guard-inbox.py", payload, {"CLAUDE_PROJECT_DIR": str(checkout)}) == "deny"


def test_guard_checkout_finds_the_shared_checkout_when_the_project_directory_is_a_checkout(tmp_path: Path):
    """Item 7e: without the mapping the hook took the checkout for the repository and a path of the shared checkout
    for one outside it."""
    root = tmp_path / "repo"
    checkout = root / ".claude" / "worktrees" / "r1-plan"
    (root / "packages").mkdir(parents=True)
    (checkout / "packages").mkdir(parents=True)
    (root / "packages" / "x.py").write_text("BASE\n", encoding="utf-8")
    env = {"HARNESS_RUN_DIR": str(tmp_path / "repo-runs" / "r1"), "HARNESS_WORKTREE": "r1-plan",
           "CLAUDE_PROJECT_DIR": str(checkout)}  # fmt: skip
    payload = {"tool_name": "Read", "tool_input": {"file_path": str(root / "packages" / "x.py")}, "cwd": str(checkout),
               "hook_event_name": "PreToolUse"}  # fmt: skip
    assert answer("guard-checkout.py", payload, env) == "deny"


@pytest.mark.parametrize(
    ("command", "where"),
    [("cd ../../..", "checkout"), ("cd ../../../../repo", "stage"), ("cd ..", "root"), ("cd ../../../..", "checkout")],
)
def test_a_lone_cd_into_the_shared_checkout_or_above_it_is_refused(tmp_path: Path, command: str, where: str):
    """04/F3: the target of a `cd` is judged even when no command follows it in the call; a relative target is no
    word the fallback for absolute words looks at."""
    root = tmp_path / "repo"
    checkout = root / ".claude" / "worktrees" / "r1-plan"
    stage = tmp_path / "repo-runs" / "r1" / "stages" / "plan"
    for d in (root / "packages", checkout / "packages", stage):
        d.mkdir(parents=True, exist_ok=True)
    env = {"HARNESS_RUN_DIR": str(stage.parents[1]), "HARNESS_WORKTREE": "r1-plan", "CLAUDE_PROJECT_DIR": str(root)}
    cwd = {"checkout": checkout, "stage": stage, "root": root}[where]
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": str(cwd),
        "hook_event_name": "PreToolUse",
    }
    assert answer("guard-checkout.py", payload, env) == "deny"
