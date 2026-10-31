"""harness/gates/_sandbox.py — run a command of a branch in a sandbox, without the environment of the process that
gates it (docs/decisions/0017-the-write-gate-runs-a-branch-s-tests-in-a-sandbox.md).

The write gate runs the suite a writer committed, its conftest.py included, inside `harness poll`, which the manager
starts outside Claude Code's sandbox. Here that code runs where a role session's own commands run: the system
read-only, no network, no home directory but the toolchain paths of docs/roles/need-to-know.yaml and the git
configuration, the repository's `.git` read-only, a private /tmp, and the branch's checkout, which it may write; the
environment is a fixed one, not the gating process's. On Linux and WSL2 bubblewrap makes it (the copy that
`ops/machine-setup.py` provides where the system's is held back), on macOS Seatbelt (`sandbox-exec`), as Claude Code's
own sandbox does. Where no sandbox starts the command is not run: `problem` says why, and the check fails with it.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from ..gitcall import GIT

# Folders a role session's sandbox hides, and the ones that hold other processes' sockets and files.
HIDDEN = ("/home", "/root", "/mnt", "/media", "/srv", "/run", "/tmp", "/var/tmp")
GIT_CONFIG = ("~/.gitconfig", "~/.config/git/config", "~/.config/git/ignore", "~/.config/git/attributes")
SYSTEM_PATH = ("/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin")


def toolchain(root: Path) -> tuple[list[Path], list[Path]]:
    """(read-only, writable) paths of the toolchain a role session's sandbox re-opens, as need-to-know.yaml lists
    them, with the git configuration and the gating interpreter's environment (read-only); those that exist."""
    from .. import access  # access imports the gates' helpers lazily; this module is imported by _common

    try:
        paths = access.load_policy(root)["defaults"].get("toolchain") or {}
    except (OSError, access.AccessError):
        paths = {}
    read = [Path(p).expanduser() for p in [*paths.get("read", []), *GIT_CONFIG]] + [Path(sys.prefix)]
    write = [Path(p).expanduser() for p in paths.get("write", [])]
    return [p for p in read if p.exists() and p not in write], [p for p in write if p.exists()]


def environment(root: Path, tmp: str = "/tmp") -> dict[str, str]:
    """The whole environment of the sandboxed command: no variable of the gating process is passed on."""
    read, _ = toolchain(root)
    bins = [str(p) for p in read if p.name == "bin" and p.is_dir()]
    return {
        "PATH": ":".join(dict.fromkeys([*bins, *SYSTEM_PATH])),
        "HOME": str(Path.home()),
        "LANG": "C.UTF-8",
        "TMPDIR": tmp,
        "NO_COLOR": "1",
        "UV_OFFLINE": "1",  # no network: uv takes what its cache holds and says at once what it lacks
    }


def git_dir(tree: Path) -> Path | None:
    """The repository's `.git` that the checkout `tree` belongs to."""
    done = subprocess.run(
        [*GIT, "-C", str(tree), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True,
        text=True,
        check=False,
    )
    return Path(done.stdout.strip()) if done.returncode == 0 and done.stdout.strip() else None


def _bwrap(bwrap: str, root: Path, tree: Path, argv: list[str]) -> list[str]:
    read, write = toolchain(root)
    cmd = [bwrap, "--die-with-parent", "--new-session", "--unshare-all", "--ro-bind", "/", "/"]
    cmd += ["--dev", "/dev", "--proc", "/proc"]
    for hidden in [*HIDDEN, str(Path.home())]:
        if Path(hidden).is_dir():
            cmd += ["--tmpfs", hidden]
    for p in read:
        cmd += ["--ro-bind", str(p), str(p)]
    for p in write:
        cmd += ["--bind", str(p), str(p)]
    gd = git_dir(tree)
    if gd:
        cmd += ["--ro-bind", str(gd), str(gd)]
    return [*cmd, "--bind", str(tree), str(tree), "--chdir", str(tree), *argv]


def _quote(path: Path) -> str:
    return '"' + str(path).replace("\\", "\\\\").replace('"', '\\"') + '"'


def profile(root: Path, tree: Path, tmp: Path) -> str:
    """The Seatbelt profile of macOS: no network, no write but the checkout, the private temporary folder and the
    writable toolchain paths, no read of the home directory but the toolchain, the git configuration and `.git`."""
    read, write = toolchain(root)
    gd = git_dir(tree)
    opened = " ".join(f"(subpath {_quote(p)})" for p in [*read, *write, *([gd] if gd else []), tree, tmp])
    writable = " ".join(f"(subpath {_quote(p)})" for p in [*write, tree, tmp])
    return "\n".join(
        [
            "(version 1)",
            "(allow default)",
            "(deny network*)",
            "(deny file-write*)",
            f'(allow file-write* {writable} (literal "/dev/null") (regex #"^/dev/(tty|fd/)"))',
            f"(deny file-read* (subpath {_quote(Path.home())}))",
            f"(allow file-read* {opened})",
        ]
    )


def command(root: Path, tree: Path, argv: list[str], tmp: Path | None = None) -> list[str]:
    """`argv` wrapped in the sandbox of this platform. `tmp` is the private temporary folder macOS needs."""
    if sys.platform.startswith("linux"):
        return _bwrap(shutil.which("bwrap") or "bwrap", root, tree, argv)
    if sys.platform == "darwin":
        return ["sandbox-exec", "-p", profile(root, tree, tmp or tree.parent), *argv]
    raise OSError(f"no sandbox on this platform ({sys.platform})")


def problem(root: Path, tree: Path, tmp: Path | None = None) -> str | None:
    """Why no sandbox starts here, or None: the platform has none, its program is missing, or it fails to start."""
    if sys.platform.startswith("linux"):
        if not shutil.which("bwrap"):
            return "bubblewrap (bwrap) is not on PATH; `python3 ops/machine-setup.py` provides it"
    elif sys.platform == "darwin":
        if not shutil.which("sandbox-exec"):
            return "sandbox-exec is not on PATH"
    else:
        return f"no sandbox on this platform ({sys.platform}); the template runs on Linux, macOS and WSL2"
    try:
        done = subprocess.run(
            command(root, tree, ["true"], tmp),
            env=environment(root),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"the sandbox did not start: {exc}"
    if done.returncode != 0:
        return "the sandbox did not start: " + (done.stderr or done.stdout).strip()[-200:]
    return None


def run(root: Path, tree: Path, argv: list[str], timeout: int) -> subprocess.CompletedProcess | str:
    """Run `argv` in `tree` inside the sandbox; the reason as a string when no sandbox starts (nothing is run then)."""
    tmp = tree.parent / "tmp" if sys.platform == "darwin" else None
    if tmp:
        tmp.mkdir(exist_ok=True)
    why = problem(root, tree, tmp)
    if why:
        return why
    env = environment(root, str(tmp) if tmp else "/tmp")
    return subprocess.run(
        command(root, tree, argv, tmp), cwd=tree, env=env, capture_output=True, text=True, check=False, timeout=timeout
    )
