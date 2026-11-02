"""ops/adopt-obsidian.py (wiki/decisions/the-checkout-is-a-claude-obsidian-vault.md): declaring the plugin and the
ignore lines are idempotent on a copy of the checkout's files; the plugin's CLI is found in Claude Code's cache or not
at all; the lint tolerates only the categories the decision names."""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = ("plugins/.claude-plugin/marketplace.json", ".claude/settings.json", ".gitignore")


def load():
    spec = importlib.util.spec_from_file_location("adopt_obsidian", ROOT / "ops" / "adopt-obsidian.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checkout_without_the_plugin(tmp_path: Path, m) -> Path:
    for rel in FILES:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, tmp_path / rel)
    market_path = tmp_path / FILES[0]
    market = json.loads(market_path.read_text(encoding="utf-8"))
    market["plugins"] = [p for p in market["plugins"] if p["name"] != m.PLUGIN]
    market_path.write_text(json.dumps(market, indent=2) + "\n", encoding="utf-8")
    settings_path = tmp_path / FILES[1]
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    settings["enabledPlugins"].pop(f"{m.PLUGIN}@{market['name']}", None)
    settings["env"].pop(m.CONTEXT_ENV, None)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    ignore = tmp_path / ".gitignore"
    ignore.write_text(
        ignore.read_text(encoding="utf-8").replace(".vault-meta/transactions/\n", "")
        + f"{m.OLD_HEAD}\nwiki/.obsidian/*\n!wiki/.obsidian/app.json\n",
        encoding="utf-8",
    )
    (tmp_path / "wiki" / ".obsidian").mkdir(parents=True)
    (tmp_path / "wiki" / ".obsidian" / "app.json").write_text("{}\n", encoding="utf-8")
    return tmp_path


def test_declare_adds_the_plugin_once(tmp_path):
    m = load()
    root = checkout_without_the_plugin(tmp_path, m)
    assert m.declare(root) and not m.declare(root)
    market = json.loads((root / FILES[0]).read_text(encoding="utf-8"))
    entry = next(p for p in market["plugins"] if p["name"] == m.PLUGIN)
    assert entry["source"] == {"source": "url", "url": f"https://github.com/{m.REPO}.git"}  # HTTPS: no SSH key needed
    settings = json.loads((root / FILES[1]).read_text(encoding="utf-8"))
    assert settings["enabledPlugins"][f"{m.PLUGIN}@{market['name']}"] is True
    assert settings["env"][m.CONTEXT_ENV] == "1"


def test_declare_moves_a_github_source_to_https(tmp_path):
    """The macOS workflow: a `github` source is cloned as git@github.com and refused on a machine without an SSH key
    (`Permission denied (publickey)`); a checkout declared before keeps its entry, its source moved to HTTPS."""
    m = load()
    root = checkout_without_the_plugin(tmp_path, m)
    market_path = root / FILES[0]
    market = json.loads(market_path.read_text(encoding="utf-8"))
    market["plugins"].append({**m.ENTRY, "source": {"source": "github", "repo": m.REPO}})
    market_path.write_text(json.dumps(market), encoding="utf-8")
    assert any("not over SSH" in line for line in m.declare(root))
    entry = next(p for p in json.loads(market_path.read_text(encoding="utf-8"))["plugins"] if p["name"] == m.PLUGIN)
    assert entry["source"] == m.ENTRY["source"] and not any("marketplace" in line for line in m.declare(root))


def test_ignore_lines_replace_the_old_vault_once(tmp_path):
    m = load()
    root = checkout_without_the_plugin(tmp_path, m)
    assert m.ignore(root) and not m.ignore(root)
    text = (root / ".gitignore").read_text(encoding="utf-8")
    assert ".vault-meta/transactions/" in text and "!.obsidian/app.json" in text
    assert "wiki/.obsidian" not in text and not (root / "wiki" / ".obsidian").exists()


def test_the_checkout_declares_the_plugin_and_the_cli_is_a_file_or_none():
    m = load()
    assert not m.declare(ROOT), "the checkout itself declares the plugin already"
    found = m.cli(ROOT)
    assert found is None or found.is_file()
    assert m.LINT_TOLERATED == {"hidden_target_links", "empty_sections"}
