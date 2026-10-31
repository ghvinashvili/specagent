"""harness/extensions.py — what comes from outside the repository, compared with what a human accepted.

An extension is anything the flow uses that this repository did not write: a Claude Code plugin, a set of skills,
an MCP server, a command-line tool, another coding agent, a proxy in front of the API, a service. Its text and code
did not pass this repository's review, and an update can change what it does. docs/roles/extensions.yaml records
every extension with its form, source and version; for a plugin also the components a human accepted. `check`
reads what is installed and reports every difference; `harness validate` fails on one. Whether an extension is
good is not decided here; docs/roles/EXTENSIONS.md describes how that is decided.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

from . import access

ACCEPTED_PATH = "docs/roles/extensions.yaml"
# plugin and mcp are compared with what is installed; the other forms are recorded so that a human can find them.
FORMS = ("plugin", "skills", "mcp", "cli", "agent-cli", "proxy", "service")
# Every kind of component the plugin reference names, except colour themes, which change nothing a session does.
KINDS = (
    "hooks",
    "skills",
    "agents",
    "commands",
    "mcp_servers",
    "lsp_servers",
    "channels",
    "monitors",
    "executables",
    "output_styles",
    "settings",
    "dependencies",
)
# What happens to a component in a role session; printed as a note for the human who reviews the plugin.
ROLE_SESSION = {
    "agents": "cannot be started in a role session (the Agent tool is denied); to use one as a role type, copy its file into .claude/agents/ with the new-role-type skill",
    "commands": "are typed by a person; a role session has nobody to type them",
    "mcp_servers": "are not loaded in a role session (--strict-mcp-config)",
    "channels": "are not loaded in a role session (they are MCP servers)",
    "monitors": "do not start in a print stage (-p); in a background stage they run for the whole session and their output reaches the model",
    "output_styles": "are picked by a person; a role session keeps the default",
    "settings": "the plugin sets a default main agent; the launcher's --agent overrides it",
    "dependencies": "are enabled together with the plugin and need their own entry in this file",
}


def load(root: Path) -> dict:
    return yaml.safe_load((root / ACCEPTED_PATH).read_text(encoding="utf-8"))


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _config_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def locate(root: Path, key: str, version: str | None = None) -> tuple[Path | None, dict]:
    """The plugin's directory and its marketplace entry. An internal plugin lives in plugins/<name>; any other in
    Claude Code's plugin cache, one directory per version."""
    name, _, market = key.partition("@")
    if (root / "plugins" / name).is_dir():
        market_dir, plugin_dir = root / "plugins", root / "plugins" / name
    else:
        market_dir = _config_dir() / "plugins" / "marketplaces" / market
        base = _config_dir() / "plugins" / "cache" / market / name
        versions = sorted(p for p in base.iterdir() if p.is_dir()) if base.is_dir() else []
        plugin_dir = next((p for p in versions if p.name == version), versions[-1] if versions else None)
    entries = _json(market_dir / ".claude-plugin" / "marketplace.json").get("plugins", [])
    return plugin_dir, next((e for e in entries if e.get("name") == name), {})


def inventory(plugin_dir: Path, entry: dict | None = None) -> dict:
    """Everything the plugin adds to a session. A component can be declared in its own file, in plugin.json or in
    the marketplace entry, so all three are read."""
    entry = entry or {}
    manifest = _json(plugin_dir / ".claude-plugin" / "plugin.json")

    def declared(field: str, own: dict) -> list[str]:
        names = set(own)
        for src in (manifest, entry):
            if isinstance(src.get(field), dict):
                names |= set(src[field])
        return sorted(names)

    def names(value) -> list[str]:  # a manifest list of entries: strings, or objects with a name
        return sorted({v if isinstance(v, str) else str(v.get("name") or v.get("server")) for v in value or []})

    mcp = _json(plugin_dir / ".mcp.json")
    experimental = manifest.get("experimental") or {}
    monitors = experimental.get("monitors")
    if not isinstance(monitors, list):
        path = plugin_dir / (monitors or "monitors/monitors.json")
        monitors = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
    own_settings = _json(plugin_dir / "settings.json") or manifest.get("settings") or {}
    return {
        "version": str(manifest.get("version") or entry.get("version") or plugin_dir.name),
        "hooks": declared("hooks", _json(plugin_dir / "hooks" / "hooks.json").get("hooks", {})),
        "skills": sorted(p.parent.name for p in plugin_dir.glob("skills/*/SKILL.md")),
        "agents": sorted(p.stem for p in plugin_dir.glob("agents/*.md")),
        "commands": sorted(p.stem for p in plugin_dir.glob("commands/*.md")),
        "mcp_servers": declared("mcpServers", mcp.get("mcpServers", mcp)),
        "lsp_servers": declared("lspServers", _json(plugin_dir / ".lsp.json")),
        "channels": names(manifest.get("channels")),
        "monitors": names(monitors),
        "executables": sorted(p.name for p in plugin_dir.glob("bin/*") if p.is_file()),
        "output_styles": sorted(p.stem for p in plugin_dir.glob("output-styles/*.md")),
        "settings": sorted(
            k for k in own_settings if k in ("agent", "subagentStatusLine")
        ),  # every other key is dropped by Claude Code
        "dependencies": names(manifest.get("dependencies")),
    }


def inspect(plugin_dir: Path) -> dict:
    """What a plugin directory brings, before anything is admitted: for the human who compares and reviews it."""
    inv = inventory(plugin_dir)
    return {
        "ok": True,
        "plugin": str(plugin_dir),
        "brings": inv,
        "notes": [f"{kind} {ROLE_SESSION[kind]}" for kind in KINDS if inv[kind] and kind in ROLE_SESSION],
    }


def check(root: Path) -> dict:
    """Problems fail `harness validate`; notes are for the human who reviews an extension."""
    accepted = load(root)["extensions"]
    policy = access.load_policy(root)
    problems, notes, seen = [], [], {}
    for key, acc in sorted(accepted.items()):
        if acc.get("form") not in FORMS:
            problems.append(f"{key}: form {acc.get('form')!r} is not one of {', '.join(FORMS)}")
        problems += [f"{key}: `{field}` is missing" for field in ("source", "version", "serves") if not acc.get(field)]

    plugins = {k: v for k, v in accepted.items() if v.get("form") == "plugin"}
    listed = set(policy["defaults"]["project_plugins"])
    for key in sorted(listed ^ set(plugins)):
        where = "docs/roles/need-to-know.yaml" if key in listed else ACCEPTED_PATH
        problems.append(f"{key}: named in {where} only; a project plugin is listed in both files")
    for key, acc in sorted(plugins.items()):
        plugin_dir, entry = locate(root, key, str(acc.get("version")))
        if plugin_dir is None:
            notes.append(f"{key}: not installed on this machine; not compared")
            continue
        inv = seen[key] = inventory(plugin_dir, entry)
        if inv["version"] != str(acc.get("version")):
            problems.append(f"{key}: version {inv['version']} is installed, {acc.get('version')} was accepted")
        for kind in KINDS:
            now, then = set(inv[kind]), set((acc.get("brings") or {}).get(kind) or [])
            if now - then:
                problems.append(f"{key}: brings {kind} nobody accepted: {', '.join(sorted(now - then))}")
            if then - now:
                problems.append(f"{key}: accepted {kind} are gone: {', '.join(sorted(then - now))}")
        notes += [f"{key}: {kind} {ROLE_SESSION[kind]}" for kind in KINDS if inv[kind] and kind in ROLE_SESSION]

    for role_type in sorted(policy["types"]):  # a pre-approved plugin skill exists in a plugin the type keeps
        t = access.type_row(policy, role_type)
        kept = {key.split("@")[0]: key for key in t["plugins"]}
        for name in t["plugin_skills"]:
            plugin, _, skill = str(name).partition(":")
            if plugin not in kept:
                problems.append(f"{role_type}: plugin_skills names {name}, but the type does not keep plugin {plugin}")
            elif kept[plugin] in seen and skill not in seen[kept[plugin]]["skills"]:
                problems.append(f"{role_type}: plugin_skills names {name}, which {kept[plugin]} does not bring")

    servers = set(_json(root / ".mcp.json").get("mcpServers", {}))
    registered = {k for k, v in accepted.items() if v.get("form") == "mcp"}
    for name in sorted(servers ^ registered):
        where = ".mcp.json" if name in servers else ACCEPTED_PATH
        problems.append(f"{name}: MCP server named in {where} only; a server is listed in both files")
    for role_type in sorted(policy["types"]):
        unknown = set(access.type_row(policy, role_type)["mcp_servers"]) - servers
        if unknown:
            problems.append(
                f"{role_type}: mcp_servers names {', '.join(sorted(unknown))}, which .mcp.json does not define"
            )
    return {"ok": not problems, "problems": problems, "notes": notes, "plugins": seen}
