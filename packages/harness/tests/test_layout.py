"""Where run state lives (state.runs_root, and the hooks that cannot import harness) and what the template names
after the project."""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from harness import cli, state

REPO = Path(__file__).resolve().parents[3]
HOOKS = ("guard-inbox", "config-audit", "instructions-audit", "skill-audit", "statusline", "notify", "stop-failure")
# The hooks that take rules, schemas, runs or the harness from the project directory (item 7e of wave 1; the two
# guards of a role session's tools are held to it in test_guards.py).
MAPPED = ("guard-inbox", "validate-json", "stop-gate", "config-audit", "instructions-audit", "skill-audit",
          "statusline", "notify", "stop-failure")  # fmt: skip


def hook(name: str):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), REPO / ".claude" / "hooks" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runs_live_in_a_marked_runs_folder_beside_the_checkout_or_in_repo_runs(tmp_path: Path):
    repo = tmp_path / "container" / "template"
    repo.mkdir(parents=True)
    assert state.runs_root(repo) == tmp_path / "container" / "template-runs"
    shared = tmp_path / "container" / "runs"
    shared.mkdir()
    assert state.runs_root(repo) == tmp_path / "container" / "template-runs"  # a folder named runs is not enough
    (shared / state.RUNS_MARKER).write_text("")
    assert state.runs_root(repo) == shared


@pytest.mark.parametrize("name", HOOKS)
def test_every_hook_finds_the_runs_root_where_the_harness_does(name: str, tmp_path: Path):
    repo = tmp_path / "container" / "template"
    repo.mkdir(parents=True)
    module = hook(name)
    assert module.runs_root(repo) == tmp_path / "container" / "template-runs"
    (tmp_path / "container" / "runs").mkdir()
    (tmp_path / "container" / "runs" / state.RUNS_MARKER).write_text("")
    assert module.runs_root(repo) == state.runs_root(repo) == tmp_path / "container" / "runs"


@pytest.mark.parametrize("name", MAPPED)
def test_every_hook_takes_the_main_checkout_for_a_project_directory_that_is_a_checkout(name: str, tmp_path: Path):
    """Item 7e: CLAUDE_PROJECT_DIR is where the session started (hooks.md:601-612 in the facts file); when that is a
    checkout under .claude/worktrees/, its rules, schemas, runs and harness are still the main checkout's: a unit that
    fixes the hooks edits the checkout's own copies."""
    module = hook(name)
    repo = tmp_path / "template"
    assert module.main_checkout(repo / ".claude" / "worktrees" / "r1-write-01") == repo
    assert module.main_checkout(repo) == repo


def test_the_night_tick_finds_the_marked_runs_folder_too():
    assert f'"$runs/{state.RUNS_MARKER}"' in (REPO / "ops" / "night-tick.sh").read_text(encoding="utf-8")


def test_a_new_project_can_be_made_in_a_container_with_its_runs_and_experiments(tmp_path: Path):
    container = tmp_path / "gex"
    command = [sys.executable, str(REPO / "ops" / "new-project.py"), str(container), "repo_name=gexhex"]
    done = subprocess.run([*command, "--container", "--no-setup"], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    repo = container / "gexhex"
    assert (repo / "CLAUDE.md").is_file()
    assert (container / "runs" / state.RUNS_MARKER).is_file() and (container / "experiments").is_dir()
    assert state.runs_root(repo) == container / "runs"
    (tmp_path / "other" / "runs").mkdir(parents=True)  # a runs/ folder that belongs to something else
    refused = subprocess.run(
        [*command[:2], str(tmp_path / "other"), "--container", "--no-setup"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert refused.returncode == 1 and "is not a runs root" in refused.stdout


def test_harness_runs_root_prints_the_place_and_init_makes_the_marked_folder(tmp_path: Path, monkeypatch, capsys):
    repo = tmp_path / "container" / "template"
    repo.mkdir(parents=True)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(repo))
    assert cli.main(["runs-root", "--plain"]) == 0
    assert capsys.readouterr().out.strip() == str(tmp_path / "container" / "template-runs")
    assert cli.main(["runs-root", "--init"]) == 0
    assert json.loads(capsys.readouterr().out)["runs_root"] == str(tmp_path / "container" / "runs")
    assert (tmp_path / "container" / "runs" / state.RUNS_MARKER).is_file()


def test_init_takes_only_a_container_of_one_checkout(tmp_path: Path, monkeypatch, capsys):
    """The marked runs/ is the runs root of every checkout beside it: in a shared folder such as ~/Desktop the projects
    would mix their runs and lose sight of their active ones. A runs/ folder without the marker is not taken either."""
    repo = tmp_path / "desk" / "one"
    repo.mkdir(parents=True)
    (tmp_path / "desk" / "two" / ".git").mkdir(parents=True)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(repo))
    assert cli.main(["runs-root", "--init"]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "shared_parent"
    assert not (tmp_path / "desk" / "runs").exists()
    lone = tmp_path / "box" / "repo"
    lone.mkdir(parents=True)
    (tmp_path / "box" / "runs").mkdir()  # a runs/ folder that belongs to something else
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(lone))
    assert cli.main(["runs-root", "--init", "--plain"]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "not_a_runs_root"
    assert not (tmp_path / "box" / "runs" / state.RUNS_MARKER).exists()


def test_a_container_that_holds_another_checkout_is_refused(tmp_path: Path):
    (tmp_path / "desk" / "site" / ".git").mkdir(parents=True)
    command = [sys.executable, str(REPO / "ops" / "new-project.py"), str(tmp_path / "desk"), "repo_name=gexhex"]
    done = subprocess.run([*command, "--container", "--no-setup"], capture_output=True, text=True, check=False)
    assert done.returncode == 1 and "holds other checkouts (site)" in done.stdout
    assert not (tmp_path / "desk" / "runs").exists() and not (tmp_path / "desk" / "gexhex").exists()


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads every folder")
def test_an_unreadable_folder_in_the_container_is_no_checkout(tmp_path: Path):
    locked = tmp_path / "box" / "private"
    locked.mkdir(parents=True)
    locked.chmod(0)
    command = [sys.executable, str(REPO / "ops" / "new-project.py"), str(tmp_path / "box"), "repo_name=gexhex"]
    try:
        done = subprocess.run([*command, "--container", "--no-setup"], capture_output=True, text=True, check=False)
    finally:
        locked.chmod(0o700)
    assert done.returncode == 0, done.stdout + done.stderr


def test_every_function_of_the_new_project_script_stays_under_50_lines():
    """V1: main() had 71 lines once it copied a tracked link as a link (`.claude/rules/python.md`: under 50)."""
    tree = ast.parse((REPO / "ops" / "new-project.py").read_text(encoding="utf-8"))
    lengths = {f.name: f.end_lineno - f.lineno + 1 for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)}
    assert "main" in lengths and max(lengths.values()) < 50, lengths


def test_the_internal_marketplace_is_named_after_the_project():
    """Claude Code knows a marketplace by one name on the whole machine: projects that share the name share it."""
    name = json.loads((REPO / "plugins/.claude-plugin/marketplace.json").read_text())["name"]
    variables = yaml.safe_load((REPO / "docs/template/variables.yaml").read_text())
    repo_name = next(v["default"] for v in variables["variables"] if v["name"] == "repo_name")
    assert name == f"{repo_name}-plugins"
    settings = json.loads((REPO / ".claude/settings.json").read_text())
    assert set(settings["extraKnownMarketplaces"]) == {name}
    assert all(key.endswith("@" + name) for key in settings["enabledPlugins"])
