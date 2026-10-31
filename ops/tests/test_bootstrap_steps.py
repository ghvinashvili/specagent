"""ops/bootstrap.py (index D11, spec A3): a checkout gets `just` when it has none, points git at its versioned hooks,
sets up or checks the sandbox of role sessions, and builds its first code graph once. `setup()` downloads and
installs, so the file is loaded by its path and every command is recorded instead of run, as
packages/harness/tests/test_setup.py loads it; the order is then tested offline."""

import ast
import importlib.util
import io
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def boot(tmp_path, monkeypatch):
    """ops/bootstrap.py with a checkout in tmp_path on Linux, uv and claude present, graphify installed, `just`
    missing, the sandbox enabled, and the checkout the top of a git repository with no hooks path set."""
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    spec = importlib.util.spec_from_file_location("ops_bootstrap_steps", REPO / "ops" / "bootstrap.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root = tmp_path / "checkout"
    (root / ".venv").mkdir(parents=True)
    (root / ".claude").mkdir()
    (root / ".claude" / "settings.json").write_text('{"sandbox": {"enabled": true}}', encoding="utf-8")
    tools = {"claude": "/usr/bin/claude", "python3": sys.executable, "graphify": "/opt/bin/graphify"}
    rec = SimpleNamespace(calls=[], fail=set(), tools=tools, root=root, hooks=None, top=root)

    def step(name, cmd, log, env=None):
        rec.calls.append((name, cmd))
        return name not in rec.fail

    monkeypatch.setattr(module, "ROOT", root)
    monkeypatch.setattr(module, "LOCAL_BIN", tmp_path / "bin")
    monkeypatch.setattr(module, "USER_SKILLS", tmp_path / "home" / ".claude" / "skills", raising=False)
    monkeypatch.setattr(module, "step", step)
    monkeypatch.setattr(module, "uv_path", lambda: Path("/opt/bin/uv"))
    monkeypatch.setattr(module, "install_plugins", lambda log: [])
    monkeypatch.setattr(module, "_ensure_module", lambda: SimpleNamespace(data_dir=lambda: tmp_path / "data"))
    monkeypatch.setattr(module.shutil, "which", lambda name, *args, **kwargs: rec.tools.get(name))
    monkeypatch.setattr(module, "hooks_path", lambda: rec.hooks, raising=False)
    monkeypatch.setattr(module, "git_top", lambda: rec.top, raising=False)
    monkeypatch.setattr(module, "PLATFORM", "linux", raising=False)
    return module, rec


def test_a_fresh_checkout_gets_just_its_hooks_and_its_sandbox_then_its_first_graph(boot):
    module, rec = boot

    assert module.setup(io.StringIO()) == []

    names = ["workspace", "just", "hooks", "code-intel", "sandbox", "graph", "graphify-skill"]
    assert [name for name, _ in rec.calls] == names
    commands = dict(rec.calls)
    assert commands["just"] == ["/opt/bin/uv", "tool", "install", "rust-just==1.58.0"]
    assert commands["hooks"] == ["git", "-C", str(rec.root), "config", "--local", "core.hooksPath", ".githooks"]
    assert commands["sandbox"] == [sys.executable, str(rec.root / "ops" / "machine-setup.py"), "--auto"]
    assert commands["graph"] == ["bash", str(rec.root / "ops" / "graph.sh")]
    assert commands["graphify-skill"] == ["/opt/bin/graphify", "install", "--platform", "claude"]
    texts = ("rust-just", "core.hooksPath", "machine-setup.py --auto", "sandbox-exec", "ops/graph.sh")
    for text in (*texts, "graphify install --platform claude", "~/.claude/skills/running-specagent-pipelines"):
        assert text in module.__doc__, text


def test_a_checkout_that_is_set_up_installs_neither_again(boot, tmp_path):
    module, rec = boot
    (rec.root / "wiki" / "graph").mkdir(parents=True)
    (rec.root / "wiki" / "graph" / "index.md").write_text("# Code graph\n", encoding="utf-8")
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "just").write_text("", encoding="utf-8")
    (tmp_path / "home" / ".claude" / "skills" / "graphify").mkdir(parents=True)
    (tmp_path / "home" / ".claude" / "skills" / "graphify" / "SKILL.md").write_text("# graphify\n", encoding="utf-8")
    rec.hooks = ".githooks"

    assert module.just_path() == tmp_path / "bin" / "just"
    assert module.setup(io.StringIO()) == []
    assert [name for name, _ in rec.calls] == ["workspace", "code-intel", "sandbox"]
    rec.tools["just"] = "/usr/local/bin/just"
    assert module.just_path() == Path("/usr/local/bin/just")


def test_a_failed_sandbox_or_graph_is_reported_and_a_failed_just_or_hooks_step_is_not(boot):
    module, rec = boot
    rec.fail = {"just", "hooks", "sandbox", "graph"}

    assert module.setup(io.StringIO()) == ["sandbox", "graph"]


def test_without_graphify_the_graph_is_a_log_line_not_a_failure(boot):
    module, rec = boot
    del rec.tools["graphify"]
    log = io.StringIO()

    assert module.setup(log) == []

    assert "graph" not in [name for name, _ in rec.calls]
    assert "graph: graphify is not installed" in log.getvalue()


def test_on_macos_the_seatbelt_is_checked_and_a_hooks_folder_of_the_checkout_is_kept(boot):
    module, rec = boot
    module.PLATFORM = "darwin"
    rec.hooks = ".husky/_"
    rec.tools["sandbox-exec"] = "/usr/bin/sandbox-exec"
    log = io.StringIO()

    assert module.setup(log) == []

    assert [name for name, _ in rec.calls] == ["workspace", "just", "code-intel", "graph", "graphify-skill"]
    assert "hooks: core.hooksPath is .husky/_, kept" in log.getvalue()
    del rec.tools["sandbox-exec"]
    assert module.setup(io.StringIO()) == ["sandbox"]


def test_a_checkout_that_does_not_enable_the_sandbox_sets_none_up(boot):
    module, rec = boot
    rec.fail = {"sandbox"}
    (rec.root / ".claude" / "settings.json").write_text('{"sandbox": {"enabled": false}}', encoding="utf-8")
    log = io.StringIO()

    assert module.setup(log) == []

    assert "sandbox" not in [name for name, _ in rec.calls]
    assert "sandbox: .claude/settings.json does not enable it" in log.getvalue()
    (rec.root / ".claude" / "settings.json").unlink()
    assert module.setup(io.StringIO()) == []


def test_a_folder_that_is_not_the_top_of_a_repository_gets_no_hooks_path(boot):
    module, rec = boot
    for top in (rec.root.parent, None):  # a project inside another checkout; a project before its `git init`
        rec.top, rec.calls, log = top, [], io.StringIO()

        assert module.setup(log) == []

        assert "hooks" not in [name for name, _ in rec.calls]
        assert f"hooks: {rec.root} is not the top of a git repository yet" in log.getvalue()


def test_graphifys_skill_is_installed_only_where_graphify_is_and_its_skill_is_not(boot, tmp_path):
    module, rec = boot
    skill = tmp_path / "home" / ".claude" / "skills" / "graphify"
    skill.mkdir(parents=True)  # a folder without SKILL.md is no skill

    assert module.setup(io.StringIO()) == []
    assert dict(rec.calls)["graphify-skill"] == ["/opt/bin/graphify", "install", "--platform", "claude"]

    (skill / "SKILL.md").write_text("# graphify\n", encoding="utf-8")
    rec.calls = []
    assert module.setup(io.StringIO()) == []
    assert "graphify-skill" not in [name for name, _ in rec.calls]

    (skill / "SKILL.md").unlink()
    del rec.tools["graphify"]
    rec.calls = []
    assert module.setup(io.StringIO()) == []
    assert "graphify-skill" not in [name for name, _ in rec.calls]


def test_a_failed_graphify_skill_install_is_not_a_failed_setup(boot):
    module, rec = boot
    rec.fail = {"graphify-skill"}

    assert module.setup(io.StringIO()) == []
    assert "graphify-skill" in [name for name, _ in rec.calls]


def test_the_user_level_pipeline_skill_becomes_a_link_to_the_checkouts_once(boot, tmp_path):
    module, rec = boot
    source = rec.root / ".claude" / "skills" / "running-specagent-pipelines"
    source.mkdir(parents=True)
    (source / "SKILL.md").write_text("---\nname: running-specagent-pipelines\n---\n", encoding="utf-8")
    link = tmp_path / "home" / ".claude" / "skills" / "running-specagent-pipelines"
    log = io.StringIO()

    assert module.setup(log) == []

    assert link.is_symlink() and os.readlink(link) == str(source)
    assert (link / "SKILL.md").read_text(encoding="utf-8") == "---\nname: running-specagent-pipelines\n---\n"
    assert f"skill: {link} -> {source}\n" in log.getvalue()
    again = io.StringIO()
    assert module.setup(again) == []
    assert os.readlink(link) == str(source) and f"skill: {link}" not in again.getvalue()


def test_an_existing_link_or_copy_of_the_pipeline_skill_is_kept_and_a_checkout_without_it_links_nothing(boot, tmp_path):
    module, rec = boot
    link = tmp_path / "home" / ".claude" / "skills" / "running-specagent-pipelines"
    module.link_user_skill(io.StringIO())
    assert not link.exists() and not link.is_symlink()
    source = rec.root / ".claude" / "skills" / "running-specagent-pipelines"
    source.mkdir(parents=True)
    link.parent.mkdir(parents=True)
    elsewhere, gone = tmp_path / "template-skill", tmp_path / "gone"
    elsewhere.mkdir()
    dangling = f"skill: {link} -> {gone} is dangling, kept; ln -sfn {source} {link} makes it the link\n"
    for target, said in ((elsewhere, ""), (gone, dangling)):  # a live link stays quiet, a dangling one is named
        link.symlink_to(target, target_is_directory=True)
        out = io.StringIO()
        module.link_user_skill(out)
        assert link.is_symlink() and os.readlink(link) == str(target) and out.getvalue() == said
        link.unlink()
    link.mkdir()
    (link / "mine.md").write_text("kept\n", encoding="utf-8")
    log = io.StringIO()

    module.link_user_skill(log)

    assert not link.is_symlink() and (link / "mine.md").read_text(encoding="utf-8") == "kept\n"
    assert f"skill: {link} is a copy, kept;" in log.getvalue() and f"ln -s {source} {link}" in log.getvalue()


def test_the_projects_page_and_new_project_name_every_step_of_the_bootstrap() -> None:
    """Task 11 (lesson 00:42): the texts that say what `ops/bootstrap.py` sets up name all eleven of its steps, each as
    whole words: in `docs/template/PROJECTS.md` and in the docstring of `ops/new-project.py`, read without backticks, the
    span from `ops/bootstrap.py:` to the first `--no-setup` after it."""
    steps = ("uv", "the workspace", "just", "the git hooks", "the plugins", "the language servers", "the sandbox",
             "the first code graph", "graphify's skill", "the user-level pipeline skill", "harness doctor")  # fmt: skip
    texts = {
        "PROJECTS": (REPO / "docs" / "template" / "PROJECTS.md").read_text(encoding="utf-8"),
        "new-project": ast.get_docstring(ast.parse((REPO / "ops" / "new-project.py").read_text(encoding="utf-8"))),
    }
    flat = {name: " ".join(text.replace("`", "").split()) for name, text in texts.items()}
    assert {name: text.count("ops/bootstrap.py:") for name, text in flat.items()} == {"PROJECTS": 1, "new-project": 1}
    spans = {name: text.split("ops/bootstrap.py:", 1)[1].split("--no-setup", 1)[0] for name, text in flat.items()}
    missing = {name: [s for s in steps if not re.search(rf"\b{re.escape(s)}\b", span)] for name, span in spans.items()}
    assert missing == {"PROJECTS": [], "new-project": []}
