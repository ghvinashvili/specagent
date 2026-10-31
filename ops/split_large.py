#!/usr/bin/env python3
"""Split every large text file it is given into titled parts with an index (owner, 2026-10-25: "split it part by
part, by topic, titled so it is easy to find and an agent need not read the whole file").

A Markdown file is cut at its own headings (never inside a code fence): a section that fits stays whole, a larger one
is cut at its sub-headings, and small neighbouring sections are joined up to TARGET bytes without crossing a heading
of a higher level. Text without headings (notes, .txt) is cut at blank lines. `X.md` becomes the folder `X/` with
`README.md` (the index: every part, its original line range, the headings above it and the headings in it) and the
parts `NN-<first heading>.md`; each part's first line names the file and line range it came from. A file identical to
one already split gets only a README pointing there. The original stays in git history. An index, too, stays within
TARGET bytes: its rows list fewer headings and count the rest (STEPS), and a file whose flat index passes TARGET even
so is grouped as one of more than GROUP parts is. A group's index or a grouped README that still passes it gets brief
lines: a part linked by its number, a group by 20 characters of its label, other text cut to 20 characters, headings
only counted; two layers of brief lines hold about 3,000 parts.

Usage: python3 ops/split_large.py [--dry-run] [--limit BYTES] [--relink PATH]... PATH [PATH ...]
  (run from the repository root, each PATH relative to it; idempotent: split files no longer exist)
A PATH is a file or a folder (its .md and .txt files); a file larger than --limit bytes (default LIMIT) is split, and
each part, its header and title lines included, is at most TARGET bytes. --relink PATH rewrites, in the .md files under
PATH, each split file's path from the root to its index. --dry-run prints the same lines and writes nothing.
"""

import argparse
import hashlib
import itertools
import re
import sys
import time
from pathlib import Path

LIMIT = 24_000  # files larger than this are split (about 6k tokens)
TARGET = 12_000  # no part larger than this (about 3k tokens), its header included, except one line longer than it
MIN = 2_000  # a smaller part joins its neighbour
GROUP = 25  # a file index with more parts than this is layered: groups first, then a small index per group
STEPS = (25, 12, 6, 3, 1, 0)  # the most headings an index row lists, fewer while the index would pass TARGET
Row = tuple[str, list[str], str, str]  # an index row: start, texts, text when none is listed, brief line
EXTS = {".md", ".txt"}
DAY = time.strftime("%Y-%m-%d")  # the day of the run
HEAD = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")


def headings(lines):
    out, fence = [], None
    for i, ln in enumerate(lines):
        m = FENCE.match(ln)
        if m:
            fence = None if fence == m.group(1) else (fence or m.group(1))
            continue
        if fence is None:
            h = HEAD.match(ln)
            if h:
                out.append((i, len(h.group(1)), h.group(2).strip()))
    return out


def blank_breaks(lines, lo, hi):
    """Indexes in (lo, hi) where a new paragraph starts outside a code fence."""
    out, fence = [], None
    for i in range(lo, hi):
        m = FENCE.match(lines[i])
        if m:
            fence = None if fence == m.group(1) else (fence or m.group(1))
        if fence is None and i > lo and not lines[i - 1].strip() and lines[i].strip():
            out.append(i)
    return out


def size(lines, lo, hi):
    return sum(len(x.encode()) for x in lines[lo:hi])


def greedy(lines, cuts, lo, hi, cap=TARGET):
    """Join consecutive pieces [lo, c1), [c1, c2), ... up to cap; returns ranges, some maybe over cap."""
    bounds = [lo] + [c for c in cuts if lo < c < hi] + [hi]
    out, start = [], bounds[0]
    for a, b in itertools.pairwise(bounds):
        if start < a and size(lines, start, b) > cap:
            out.append((start, a))
            start = a
    out.append((start, hi))
    return out


def split(lines, heads, lo, hi, cap=TARGET):
    if size(lines, lo, hi) <= cap or hi - lo <= 1:
        return [(lo, hi)]
    inner = [h for h in heads if lo < h[0] < hi]
    if inner:
        top = min(h[1] for h in inner)
        cuts = [h[0] for h in inner if h[1] == top]
    else:
        cuts = blank_breaks(lines, lo, hi) or list(range(lo + 1, hi))
    out = []
    for a, b in greedy(lines, cuts, lo, hi, cap):
        out += split(lines, heads, a, b, cap) if size(lines, a, b) > cap and (a, b) != (lo, hi) else [(a, b)]
    return out


def slug(text, n=48):
    s = re.sub(r"[^\w]+", "-", text.lower(), flags=re.UNICODE).strip("-")
    return s[:n].rstrip("-") or "part"


def cell(text, n=70):
    t = text.replace("|", "\\|").replace("`", "")
    return t if len(t) <= n else t[: n - 1] + "…"


def cells(texts: list[str], k: int, count: bool) -> str:
    """At most k of the texts, joined by " · ", then "+<n> more" for the rest when count is set."""
    shown = " · ".join(texts[:k])
    more = f"+{len(texts) - k} more" if count and len(texts) > k else ""
    return f"{shown} · {more}" if shown and more else shown or more


def fit(top: str, rows: list[Row], cap: int = 25, count: bool = True, brief: bool = True) -> str:
    """top, then a line per row with the most texts of STEPS and cap within TARGET; else the brief lines, or 0 texts."""

    def text(k: int) -> str:
        return top + "".join(
            f"{start}{cells(texts, min(k, cap), count) or other} |\n" for start, texts, other, _ in rows
        )

    found = next((t for t in map(text, STEPS) if len(t.encode()) <= TARGET), None)
    return found or (top + "".join(f"{line}\n" for *_, line in rows) if brief else text(0))


def part_row(n: int, name: str, span: str, under: str, shown: list[str], first: str) -> Row:
    """A part's index row; its brief line links the part by its number and counts its headings."""
    line = f"| [{n:02d}]({name}) | {span} | {cell(under, 20)} | {cells(shown, 0, True) or cell(first, 20)} |"
    return f"| [{name}]({name}) | {span} | {cell(under, 60)} | ", [cell(t, 50) for t in shown], cell(first, 60), line


def reserve(rel: str, lines: list[str], heads: list[tuple[int, int, str]], title: str) -> int:
    """The bytes of the longest header line and title line a part of this file can get, which count within TARGET."""
    d = "9" * len(str(len(lines)))
    top = f"<!-- part {d} of {d} of {rel}, lines {d}-{d}; split {DAY} by ops/split_large.py; index: README.md -->\n"
    texts, above = [title], {}
    for _, lv, t in heads:
        above = {k: v for k, v in above.items() if k < lv}
        above[lv] = t
        texts.append(" › ".join(above.values()))
    return len(top.encode()) + max(len(f"# {cell(t, 120)} — part {d} of {d}\n\n".encode()) for t in texts)


def layer(chains):
    """Groups of consecutive parts for a layered index: the shallowest heading level that gives 3-30 groups of at most
    30 parts each; otherwise runs of 20. Returns [(first, end, label)]."""
    levels = sorted({lv for c in chains for lv in c})
    for L in levels[:3]:
        keys = [tuple(c.get(lv) for lv in levels if lv <= L) for c in chains]
        runs, lo = [], 0
        for i in range(1, len(keys) + 1):
            if i == len(keys) or keys[i] != keys[lo]:
                runs.append((lo, i, next((k for k in reversed(keys[lo]) if k), f"parts {lo + 1}-{i}")))
                lo = i
        if 3 <= len(runs) <= 30 and max(b - a for a, b, _ in runs) <= 30:
            return runs
    return [
        (i, min(i + 20, len(chains)), f"parts {i + 1}-{min(i + 20, len(chains))}") for i in range(0, len(chains), 20)
    ]


def split_file(path, root, seen, dry):
    raw = path.read_text(encoding="utf-8", errors="replace")
    rel = path.relative_to(root).as_posix()
    folder = path.with_suffix("")
    digest = hashlib.sha256(raw.encode()).hexdigest()
    if folder.exists():
        print(f"skip {rel}: {folder.name}/ exists")
        return None
    if digest in seen:
        first = seen[digest]
        print(f"dup  {rel} = {first}")
        if not dry:
            folder.mkdir()
            (folder / "README.md").write_text(
                f"# {path.name}: the same text as `{first}`\n\n<!-- split {DAY} by ops/split_large.py -->\n"
                f"This file was identical to `{first}` (sha256 {digest[:12]}), which is split into titled parts; "
                f"read its index: `{Path(first).with_suffix('').as_posix()}/README.md`.\n",
                encoding="utf-8",
            )
            path.unlink()
        return rel, Path(first).with_suffix("").as_posix() + "/README.md"
    seen[digest] = rel
    lines = re.findall(r"[^\n]*\n|[^\n]+$", raw)  # "\n" only, as grep -n counts (not U+2028 and friends)
    heads = headings(lines) if path.suffix == ".md" else []
    first_line = next((x.strip() for x in lines if x.strip()), path.stem)
    title = next((t for _, lv, t in heads if lv == 1), None) or first_line[:100]
    cap = TARGET - reserve(rel, lines, heads, title)  # what a part's own lines may take
    parts = []
    for a, b in split(
        lines, heads, 0, len(lines), cap
    ):  # a part under MIN joins its neighbour (a heading with nothing else)
        if parts and (size(lines, *parts[-1]) < MIN or size(lines, a, b) < MIN) and size(lines, parts[-1][0], b) <= cap:
            parts[-1] = (parts[-1][0], b)
        else:
            parts.append((a, b))
    rows, names, chains, firsts = [], set(), [], []
    for n, (a, b) in enumerate(parts, 1):
        above = {}
        for i, lv, t in heads:
            if i >= a:
                break
            above = {k: v for k, v in above.items() if k < lv}
            above[lv] = t
        inside = [(lv, t) for i, lv, t in heads if a <= i < b]
        starts_with_head = bool(inside) and any(i == a for i, _, _ in heads)
        chain = dict(above)
        if starts_with_head:
            lv0 = next(lv for i, lv, _ in heads if i == a)
            chain = {k: v for k, v in chain.items() if k < lv0}
            chain[lv0] = inside[0][1]
        chains.append(chain)
        first_text = next(
            (
                re.sub(r"[^\w.,:;()'\"/+-]+", " ", x, flags=re.UNICODE).strip()
                for x in lines[a:b]
                if re.search(r"\w", x)
            ),
            path.stem,
        )[:60]
        lead = (
            inside[0][1]
            if starts_with_head
            else (f"{list(above.values())[-1]} — {first_text}" if above else first_text)
        )
        name = f"{n:02d}-{slug(lead)}.md"
        while name in names:
            name = name[:-3] + "-x.md"
        names.add(name)
        body = "".join(lines[a:b])
        top = (
            f"<!-- part {n} of {len(parts)} of {rel}, lines {a + 1}-{b}; split {DAY} by ops/split_large.py; "
            f"index: README.md -->\n"
        )
        if not starts_with_head:
            path_txt = " › ".join(above.values()) or title
            top += f"# {cell(path_txt, 120)} — part {n} of {len(parts)}\n\n"
        if not dry:
            folder.mkdir(exist_ok=True)
            (folder / name).write_text(top + body, encoding="utf-8")
        lvls = sorted({lv for lv, _ in inside})[:2]
        shown = [t for lv, t in inside if lv in lvls]
        under = " › ".join(v for v in above.values() if v != title) or "—"
        firsts.append(shown[0] if shown else first_text)
        rows.append(part_row(n, name, f"{a + 1}-{b}", under, shown, first_text))
    head = (
        f"<!-- split {DAY} by ops/split_large.py from {rel} ({len(lines)} lines, {len(raw.encode()) // 1024} KB); "
        f"the whole file is in git history -->\n"
    )
    table = "| Part | Lines | Under | Headings in it |\n|---|---|---|---|\n"
    index = None
    if len(parts) <= GROUP:
        index = fit(
            f"# {cell(title, 120)} — index of {len(parts)} parts\n\n"
            + head
            + f"Read this index, then open only the part you need. Line numbers are those of the original "
            f"`{path.name}`.\n\n" + table,
            rows,
            brief=False,
        )
    extra = {}
    if index is None or len(index.encode()) > TARGET:  # more than GROUP parts, or too long to list flat
        groups = layer(chains)
        grows = []
        for g, (lo, hi, label) in enumerate(groups, 1):
            gname = f"_group-{g:02d}-{slug(label, 40)}.md"
            a0, b0 = parts[lo][0] + 1, parts[hi - 1][1]
            heads_in = [t for t in dict.fromkeys(firsts[lo:hi]) if t not in (label, title)]
            extra[gname] = fit(
                f"# {cell(title, 100)} › {cell(label, 100)}: parts {lo + 1}-{hi}\n\n"
                + head
                + f"Group {g} of {len(groups)} of the index `README.md`. Open only the part you need.\n\n"
                + table,
                rows[lo:hi],
            )
            tail = f"]({gname}) | {a0}-{b0} | {lo + 1}-{hi} | "
            sections = [cell(t, 40) for t in heads_in]
            grows.append((f"| [{cell(label, 70)}{tail}", sections, "", f"| [{cell(label, 20)}{tail} |"))
        index = fit(
            f"# {cell(title, 120)} — index: {len(groups)} groups, {len(parts)} parts\n\n"
            + head
            + f"Pick a group, open its index, then only the part you need. Line numbers are those of the original "
            f"`{path.name}`.\n\n| Group | Lines | Parts | Sections |\n|---|---|---|---|\n",
            grows,
            cap=8,
            count=False,
        )
    if not dry:
        (folder / "README.md").write_text(index, encoding="utf-8")
        for gname, text in extra.items():
            (folder / gname).write_text(text, encoding="utf-8")
        path.unlink()
    print(f"split {rel}: {len(parts)} parts, largest {max(size(lines, a, b) for a, b in parts) // 1024} KB")
    return rel, folder.relative_to(root).as_posix() + "/README.md"


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """The command line of the Usage line above."""
    ap = argparse.ArgumentParser(prog="split_large.py", description="Split large text files into titled parts.")
    ap.add_argument("--dry-run", action="store_true", help="print the same lines and write nothing")
    ap.add_argument("--limit", type=int, default=LIMIT, help=f"split a file larger than this, in bytes ({LIMIT})")
    ap.add_argument(
        "--relink",
        action="append",
        default=[],
        metavar="PATH",
        help="point the .md files under PATH at the indexes (may be given more than once)",
    )
    ap.add_argument("paths", nargs="+", metavar="PATH", help="a file, or a folder (its .md and .txt files)")
    return ap.parse_args(argv)


def large_files(root: Path, paths: list[str], limit: int) -> list[Path]:
    """The files over limit bytes that the PATHs name, in the order given; a folder's by depth, then by path."""
    files: list[Path] = []
    for arg in paths:
        p = root / arg
        found = (
            [p]
            if p.is_file()
            else sorted(
                (f for f in p.rglob("*") if f.is_file() and f.suffix in EXTS),
                key=lambda f: (len(f.parts), f.as_posix()),
            )
        )
        files += [f for f in found if f.stat().st_size > limit and f not in files]
    return files


def relink(root: Path, under: list[str], moved: list[tuple[str, str]], dry: bool) -> None:
    """In the .md files under each PATH, a split file's path from the root becomes the path of its index."""
    made = {root / old for old, _ in moved} | {root / Path(old).with_suffix("") for old, _ in moved}
    pages = {}
    for arg in under:
        p = root / arg
        for page in [p] if p.is_file() else sorted(p.rglob("*.md")):
            if page not in made and not made.intersection(page.parents):  # never a split file or the parts made of it
                pages[page] = None
    for page in pages:
        t = page.read_text(encoding="utf-8")
        new = t
        for old, idx in moved:
            new = re.sub(re.escape(old) + r"(?![\w/-])", idx, new)
        if new != t:
            if not dry:
                page.write_text(new, encoding="utf-8")
            print(f"links {page.relative_to(root)}")


def main(argv: list[str] | None = None) -> int:
    """Split the large files the PATHs name, then point the pages under each --relink PATH at their indexes."""
    a = parse_args(argv)
    root = Path.cwd()
    missing = [p for p in a.paths + a.relink if not (root / p).exists()]
    if missing:
        print(f"split_large.py: no such file or folder: {' '.join(missing)} (nothing written)", file=sys.stderr)
        return 2
    seen, moved = {}, []
    for p in large_files(root, a.paths, a.limit):
        r = split_file(p, root, seen, a.dry_run)
        if r:
            moved.append(r)
    relink(root, a.relink, moved, a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
