"""The plans in the Obsidian vault (owner's order, 2026-10-28): wiki/plans is a tracked relative link to
docs/exec-plans/active, a new project gets it as a link, and the vault's settings are committed (spec A3)."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
IDENTITY = ["-c", "user.email=t@example.com", "-c", "user.name=t", "-c", "commit.gpgsign=false"]
TARGET = "../docs/exec-plans/active"


def git(root: Path, *args: str) -> None:
    command = ["git", "-C", str(root), *IDENTITY]
    subprocess.run([*command, *args], check=True, capture_output=True)


def test_the_template_links_its_active_plans_into_the_vault():
    link = REPO / "wiki" / "plans"
    assert link.is_symlink() and os.readlink(link) == TARGET
    assert link.resolve() == (REPO / "docs" / "exec-plans" / "active").resolve()
    assert (link / "README.md").is_file()  # listed through the link


def test_a_new_project_gets_the_link_as_a_link_that_resolves_inside_the_project(tmp_path: Path):
    template = tmp_path / "template"
    for rel in ("ops/new-project.py", "docs/template/variables.yaml", "docs/template/VERSION"):
        (template / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / rel, template / rel)
    (template / "docs" / "exec-plans" / "active").mkdir(parents=True)
    (template / "docs" / "exec-plans" / "active" / "README.md").write_text("# Plans\n", encoding="utf-8")
    (template / "ops" / "run.sh").write_text("#!/bin/sh\necho run\n", encoding="utf-8")
    (template / "ops" / "run.sh").chmod(0o755)
    (template / "wiki").mkdir()
    os.symlink(TARGET, template / "wiki" / "plans")
    git(template, "init", "-q", "-b", "main")
    git(template, "add", "-A")
    git(template, "commit", "-qm", "template")
    project = tmp_path / "project"
    command = [sys.executable, str(template / "ops" / "new-project.py"), str(project), "--no-setup"]
    done = subprocess.run(command, capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    link = project / "wiki" / "plans"
    assert link.is_symlink() and os.readlink(link) == TARGET
    assert link.resolve() == (project / "docs" / "exec-plans" / "active").resolve()  # the project's own plans
    assert (link / "README.md").read_text(encoding="utf-8") == "# Plans\n"
    assert os.stat(project / "ops" / "run.sh").st_mode & stat.S_IXUSR  # the other files keep their modes


def test_the_vault_settings_are_the_files_the_plugin_and_the_spec_name():
    vault = (
        REPO / ".obsidian"
    )  # the checkout root is the claude-obsidian vault; the plugin wrote app, appearance, graph
    settings = {
        name: json.loads((vault / name).read_text(encoding="utf-8"))
        for name in ("app.json", "appearance.json", "core-plugins.json", "graph.json")
    }
    assert all(isinstance(value, dict) for value in settings.values())
    plugins = settings["core-plugins.json"]
    assert all(plugins[k] is True for k in ("file-explorer", "global-search", "graph", "backlink", "outgoing-link"))
    assert all(plugins[k] is False for k in ("sync", "publish", "daily-notes"))  # nothing leaves the machine
    groups = settings["graph.json"]["colorGroups"]
    assert [g["query"] for g in groups] == ["path:wiki/decisions/", "path:wiki/graph/", "path:wiki/plans/"]
    assert all(set(g["color"]) == {"a", "rgb"} and isinstance(g["color"]["rgb"], int) for g in groups)
