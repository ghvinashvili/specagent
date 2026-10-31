"""The guards refuse the plain spellings of what a role session may not do (docs/decisions/0025): a command that
stands after a `#` inside a word is read (R1 of run 20261009-022929-fix-w1-revise), and a Glob whose relative pattern
climbs into the shared checkout is refused (R5). What a command builds at run time is held by the sandbox and the
write gate instead (test_boundary_settings.py, test_closed_paths.py)."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[3] / ".claude" / "hooks"


def decide(name: str, payload: dict, env: dict) -> str:
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


@pytest.fixture()
def box(tmp_path: Path) -> dict:
    """A shared checkout `repo` with the session's checkout in it, and beside it the runs root with the session's run,
    its stage directory and the inbox."""
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
    shutil.copy(HOOKS / "guard-bash.json", root / ".claude/hooks/guard-bash.json")
    shutil.copy(HOOKS.parent / "settings.json", root / ".claude/settings.json")
    role = {"HARNESS_RUN_DIR": str(run), "HARNESS_STAGE": "plan", "HARNESS_WORKTREE": "r1-plan",
            "CLAUDE_PROJECT_DIR": str(root), "HOME": str(tmp_path)}  # fmt: skip
    manager = {"CLAUDE_PROJECT_DIR": str(root), "HOME": str(tmp_path)}
    return {"root": root, "checkout": checkout, "stage": stage, "inbox": inbox, "role": role, "manager": manager}


def fill(box: dict, text: str) -> str:
    for key in ("root", "checkout", "stage", "inbox"):
        text = text.replace("{" + key.upper() + "}", str(box[key]))
    return text


HASH_CASES = [
    ("guard-bash.py", "role", "echo a#b; git add -A", "{CHECKOUT}"),
    ("guard-checkout.py", "role", "cat x#; cat ../../../packages/x.py", "{CHECKOUT}"),
    ("guard-checkout.py", "role", "cat x#; cat {ROOT}/packages/x.py", "{CHECKOUT}"),
    ("guard-bash.py", "manager", "echo x#; cat {INBOX}/note.txt", "{ROOT}"),
    ("guard-bash.py", "role", "echo x#; echo '{}' > result.json", "{STAGE}"),
]


@pytest.mark.parametrize(
    ("hook", "who", "command", "cwd"),
    HASH_CASES,
    ids=["whole-tree-add", "relative-read", "absolute-read", "inbox-read", "run-file-write"],
)
def test_a_command_after_a_hash_inside_a_word_is_read_by_the_guards(box, hook, who, command, cwd):
    """R1: the command reader took the rest of a line after a `#` inside a word for a comment, while bash starts a
    comment only at the start of a word and runs what follows the `;`."""
    payload = {"tool_name": "Bash", "tool_input": {"command": fill(box, command)}, "cwd": fill(box, cwd),
               "hook_event_name": "PreToolUse"}  # fmt: skip
    assert decide(hook, payload, box[who]) == "deny"


def shellwords():
    spec = importlib.util.spec_from_file_location("shellwords", HOOKS / "shellwords.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_command_reader_takes_a_hash_inside_a_word_as_part_of_the_word():
    """R1: `#` is a word character to the reader; the words of a real comment are read as words, which can only make a
    guard refuse more."""
    reader = shellwords()
    assert reader.simple_commands("echo a#b; git add -A") == [["echo", "a#b"], ["git", "add", "-A"]]
    assert reader.tokens("ls  # a comment") == ["ls", "#", "a", "comment"]
    assert reader.simple_commands("git status  # then git add -A") == [
        ["git", "status", "#", "then", "git", "add", "-A"]
    ]


@pytest.mark.parametrize(
    ("pattern", "cwd", "expect"),
    [
        ("../../../packages/*.py", "{CHECKOUT}", "deny"),
        ("../../../packages/x.py", "{CHECKOUT}", "deny"),
        ("../../../{packages,other}/*.py", "{CHECKOUT}", "deny"),
        ("../../../../repo/packages/*.py", "{STAGE}", "deny"),
        ("packages/*.py", "{CHECKOUT}", "allow"),
        ("**/*.py", "{CHECKOUT}", "allow"),
        ("*.md", "{STAGE}", "allow"),
    ],
)
def test_a_glob_whose_relative_pattern_climbs_into_the_shared_checkout_is_refused(box, pattern, cwd, expect):
    """R5: guard-checkout resolved only an absolute pattern, so `../../../packages/*.py` with no path passed. The folder
    a pattern names before its first wildcard is now resolved from the search root, as an absolute pattern's is."""
    payload = {"tool_name": "Glob", "tool_input": {"pattern": pattern}, "cwd": fill(box, cwd),
               "hook_event_name": "PreToolUse"}  # fmt: skip
    assert decide("guard-checkout.py", payload, box["role"]) == expect
