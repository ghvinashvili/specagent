"""Tests for harness/extensions.py. Run from packages/harness: `uv run pytest -q tests/test_extensions.py`."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from harness import access, extensions

DEFAULTS = {
    "dirs": ["stage"],
    "blind": False,
    "brief_drop": [],
    "cache_ttl": "5m",
    "plugins": [],
    "mcp_servers": [],
    "pack_files": [],
    "repo_deny": [],
    "project_plugins": ["conv@internal"],
}


def edit(path: Path, change) -> None:
    data = yaml.safe_load(path.read_text())
    change(data)
    path.write_text(yaml.safe_dump(data))


def make_repo(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "repo"
    plugin = root / "plugins" / "conv"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / "skills" / "commit-style").mkdir(parents=True)
    (plugin / "hooks").mkdir()
    (plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": "conv", "version": "0.1.0"}))
    (plugin / "skills" / "commit-style" / "SKILL.md").write_text("---\nname: commit-style\n---\n")
    (plugin / "hooks" / "hooks.json").write_text(json.dumps({"hooks": {"PreToolUse": []}}))
    (root / "plugins" / ".claude-plugin").mkdir()
    (root / "plugins" / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps({"name": "internal", "plugins": [{"name": "conv", "source": "./conv"}]})
    )
    (root / "docs" / "roles").mkdir(parents=True)
    (root / "docs" / "roles" / "need-to-know.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "defaults": DEFAULTS, "types": {"writer": {"may_receive": []}}})
    )
    brings = {
        "hooks": ["PreToolUse"],
        "skills": ["commit-style"],
        "agents": [],
        "commands": [],
        "mcp_servers": [],
        "lsp_servers": [],
    }
    (root / "docs" / "roles" / "extensions.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "extensions": {
                    "conv@internal": {
                        "form": "plugin",
                        "source": "./plugins/conv",
                        "version": "0.1.0",
                        "serves": "commit style",
                        "brings": brings,
                    }
                },
            }
        )
    )
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "config"))  # no plugin cache of the developer is read
    return root


def test_accepted_plugin_passes(tmp_path, monkeypatch):
    assert extensions.check(make_repo(tmp_path, monkeypatch)) == {
        "ok": True,
        "problems": [],
        "notes": [],
        "plugins": {
            "conv@internal": {
                "version": "0.1.0",
                "hooks": ["PreToolUse"],
                "skills": ["commit-style"],
                "agents": [],
                "commands": [],
                "mcp_servers": [],
                "lsp_servers": [],
                "channels": [],
                "monitors": [],
                "executables": [],
                "output_styles": [],
                "settings": [],
                "dependencies": [],
            }
        },
    }


def test_update_that_adds_a_hook_an_agent_or_a_server_fails(tmp_path, monkeypatch):
    root = make_repo(tmp_path, monkeypatch)
    plugin = root / "plugins" / "conv"
    (plugin / "hooks" / "hooks.json").write_text(json.dumps({"hooks": {"PreToolUse": [], "SessionStart": []}}))
    (plugin / "agents").mkdir()
    (plugin / "agents" / "reviewer.md").write_text("---\nname: reviewer\n---\n")
    (plugin / ".mcp.json").write_text(json.dumps({"mcpServers": {"search": {"command": "x"}}}))
    (plugin / "bin").mkdir()
    (plugin / "bin" / "tool").write_text("#!/bin/sh\n")
    (plugin / "monitors").mkdir()
    (plugin / "monitors" / "monitors.json").write_text(
        json.dumps([{"name": "log", "command": "tail -F x", "description": "d"}])
    )
    (plugin / ".claude-plugin" / "plugin.json").write_text(
        json.dumps(
            {
                "name": "conv",
                "version": "0.2.0",
                "settings": {"agent": "reviewer", "model": "x"},
                "dependencies": ["base", {"name": "lint"}],
            }
        )
    )
    out = extensions.check(root)
    assert not out["ok"]
    text = "\n".join(out["problems"])
    for expected in (
        "version 0.2.0 is installed, 0.1.0 was accepted",
        "hooks nobody accepted: SessionStart",
        "agents nobody accepted: reviewer",
        "mcp_servers nobody accepted: search",
        "executables nobody accepted: tool",
        "monitors nobody accepted: log",
        "settings nobody accepted: agent",
        "dependencies nobody accepted: base, lint",
    ):
        assert expected in text
    assert (
        len(out["notes"]) == 5
    )  # agents, MCP servers, monitors, settings, dependencies: what becomes of each in a role session


def test_plugin_must_be_in_both_files(tmp_path, monkeypatch):
    root = make_repo(tmp_path, monkeypatch)
    edit(
        root / "docs" / "roles" / "need-to-know.yaml",
        lambda d: d["defaults"]["project_plugins"].append("other@somewhere"),
    )
    out = extensions.check(root)
    assert out["problems"] == [
        "other@somewhere: named in docs/roles/need-to-know.yaml only; a project plugin is listed in both files"
    ]


def test_component_declared_in_the_marketplace_entry_counts(tmp_path, monkeypatch):
    root = make_repo(tmp_path, monkeypatch)
    market = root / "plugins" / ".claude-plugin" / "marketplace.json"
    market.write_text(
        json.dumps(
            {
                "name": "internal",
                "plugins": [
                    {"name": "conv", "source": "./conv", "lspServers": {"pyright": {"command": "pyright-langserver"}}}
                ],
            }
        )
    )
    assert extensions.check(root)["problems"] == ["conv@internal: brings lsp_servers nobody accepted: pyright"]


def test_plugin_that_is_not_installed_is_a_note(tmp_path, monkeypatch):
    root = make_repo(tmp_path, monkeypatch)
    edit(
        root / "docs" / "roles" / "extensions.yaml",
        lambda d: d["extensions"].update(
            {"ext@official": {"form": "plugin", "source": "official", "version": "1.0.0", "serves": "x"}}
        ),
    )
    edit(
        root / "docs" / "roles" / "need-to-know.yaml", lambda d: d["defaults"]["project_plugins"].append("ext@official")
    )
    out = extensions.check(root)
    assert out["ok"] and out["notes"] == ["ext@official: not installed on this machine; not compared"]


def test_mcp_server_is_registered_and_given_to_named_types_only(tmp_path, monkeypatch):
    root = make_repo(tmp_path, monkeypatch)
    (root / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"docs": {"command": "docs-server"}, "db": {"command": "db-server"}}})
    )
    edit(
        root / "docs" / "roles" / "extensions.yaml",
        lambda d: d["extensions"].update(
            {"docs": {"form": "mcp", "source": ".mcp.json", "version": "1.2.0", "serves": "library documentation"}}
        ),
    )
    edit(
        root / "docs" / "roles" / "need-to-know.yaml",
        lambda d: d["types"]["writer"].update({"mcp_servers": ["docs", "search"]}),
    )
    assert extensions.check(root)["problems"] == [
        "db: MCP server named in .mcp.json only; a server is listed in both files",
        "writer: mcp_servers names search, which .mcp.json does not define",
    ]
    edit(
        root / "docs" / "roles" / "need-to-know.yaml", lambda d: d["types"]["writer"].update({"mcp_servers": ["docs"]})
    )
    policy = access.load_policy(root)
    assert access.mcp_config(root, policy, {"role_type": "writer"}) == {
        "mcpServers": {"docs": {"command": "docs-server"}}
    }
    edit(root / "docs" / "roles" / "need-to-know.yaml", lambda d: d["types"]["writer"].update({"mcp_servers": []}))
    assert access.mcp_config(root, access.load_policy(root), {"role_type": "writer"}) is None


def test_every_form_is_recorded_with_source_version_and_purpose(tmp_path, monkeypatch):
    root = make_repo(tmp_path, monkeypatch)
    edit(
        root / "docs" / "roles" / "extensions.yaml",
        lambda d: d["extensions"].update(
            {
                "graph-tool": {
                    "form": "cli",
                    "source": "https://example.com/graph-tool",
                    "version": "2.1.0",
                    "serves": "code graph",
                },
                "router": {"form": "gateway", "source": "x", "version": "1", "serves": "y"},
                "notes": {"form": "skills", "source": "https://example.com/notes"},
            }
        ),
    )
    assert extensions.check(root)["problems"] == [
        "notes: `version` is missing",
        "notes: `serves` is missing",
        "router: form 'gateway' is not one of plugin, skills, mcp, cli, agent-cli, proxy, service",
    ]


def test_a_pre_approved_plugin_skill_exists_in_a_plugin_the_type_keeps(tmp_path, monkeypatch):
    root = make_repo(tmp_path, monkeypatch)
    policy = root / "docs" / "roles" / "need-to-know.yaml"
    edit(policy, lambda d: d["types"]["writer"].update(plugins=["conv@internal"], plugin_skills=["conv:commit-style"]))
    assert extensions.check(root)["ok"]
    edit(policy, lambda d: d["types"]["writer"].update(plugin_skills=["conv:no-such-skill"]))
    assert any("does not bring" in p for p in extensions.check(root)["problems"])
    edit(policy, lambda d: d["types"]["writer"].update(plugins=[], plugin_skills=["conv:commit-style"]))
    assert any("does not keep plugin conv" in p for p in extensions.check(root)["problems"])
