#!/usr/bin/env python3
"""The layered index of the code graph (spec A3): graphify's flat wiki export becomes one line per top folder or
package, one page per folder with one line per community, then the articles, and no page this writes passes 12,000
bytes.

    python3 ops/graph_index.py [WIKI_DIR]    from the repository root; WIKI_DIR is wiki/graph by default

WIKI_DIR holds graphify's flat export (`graphify export wiki`: index.md and one article per community and god node).
index.md becomes the layered index, the folder pages go to WIKI_DIR/_index/, an article over 12,000 bytes is split by
ops/split_large.py and keeps its name as a stub that links the parts, and every other article stays as graphify wrote
it. ops/graph.sh runs this once per fresh export, so an index.md that graphify did not write is refused.
"""

from __future__ import annotations

import argparse
import posixpath
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

LIMIT = 12_000  # bytes (UTF-8) of any page this script writes, about 3k tokens
MARK = "<!-- built by ops/graph_index.py; do not edit by hand -->"
FLAT = "# Knowledge Graph Index"  # line 1 of graphify's flat index
MANIFESTS = ("pyproject.toml", "package.json", "Cargo.toml", "go.mod", "CMakeLists.txt", ".claude-plugin/plugin.json")
COMMUNITY = re.compile(r"> (\d+) nodes(?: · cohesion \S+)?")
GOD = re.compile(r"> God node · (\d+) connections · `([^`]*)`")
CONCEPT = re.compile(r"- \*\*.*\*\* \(\d+ connections\)(?: — `([^`]*)`)?")
LOCAL = re.compile(r"\]\(([^)/\s]+\.md)\)")  # a link to a page in the same folder


@dataclass
class Article:
    """A community or god-node article of the flat export."""

    name: str  # its file name in WIKI_DIR
    label: str  # line 1 without "# "
    kind: str  # line 3: "> <n> nodes ..." or "> God node · ..."
    count: int  # a community's nodes, a god node's connections
    god: bool
    sources: list[str]  # a community's Key Concepts paths; a god node's one source, maybe empty
    size: int  # bytes


def parse(name: str, text: str) -> Article | None:
    """An article's label, kind and sources (G2, G3); None for a page that is neither a community nor a god node."""
    lines = text.split("\n")
    if len(lines) < 3 or not lines[0].startswith("# "):
        return None
    size = len(text.encode("utf-8"))
    if god := GOD.fullmatch(lines[2]):
        return Article(name, lines[0][2:], lines[2], int(god.group(1)), True, [god.group(2)], size)
    if nodes := COMMUNITY.fullmatch(lines[2]):
        return Article(name, lines[0][2:], lines[2], int(nodes.group(1)), False, concepts(lines), size)
    return None


def concepts(lines: list[str]) -> list[str]:
    """The backticked path at the end of each `## Key Concepts` line, in order; a line without one adds none (G3)."""
    paths, inside = [], False
    for line in lines:
        if line.startswith("## "):
            inside = line == "## Key Concepts"
        elif inside and (found := CONCEPT.fullmatch(line)) and found.group(1):
            paths.append(found.group(1))
    return paths


def read(wiki: Path) -> list[Article]:
    """Every article directly in WIKI_DIR but index.md, by name; any other page is named on stderr and left (G2)."""
    articles = []
    for path in sorted(p for p in wiki.glob("*.md") if p.is_file() and p.name != "index.md"):
        article = parse(path.name, path.read_text(encoding="utf-8"))
        if article is None:
            print(f"graph_index: skipped {path.name}: not a community or god-node article", file=sys.stderr)
        else:
            articles.append(article)
    return articles


def group_of(path: str) -> str:
    """(root) for a file at the root, <p0>/<p1> for a package folder that holds a manifest, otherwise <p0> (G4)."""
    parts = path.split("/")
    if len(parts) == 1:
        return "(root)"
    if len(parts) >= 3 and any(Path(parts[0], parts[1], manifest).is_file() for manifest in MANIFESTS):
        return f"{parts[0]}/{parts[1]}"
    return parts[0]


def most(items: list[str]) -> str:
    """The most frequent item; a tie goes to the first by name."""
    counts = Counter(items)
    return min(counts, key=lambda item: (-counts[item], item))


def folder_of(community: Article) -> str:
    """The folder most of a community's sources are in, `.` for the root; without sources, no source file (G4)."""
    if not community.sources:
        return "no source file"
    return f"`{most([posixpath.dirname(path) or '.' for path in community.sources])}`"


def layer(communities: list[Article]) -> dict[str, list[Article]]:
    """Each community under the most frequent group of its sources (G4), by node count, then label."""
    groups: dict[str, list[Article]] = {}
    for community in communities:
        group = most([group_of(path) for path in community.sources]) if community.sources else "(no source file)"
        groups.setdefault(group, []).append(community)
    for members in groups.values():
        members.sort(key=lambda member: (-member.count, member.label))
    return groups


def slugs(order: list[str]) -> dict[str, str]:
    """Each group's page name in the order of the folder list: a run outside [A-Za-z0-9_-] becomes `-`, the ends are
    stripped, lower case; `index` is reserved and a name already taken gets -2, -3, ... (G5)."""
    taken, names = {"index"}, {}
    for group in order:
        base = re.sub(r"[^A-Za-z0-9_-]+", "-", group).strip("-").lower() or "group"
        name, n = base, 2
        while name in taken:
            name, n = f"{base}-{n}", n + 1
        taken.add(name)
        names[group] = name
    return names


def esc(label: str) -> str:
    """A label as link text: `[` and `]` escaped with a backslash, as graphify does (G6)."""
    return label.replace("[", r"\[").replace("]", r"\]")


def page(lines: list[str]) -> str:
    """A page's text: every line ends with a newline (G6)."""
    return "".join(line + "\n" for line in lines)


def fits(lines: list[str]) -> bool:
    """The page of these lines is at most LIMIT bytes."""
    return len(page(lines).encode("utf-8")) <= LIMIT


def chunks(lines: list[str], heading: Callable[[int, int], str]) -> list[list[str]]:
    """The lines in order, in parts that stay within LIMIT bytes under heading(k, m), the marker and a blank line; a
    line longer than that is a part of its own (G6, G7)."""
    total = 1
    while True:
        parts: list[list[str]] = []
        used = LIMIT + 1
        for line in lines:
            need = len(line.encode("utf-8")) + 1
            if used + need > LIMIT:
                parts.append([])
                used = len(page([heading(len(parts), total), MARK, ""]).encode("utf-8"))
            parts[-1].append(line)
            used += need
        if len(parts) <= total:
            return parts
        total = len(parts)


def write_parts(index_dir: Path, stem: str, lines: list[str], title: str) -> list[list[str]]:
    """The lines in `_index/<stem>.<k>.md`, headed `# <title> — part <k> of <m>`; returns the parts (G7, G8)."""
    parts = chunks(lines, lambda k, m: f"# {title} — part {k} of {m}")
    for k, part in enumerate(parts, 1):
        text = page([f"# {title} — part {k} of {len(parts)}", MARK, "", *part])
        (index_dir / f"{stem}.{k}.md").write_text(text, encoding="utf-8")
    return parts


def write_group(index_dir: Path, group: str, slug: str, members: list[Article]) -> None:
    """_index/<slug>.md: one line per community, or, when that passes LIMIT, the parts that hold the lines (G7)."""
    lines = [f"- [{esc(c.label)}](../{c.name}) — {c.count} nodes · {folder_of(c)}" for c in members]
    head = [f"# {group} — {len(members)} communities, {sum(c.count for c in members)} nodes", MARK, ""]
    if not fits(head + lines):
        parts = write_parts(index_dir, slug, lines, group)
        lines = [f"- [part {k} of {len(parts)}]({slug}.{k}.md) — {len(p)} communities" for k, p in enumerate(parts, 1)]
    (index_dir / f"{slug}.md").write_text(page(head + lines), encoding="utf-8")


def folder_lines(order: list[str], groups: dict[str, list[Article]], names: dict[str, str], prefix: str) -> list[str]:
    """One line per folder, its page linked through prefix (`_index/` from index.md, none from a part)."""
    return [
        f"- [{esc(g)}]({prefix}{names[g]}.md) — {len(groups[g])} communities, {sum(c.count for c in groups[g])} nodes"
        for g in order
    ]


def god_line(god: Article) -> str:
    """A god node's line in the index: its degree, and its source when it has one (G8)."""
    source = f" · `{god.sources[0]}`" if god.sources[0] else ""
    return f"- [{esc(god.label)}]({god.name}) — {god.count} connections{source}"


def write_index(wiki: Path, order: list[str], groups: dict[str, list[Article]], gods: list[Article]) -> None:
    """WIKI_DIR/index.md: the folders by node count, then the most connected nodes; when that passes LIMIT, the
    folder lines go to _index/index.<k>.md and the index lists those parts (G8)."""
    names = slugs(order)
    for group in order:
        write_group(wiki / "_index", group, names[group], groups[group])
    communities = sum(len(members) for members in groups.values())
    nodes = sum(c.count for members in groups.values() for c in members)
    head = [
        "# Code graph",
        MARK,
        "",
        (
            f"{communities} communities, {nodes} nodes in {len(order)} folders, from graphify's wiki export (`bash "
            'ops/graph.sh`). Agents ask `graphify query "<question>" --budget 1500` first; here, open one folder, '
            "then one article."
        ),
        "",
        "## Folders",
        "",
    ]
    lines = folder_lines(order, groups, names, "_index/")
    tail = ["", "## Most connected nodes", "", *map(god_line, gods)] if gods else []
    if not fits(head + lines + tail):
        parts = write_parts(wiki / "_index", "index", folder_lines(order, groups, names, ""), "Folders")
        n = len(parts)
        lines = [
            f"- [folders, part {k} of {n}](_index/index.{k}.md) — {len(p)} folders" for k, p in enumerate(parts, 1)
        ]
    (wiki / "index.md").write_text(page(head + lines + tail), encoding="utf-8")


def split(wiki: Path, big: list[Article]) -> bool:
    """Articles over LIMIT bytes, split by ops/split_large.py in one call; the links in their parts point one folder
    up, and a stub under the old name links the parts' index (G9). False when split_large.py fails."""
    script = Path(__file__).resolve().parent / "split_large.py"
    cmd = [sys.executable, "-I", str(script), "--limit", str(LIMIT), *(str(wiki / a.name) for a in big)]
    done = subprocess.run(cmd, capture_output=True, text=True, check=False)
    print(done.stdout, end="")
    if done.returncode:
        print(done.stderr, end="", file=sys.stderr)
        return False
    for article in big:
        stem = article.name.removesuffix(".md")
        for part in sorted((wiki / stem).glob("*.md")):
            if part.name != "README.md" and not part.name.startswith("_group-"):
                part.write_text(LOCAL.sub(r"](../\1)", part.read_text(encoding="utf-8")), encoding="utf-8")
        link = f"[{stem}/README.md]({stem}/README.md)"
        stub = [f"# {article.label}", MARK, article.kind, "", f"Split into parts of at most 12,000 bytes: {link}"]
        (wiki / article.name).write_text(page(stub), encoding="utf-8")
    return True


def main(argv: list[str]) -> int:
    """Check the export, read every article, write the folder pages and the index, then split the large articles."""
    ap = argparse.ArgumentParser(description="The layered index of graphify's flat wiki export (spec A3).")
    ap.add_argument("wiki", nargs="?", default="wiki/graph", help="graphify's flat export (default: wiki/graph)")
    wiki = Path(ap.parse_args(argv).wiki)
    flat = wiki / "index.md"
    first = ""
    if flat.is_file():
        with open(flat, encoding="utf-8", errors="replace") as fh:
            first = fh.readline().rstrip("\n")
    if first != FLAT:
        print(f"graph_index: {flat} is not graphify's flat index; run bash ops/graph.sh", file=sys.stderr)
        return 2
    articles = read(wiki)
    communities = [a for a in articles if not a.god]
    gods = sorted((a for a in articles if a.god), key=lambda a: (-a.count, a.label))
    groups = layer(communities)
    order = sorted(groups, key=lambda g: (-sum(c.count for c in groups[g]), g))
    (wiki / "_index").mkdir(exist_ok=True)
    write_index(wiki, order, groups, gods)
    big = [a for a in articles if a.size > LIMIT]
    if big and not split(wiki, big):
        return 1
    nodes = sum(c.count for c in communities)
    print(
        f"{flat}: {len(communities)} communities, {nodes} nodes, {len(order)} folders, "
        f"{len(gods)} most connected nodes, {len(big)} split"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
