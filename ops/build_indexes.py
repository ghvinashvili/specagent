#!/usr/bin/env python3
"""Build the layered indexes of a folder of source material (the owner's rule of layered indexes and small parts,
2026-10-25). The folder, its README text and its categories come from a config file, ops/indexes.json by default.

Finding goes down short steps, each a small file: `<root>/README.md` (the categories) → `<root>/_index/<category>.md`
(one line per document, or the category's sub-groups when it has more than MAX entries) → a split file's own
`README.md` (from ops/split_large.py) → the part. A document is a file, or a folder that ops/split_large.py made from
one file. A file identical to one listed earlier is not listed again; the later folder's index names it in one line.
The descriptions come from the files themselves (frontmatter `description`, first heading, first line); the category
and sub-group texts are written by hand in the config. Run after ops/split_large.py; it rewrites only the files it owns,
none larger than CAP bytes: a list of more than MAX lines, or too long for one index, is cut into runs of its own.

Usage: python3 ops/build_indexes.py [--config PATH]   (from the repository root; the config's `root` is relative to it)
The config is JSON: `root` (the folder), `title` (the README's heading), `intro` (the paragraph under it) and
`categories`, a list of {slug, title, what, prefixes, groups (optional: a list of {slug, title, prefixes})}. A document
goes to the category whose prefix matches it longest; one that no prefix matches goes to the last category.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

MAX = 40
CAP = 12_000  # no index the script writes is larger than this, in bytes
SPLIT_MARK = "by ops/split_large.py from "
SPLIT_DAY = re.compile(r"split \d{4}-\d{2}-\d{2}")


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def strip_head(text):
    lines = text.splitlines()
    while lines and (lines[0].startswith("<!--") or not lines[0].strip()):
        lines.pop(0)
    return lines


def describe(p):
    if p.is_dir():
        first = (p / "README.md").read_text(encoding="utf-8").splitlines()[0].lstrip("# ")
        if ": the same text as " in first:
            return first.split(": ", 1)[1]
        m = re.match(r"(.*?) — index(?: of (\d+) parts|: (\d+) groups, (\d+) parts)", first)
        return f"{m.group(1)} ({m.group(2) or m.group(4)} parts)" if m else first
    if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}:
        return "image"
    try:
        lines = strip_head(p.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return ""
    if lines and lines[0].strip() == "---":
        fm = []
        for ln in lines[1:]:
            if ln.strip() == "---":
                break
            fm.append(ln)
        m = re.search(r"^description:\s*(.+?)(?=^\w[\w-]*:|\Z)", "\n".join(fm), re.MULTILINE | re.DOTALL)
        if m:
            return " ".join(m.group(1).split()).strip("\"'").replace('\\"', '"')[:180]
    head = next((ln.lstrip("# ").strip() for ln in lines if ln.startswith("#")), None) if p.suffix == ".md" else None
    text = next((ln.strip() for ln in lines if ln.strip() and not ln.startswith(("#", "---", "|", "```"))), "")
    out = f"{head}: {text}" if head and text and head != text else (head or text)
    return out[:180]


def documents(ctx):
    """Every document under the root: files, and the split folders as one document each (their parts not listed)."""
    split_dirs = set()
    for r in ctx.rglob("README.md"):
        t = r.read_text(encoding="utf-8", errors="replace")[:600]
        if SPLIT_MARK in t or SPLIT_DAY.search(t) and "ops/split_large.py" in t:
            split_dirs.add(r.parent)
    docs = list(split_dirs)
    for f in ctx.rglob("*"):
        if (
            f.is_file()
            and not any(d in f.parents for d in split_dirs)
            and f.parent != ctx / "_index"
            and f != ctx / "README.md"
            and f.name != "_skipped.md"
        ):
            docs.append(f)
    return sorted(docs, key=lambda p: p.as_posix())


def content_key(p):
    if p.is_dir():
        return None
    data = p.read_bytes()
    if data.startswith(b"<!-- collected"):
        data = data.split(b"\n", 1)[-1]
    return hashlib.sha256(data).hexdigest()


def best_match(rel, prefixes):
    return max((len(x) for x in prefixes if rel.startswith(x)), default=-1)


def line(doc, ctx, idx_dir):
    target = (doc / "README.md") if doc.is_dir() else doc
    link = (
        Path("..", target.relative_to(ctx)).as_posix()
        if idx_dir == ctx / "_index"
        else target.relative_to(ctx).as_posix()
    )
    kb = sum(f.stat().st_size for f in doc.rglob("*") if f.is_file()) if doc.is_dir() else doc.stat().st_size
    return f"- [{doc.name}{'/' if doc.is_dir() else ''}]({link}) — {describe(doc)} ({max(1, kb // 1024)} KB)"


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """The command line of the Usage line above."""
    ap = argparse.ArgumentParser(prog="build_indexes.py", description="Build the layered indexes of a folder.")
    ap.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parent / "indexes.json",
        help="the JSON config (default: indexes.json beside this script)",
    )
    return ap.parse_args(argv)


def load_config(path: Path) -> dict:
    """The config, each category as the tuple (slug, title, what, prefixes, [(slug, title, prefixes) per group])."""
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg["root"] = str(cfg["root"]).rstrip("/")
    cfg["categories"] = [
        (
            c["slug"],
            c["title"],
            c["what"],
            c["prefixes"],
            [(g["slug"], g["title"], g["prefixes"]) for g in c.get("groups", [])],
        )
        for c in cfg["categories"]
    ]
    return cfg


def place(docs: list[Path], ctx: Path, categories: list[tuple]) -> dict[str, list[Path]]:
    """Each document to the category whose prefix matches it longest; one that no prefix matches to the last."""
    placed = {c[0]: [] for c in categories}
    for d in docs:
        rel = d.relative_to(ctx).as_posix() + ("/" if d.is_dir() else "")
        best = max(categories, key=lambda c: best_match(rel, c[3]))
        if best_match(rel, best[3]) < 0:
            best = categories[-1]
        placed[best[0]].append(d)
    return placed


def runs(rows: list[str], head: int) -> list[tuple[int, int]]:
    """Cut rows into runs [a, b) of at most MAX lines, each within CAP bytes with head bytes above its lines."""
    out, a, used = [], 0, head
    for i, row in enumerate(rows):
        n = len(row.encode()) + 1
        if i > a and (i - a == MAX or used + n > CAP):
            out.append((a, i))
            a, used = i, head
        used += n
    out.append((a, len(rows)))
    return out


def write_index(idx: Path, gslug: str, gtitle: str, rows: list[str], dups: list[str], root: str) -> None:
    """Write <gslug>.md: one line per document, or links to runs of them when they pass MAX lines or CAP bytes."""
    body = f"# {gtitle}\n\n<!-- built by ops/build_indexes.py; do not edit by hand -->\n"
    tail = ""
    if dups:
        tail = (
            f"\nNot listed, identical to a copy listed earlier ({len(dups)}): "
            + "; ".join(x.split(" = ")[0].split("/")[-1] + " (= " + x.split(" = ")[1] + ")" for x in dups)
            + "\n"
        )
    plain = (
        f"Category index of `{root}/` ({len(rows)} documents). Open a document; a split one opens at its own "
        f"index.\n\n" + "\n".join(rows) + "\n"
    )
    if len(rows) > MAX or len((body + plain + tail).encode()) > CAP:  # one more layer: runs of MAX lines or CAP bytes
        n = len(rows)
        head = len(
            f"# {gtitle} › Documents {n}-{n}\n\n<!-- built by ops/build_indexes.py; do not edit by hand -->\n"
            f"{n} documents.\n\n".encode()
        )
        links = []
        for a, b in runs(rows, head):
            title = f"Documents {a + 1}-{b}"
            tname = f"{gslug}--{slugify(title)}.md"
            (idx / tname).write_text(
                f"# {gtitle} › {title}\n\n<!-- built by ops/build_indexes.py; do not "
                f"edit by hand -->\n{b - a} documents.\n\n" + "\n".join(rows[a:b]) + "\n",
                encoding="utf-8",
            )
            links.append(f"- [{title}]({tname}): {b - a} documents")
        body += f"{len(rows)} documents; pick a topic:\n\n" + "\n".join(links) + "\n"
    else:
        body += plain
    (idx / f"{gslug}.md").write_text(body + tail, encoding="utf-8")


def index_category(cat: tuple, items: list[Path], ctx: Path, seen: dict[str, str], root: str) -> int:
    """Write a category's index (its groups' too, when it has groups and more than MAX documents); return its count."""
    slug, title, what, _, subs = cat
    idx = ctx / "_index"
    groups = []
    if subs and len(items) > MAX:
        for sslug, stitle, sprefix in subs:
            g = [
                d
                for d in items
                if max(subs, key=lambda s: best_match(d.relative_to(ctx).as_posix() + "/", s[2]))[0] == sslug
            ]
            groups.append((f"{slug}--{sslug}", stitle, g))
    else:
        groups.append((slug, title, items))
    sub_rows = []
    for gslug, gtitle, g in groups:
        rows, dups = [], []
        for d in g:
            k = content_key(d)
            if k and k in seen:
                dups.append(f"{d.relative_to(ctx).as_posix()} = {seen[k]}")
                continue
            if k:
                seen[k] = d.relative_to(ctx).as_posix()
            rows.append(line(d, ctx, idx))
        write_index(idx, gslug, gtitle, rows, dups, root)
        sub_rows.append((gslug, gtitle, len(rows), len(dups)))
    if len(groups) > 1:
        body = f"# {title}\n\n<!-- built by ops/build_indexes.py; do not edit by hand -->\n{what[0].upper() + what[1:]}.\n\n"
        body += (
            "Pick a group:\n\n"
            + "\n".join(
                f"- [{t}]({s}.md): {n} documents" + (f", {k} identical copies not listed again" if k else "")
                for s, t, n, k in sub_rows
            )
            + "\n"
        )
        (idx / f"{slug}.md").write_text(body, encoding="utf-8")
    return sum(n for _, _, n, _ in sub_rows)


def main(argv: list[str] | None = None) -> int:
    """Build the README and the category indexes of the config's root folder."""
    a = parse_args(argv)
    try:
        cfg = load_config(a.config)
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"build_indexes.py: cannot read the config {a.config}: {e!r} (nothing written)", file=sys.stderr)
        return 2
    ctx = Path.cwd() / cfg["root"]
    if not ctx.is_dir():
        print(
            f"build_indexes.py: the config's root {cfg['root']}/ is not a folder here (nothing written)",
            file=sys.stderr,
        )
        return 2
    idx = ctx / "_index"
    idx.mkdir(exist_ok=True)
    for old in idx.glob("*.md"):
        old.unlink()
    docs = documents(ctx)
    placed = place(docs, ctx, cfg["categories"])
    seen, top_rows = {}, []
    for cat in cfg["categories"]:
        n = index_category(cat, placed[cat[0]], ctx, seen, cfg["root"])
        top_rows.append(f"| [{cat[1]}](_index/{cat[0]}.md) | {cat[2]} | {n} |")
    readme = (
        f"# {cfg['title']}\n\n{cfg['intro']}\n\n"
        "| Category | What is in it | Documents |\n|---|---|---|\n" + "\n".join(top_rows) + "\n"
    )
    (ctx / "README.md").write_text(readme, encoding="utf-8")
    print(f"{len(docs)} documents in {len(cfg['categories'])} categories; indexes: {len(list(idx.glob('*.md')))} files")
    for f in sorted(idx.glob("*.md")):
        print(f"  {f.name}: {f.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
