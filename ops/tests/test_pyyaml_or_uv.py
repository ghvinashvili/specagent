"""ops/pyyaml_or_uv.py: the Quick start's `python3 ops/new-project.py` works on a python3 without PyYAML (a fresh
macOS, found by the macOS workflow): the script runs itself again under uv with PyYAML, and says what to install when
it cannot."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HELPER = REPO / "ops" / "pyyaml_or_uv.py"


def _helper():
    spec = importlib.util.spec_from_file_location("pyyaml_or_uv", HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_uv(tmp_path: Path) -> tuple[Path, Path]:
    """A `uv` that records its arguments and its environment flag instead of running anything."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    record = tmp_path / "argv.txt"
    uv = bin_dir / "uv"
    uv.write_text(f'#!/bin/sh\nprintf "%s\\n" "$SPECAGENT_PYYAML_REEXEC" "$@" > "{record}"\n', encoding="utf-8")
    uv.chmod(0o755)
    return bin_dir, record


def _without_pyyaml(script: str, args: list[str], env: dict) -> subprocess.CompletedProcess:
    """Run a script on this interpreter with no site-packages (-S), so `import yaml` fails as on a fresh python3."""
    return subprocess.run(
        [sys.executable, "-S", str(REPO / "ops" / script), *args], env=env, capture_output=True, text=True, check=False
    )


def test_it_returns_when_pyyaml_imports():
    _helper().ensure_pyyaml()  # the test environment has PyYAML: nothing is run again


def test_the_rerun_keeps_the_interpreter_the_script_and_its_arguments():
    argv = _helper().rerun_argv(Path("/x/uv"), "/py/python3", "ops/new-project.py", ["d", "repo_name=a"])
    assert argv == [
        "/x/uv",
        "run",
        "--no-project",
        "--python",
        "/py/python3",
        "--with",
        "pyyaml",
        "python",
        "ops/new-project.py",
        "d",
        "repo_name=a",
    ]


def test_new_project_without_pyyaml_runs_again_under_uv(tmp_path):
    bin_dir, record = _fake_uv(tmp_path)
    env = {**os.environ, "PATH": str(bin_dir)}
    env.pop("SPECAGENT_PYYAML_REEXEC", None)
    res = _without_pyyaml("new-project.py", [str(tmp_path / "demo"), "repo_name=demo"], env)
    assert res.returncode == 0, res.stderr
    lines = record.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "1"  # the guard against a second rerun is set
    assert lines[1:4] == ["run", "--no-project", "--python"]
    assert "--with" in lines and lines[lines.index("--with") + 1] == "pyyaml"
    assert lines[-3:] == [str(REPO / "ops" / "new-project.py"), str(tmp_path / "demo"), "repo_name=demo"]


def test_a_second_rerun_stops_with_what_to_install(tmp_path):
    bin_dir, record = _fake_uv(tmp_path)
    env = {**os.environ, "PATH": str(bin_dir), "SPECAGENT_PYYAML_REEXEC": "1"}
    res = _without_pyyaml("new-vault.py", [str(tmp_path / "vault")], env)
    assert res.returncode != 0
    assert "PyYAML is still missing under uv" in res.stderr and "pip install pyyaml" in res.stderr
    assert not record.exists()
