"""The template's own plans stay in the template (C4): ops/new-project.py copies every tracked file except the
`omit:` prefixes of docs/template/variables.yaml, and those include the template-core and manager-build plans, active
or completed."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
PLAN = "docs/exec-plans/active/template-core/"
DONE = "docs/exec-plans/done/template-core/"  # where docs/exec-plans/active/README.md moves a finished plan
MANAGER_PLAN = "docs/exec-plans/active/manager-build/"  # the plan of the manager-build run (release 1.5.0)
MANAGER_DONE = "docs/exec-plans/done/manager-build/"


def template(tmp_path: Path) -> Path:
    """A git repository with the checkout's new-project.py, variables.yaml and VERSION, a tracked file in each plan
    folder of the template, a plan of a project and the design record."""
    root = tmp_path / "template"
    for rel in ("ops/new-project.py", "docs/template/variables.yaml", "docs/template/VERSION"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, root / rel)
    files = {
        f"{PLAN}00-index.md": "# Index\n",
        f"{PLAN}task-01.md": "# Task 1 — demo\n",
        f"{DONE}00-index.md": "# Index\n",
        "docs/exec-plans/active/README.md": "# Active plans\n",
        "docs/exec-plans/active/demo/00-index.md": "# Demo\n",
        "design/notes.md": "# Notes\n",
    }
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    return root


def test_a_project_gets_none_of_the_template_core_plan(tmp_path: Path):
    root, target = template(tmp_path), tmp_path / "demo"
    command = [sys.executable, str(root / "ops" / "new-project.py"), str(target), "--no-setup"]
    done = subprocess.run(command, capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    assert (target / "docs/exec-plans/active/README.md").is_file()
    assert (target / "docs/exec-plans/active/demo/00-index.md").is_file()
    assert not (target / PLAN).exists() and not (target / DONE).exists() and not (target / "design").exists()


def test_the_omit_list_keeps_the_design_record_and_adds_both_plan_folders():
    spec = yaml.safe_load((REPO / "docs" / "template" / "variables.yaml").read_text(encoding="utf-8"))
    assert spec["omit"][:2] == ["design/", "context/fix-20261004/"]
    assert PLAN in spec["omit"] and DONE in spec["omit"]


def test_a_project_drops_the_index_lines_that_link_into_an_omitted_folder(tmp_path: Path):
    root, target = template(tmp_path), tmp_path / "demo"
    readme = ("# Active plans\n\n## Plans\n- [template-core](template-core/00-index.md): the template's own run\n"
              "- [demo](demo/00-index.md): a plan of the project\n")  # fmt: skip
    index = ("# Wiki index\n\n## Plans and the code graph\n- [Active plans](plans/README.md): the plans in progress\n"
             "- [The template-core plan](plans/template-core/00-index.md): its index\n"
             "The template-core run wrote these pages.\n")  # fmt: skip
    (root / "docs/exec-plans/active/README.md").write_text(readme, encoding="utf-8")
    (root / "wiki").mkdir()
    (root / "wiki/index.md").write_text(index, encoding="utf-8")
    (root / "wiki/plans").symlink_to("../docs/exec-plans/active")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    command = [sys.executable, str(root / "ops" / "new-project.py"), str(target), "--no-setup"]
    done = subprocess.run(command, capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    assert (target / "docs/exec-plans/active/README.md").read_text(encoding="utf-8") == (
        "# Active plans\n\n## Plans\n- [demo](demo/00-index.md): a plan of the project\n"
    )
    assert (target / "wiki/index.md").read_text(encoding="utf-8") == (
        "# Wiki index\n\n## Plans and the code graph\n- [Active plans](plans/README.md): the plans in progress\n"
        "The template-core run wrote these pages.\n"
    )


def test_the_omit_list_adds_both_manager_build_plan_folders():
    spec = yaml.safe_load((REPO / "docs" / "template" / "variables.yaml").read_text(encoding="utf-8"))
    assert MANAGER_PLAN in spec["omit"] and MANAGER_DONE in spec["omit"]


def test_a_project_gets_none_of_the_manager_build_plan_nor_its_plans_line(tmp_path: Path):
    root, target = template(tmp_path), tmp_path / "demo"
    for rel in (f"{MANAGER_PLAN}00-index.md", f"{MANAGER_PLAN}task-11.md", f"{MANAGER_DONE}00-index.md"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("# Plan\n", encoding="utf-8")
    readme = ("# Active plans\n\n## Plans\n\n"
              "- [manager-build](manager-build/00-index.md): the template's manager-build run, eleven tasks to release"
              " 1.5.0\n- [demo](demo/00-index.md): a plan of the project\n")  # fmt: skip
    (root / "docs/exec-plans/active/README.md").write_text(readme, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    command = [sys.executable, str(root / "ops" / "new-project.py"), str(target), "--no-setup"]
    done = subprocess.run(command, capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    assert not (target / MANAGER_PLAN).exists() and not (target / MANAGER_DONE).exists()
    assert (target / "docs/exec-plans/active/demo/00-index.md").is_file()
    assert (target / "docs/exec-plans/active/README.md").read_text(encoding="utf-8") == (
        "# Active plans\n\n## Plans\n\n- [demo](demo/00-index.md): a plan of the project\n"
    )
