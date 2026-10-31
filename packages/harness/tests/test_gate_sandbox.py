"""The write gate runs a branch's suite in a sandbox, without the environment of the process that gates it
(harness/gates/_sandbox.py; 03/F21 of the audit of 2026-10-04, docs/decisions/0017)."""

from __future__ import annotations

import itertools
import subprocess
import sys
from pathlib import Path

import pytest
from harness.gates import _common, _sandbox


def git(root: Path, *args: str) -> None:
    cmd = ["git", "-C", str(root), "-c", "user.email=t@example.com", "-c", "user.name=t", "-c", "commit.gpgsign=false"]
    subprocess.run([*cmd, *args], check=True, capture_output=True)


@pytest.fixture()
def branch(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    """A repository whose branch `work` carries a conftest.py that writes outside the checkout what it finds in the
    environment, and a test that passes only where the gating process's variables are not."""
    root, mark = tmp_path / "repo", tmp_path / "outside" / "mark.txt"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    git(root, "add", "a.txt")
    git(root, "commit", "-qm", "base")
    git(root, "checkout", "-qb", "work")
    (root / "conftest.py").write_text(
        f"import os, pathlib\nmark = pathlib.Path({str(mark)!r})\nmark.parent.mkdir(parents=True, exist_ok=True)\n"
        "mark.write_text(str('GATE_SECRET' in os.environ))\n",
        encoding="utf-8",
    )
    (root / "tests").mkdir()
    (root / "tests" / "test_env.py").write_text(  # a failure shows `assert not True`, never the environment
        "import os\n\n\ndef test_the_gating_environment_is_not_here():\n"
        "    leaked = 'GATE_SECRET' in os.environ\n    assert not leaked\n",
        encoding="utf-8",
    )
    git(root, "add", "conftest.py", "tests/test_env.py")
    git(root, "commit", "-qm", "work")
    git(root, "checkout", "-q", "main")
    monkeypatch.setenv("GATE_SECRET", "a-token-of-the-gating-process")
    monkeypatch.setattr(_common, "TEST_CMD", [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"])
    return root, mark


def test_the_suite_of_a_branch_runs_in_a_sandbox_without_the_gating_environment(branch):
    """03/F21: the branch's conftest.py ran with the gating process's access and variables (`harness poll` runs
    outside Claude Code's sandbox). In the sandbox the suite still runs and passes, sees none of those variables, and
    what it writes outside the checkout stays in the sandbox."""
    root, mark = branch
    why = _sandbox.problem(root, root)
    if why:
        pytest.skip(f"no sandbox on this machine: {why}")
    found = _common.tests_check(root, "work")
    assert found["passed"], found.get("detail")
    assert not mark.exists()


def test_where_no_sandbox_starts_the_suite_is_not_run(branch, monkeypatch):
    """Where no sandbox starts the gate fails with the reason and never runs the suite unsandboxed, as a role session
    never starts without its sandbox (failIfUnavailable)."""
    root, mark = branch
    monkeypatch.setattr(_sandbox.sys, "platform", "linux")
    monkeypatch.setattr(_sandbox.shutil, "which", lambda name: None)
    found = _common.tests_check(root, "work")
    assert not found["passed"] and found["detail"].startswith("not run: bubblewrap (bwrap) is not on PATH")
    monkeypatch.setattr(_sandbox.sys, "platform", "win32")
    assert "no sandbox on this platform (win32)" in _common.tests_check(root, "work")["detail"]
    assert not mark.exists()


def test_on_macos_the_suite_runs_under_seatbelt_with_the_same_limits(tmp_path: Path, monkeypatch):
    """The template promises macOS as well (docs/decisions/0009); no macOS machine was at hand, so the platform is
    stood in for: the command and its profile are what Seatbelt would be given."""
    monkeypatch.setattr(_sandbox.sys, "platform", "darwin")
    tree = tmp_path / "gate" / "tree"
    tree.mkdir(parents=True)
    argv = _sandbox.command(tmp_path, tree, ["uv", "run", "pytest", "-q"], tmp_path / "gate" / "tmp")
    assert argv[:2] == ["sandbox-exec", "-p"] and argv[3:] == ["uv", "run", "pytest", "-q"]
    profile = argv[2]
    assert "(deny network*)" in profile and "(deny file-write*)" in profile
    assert f'(subpath "{tree}")' in profile.split("(allow file-write*", 1)[1].split("\n")[0]
    assert f'(deny file-read* (subpath "{Path.home()}"))' in profile
    monkeypatch.setattr(_sandbox.shutil, "which", lambda name: None)
    assert _sandbox.problem(tmp_path, tree) == "sandbox-exec is not on PATH"


def test_the_sandbox_is_given_a_fixed_environment_and_the_linux_limits(tmp_path: Path, monkeypatch):
    """No variable of the gating process reaches the suite; on Linux the system is read-only, the network and the home
    directory are out of reach, and the checkout is the one place it may write."""
    for name in ("HARNESS_ROLE", "CLAUDE_PROJECT_DIR", "GATE_SECRET", "ANTHROPIC_API_KEY"):
        monkeypatch.setenv(name, "x")
    assert set(_sandbox.environment(tmp_path)) == {"PATH", "HOME", "LANG", "TMPDIR", "NO_COLOR", "UV_OFFLINE"}
    monkeypatch.setattr(_sandbox.sys, "platform", "linux")
    tree = tmp_path / "tree"
    tree.mkdir()
    argv = _sandbox.command(tmp_path, tree, ["true"])
    pairs = list(zip(argv, argv[1:], argv[2:], strict=False))
    assert "--unshare-all" in argv and "--die-with-parent" in argv and ("--ro-bind", "/", "/") in pairs
    assert ("--tmpfs", str(Path.home())) in itertools.pairwise(argv)
    assert ("--bind", str(tree), str(tree)) in pairs
    assert argv[argv.index("--chdir") + 1] == str(tree) and argv[-1] == "true"
