"""`harness wiki-lint`: the generated wiki stays navigable and traceable to its sources; decision pages, the 12 KB
limit and the plans link (ADR-0027). Reads files only."""

from __future__ import annotations

import datetime as dt
import os
import re
from pathlib import Path

import jsonschema
import yaml

from . import catalog, plans, state  # catalog.prose, plans.TASK_FILE, plans.count_lines, plans.MAX_TASK_LINES: Task 1

LINK = re.compile(r"\[[^\]]*\]\(([^)\s#]+\.md)(?:#[^)]*)?\)")
KINDS = {"concepts": "concept", "entities": "entity", "sources": "source", "decisions": "decision"}
MAX_LINES = 200  # a longer page holds more than one lesson; the number is this repository's choice
MAX_BYTES = 12_000  # a page or the index; 12 KB as the vault's ops/split_large.py counts (TARGET = 12_000)
PLANS_LINK = "../docs/exec-plans/active"  # wiki/plans: relative, so a project's copy shows that project's plans


def _frontmatter(text: str) -> dict | None:
    if not text.startswith("---"):
        return None
    fm = yaml.safe_load(text.split("---", 2)[1]) or {}
    return {
        k: (v.isoformat() if isinstance(v, dt.date) else v) for k, v in fm.items()
    }  # YAML reads a bare date as a date


def _pages(wiki: Path) -> dict[str, str]:
    """The pages: the .md files directly in wiki/<kind>/; a .summary.md summary is no page."""
    return {
        f"{sub}/{p.name}": p.read_text(encoding="utf-8")
        for sub in KINDS
        for p in sorted((wiki / sub).glob("*.md"))
        if not p.name.endswith(".summary.md")
    }


def _index(wiki: Path, indexed: set[str], pages: dict[str, str]) -> tuple[list[str], list[str]]:
    """The problems and warnings of wiki/index.md: its size, then each link target that is not a page."""
    problems: list[str] = []
    warnings: list[str] = []
    size = len((wiki / "index.md").read_bytes()) if (wiki / "index.md").is_file() else 0
    if size > MAX_BYTES:
        problems.append(f"index.md: {size} bytes; an index stays at most {MAX_BYTES}")
    for target in sorted(indexed - set(pages)):
        if target.split("/")[0] in KINDS:
            problems.append(f"index.md: {target} does not exist")
        elif target.startswith("graph/") and not (wiki / "graph").is_dir():
            warnings.append(f"index.md: {target} is not built (the graph recipe writes wiki/graph/)")
        elif not (wiki / target).exists():
            problems.append(f"index.md: {target} does not exist")
    return problems, warnings


def _links(wiki: Path, rel: str, text: str, fm: dict, inbound: dict[str, int]) -> list[str]:
    """Counts the page's links into inbound and returns the problems of the links that do not resolve."""
    problems: list[str] = []
    named = fm.get("sources", []) + fm.get("related", []) + ([fm["revised_by"]] if "revised_by" in fm else [])
    for target in named:
        if target in inbound:
            inbound[target] += 1
        else:
            problems.append(f"{rel}: {target} does not exist")
    for target in LINK.findall(catalog.prose(text)):
        resolved = (wiki / rel.split("/")[0] / target).resolve()
        if not resolved.exists():
            problems.append(f"{rel}: dead link {target}")
        elif wiki.resolve() in resolved.parents:
            key = resolved.relative_to(wiki.resolve()).as_posix()
            if key in inbound and key != rel:
                inbound[key] += 1
    return problems


def _check_pages(root: Path, pages: dict[str, str], indexed: set[str]) -> tuple[list[str], list[str], dict[str, int]]:
    """The checks of each page; returns the problems, the warnings and the inbound link count of every page."""
    wiki = root / "wiki"
    problems: list[str] = []
    warnings: list[str] = []
    schema, today = state.schema(root, "wiki-page"), dt.datetime.now(dt.UTC).date().isoformat()
    inbound = dict.fromkeys(pages, 0)
    for rel, text in pages.items():
        fm = _frontmatter(text)
        if fm is None:
            problems.append(f"{rel}: no frontmatter")
            continue
        try:
            jsonschema.validate(fm, schema)
        except jsonschema.ValidationError as exc:
            problems.append(f"{rel}: {exc.message[:160]}")
            continue
        sub = rel.split("/")[0]
        if fm["type"] != KINDS[sub]:
            problems.append(f"{rel}: type {fm['type']} does not belong in {sub}/")
        if rel not in indexed:
            problems.append(f"{rel}: not listed in index.md")
        problems += _links(wiki, rel, text, fm, inbound)
        problems += [f"{rel}: raw file {raw} does not exist" for raw in fm.get("raw", []) if not (root / raw).exists()]
        if fm.get("expires", "9999") < today:
            problems.append(f"{rel}: expired on {fm['expires']}")
        size = len((wiki / rel).read_bytes())
        if size > MAX_BYTES:
            problems.append(f"{rel}: {size} bytes; a page stays at most {MAX_BYTES}")
        if fm["status"] == "disputed":
            warnings.append(f"{rel}: disputed; needs a human decision")
        if len(text.splitlines()) > MAX_LINES:
            warnings.append(f"{rel}: {len(text.splitlines())} lines; split it")
    return problems, warnings, inbound


def _plans(wiki: Path) -> list[str]:
    """wiki/plans is the relative link PLANS_LINK, and a task file seen through it has at most 1,500 lines."""
    link = wiki / "plans"
    if not link.is_symlink() and not link.exists():
        return []
    if not link.is_symlink() or os.readlink(link).rstrip("/") != PLANS_LINK:
        return [f"plans: not a link to {PLANS_LINK}"]
    if not link.is_dir():
        return []  # a link without its target: the index line reports it
    problems = []
    for folder in sorted(p for p in link.iterdir() if p.is_dir() and not p.name.startswith(".")):
        for path in sorted(p for p in folder.iterdir() if p.is_file() and plans.TASK_FILE.fullmatch(p.name)):
            n = plans.count_lines(path.read_text(encoding="utf-8"))
            if n > plans.MAX_TASK_LINES:
                problems.append(f"plans/{folder.name}/{path.name}: {n} lines, more than {plans.MAX_TASK_LINES}")
    return problems


def lint(root: Path) -> dict:
    """`harness wiki-lint` (signature and result keys unchanged: ok, pages, problems, warnings)."""
    wiki = root / "wiki"
    pages = _pages(wiki)
    index = (wiki / "index.md").read_text(encoding="utf-8") if (wiki / "index.md").exists() else ""
    problems: list[str] = [] if index else ["index.md is missing or empty"]
    if not (wiki / "log.md").exists():
        problems.append("log.md is missing")
    indexed = set(LINK.findall(catalog.prose(index)))
    index_problems, warnings = _index(wiki, indexed, pages)
    page_problems, page_warnings, inbound = _check_pages(root, pages, indexed)
    problems += index_problems + page_problems
    problems += [
        f"{rel}: orphan (no page links to it)"
        for rel, n in inbound.items()
        if n == 0 and not rel.startswith(("sources/", "decisions/"))
    ]
    warnings += page_warnings
    warnings += [
        f"{rel}: source page no page cites" for rel, n in inbound.items() if n == 0 and rel.startswith("sources/")
    ]
    problems += _plans(wiki)
    return {"ok": not problems, "pages": len(pages), "problems": problems, "warnings": warnings}
