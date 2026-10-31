"""`ops/container.py` lays the project's folder out around a checkout (owner, 2026-10-29: "a container must hold it:
the runs, the experiments and the like in one folder"): beside the checkout it makes `runs/` (marked `.harness-runs`,
the runs root), `experiments/` and `docs/handoff/`; it refuses a parent that holds another checkout or a `runs/`
without the marker; a second run changes nothing."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MARKER = ".harness-runs"


def checkout_in(box: Path, name: str = "template") -> Path:
    """A minimal checkout `box/<name>/` with the two ops scripts the container script needs."""
    co = box / name
    (co / ".git").mkdir(parents=True)
    (co / "ops").mkdir()
    for script in ("container.py", "new-project.py"):
        shutil.copy(REPO / "ops" / script, co / "ops" / script)
    return co


def run(co: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(co / "ops" / "container.py")], capture_output=True, text=True, cwd=co, check=False
    )


def test_runs_experiments_and_handoff_appear_beside_the_checkout(tmp_path: Path) -> None:
    co = checkout_in(tmp_path / "box")
    r = run(co)
    assert r.returncode == 0, r.stdout + r.stderr
    box = tmp_path / "box"
    assert (box / "runs" / MARKER).read_text(encoding="utf-8").startswith("runs of the checkout template beside")
    assert (box / "experiments").is_dir() and (box / "docs" / "handoff").is_dir()
    assert f"{box}" in r.stdout and "runs/" in r.stdout


def test_a_second_run_changes_nothing(tmp_path: Path) -> None:
    co = checkout_in(tmp_path / "box")
    assert run(co).returncode == 0
    marker = tmp_path / "box" / "runs" / MARKER
    before = marker.stat().st_mtime_ns
    (tmp_path / "box" / "docs" / "handoff" / "note.md").write_text("kept\n", encoding="utf-8")
    r = run(co)
    assert r.returncode == 0, r.stdout + r.stderr
    assert marker.stat().st_mtime_ns == before
    assert (tmp_path / "box" / "docs" / "handoff" / "note.md").read_text(encoding="utf-8") == "kept\n"


def test_a_parent_holding_another_checkout_is_refused(tmp_path: Path) -> None:
    co = checkout_in(tmp_path / "box")
    (tmp_path / "box" / "other" / ".git").mkdir(parents=True)
    r = run(co)
    assert r.returncode == 1
    assert "other" in r.stdout and "checkout" in r.stdout
    assert not (tmp_path / "box" / "runs").exists()


def test_a_runs_folder_without_the_marker_is_refused(tmp_path: Path) -> None:
    co = checkout_in(tmp_path / "box")
    (tmp_path / "box" / "runs").mkdir()
    r = run(co)
    assert r.returncode == 1
    assert MARKER in r.stdout
    assert not (tmp_path / "box" / "experiments").exists()


def test_new_project_with_container_gives_the_folders_container_py_gives(tmp_path: Path) -> None:
    """The owner's final plan, 0.6: `ops/new-project.py --container` lays a new project out as `ops/container.py`
    does, the hand-over notes' `docs/handoff/` beside the checkout, not inside it."""
    template = tmp_path / "template"
    for rel in ("ops/new-project.py", "docs/template/variables.yaml", "docs/template/VERSION"):
        (template / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, template / rel)
    subprocess.run(["git", "init", "-q"], cwd=template, check=True)
    subprocess.run(["git", "add", "-A"], cwd=template, check=True)
    box = tmp_path / "box"
    command = [sys.executable, str(template / "ops" / "new-project.py"), str(box), "repo_name=demo", "--container"]
    done = subprocess.run([*command, "--no-setup"], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    spec = importlib.util.spec_from_file_location("ops_container_folders", REPO / "ops" / "container.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert "docs/handoff/" in module.FOLDERS
    assert [folder for folder in module.FOLDERS if not (box / folder).is_dir()] == []
    assert (box / "demo" / "ops" / "new-project.py").is_file() and not (box / "demo" / "docs" / "handoff").exists()
