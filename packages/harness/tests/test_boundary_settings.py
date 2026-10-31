"""The settings the launcher builds hold what the guards do not read (docs/decisions/0025): a role session's shell
reads nothing outside its working directories, which are never the repository, the run root or the inbox, so after
EnterWorktree the shared checkout is hidden from it whatever a command builds at run time (R1, R2, R4 of run
20261009-022929-fix-w1-revise); and it writes none of its stage's run files, its inputs or the run's escalations (R1,
R4). Each test passes on the work and fails on a copy of access.py with its layer taken out (output/trial/mutants.py
of the plan stage); that Claude Code applies them is the live check of the plan."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from harness import access

REPO = Path(__file__).resolve().parents[3]
DEFAULTS = {
    "dirs": ["stage", "escalations"], "blind": False, "brief_drop": [], "cache_ttl": "5m", "plugins": [],
    "mcp_servers": [], "pack_files": [], "repo_deny": ["docs/handoff/**"], "blind_deny": [".claude/agents/**"],
    "home_deny": ["~/.claude/projects/**"], "user_instructions": [], "project_plugins": [],
    "never_copy": ["result.json", "progress.md", "prompt.md", "pack.md", "gate.json", "escalation.json", "logs/**"],
}  # fmt: skip
TYPES = {
    "planner": {"may_receive": ["brief"], "outputs_of": [], "trial_checkout": True},
    "writer": {"may_receive": ["brief"], "outputs_of": ["planner"], "changes_repository": True},
    "verifier": {"may_receive": ["brief"], "outputs_of": ["writer"], "blind": True, "dirs": ["stage"]},
    "reader": {"may_receive": ["brief"], "outputs_of": []},
    "quarantine-reader": {"may_receive": ["brief"], "outputs_of": [], "dirs": ["stage", "inbox"], "repo_deny_extra": ["**"]},
}  # fmt: skip
POLICY = {"schema_version": 1, "defaults": DEFAULTS, "types": TYPES}
WITH_A_CHECKOUT = {"planner": "r1-plan", "writer": "r1-write", "verifier": "r1-verify"}


@pytest.fixture()
def rig(tmp_path: Path) -> dict:
    """A main checkout with the project's settings and checkouts under it, and a run in the runs root beside it."""
    root = tmp_path / "repo"
    for rel in ("packages/x.py", "CLAUDE.md", ".claude/hooks/guard.py", ".claude/worktrees/r1-plan/packages/x.py",
                ".claude/worktrees/r1-write/packages/x.py", ".claude/worktrees/r1-verify/packages/x.py"):  # fmt: skip
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("x\n", encoding="utf-8")
    shutil.copy(REPO / ".claude" / "settings.json", root / ".claude" / "settings.json")
    (root / ".claude" / "agents").mkdir()
    for name in TYPES:
        (root / ".claude" / "agents" / f"{name}.md").write_text(f"---\nname: {name}\n---\n# {name}\n", encoding="utf-8")
    run = tmp_path / "repo-runs" / "20261009-000000-r1"
    for sid in TYPES:
        (run / "stages" / sid).mkdir(parents=True)
    (run / "brief.md").write_text("# Brief\n", encoding="utf-8")
    (run / "manifest.json").write_text(json.dumps({"stages": [{"id": t} for t in TYPES]}), encoding="utf-8")
    return {"root": root, "run": run, "runs": run.parent}


def settings(rig: dict, role_type: str) -> tuple[dict, list[str], Path]:
    row = {"id": role_type, "role_type": role_type, "inputs": ["brief"]}
    stage = rig["run"] / "stages" / role_type
    built = access.stage_settings(POLICY, rig["run"], row, stage, rig["root"], WITH_A_CHECKOUT.get(role_type))
    return built, access.working_dirs(POLICY, rig["run"], row, stage), stage


@pytest.mark.parametrize("role_type", sorted(TYPES))
def test_a_role_session_reads_nothing_outside_its_working_directories(rig: dict, role_type: str):
    """The read block (`blockReadsOutsideWorkingDirectories`) hides from a sandboxed command every path outside the
    session's working directories: measured in the plan stage, after EnterWorktree a read of the main checkout, of the
    runs root and of the inbox finds nothing. None of its working directories is the repository or a folder in it,
    the runs root, the run directory or the inbox, but the quarantine reader's inbox."""
    built, dirs, stage = settings(rig, role_type)
    assert built["permissions"]["blockReadsOutsideWorkingDirectories"] is True
    root, run, runs = rig["root"].resolve(), rig["run"].resolve(), rig["runs"].resolve()
    for d in (Path(p).resolve() for p in dirs):
        assert d != root and root not in d.parents, d
        assert d not in (runs, run), d
        assert d != runs / "_inbox" or role_type == "quarantine-reader", d
    assert stage.resolve() in [Path(p).resolve() for p in dirs]


@pytest.mark.parametrize("role_type", sorted(TYPES))
def test_a_role_session_s_shell_writes_none_of_its_run_files_its_inputs_or_the_escalations(rig: dict, role_type: str):
    """R4: a shell write of result.json by a subshell, a glob, a variable or `python3 -c` was refused in the plan
    stage's sandbox ("Permission denied", "Read-only file system"): `sandbox.filesystem.denyWrite` names every run file
    of the stage, its input/ and, for a type that keeps them, the run's escalations; the file tools are held by `Edit`
    deny rules for what the harness writes."""
    built, dirs, stage = settings(rig, role_type)
    no_write = set(built["sandbox"]["filesystem"]["denyWrite"])
    for name in ("input", "result.json", "tasks.json", "escalation.json", "gate.json", "checks.json"):
        assert str(stage / name) in no_write, name
    if str(rig["run"] / "escalations") in dirs:
        assert str(rig["run"] / "escalations") in no_write
    deny = built["permissions"]["deny"]
    for rule in (f"Edit({access._abs(stage / 'input')}/**)", f"Edit({access._abs(stage / 'gate.json')})",
                 f"Edit({access._abs(stage / 'checks.json')})"):  # fmt: skip
        assert rule in deny, rule


@pytest.mark.parametrize("role_type", ["planner", "writer", "verifier"])
def test_a_role_session_with_a_checkout_writes_no_other_part_of_the_repository(rig: dict, role_type: str):
    """What the shell may write in the repository is its own checkout only: every other entry of the main checkout and
    of `.claude/worktrees/` is in denyWrite, and no write path of the project's settings inside the repository is
    repeated (`./.claude/worktrees` would open every unit's checkout)."""
    built, _, _ = settings(rig, role_type)
    root = rig["root"].resolve()
    no_write = set(built["sandbox"]["filesystem"]["denyWrite"])
    others = [c for c in WITH_A_CHECKOUT.values() if c != WITH_A_CHECKOUT[role_type]]
    for path in (root / "packages", root / "CLAUDE.md", *(root / ".claude/worktrees" / c for c in others)):
        assert str(path) in no_write, path
    allowed = built["sandbox"]["filesystem"].get("allowWrite", [])
    assert not [w for w in allowed if w == str(root) or w.startswith(str(root) + "/")]
