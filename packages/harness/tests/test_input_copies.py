"""Every input copy of a unit is written read-only and indexed with its sha256 under `<run>/_access/`, the change patch
of the work a unit reviews included, on its launch, on a recheck and on a resume (R13 of run
20261009-022929-fix-w1-revise, docs/decisions/0018); materialize_inputs and the functions this run adds keep the
project's rule of functions under 50 lines (R14, .claude/rules/python.md)."""

from __future__ import annotations

import hashlib
import inspect
import json
import stat
import subprocess
from pathlib import Path

import pytest
from harness import access, launch
from harness.gates import _common, read

POLICY = {
    "schema_version": 1,
    "defaults": {
        "dirs": ["stage"], "blind": False, "brief_drop": [], "cache_ttl": "5m", "plugins": [], "mcp_servers": [],
        "pack_files": [], "repo_deny": [], "blind_deny": [],
        "never_copy": ["result.json", "progress.md", "prompt.md", "pack.md", "gate.json", "escalation.json", "logs/**"],
    },
    "types": {
        "writer": {"may_receive": ["brief"], "outputs_of": [], "changes_repository": True},
        "verifier": {"may_receive": ["brief"], "outputs_of": ["writer"], "alias": {"writer": "work"}},
    },
}  # fmt: skip
STAGES = {
    "write": {"id": "write", "role_type": "writer", "inputs": ["brief"]},
    "verify": {"id": "verify", "role_type": "verifier", "inputs": ["brief", "write:output/"]},
}
WRITABLE = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH


def git(cwd: Path, *args: str) -> str:
    argv = ["git", "-c", "user.name=A Writer", "-c", "user.email=writer@example.com", "-c", "commit.gpgsign=false"]
    return subprocess.run([*argv, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture()
def rig(tmp_path: Path, monkeypatch) -> tuple[Path, Path, Path]:
    """A repository with a writer's branch, the writer's result naming it, and a verifier whose agent file lets it
    enter the checkout of the work."""
    for var in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"):
        monkeypatch.delenv(var, raising=False)
    root = tmp_path / "repo"
    (root / ".claude" / "agents").mkdir(parents=True)
    agent = "---\nname: verifier\ntools: Read, Bash, EnterWorktree\n---\n"
    (root / ".claude/agents/verifier.md").write_text(agent, encoding="utf-8")
    (root / "a.txt").write_text("one\n", encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "a.txt")
    git(root, "commit", "-qm", "base")
    git(root, "branch", "worktree-r1-write")
    author(root, "two")
    run = tmp_path / "repo-runs" / "r1"
    (run / "stages/write/output").mkdir(parents=True)
    (run / "stages/write/output/doc.md").write_text("what the writer did\n", encoding="utf-8")
    (run / "stages/write/result.json").write_text(json.dumps({"summary": "Branch worktree-r1-write."}))
    (run / "brief.md").write_text("# Brief\n", encoding="utf-8")
    return root, run, run / "stages" / "verify"


def author(root: Path, text: str) -> None:
    """The writer commits `a.txt` with `text` on its branch."""
    git(root, "checkout", "-q", "worktree-r1-write")
    (root / "a.txt").write_text(text + "\n", encoding="utf-8")
    git(root, "commit", "-qam", f"feat: {text}")
    git(root, "checkout", "-q", "main")


def recorded(run: Path) -> list[dict]:
    return json.loads((run / "_access" / "verify.inputs.json").read_text(encoding="utf-8"))


def held(run: Path, sd: Path, text: str) -> None:
    """The patch holds `text`, is read-only, and the unit's index names it once, with the sha256 of its bytes."""
    patch = sd / "input" / "work" / "changes.patch"
    assert f"+{text}" in patch.read_text(encoding="utf-8")
    assert not patch.stat().st_mode & WRITABLE
    entries = [e for e in recorded(run) if e["as"] == "work/changes.patch"]
    assert len(entries) == 1 and entries[0]["source"].startswith("git diff ")
    assert entries[0]["sha256"] == hashlib.sha256(patch.read_bytes()).hexdigest()
    assert _common.as_copied(sd, entries[0]) == patch.read_bytes()


def test_a_change_patch_is_written_read_only_and_indexed_with_its_sha256(rig):
    root, run, sd = rig
    index = launch.stage_inputs(root, POLICY, STAGES, run, STAGES["verify"], sd, "r1-verify")
    held(run, sd, "two")
    assert index == recorded(run)
    assert not (sd / "input/work/doc.md").stat().st_mode & WRITABLE  # the other copies, as before


def test_a_recheck_writes_the_new_patch_read_only_with_its_new_sha256(rig):
    root, run, sd = rig
    launch.stage_inputs(root, POLICY, STAGES, run, STAGES["verify"], sd, "r1-verify")
    author(root, "three")  # sent back, the writer commits again; the stage after it checks again
    launch.stage_inputs(root, POLICY, STAGES, run, STAGES["verify"], sd, "r1-verify")
    held(run, sd, "three")


def test_a_resume_records_the_patch_it_writes_again(rig):
    root, run, sd = rig
    launch.stage_inputs(root, POLICY, STAGES, run, STAGES["verify"], sd, "r1-verify")
    author(root, "four")  # the work changed while the unit was stopped: a plain resume follows it
    launch.prepare_work(root, POLICY, STAGES, run, STAGES["verify"], sd, "r1-verify")
    held(run, sd, "four")
    assert sorted(e["as"] for e in recorded(run)) == ["brief.md", "work/changes.patch", "work/doc.md"]


FUNCTIONS = [
    (access, "materialize_inputs"), (access, "_fresh"), (access, "_copy_input"), (access, "put_copy"),
    (access, "unit_record"), (access, "write_index"), (access, "settings_closed"), (access, "_settings"),
    (access, "_repo_pattern"), (access, "unreadable"), (launch, "record_work"), (launch, "prepare_work"),
    (launch, "stage_inputs"), (_common, "closed_paths"), (_common, "inside"), (_common, "is_closed"),
    (_common, "_local"), (read, "opened"), (read, "probe_problems"),
]  # fmt: skip


@pytest.mark.parametrize(("module", "name"), FUNCTIONS, ids=[f"{m.__name__}.{n}" for m, n in FUNCTIONS])
def test_the_functions_this_run_writes_stay_under_50_lines(module, name: str):
    """R14: materialize_inputs had 56 lines where the base had 49 (`.claude/rules/python.md`: under 50)."""
    assert len(inspect.getsourcelines(getattr(module, name))[0]) < 50
