"""Attack tests for the guards of run 20261009-022929-fix-w1-revise (R1, R5; plan D4, D12). Each asserts a promise
the plan makes, by the names the plan gives (shellwords.tokens/simple_commands, guard-bash.py, guard-checkout.py).
New file, self-contained: it copies the branch's own .claude/hooks into a tmp_path box (REPO = parents[3]) and runs
the hooks there; it reads no path outside the branch, no evals/baseline, no runs root and no network host. A writer
may not change this file."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOKS = REPO / ".claude" / "hooks"


def load_shellwords():
    spec = importlib.util.spec_from_file_location("shellwords_attack", HOOKS / "shellwords.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_command_reader_takes_a_hash_inside_a_word_as_part_of_the_word():
    """D4/R1: shellwords reads `#` inside a word as a word character (bash only starts a comment at the start of a
    word), so a command after `a#b;` is still seen; the words of a real comment are read as words (never fewer)."""
    sw = load_shellwords()
    assert sw.simple_commands("echo a#b; git add -A") == [["echo", "a#b"], ["git", "add", "-A"]]
    assert sw.tokens("ls  # a comment") == ["ls", "#", "a", "comment"]
    assert sw.simple_commands("git status  # then git add -A") == [["git", "status", "#", "then", "git", "add", "-A"]]
    # a `#` inside quotes stays literal and does not break the reader
    assert sw.tokens("echo 'a # b'") == ["echo", "a # b"]


@pytest.fixture()
def box(tmp_path: Path) -> dict:
    root = tmp_path / "repo"
    checkout = root / ".claude/worktrees/r1-plan"
    run = tmp_path / "repo-runs/20261009-000000-r1"
    stage = run / "stages/plan"
    inbox = tmp_path / "repo-runs/_inbox/upload"
    for d in (root / "packages", checkout / "packages", stage, inbox, root / ".claude/hooks"):
        d.mkdir(parents=True, exist_ok=True)
    (root / "packages/x.py").write_text("BASE\n", encoding="utf-8")
    (checkout / "packages/x.py").write_text("WORK\n", encoding="utf-8")
    (inbox / "note.txt").write_text("UNTRUSTED\n", encoding="utf-8")
    for name in ("guard-bash.py", "guard-checkout.py", "shellwords.py", "guard-bash.json"):
        shutil.copy(HOOKS / name, root / ".claude/hooks" / name)
    shutil.copy(REPO / ".claude/settings.json", root / ".claude/settings.json")
    role = {"HARNESS_RUN_DIR": str(run), "HARNESS_STAGE": "plan", "HARNESS_WORKTREE": "r1-plan",
            "CLAUDE_PROJECT_DIR": str(root), "HOME": str(tmp_path)}  # fmt: skip
    return {"root": root, "checkout": checkout, "stage": stage, "inbox": inbox, "role": role}


def decide(box: dict, hook: str, tool: str, tool_input: dict, cwd: Path) -> str:
    payload = {"tool_name": tool, "tool_input": tool_input, "cwd": str(cwd), "hook_event_name": "PreToolUse"}
    res = subprocess.run(
        [sys.executable, str(box["root"] / ".claude/hooks" / hook)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": "/usr/bin:/bin", **box["role"]},
    )
    if res.returncode:
        return f"exit {res.returncode}"
    return json.loads(res.stdout)["hookSpecificOutput"]["permissionDecision"] if res.stdout.strip() else "allow"


def test_guard_bash_denies_a_whole_tree_add_after_a_hash_inside_a_word(box):
    """R1: `echo a#b; git add -A` — the command after the `#` is a whole-tree add; guard-bash must deny it."""
    assert decide(box, "guard-bash.py", "Bash", {"command": "echo a#b; git add -A"}, box["checkout"]) == "deny"


def test_guard_checkout_reads_a_path_after_a_hash_inside_a_word(box):
    """R1: `cat x#; cat <shared>/packages/x.py` — guard-checkout must see the read of the shared checkout after the
    `#` and deny it, by a relative and by an absolute spelling."""
    rel = decide(box, "guard-checkout.py", "Bash", {"command": "cat x#; cat ../../../packages/x.py"}, box["checkout"])
    ab = decide(
        box, "guard-checkout.py", "Bash", {"command": f"cat x#; cat {box['root']}/packages/x.py"}, box["checkout"]
    )
    assert rel == "deny" and ab == "deny"


@pytest.mark.parametrize(
    ("pattern", "expect"),
    [
        ("../../../packages/*.py", "deny"),
        ("../../../packages/x.py", "deny"),
        ("../../../{packages,other}/*.py", "deny"),
        ("../../../packages/?.py", "deny"),
        ("packages/*.py", "allow"),
        ("**/*.py", "allow"),
    ],
)
def test_guard_checkout_refuses_a_glob_that_climbs_into_the_shared_checkout(box, pattern, expect):
    """D12/R5: guard-checkout resolves the folder a Glob names before its first wildcard and refuses one that climbs
    into the shared checkout, whatever wildcard it uses; a pattern that stays in the session's own checkout passes."""
    assert decide(box, "guard-checkout.py", "Glob", {"pattern": pattern}, box["checkout"]) == expect
