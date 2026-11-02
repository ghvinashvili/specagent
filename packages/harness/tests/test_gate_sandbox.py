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
    (root / "conftest.py").write_text(  # bubblewrap lets the write vanish in a tmpfs; Seatbelt refuses it
        f"import os, pathlib\nmark = pathlib.Path({str(mark)!r})\ntry:\n    mark.parent.mkdir(parents=True, exist_ok=True)\n"
        "    mark.write_text(str('GATE_SECRET' in os.environ))\nexcept OSError:\n    pass\n",
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
    assert f'(deny file-read* (subpath "{Path.home().resolve()}"))' in profile
    monkeypatch.setattr(_sandbox.shutil, "which", lambda name: None)
    assert _sandbox.problem(tmp_path, tree) == "sandbox-exec is not on PATH"


def test_on_macos_the_folders_above_what_is_opened_show_their_metadata_alone(tmp_path: Path, monkeypatch):
    """The macOS runner: the venv's python resolves its own folder, and Seatbelt refused the `realpath` of the folders
    above it in the home directory (`python: realpath: …/.venv/bin/: Operation not permitted`). The folders above
    every opened path show their metadata, not their content; the interpreter the venv was made from is opened; every
    path stands as given and as the kernel resolves it (`/var` is `/private/var` on macOS)."""
    monkeypatch.setattr(_sandbox.sys, "platform", "darwin")
    real = tmp_path / "real"
    (real / "gate" / "tree").mkdir(parents=True)
    (tmp_path / "link").symlink_to(real)
    tree = tmp_path / "link" / "gate" / "tree"
    profile = _sandbox.command(tmp_path, tree, ["true"], tmp_path / "link" / "gate" / "tmp")[2]
    lines = profile.splitlines()
    metadata = next(line for line in lines if line.startswith("(allow file-read-metadata "))
    assert lines.index(metadata) > lines.index(next(line for line in lines if line.startswith("(deny file-read* ")))
    for folder in (real / "gate", real, tmp_path, Path("/")):
        assert f'(literal "{folder.resolve()}")' in metadata
    assert f'(subpath "{real / "gate" / "tree"}")' in profile and f'(subpath "{tree}")' in profile
    opened = next(line for line in lines if line.startswith("(allow file-read* "))
    assert f'(subpath "{Path(sys.prefix).resolve()}")' in opened
    for part in ("bin", "lib"):  # of the installation the venv was made from, its bin and lib
        assert f'(subpath "{(Path(sys.base_prefix) / part).resolve()}")' in opened
    assert "(subpath" not in metadata


def uv_layout(base: Path, venv: Path) -> Path:
    """uv's python under base (`cpython-3.12` a link to the release) and a venv made from it; the minor folder."""
    release = base / "cpython-3.12.12"
    (release / "bin").mkdir(parents=True)
    (release / "lib" / "python3.12").mkdir(parents=True)
    (release / "bin" / "python3.12").write_text("", encoding="utf-8")
    (base / "cpython-3.12").symlink_to(release)
    minor = base / "cpython-3.12"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").symlink_to(minor / "bin" / "python3.12")
    (venv / "pyvenv.cfg").write_text(f"home = {minor / 'bin'}\nversion_info = 3.12.12\n", encoding="utf-8")
    return minor


def as_python(monkeypatch, venv: Path, base_prefix: Path, name: str = "python") -> None:
    monkeypatch.setattr(_sandbox.sys, "executable", str(venv / "bin" / name))
    monkeypatch.setattr(_sandbox.sys, "prefix", str(venv))
    monkeypatch.setattr(_sandbox.sys, "base_prefix", str(base_prefix))


def test_the_interpreter_a_uv_venv_names_is_opened_with_the_links_to_it(tmp_path: Path, monkeypatch):
    """The WSL2 workflow: the venv's python links to uv's `cpython-3.12-…` folder, a link to the patch release, and
    pyvenv.cfg names that folder as python's home; bubblewrap, given the release alone, found no python."""
    venv = tmp_path / "proj" / ".venv"
    minor = uv_layout(tmp_path / "uv", venv)
    as_python(monkeypatch, venv, (minor / "bin").resolve().parent)
    paths = _sandbox.interpreter_paths()
    release = tmp_path / "uv" / "cpython-3.12.12"
    assert {venv, venv / "bin", minor / "bin", minor / "lib", release / "bin", release / "lib"} <= set(paths)
    assert minor not in paths and release not in paths  # an installation's bin and lib, not the whole of it
    read, _ = _sandbox.toolchain(tmp_path)
    assert minor / "bin" in read and minor / "lib" in read and venv / "bin" in read
    (venv / "bin" / "python3").symlink_to("python")  # a relative link is read from its own folder
    as_python(monkeypatch, venv, (minor / "bin").resolve().parent, "python3")
    assert minor / "bin" in _sandbox.interpreter_paths()


def test_a_linked_folder_on_the_way_to_python_is_not_opened_whole(tmp_path: Path, monkeypatch):
    """V2 of the macos-windows run: `~/code` linked to a Windows folder (`/mnt/c/Users/me/code`) lies on the way to a
    venv in it; the link was opened whole, and a sandboxed `cat` read another project's file. Only the venv is."""
    windows = tmp_path / "mnt" / "c" / "Users" / "me"
    (windows / "code" / "other").mkdir(parents=True)
    home = tmp_path / "home" / "me"
    home.mkdir(parents=True)
    (home / "code").symlink_to(windows / "code")
    monkeypatch.setattr(_sandbox.Path, "home", classmethod(lambda cls: home))
    venv = home / "code" / "proj" / ".venv"
    minor = uv_layout(tmp_path / "uv", venv)
    as_python(monkeypatch, venv, (minor / "bin").resolve().parent)
    paths = _sandbox.interpreter_paths()
    assert home / "code" not in paths and windows / "code" not in paths
    assert not any(p in (home / "code", windows / "code") or p in (home / "code").parents for p in paths)
    assert venv in paths and venv / "bin" in paths


def test_an_interpreter_in_the_home_directory_itself_is_never_opened(tmp_path: Path, monkeypatch):
    """V3 of the macos-windows run: a python installed with the prefix $HOME has the home directory as its base prefix
    and its venv's home; opening it showed `~/.ssh` to the suite. It is left out, by any of its names."""
    real = tmp_path / "real-home"
    (real / "bin").mkdir(parents=True)
    (real / "lib" / "python3.12").mkdir(parents=True)  # a python installation, so only _hides() keeps it shut (V6)
    (real / "bin" / "python3.12").write_text("", encoding="utf-8")
    (tmp_path / "home").symlink_to(real)
    monkeypatch.setattr(_sandbox.Path, "home", classmethod(lambda cls: tmp_path / "home"))
    venv = tmp_path / "opt" / "proj" / ".venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").symlink_to(real / "bin" / "python3.12")
    (venv / "pyvenv.cfg").write_text(f"home = {real / 'bin'}\n", encoding="utf-8")
    as_python(monkeypatch, venv, real)
    paths = _sandbox.interpreter_paths()
    assert real not in paths and tmp_path / "home" not in paths and real / "bin" not in paths
    assert real / "lib" not in paths and paths == [venv, venv / "bin"]
    monkeypatch.setattr(_sandbox, "HIDDEN", (str(venv),))
    assert _sandbox.interpreter_paths() == []  # a hidden folder itself is not opened either


def test_a_link_through_a_folder_of_the_user_opens_nothing_of_it(tmp_path: Path, monkeypatch):
    """V2's second case: the venv's python links to `~/bin/python3`, a link to the system's python; `~/bin` holds the
    user's own scripts and is a step on the way, not part of the interpreter, so it stays shut."""
    system = tmp_path / "usr"
    (system / "bin").mkdir(parents=True)
    (system / "lib" / "python3.12").mkdir(parents=True)
    (system / "bin" / "python3.12").write_text("", encoding="utf-8")
    home = tmp_path / "home" / "me"
    (home / "bin").mkdir(parents=True)
    (home / "bin" / "python3").symlink_to(system / "bin" / "python3.12")
    monkeypatch.setattr(_sandbox.Path, "home", classmethod(lambda cls: home))
    venv = tmp_path / "proj" / ".venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").symlink_to(home / "bin" / "python3")
    (venv / "pyvenv.cfg").write_text(f"home = {system / 'bin'}\n", encoding="utf-8")
    as_python(monkeypatch, venv, system)
    paths = _sandbox.interpreter_paths()
    assert home / "bin" not in paths and paths == [venv, system / "bin", system / "lib", venv / "bin"]


def test_a_folder_pyvenv_cfg_names_is_opened_only_when_it_holds_a_python(tmp_path: Path, monkeypatch):
    """A venv whose pyvenv.cfg names `~/code/bin` as python's home would open `~/code`, every project in it, as the
    interpreter's folder; a folder is opened whole only when it is a venv or holds `lib/python3.*` and a python."""
    home = tmp_path / "home" / "me"
    code = home / "code"
    (code / "bin").mkdir(parents=True)
    (code / "bin" / "python3.12").write_text("", encoding="utf-8")
    (code / "other").mkdir()
    monkeypatch.setattr(_sandbox.Path, "home", classmethod(lambda cls: home))
    venv = tmp_path / "proj" / ".venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").symlink_to(code / "bin" / "python3.12")
    (venv / "pyvenv.cfg").write_text(f"home = {code / 'bin'}\n", encoding="utf-8")
    as_python(monkeypatch, venv, code)
    paths = _sandbox.interpreter_paths()
    assert code not in paths and code / "bin" not in paths and paths == [venv, venv / "bin"]
    (code / "lib" / "python3.12").mkdir(parents=True)  # a python installed with the prefix ~/code: its bin and lib
    assert _sandbox.interpreter_paths() == [venv, code / "bin", code / "lib", venv / "bin"]


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


def test_of_a_python_installed_in_dot_local_only_its_bin_and_lib_are_opened(tmp_path: Path, monkeypatch):
    """V5 of the macos-windows run: a python built with `--prefix=$HOME/.local` is the base prefix and pyvenv.cfg's
    home of a venv made from it; `~/.local` was opened whole, and a sandboxed `cat` read `~/.local/share/keyrings`."""
    home = tmp_path / "home" / "me"
    local = home / ".local"
    for folder in (local / "bin", local / "lib" / "python3.12", local / "share" / "keyrings", local / "state"):
        folder.mkdir(parents=True)
    (local / "bin" / "python3.12").write_text("", encoding="utf-8")
    (local / "share" / "keyrings" / "login.keyring").write_text("a keyring\n", encoding="utf-8")
    monkeypatch.setattr(_sandbox.Path, "home", classmethod(lambda cls: home))
    venv = tmp_path / "opt" / "proj" / ".venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").symlink_to(local / "bin" / "python3.12")
    (venv / "pyvenv.cfg").write_text(f"home = {local / 'bin'}\n", encoding="utf-8")
    as_python(monkeypatch, venv, local)
    read, _ = _sandbox.toolchain(tmp_path)
    assert local / "bin" in read and local / "lib" in read
    assert not any(p in (local, local / "share", local / "state") or local / "share" in p.parents for p in read)
    assert _sandbox.interpreter_paths() == [venv, local / "bin", local / "lib", venv / "bin"]
