#!/usr/bin/env python3
"""Move a checkout onto the claude-obsidian plugin (owner, 2026-10-30): the checkout is the plugin's vault, `wiki/` its
pages (wiki/decisions/the-checkout-is-a-claude-obsidian-vault.md).
  ops/adopt-obsidian.py [--apply] [--root PATH]   declare, install, adopt, ignore, check; without --apply a dry run
  ops/adopt-obsidian.py cli [--dir]                print the installed plugin's CLI (or its directory)
  ops/adopt-obsidian.py lint | doctor              run the plugin's check on this checkout
Steps, each skipped when it is done: 1. declare: the plugin in plugins/.claude-plugin/marketplace.json (a github
source, so `ops/bootstrap.py` installs the latest version from git) and in .claude/settings.json (enabledPlugins, and
CLAUDE_OBSIDIAN_SESSION_CONTEXT=1, so every session starts with wiki/hot.md); docs/roles/extensions.yaml and
need-to-know.yaml are reviewed by hand, `harness validate` compares them. 2. install: bootstrap's install_plugins, project
scope, never the user scope. 3. adopt: the plugin's dry run, then the same plan applied with its hash
(.claude-obsidian.json, .obsidian/, .raw/, inbox/, wiki/hot.md, wiki/overview.md, wiki/meta/ledgers/). 4. ignore:
.gitignore keeps the shared Obsidian settings and leaves the transaction journal local; the old vault at wiki/.obsidian
goes. 5. check: the plugin's lint and doctor."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN = "obsidian-vault"  # the marketplace entry: a third party's name may not start with "claude-"
UPSTREAM = "claude-obsidian"  # the plugin's own name and repository
REPO = "AgriciDaniel/claude-obsidian"
ENTRY = {
    "name": PLUGIN,
    "source": {"source": "github", "repo": REPO},
    "description": "Source-cited Obsidian vault: adoption, journaled writes, lint, retrieval and provenance ledgers for wiki/",
    "category": "knowledge",
    "tags": ["obsidian", "wiki", "knowledge-base"],
}
CONTEXT_ENV = "CLAUDE_OBSIDIAN_SESSION_CONTEXT"
IGNORE = """# ── Obsidian (the checkout is the claude-obsidian vault, wiki/ its pages): only the shared settings are committed;
# workspace*.json, the rest of .obsidian/ and the plugin's transaction journal stay local
.obsidian/*
!.obsidian/app.json
!.obsidian/appearance.json
!.obsidian/core-plugins.json
!.obsidian/graph.json
!.obsidian/snippets/
.vault-meta/transactions/
"""
OLD_HEAD = "# ── Obsidian (wiki/ is the vault)"
ADOPTED = ".claude-obsidian.json"
LINT_TOLERATED = {
    "hidden_target_links",
    "empty_sections",
}  # links from pages to code files; a heading a later entry fills


def config_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def market_name(root: Path) -> str:
    return json.loads((root / "plugins" / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))["name"]


def plugin_dir(root: Path | None = None) -> Path | None:
    """The installed plugin's directory: the newest version in Claude Code's cache, the checkout's marketplace first,
    else a marketplace clone that is the plugin itself. None when it is not installed on this machine."""
    cache = config_dir() / "plugins" / "cache"
    markets = []
    if root is not None and (root / "plugins" / ".claude-plugin" / "marketplace.json").is_file():
        markets.append(market_name(root))
    if cache.is_dir():
        markets += sorted(p.name for p in cache.iterdir() if p.is_dir() and p.name not in markets)
    for market in markets:
        for name in (PLUGIN, UPSTREAM):
            versions = sorted(
                p for p in (cache / market / name).glob("*") if (p / "scripts" / f"{UPSTREAM}.py").is_file()
            )
            if versions:
                return versions[-1]
    clones = config_dir() / "plugins" / "marketplaces"
    for p in sorted(clones.glob("*")) if clones.is_dir() else []:
        if (p / "scripts" / f"{UPSTREAM}.py").is_file():
            return p
    return None


def cli(root: Path | None = None) -> Path | None:
    d = plugin_dir(root)
    return d / "scripts" / f"{UPSTREAM}.py" if d else None


def run_cli(root: Path, *args: str) -> dict | str:
    tool = cli(root)
    if tool is None:
        raise SystemExit(
            f"{UPSTREAM} ({PLUGIN}) is not installed on this machine: python3 ops/bootstrap.py installs it"
        )
    done = subprocess.run([sys.executable, "-I", str(tool), *args], capture_output=True, text=True, check=False)
    out = done.stdout.strip() or done.stderr.strip()
    try:
        return json.loads(out)
    except ValueError:
        return out


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def declare(root: Path) -> list[str]:
    """The plugin in the marketplace and in the project settings. Returns what changed; nothing when it is declared."""
    changed = []
    market_path = root / "plugins" / ".claude-plugin" / "marketplace.json"
    market = json.loads(market_path.read_text(encoding="utf-8"))
    if not any(p.get("name") == PLUGIN for p in market.get("plugins", [])):
        market.setdefault("plugins", []).append(ENTRY)
        _write_json(market_path, market)
        changed.append(f"{market_path.relative_to(root)}: {PLUGIN} from github:{REPO}")
    settings_path = root / ".claude" / "settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    key = f"{PLUGIN}@{market['name']}"
    before = json.dumps(settings)
    settings.setdefault("enabledPlugins", {})[key] = True
    settings.setdefault("env", {})[CONTEXT_ENV] = "1"
    if json.dumps(settings) != before:
        _write_json(settings_path, settings)
        changed.append(f"{settings_path.relative_to(root)}: {key} enabled, {CONTEXT_ENV}=1")
    return changed


def install(root: Path) -> list[str]:
    """Bootstrap's plugin step for this checkout (project scope). Returns the keys that failed."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import bootstrap

    bootstrap.ROOT = root
    with tempfile.TemporaryFile("w+", encoding="utf-8") as log:
        failed = bootstrap.install_plugins(log)
        if failed:
            log.seek(0)
            sys.stderr.write(log.read()[-2000:])
    return failed


def adopt(root: Path, apply: bool) -> dict:
    """The plugin's adopt: a dry run, then (with apply) the reviewed plan applied with its hash."""
    if (root / ADOPTED).is_file():
        return {"skipped": f"{ADOPTED} exists"}
    plan = run_cli(root, "adopt", str(root))
    if not isinstance(plan, dict) or "approved_plan_sha256" not in plan:
        raise SystemExit(f"adopt dry run failed: {str(plan)[:500]}")
    if not apply:
        return {"would_write": plan.get("changed_paths", [])}
    done = run_cli(
        root,
        "adopt",
        str(root),
        "--apply",
        "--approved-plan-sha256",
        plan["approved_plan_sha256"],
        "--generated-at",
        plan["generated_at"],
        "--operation-id",
        plan["operation"]["operation_id"],
    )
    if not isinstance(done, dict) or not (root / ADOPTED).is_file():
        raise SystemExit(f"adopt apply failed: {str(done)[:500]}")
    return {"wrote": plan.get("changed_paths", []), "operation_id": plan["operation"]["operation_id"]}


def ignore(root: Path, apply: bool = True) -> bool:
    """The .gitignore lines of the vault; the old vault settings under wiki/.obsidian removed. True when it changed."""
    path = root / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    old_vault = root / "wiki" / ".obsidian"
    if ".vault-meta/transactions/" in text and not old_vault.exists():
        return False
    if apply:
        lines = text.splitlines()
        if ".vault-meta/transactions/" not in text:
            if OLD_HEAD in text:
                i = next(n for n, ln in enumerate(lines) if ln.startswith(OLD_HEAD))
                j = i + 1
                while j < len(lines) and ("wiki/.obsidian" in lines[j] or lines[j].startswith("#")):
                    j += 1
                lines[i:j] = IGNORE.rstrip("\n").splitlines()
            else:
                lines += [""] + IGNORE.rstrip("\n").splitlines()
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        if old_vault.exists():
            shutil.rmtree(old_vault)
    return True


def _summary(result: dict | str) -> str:
    if not isinstance(result, dict):
        return str(result)[:800]
    flat = {k: (f"{len(v)} items" if isinstance(v, (list, dict)) else v) for k, v in result.items()}
    return json.dumps(flat, ensure_ascii=False)


def check(root: Path) -> dict:
    return {
        "lint": run_cli(root, "lint", "--vault", str(root), "--format", "json"),
        "doctor": run_cli(root, "doctor", "--vault", str(root)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", nargs="?", default="adopt", choices=["adopt", "cli", "lint", "doctor"])
    parser.add_argument("--apply", action="store_true", help="write; without it the steps print what they would do")
    parser.add_argument("--dir", action="store_true", help="with cli: the plugin's directory instead of its script")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.command == "cli":
        found = plugin_dir(root) if args.dir else cli(root)
        print(found or "")
        return 0 if found else 1
    if args.command == "doctor":
        result = run_cli(root, "doctor", "--vault", str(root))
        print(_summary(result))
        return 0 if isinstance(result, dict) and result.get("ok") else 1
    if args.command == "lint":
        result = run_cli(root, "lint", "--vault", str(root), "--format", "json")
        if not isinstance(result, dict):
            print(result)
            return 1
        counts = result.get("summary", {}).get("category_counts", {})
        errors = {k: v for k, v in counts.items() if v and k not in LINT_TOLERATED}
        print(json.dumps(counts))
        for kind in errors:
            print(f"{kind}: {json.dumps(result.get(kind, [])[:5], ensure_ascii=False)[:600]}")
        return 1 if errors else 0
    print("1. declare:", "; ".join(declare(root)) if args.apply else "(dry run)")
    failed = install(root) if args.apply else []
    print("2. install:", "failed " + ", ".join(failed) if failed else "ok")
    print("3. adopt:", _summary(adopt(root, args.apply)))
    print("4. ignore:", "changed" if ignore(root, args.apply) else "done already")
    if args.apply and (root / ADOPTED).is_file():
        result = check(root)
        print("5. lint:", _summary(result["lint"]))
        print("   doctor:", _summary(result["doctor"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
