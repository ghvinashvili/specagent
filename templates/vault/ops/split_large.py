#!/usr/bin/env python3
"""Split every large text file under context/ into titled parts with an index, part by part and by
topic, titled so that it is easy to find and an agent need not read the whole file.

A Markdown file is cut at its own headings (never inside a code fence): a section that fits stays whole, a larger one
is cut at its sub-headings, and small neighbouring sections are joined up to TARGET bytes without crossing a heading
of a higher level. Text without headings (notes, .txt) is cut at blank lines. `X.md` becomes the folder `X/` with
`README.md` (the index: every part, its original line range, the headings above it and the headings in it) and the
parts `NN-<first heading>.md`; each part's first line names the file and line range it came from. A file identical to
one already split gets only a README pointing there. The original stays in git history.

Usage: python3 ops/split_large.py [--dry-run]   (run from the vault root; idempotent: split files no longer exist)
"""
import hashlib
import re
import sys
from datetime import date
from pathlib import Path

LIMIT = 24_000   # files larger than this are split (about 6k tokens)
TARGET = 12_000  # no part larger than this (about 3k tokens), except one line longer than it
MIN = 2_000      # a smaller part joins its neighbour
GROUP = 25       # a file index with more parts than this is layered: groups first, then a small index per group
EXTS = {".md", ".txt"}
DAY = date.today().isoformat()
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


def greedy(lines, cuts, lo, hi):
    """Join consecutive pieces [lo, c1), [c1, c2), ... up to TARGET; returns ranges, some maybe over TARGET."""
    bounds = [lo] + [c for c in cuts if lo < c < hi] + [hi]
    out, start = [], bounds[0]
    for a, b in zip(bounds, bounds[1:]):
        if start < a and size(lines, start, b) > TARGET:
            out.append((start, a))
            start = a
    out.append((start, hi))
    return out


def split(lines, heads, lo, hi):
    if size(lines, lo, hi) <= TARGET or hi - lo <= 1:
        return [(lo, hi)]
    inner = [h for h in heads if lo < h[0] < hi]
    if inner:
        top = min(h[1] for h in inner)
        cuts = [h[0] for h in inner if h[1] == top]
    else:
        cuts = blank_breaks(lines, lo, hi) or list(range(lo + 1, hi))
    out = []
    for a, b in greedy(lines, cuts, lo, hi):
        out += split(lines, heads, a, b) if size(lines, a, b) > TARGET and (a, b) != (lo, hi) else [(a, b)]
    return out


def slug(text, n=48):
    s = re.sub(r"[^\w]+", "-", text.lower(), flags=re.UNICODE).strip("-")
    return (s[:n].rstrip("-") or "part")


def cell(text, n=70):
    t = text.replace("|", "\\|").replace("`", "")
    return t if len(t) <= n else t[: n - 1] + "…"


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
    return [(i, min(i + 20, len(chains)), f"parts {i + 1}-{min(i + 20, len(chains))}") for i in range(0, len(chains), 20)]


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
                f"read its index: `{Path(first).with_suffix('').as_posix()}/README.md`.\n", encoding="utf-8")
            path.unlink()
        return rel, Path(first).with_suffix("").as_posix() + "/README.md"
    seen[digest] = rel
    lines = re.findall(r"[^\n]*\n|[^\n]+$", raw)  # "\n" only, as grep -n counts (not U+2028 and friends)
    heads = headings(lines) if path.suffix == ".md" else []
    parts = []
    for a, b in split(lines, heads, 0, len(lines)):  # a part under MIN joins its neighbour (a heading with nothing else)
        if parts and (size(lines, *parts[-1]) < MIN or size(lines, a, b) < MIN) and \
                size(lines, parts[-1][0], b) <= TARGET + MIN:
            parts[-1] = (parts[-1][0], b)
        else:
            parts.append((a, b))
    first_line = next((x.strip() for x in lines if x.strip()), path.stem)
    title = next((t for _, lv, t in heads if lv == 1), None) or first_line[:100]
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
        first_text = next((re.sub(r"[^\w.,:;()'\"/+-]+", " ", x, flags=re.UNICODE).strip() for x in lines[a:b]
                           if re.search(r"\w", x)), path.stem)[:60]
        lead = inside[0][1] if starts_with_head else (
            f"{list(above.values())[-1]} — {first_text}" if above else first_text)
        name = f"{n:02d}-{slug(lead)}.md"
        while name in names:
            name = name[:-3] + "-x.md"
        names.add(name)
        body = "".join(lines[a:b])
        top = (f"<!-- part {n} of {len(parts)} of {rel}, lines {a + 1}-{b}; split {DAY} by ops/split_large.py; "
               f"index: README.md -->\n")
        if not starts_with_head:
            path_txt = " › ".join(above.values()) or title
            top += f"# {cell(path_txt, 120)} — part {n} of {len(parts)}\n\n"
        if not dry:
            folder.mkdir(exist_ok=True)
            (folder / name).write_text(top + body, encoding="utf-8")
        lvls = sorted({lv for lv, _ in inside})[:2]
        shown = [t for lv, t in inside if lv in lvls]
        more = f" · +{len(shown) - 25} more" if len(shown) > 25 else ""
        under = " › ".join(v for v in above.values() if v != title) or "—"
        firsts.append(shown[0] if shown else first_text)
        rows.append(f"| [{name}]({name}) | {a + 1}-{b} | {cell(under, 60)} | "
                    f"{' · '.join(cell(t, 50) for t in shown[:25]) + more or cell(first_text, 60)} |")
    head = (f"<!-- split {DAY} by ops/split_large.py from {rel} ({len(lines)} lines, {len(raw.encode()) // 1024} KB); "
            f"the whole file is in git history -->\n")
    table = "| Part | Lines | Under | Headings in it |\n|---|---|---|---|\n"
    groups = layer(chains) if len(parts) > GROUP else None
    extra = {}
    if groups:
        grows = []
        for g, (lo, hi, label) in enumerate(groups, 1):
            gname = f"_group-{g:02d}-{slug(label, 40)}.md"
            a0, b0 = parts[lo][0] + 1, parts[hi - 1][1]
            heads_in = [t for t in dict.fromkeys(firsts[lo:hi]) if t not in (label, title)]
            extra[gname] = (f"# {cell(title, 100)} › {cell(label, 100)}: parts {lo + 1}-{hi}\n\n" + head +
                            f"Group {g} of {len(groups)} of the index `README.md`. Open only the part you need.\n\n" +
                            table + "\n".join(rows[lo:hi]) + "\n")
            grows.append(f"| [{cell(label, 70)}]({gname}) | {a0}-{b0} | {lo + 1}-{hi} | "
                         f"{' · '.join(cell(t, 40) for t in heads_in[:8])} |")
        index = (f"# {cell(title, 120)} — index: {len(groups)} groups, {len(parts)} parts\n\n" + head +
                 f"Pick a group, open its index, then only the part you need. Line numbers are those of the original "
                 f"`{path.name}`.\n\n| Group | Lines | Parts | Sections |\n|---|---|---|---|\n" + "\n".join(grows) + "\n")
    else:
        index = (f"# {cell(title, 120)} — index of {len(parts)} parts\n\n" + head +
                 f"Read this index, then open only the part you need. Line numbers are those of the original "
                 f"`{path.name}`.\n\n" + table + "\n".join(rows) + "\n")
    if not dry:
        (folder / "README.md").write_text(index, encoding="utf-8")
        for gname, text in extra.items():
            (folder / gname).write_text(text, encoding="utf-8")
        path.unlink()
    print(f"split {rel}: {len(parts)} parts, largest {max(size(lines, a, b) for a, b in parts) // 1024} KB")
    return rel, folder.relative_to(root).as_posix() + "/README.md"


def main():
    dry = "--dry-run" in sys.argv
    root = Path.cwd()
    if not (root / "INDEX.md").exists():
        sys.exit("run from the vault root")
    files = sorted((p for p in (root / "context").rglob("*") if p.is_file() and p.suffix in EXTS
                    and p.stat().st_size > LIMIT), key=lambda p: (len(p.parts), p.as_posix()))
    seen, moved = {}, []
    for p in files:
        r = split_file(p, root, seen, dry)
        if r:
            moved.append(r)
    if dry:
        return
    # point the compiled pages at the indexes
    pages = [p for d in ("decisions", "concepts", "entities", "sources") for p in (root / d).rglob("*.md")]
    pages += [root / "INDEX.md", root / "README.md", root / "context" / "README.md"]
    for page in pages:
        if not page.exists():
            continue
        t = page.read_text(encoding="utf-8")
        new = t
        for old, idx in moved:
            new = re.sub(re.escape(old) + r"(?![\w/-])", idx, new)
        if new != t:
            page.write_text(new, encoding="utf-8")
            print(f"links {page.relative_to(root)}")


if __name__ == "__main__":
    main()
