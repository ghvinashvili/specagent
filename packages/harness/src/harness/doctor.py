"""harness/doctor.py — what this machine needs before a role session can run (`harness doctor`).

Every check here failed at least once in a live run on a real machine. A check names its remedy, so the output can be
followed without reading the code. Nothing is changed: the command only looks.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

from . import trust


def _run(cmd: list[str], timeout: int = 20) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(cmd, 127, "", str(exc))


def _item(name: str, ok: bool, detail: str = "", fix: str = "", required: bool = True) -> dict:
    return {
        "name": name,
        "ok": ok,
        "required": required,
        **({"detail": detail} if detail else {}),
        **({"fix": fix} if fix and not ok else {}),
    }


def _native_windows() -> bool:
    return os.name == "nt"


def _version(text: str) -> tuple[int, ...]:
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def service_path() -> str | None:
    """The PATH of Claude Code's background service, which every background session inherits; None when no service
    runs (the next `claude --bg` starts one with the PATH of the command that runs it) or its environment cannot be
    read here."""
    status = _run(["claude", "daemon", "status"])
    m = re.search(r"^pid:\s+(\d+)", status.stdout, re.MULTILINE)
    if not m:
        return None
    try:
        environ = Path(f"/proc/{m.group(1)}/environ").read_bytes().split(b"\0")
    except OSError:
        return None
    return next((e[5:].decode(errors="replace") for e in environ if e.startswith(b"PATH=")), None)


def service_environment() -> dict:
    """Background sessions inherit the environment of Claude Code's background service, which keeps the environment
    of the command that first ran `claude --bg`. A service started inside a Python environment puts that
    environment's `bin` first on the PATH of every later session; one started with the variables of a role session
    makes the hooks take every later background session for that role."""
    name = "the background service carries no Python environment and no variables of a role session"
    status = _run(["claude", "daemon", "status"])
    m = re.search(r"^pid:\s+(\d+)", status.stdout, re.MULTILINE)
    if not m:
        return _item(name, True, detail="no background service is running", required=False)
    try:
        environ = Path(f"/proc/{m.group(1)}/environ").read_bytes().split(b"\0")
    except OSError:
        return _item(name, True, detail="the service's environment cannot be read on this system", required=False)
    found = [
        e.decode(errors="replace").split("=", 1)[0]
        for e in environ
        if (e.startswith(b"VIRTUAL_ENV=") and e != b"VIRTUAL_ENV=") or e.startswith(b"HARNESS_")
    ]
    return _item(
        name,
        not found,
        detail=", ".join(found),
        fix="a role session overrides these in its settings, but any other background session (a manager started "
        "from the agent view) inherits them and is taken for a role session of an old run. When no background "
        "session is running: `claude daemon stop --any`; the next `harness launch` starts the service clean",
        required=False,
    )


def nested_userns(bwrap: str) -> subprocess.CompletedProcess:
    """A user namespace inside the sandbox: what Claude Code's seccomp helper needs for every sandboxed command."""
    return _run(
        [
            bwrap,
            "--unshare-user",
            "--ro-bind",
            "/",
            "/",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "unshare",
            "--user",
            "--map-root-user",
            "true",
        ]
    )


SANDBOX_FIX = (
    "a session that starts in this checkout sets the sandbox up by itself where it can, as this user and without a "
    "password (python3 ops/machine-setup.py --user, which also lifts a decline made with --undo); where only the "
    "administrator can, the session offers python3 ops/machine-setup.py and its one password. --plan shows what "
    "either would change"
)
SERVICE_PATH_FIX = (
    "Claude Code's background service keeps the PATH it started with, and only a restart gives it this one: ask the "
    "human whether to stop it (`claude daemon stop --any`, once no background session runs; it stops the service for "
    "every project of this user), and the next launch starts it again"
)
MACOS_FIX = (
    "macOS ships the seatbelt as /usr/bin/sandbox-exec: put /usr/bin on PATH. Without it no role session starts: its "
    "settings hold sandbox.failIfUnavailable"
)


def _sandbox_problem(path: str | None) -> str | None:
    found = {command: shutil.which(command, path=path) for command in ("bwrap", "socat")}
    missing = [name for name, command in (("bubblewrap", "bwrap"), ("socat", "socat")) if found[command] is None]
    if missing:
        return f"{' and '.join(missing)} not on PATH"
    probe = nested_userns(found["bwrap"])
    if probe.returncode != 0:
        return "a user namespace inside bubblewrap is refused: " + (probe.stderr or probe.stdout).strip()[-200:]
    return None


def sandbox_problem(root: Path, path: str | None = None) -> str | None:
    """Why the sandbox of a role session cannot start on this machine, or None. A role session starts only inside it
    (`sandbox.failIfUnavailable` in its settings, harness/access.py), so the launcher asks before it starts one.
    `path` is the PATH the session will run with: a background session's is the background service's
    (service_path), which may not be this process's."""
    if not sys.platform.startswith("linux"):
        return None
    settings = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
    if not settings.get("sandbox", {}).get("enabled"):
        return None
    problem = _sandbox_problem(path)
    if problem and path is not None and _sandbox_problem(None) is None:
        return f"{problem}, the PATH of Claude Code's background service. {SERVICE_PATH_FIX}"
    return problem


# What the hooks do when python3 has no jsonschema: take it from the workspace when that was made from the same Python.
JSONSCHEMA_PROBE = (
    "import sys, pathlib; v = sys.version_info; "
    "sys.path.append(str(pathlib.Path(sys.argv[1]) / '.venv' / 'lib' / f'python{v[0]}.{v[1]}' / 'site-packages')); "
    "import jsonschema"
)


def code_intel(root: Path) -> dict:
    """The language servers of plugins/code-intel: installed, and each one answers when it is started."""
    script = root / "plugins" / "code-intel" / "scripts" / "ensure.py"
    name = "the language servers of code-intel are installed and answer"
    fix = "they install on their own when a session starts; now: python3 ops/bootstrap.py --wait"
    if not script.is_file():
        return _item(name, False, "plugins/code-intel is missing", fix, required=False)
    state = _run(["python3", str(script), "--check"])
    if state.returncode != 0:
        detail = state.stdout.strip()
        try:
            detail = "missing: " + ", ".join(json.loads(detail)["missing"]) or "not installed for these versions"
        except (ValueError, KeyError):
            pass
        return _item(name, False, detail, fix, required=False)
    probe = _run(["python3", str(script), "--probe"], timeout=180)
    failed = {}
    try:
        failed = json.loads(probe.stdout)["failed"]
    except (ValueError, KeyError):
        failed = {"probe": (probe.stdout or probe.stderr).strip()[-200:]}
    return _item(name, not failed, "; ".join(f"{k}: {v}" for k, v in failed.items()), fix, required=False)


def sandbox_items(settings: dict, platform: str | None = None) -> list[dict]:
    """The sandbox's items for this OS (None: this machine's, read when the doctor runs): the WSL2 path on native
    Windows, the seatbelt on macOS, bubblewrap, socat and a nested probe on Linux; none while the sandbox is off."""
    if platform is None:
        platform = "win32" if _native_windows() else sys.platform
    if platform == "win32":
        return [
            _item(
                "the repository runs in WSL2",
                False,
                "native Windows",
                "Claude Code has no sandbox on native Windows and a role session does not start without one: open "
                "the repository in a WSL2 distribution, where everything else sets itself up",
            )
        ]
    if not settings.get("sandbox", {}).get("enabled"):
        return []
    if platform == "darwin":
        path = shutil.which("sandbox-exec")
        return [_item("sandbox-exec is on PATH", bool(path), path or "", MACOS_FIX)]
    if not platform.startswith("linux"):
        return []
    items = []
    bwrap, socat = shutil.which("bwrap"), shutil.which("socat")
    items.append(_item("bubblewrap is on PATH", bwrap is not None, bwrap or "", SANDBOX_FIX))
    items.append(
        _item(
            "socat is on PATH",
            socat is not None,
            socat or "",
            SANDBOX_FIX + ". Without socat no role session starts: its settings hold sandbox.failIfUnavailable",
        )
    )
    if bwrap:
        probe = nested_userns(bwrap)
        items.append(
            _item(
                "a sandboxed command can run (user namespace inside bubblewrap)",
                probe.returncode == 0,
                (probe.stderr or probe.stdout).strip()[-200:],
                "an AppArmor profile strips capabilities from what bubblewrap starts (Zorin OS ships "
                "bwrap-userns-restrict-patched, Ubuntu offers bwrap-userns-restrict), or Ubuntu's restriction "
                "refuses bubblewrap the namespace. With socat installed every Bash call of a role session then "
                "fails (`apply-seccomp: ... nested userns is capability-restricted`). " + SANDBOX_FIX,
            )
        )
    return items


def optional_items() -> list[dict]:
    """The items no role session needs: gh (pull requests) and just (the justfile's recipes)."""
    return [
        _item("gh is on PATH", shutil.which("gh") is not None, fix="needed only for pull requests", required=False),
        just_item(),
    ]


COMMONS_URL = "https://github.com/ghvinashvili/aftpro-commons.git"  # the public commons; ops/new-vault.py names it too
FRESH_DAYS = 7  # a clone of the commons older than this is read stale


def vault_item(root: Path) -> dict:
    """The user's vault and the clone of the commons, at the paths docs/template/variables.yaml gives: the vault holds
    INDEX.md, rules.md and its own ops/check_pages.py, which passes; the clone was fetched within FRESH_DAYS days (the
    newest of .git/FETCH_HEAD and .git/packed-refs: a fresh clone has only the second). Optional: no role needs it."""
    spec = yaml.safe_load((root / "docs" / "template" / "variables.yaml").read_text(encoding="utf-8"))
    paths = {v["name"]: Path(v["default"]).expanduser() for v in spec["variables"]}
    vault, commons = paths["vault_path"], paths["commons_path"]
    problems, fixes = [], []
    missing = [name for name in ("INDEX.md", "rules.md", "ops/check_pages.py") if not (vault / name).is_file()]
    if missing:
        problems.append(f"{vault} lacks {', '.join(missing)}")
        fixes.append(f"python3 ops/new-vault.py {vault}")
    elif (pages := _run(["python3", "-B", str(vault / "ops" / "check_pages.py"), str(vault)], timeout=60)).returncode:
        problems.append(f"the vault's check fails: {(pages.stdout.strip().splitlines() or [pages.stderr.strip()])[-1]}")
        fixes.append(f"python3 {vault}/ops/check_pages.py {vault} lists what to mend")
    if not (commons / ".git").is_dir():
        problems.append(f"{commons} is not a clone of the commons")
        fixes.append(f"git clone {COMMONS_URL} {commons}")
    else:
        stamps = [
            p.stat().st_mtime
            for p in (commons / ".git" / "FETCH_HEAD", commons / ".git" / "packed-refs")
            if p.is_file()
        ]
        if not stamps or time.time() - max(stamps) > FRESH_DAYS * 86400:
            problems.append(f"{commons} was not fetched in {FRESH_DAYS} days")
            fixes.append(f"git -C {commons} pull --ff-only")
    return _item(
        "the vault and the commons are in place",
        not problems,
        "; ".join(problems) or f"{vault}, {commons}",
        "; ".join(fixes),
        required=False,
    )


def check(root: Path) -> dict:
    items = []
    settings = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
    need = settings.get("minimumVersion", "0.0.0")
    claude = _run(["claude", "--version"])
    items.append(
        _item(
            "claude is installed and new enough",
            claude.returncode == 0 and _version(claude.stdout) >= _version(need),
            f"found {claude.stdout.strip() or 'nothing'}, need {need}",
            "install or update Claude Code (https://code.claude.com/docs/en/setup)",
        )
    )
    for tool, fix in (
        (
            "uv",
            "set up on its own when a session starts in the repository (ops/bootstrap.py); now: python3 ops/bootstrap.py --wait",
        ),
        ("git", "install git"),
    ):
        items.append(_item(f"{tool} is on PATH", shutil.which(tool) is not None, fix=fix))
    items += sandbox_items(settings)
    hook_python = _run(["python3", "-c", JSONSCHEMA_PROBE, str(root)])
    items.append(
        _item(
            "the hooks can import jsonschema (python3's own, or the workspace's when it was made from python3)",
            hook_python.returncode == 0,
            fix="python3 ops/bootstrap.py --wait makes the workspace from python3 when it is 3.12 or newer; otherwise "
            "sudo apt-get install python3-jsonschema. Without it the Write hook and the stop gate only check that a "
            "file is JSON",
        )
    )
    items.append(code_intel(root))
    items.append(
        _item(
            "the repository is a trusted workspace",
            trust.trusted(root),
            fix="the next `harness launch` or `harness resume` records it, the flag alone (harness/trust.py); "
            "`claude --bg` refuses an untrusted directory, and Claude Code looks no higher than the repository's root",
        )
    )
    items.append(service_environment())
    items.append(vault_item(root))
    items += optional_items()
    items.append(leftovers_check(root))
    return {"ok": all(i["ok"] for i in items if i["required"]), "checks": items}


def leftovers_check(root: Path, listing: list[dict] | None = None) -> dict:
    """What earlier runs left behind (harness.leftovers): optional, each with the command that removes it."""
    from . import leftovers

    found = leftovers.find(root, listing=listing)
    kinds = sorted({f["kind"] for f in found})
    item = _item(
        "nothing is left behind by earlier runs",
        not found,
        f"{len(found)} found: " + ", ".join(f"{sum(f['kind'] == k for f in found)} {k}" for k in kinds)
        if found
        else "nothing found",
        "; ".join(dict.fromkeys(f["fix"] for f in found)),
        required=False,
    )
    item["found"] = found
    return item


def just_item() -> dict:
    """The optional `just` item: where it is, or the commands that install it (lessons.md "Read first" 4)."""
    path = shutil.which("just")
    fix = (
        "optional: the justfile's recipes. `uv tool install rust-just`, or `python3 ops/bootstrap.py --wait`, which "
        "installs it when it is missing; without it, run a recipe's body as the justfile writes it"
    )
    return _item("just is on PATH", path is not None, path or "", fix, required=False)
