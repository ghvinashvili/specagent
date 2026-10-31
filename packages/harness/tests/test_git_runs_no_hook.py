"""No git command the harness runs fires a hook, neither the trunk's nor one that a role's branch brings (R4;
docs/decisions/0029-a-checkout-sets-up-its-hooks-sandbox-and-graph.md)."""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

import pytest
from harness import access, work
from harness.gates import _common, _sandbox

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "packages" / "harness" / "src"
QUIET = ("git", "-c", "core.hooksPath=/dev/null")  # this file's own git fires no hook either
BRANCH = "worktree-r1-write-01"
HOOKS = ("post-checkout", "reference-transaction", "post-index-change")
STAGES = [
    {"id": "read", "role_type": "reader", "inputs": ["brief"]},
    {"id": "write", "role_type": "writer", "inputs": ["brief", "read:output/notes.md"]},
    {"id": "verify", "role_type": "verifier", "inputs": ["brief", "write:output/", "write:tasks.json"]},
    {"id": "accept", "role_type": "test-verifier", "inputs": ["brief", "write:output/"]},
]
BY_ID = {s["id"]: s for s in STAGES}


def git(cwd: Path, *args: str) -> str:
    return subprocess.run([*QUIET, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def executable(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o755)


def ran(tmp_path: Path) -> list[str]:
    return sorted(p.name for p in (tmp_path / "ran").iterdir())


@pytest.fixture
def hooked(tmp_path: Path, monkeypatch):
    """A trunk whose post-checkout runs the checked-out tree's ops/graph.sh, as .githooks/post-checkout does; a
    writer's branch that brings its own graph.sh and three hooks, each leaving a file in tmp_path/ran; then hooks on."""
    for var in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"):
        monkeypatch.delenv(var, raising=False)
    root, marks = tmp_path / "repo", tmp_path / "ran"
    root.mkdir()
    marks.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.name", "A Writer")
    git(root, "config", "user.email", "writer@example.com")
    git(root, "config", "commit.gpgsign", "false")
    (root / "a.txt").write_text("one\n")
    (root / "b.txt").write_text("one\n")
    executable(root / ".githooks" / "post-checkout", "#!/usr/bin/env bash\nbash ops/graph.sh --quick || true\n")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "base")
    git(root, "checkout", "-q", "-b", BRANCH, "main")
    executable(root / "ops" / "graph.sh", f"touch {marks / 'ran-graph'}\n")
    for name in HOOKS:
        executable(root / ".githooks" / name, f"#!/usr/bin/env bash\ntouch {marks / ('ran-' + name)}\n")
    (root / "a.txt").write_text("two\n")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "feat: change a.txt\n\nCo-Authored-By: Claude <noreply@anthropic.com>")
    git(root, "checkout", "-q", "main")
    run_dir = tmp_path / "repo-runs" / "r1"
    unit = run_dir / "stages" / "write" / "01"
    unit.mkdir(parents=True)
    result = {"summary": f"Branch {BRANCH}, one commit.", "outputs": [{"path": "a.txt", "kind": "code"}]}
    (unit / "result.json").write_text(json.dumps(result))
    git(root, "config", "core.hooksPath", ".githooks")
    return root, run_dir


def test_the_harness_git_prefix_turns_hooks_off():
    from harness.gitcall import GIT

    assert GIT == ("git", "-c", "core.hooksPath=/dev/null")


def test_no_git_argv_under_src_starts_without_the_prefix():
    bare = []
    for path in sorted(SRC.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            first = node.elts[0] if isinstance(node, ast.List) and node.elts else None
            if isinstance(first, ast.Constant) and first.value == "git":
                bare.append(f"{path.relative_to(SRC)}:{node.lineno}")
    assert bare == []


def test_a_gate_reads_a_branch_in_a_temporary_tree_and_no_hook_runs(hooked, tmp_path: Path):
    root, _ = hooked
    assert _common.on_branch(root, BRANCH, lambda tree: tree.is_dir()) == (True, "")
    assert ran(tmp_path) == []
    # the same checkout without the prefix runs the branch's own graph.sh: the hooks of the fixture are live
    plain = ["git", "-C", str(root), "worktree", "add", "-q", "--detach", str(tmp_path / "plain"), BRANCH]
    subprocess.run(plain, check=True, capture_output=True)
    assert "ran-graph" in ran(tmp_path)


def test_a_stage_checkout_and_its_follow_up_run_no_hook(hooked, tmp_path: Path):
    root, run_dir = hooked
    stage_dir, policy = run_dir / "stages" / "verify", access.load_policy(REPO)
    first = work.prepare(root, policy, BY_ID, run_dir, BY_ID["verify"], stage_dir, "r1-verify")
    assert Path(first["path"]).is_dir() and ran(tmp_path) == []
    git(root, "checkout", "-q", BRANCH)
    (root / "b.txt").write_text("two\n")
    git(root, "commit", "-q", "-am", "feat: change b.txt\n\nCo-Authored-By: Claude <noreply@anthropic.com>")
    git(root, "checkout", "-q", "main")
    again = work.prepare(root, policy, BY_ID, run_dir, BY_ID["verify"], stage_dir, "r1-verify")
    assert again["commit"] != first["commit"] and ran(tmp_path) == []


def test_the_sandbox_finds_the_main_git_dir_from_a_linked_worktree(hooked, tmp_path: Path):
    root, _ = hooked
    git(root, "worktree", "add", "-q", "--detach", str(tmp_path / "linked"), BRANCH)
    assert _sandbox.git_dir(tmp_path / "linked").resolve() == (root / ".git").resolve()
