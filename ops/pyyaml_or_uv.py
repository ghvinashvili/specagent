"""Run an ops script that needs PyYAML on a python3 that has none.

A fresh python3 (macOS, a minimal Linux, Ubuntu under WSL) has no PyYAML, and the README's Quick start runs
`python3 ops/new-project.py` before anything is installed. A script that imports yaml calls `ensure_pyyaml()` when the
import fails: it runs the same script again under uv with PyYAML (`uv run --no-project --with pyyaml`) and the same
interpreter, so the scripts it starts with `sys.executable` (ops/new-vault.py, ops/bootstrap.py) have PyYAML too.
uv comes from PATH, from ~/.local/bin, or is fetched the way ops/bootstrap.py fetches it (the pinned wheel, checked
against its hash; plugins/code-intel/scripts/ensure.py).
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REEXEC = "SPECAGENT_PYYAML_REEXEC"
ADVICE = "install uv (https://docs.astral.sh/uv/) or run `python3 -m pip install pyyaml`"


def find_uv() -> Path | None:
    """uv on PATH or in ~/.local/bin, else the pinned uv fetched into ~/.local; None when it cannot be had."""
    found = shutil.which("uv")
    if found:
        return Path(found)
    local = Path.home() / ".local" / "bin" / "uv"
    if local.exists():
        return local
    try:
        spec = importlib.util.spec_from_file_location(
            "code_intel_ensure", ROOT / "plugins" / "code-intel" / "scripts" / "ensure.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        versions = ROOT / "plugins" / "code-intel" / "toolchain" / "versions.json"
        return Path(module.fetch_uv(Path.home() / ".local", json.loads(versions.read_text(encoding="utf-8"))["uv"]))
    except Exception:  # noqa: BLE001 -- no network, no wheel: the caller says what to install
        return None


def rerun_argv(uv: Path, python: str, script: str, args: list[str]) -> list[str]:
    """The command that runs `script` again with PyYAML, on the same interpreter."""
    return [str(uv), "run", "--no-project", "--python", python, "--with", "pyyaml", python, script, *args]


def ensure_pyyaml() -> None:
    """Return when PyYAML imports; else replace this process with the script under uv, or exit with what to install."""
    if importlib.util.find_spec("yaml") is not None:
        return
    if os.environ.get(REEXEC):
        sys.exit(f"PyYAML is still missing under uv: {ADVICE}")
    uv = find_uv()
    if uv is None:
        sys.exit(f"{Path(sys.argv[0]).name} needs PyYAML: {ADVICE}")
    os.environ[REEXEC] = "1"
    argv = rerun_argv(uv, sys.executable, sys.argv[0], sys.argv[1:])
    os.execv(argv[0], argv)
