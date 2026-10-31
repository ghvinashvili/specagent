#!/usr/bin/env python3
"""Build the layered indexes of context/ (the vault's rule of layered indexes and small parts).

Finding goes down short steps, each a small file: `context/README.md` (the categories) → `context/_index/<category>.md`
(one line per document, or the category's sub-groups when it has more than MAX entries) → a split file's own
`README.md` (from ops/split_large.py) → the part. A document is a file, or a folder that ops/split_large.py made from
one file. A file identical to one listed earlier is not listed again; the later folder's index names it in one line.
The descriptions come from the files themselves (frontmatter `description`, first heading, first line); the category
and sub-group texts below are written by hand. Run after ops/split_large.py; it rewrites only the files it owns.

Usage: python3 ops/build_indexes.py   (from the vault root)
"""
import hashlib
import re
import sys
from pathlib import Path

MAX = 40
SPLIT_MARK = "by ops/split_large.py from "

# (slug, title, what is in it, path prefixes under context/, sub-groups: [(slug, title, prefixes)])
CATEGORIES = [
    ("owner-statements", "Owner statements", "what the vault's owner said and decided, one file per day or decision",
     ["owner-statements/"], []),
    ("measurements", "Measurements", "what was measured, how, and the numbers: the evidence a decision cites",
     ["measurements/"], []),
    ("memory", "Memory copies", "Claude Code memory files collected by ops/collect_memory.py (secret filter), one "
     "folder per memory directory", ["memory/"], []),
    ("other", "Everything else", "every other file under context/", [""], []),
]


TOPICS = {"topics": {}, "files": {}}


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
        m = re.search(r"^description:\s*(.+?)(?=^\w[\w-]*:|\Z)", "\n".join(fm), re.M | re.S)
        if m:
            return " ".join(m.group(1).split()).strip("\"'").replace('\\"', '"')[:180]
    head = next((ln.lstrip("# ").strip() for ln in lines if ln.startswith("#")), None) if p.suffix == ".md" else None
    text = next((ln.strip() for ln in lines if ln.strip() and not ln.startswith(("#", "---", "|", "```"))), "")
    out = f"{head}: {text}" if head and text and head != text else (head or text)
    return out[:180]


def documents(ctx):
    """Every document under context/: files, and the split folders as one document each (their parts not listed)."""
    split_dirs = set()
    for r in ctx.rglob("README.md"):
        t = r.read_text(encoding="utf-8", errors="replace")[:600]
        if SPLIT_MARK in t or re.search(r"split \d{4}-\d{2}-\d{2}", t) and "ops/split_large.py" in t:
            split_dirs.add(r.parent)
    docs = list(split_dirs)
    for f in ctx.rglob("*"):
        if f.is_file() and not f.name.startswith(".") and not any(d in f.parents for d in split_dirs) and f.parent != ctx / "_index" \
                and f != ctx / "README.md" and f.name != "_skipped.md":
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
    rel = doc.relative_to(ctx).as_posix()
    target = (doc / "README.md") if doc.is_dir() else doc
    link = Path("..", target.relative_to(ctx)).as_posix() if idx_dir == ctx / "_index" else target.relative_to(ctx).as_posix()
    kb = sum(f.stat().st_size for f in doc.rglob("*") if f.is_file()) if doc.is_dir() else doc.stat().st_size
    return f"- [{doc.name}{'/' if doc.is_dir() else ''}]({link}) — {describe(doc)} ({max(1, kb // 1024)} KB)"


def main():
    root = Path.cwd()
    if not (root / "INDEX.md").exists():
        sys.exit("run from the vault root")
    global TOPICS
    t = root / "ops" / "memory-topics.json"
    if t.exists():
        import json
        TOPICS = json.loads(t.read_text(encoding="utf-8"))
    ctx = root / "context"
    idx = ctx / "_index"
    idx.mkdir(exist_ok=True)
    for old in idx.glob("*.md"):
        old.unlink()
    docs = documents(ctx)
    # each document to the category whose prefix matches it longest
    placed = {c[0]: [] for c in CATEGORIES}
    for d in docs:
        rel = d.relative_to(ctx).as_posix() + ("/" if d.is_dir() else "")
        best = max(CATEGORIES, key=lambda c: best_match(rel, c[3]))
        if best_match(rel, best[3]) < 0:
            best = CATEGORIES[-1]
        placed[best[0]].append(d)
    seen, top_rows = {}, []
    for slug, title, what, _, subs in CATEGORIES:
        items = placed[slug]
        groups = []
        if subs and len(items) > MAX:
            for sslug, stitle, sprefix in subs:
                g = [d for d in items if max(subs, key=lambda s: best_match(d.relative_to(ctx).as_posix() + "/", s[2]))[0] == sslug]
                groups.append((f"{slug}--{sslug}", stitle, g))
        else:
            groups.append((slug, title, items))
        sub_rows = []
        for gslug, gtitle, g in groups:
            rows, dups, names = [], [], []
            for d in g:
                k = content_key(d)
                if k and k in seen:
                    dups.append(f"{d.relative_to(ctx).as_posix()} = {seen[k]}")
                    continue
                if k:
                    seen[k] = d.relative_to(ctx).as_posix()
                rows.append(line(d, ctx, idx))
                names.append(d.stem)
            body = f"# {gtitle}\n\n<!-- built by ops/build_indexes.py; do not edit by hand -->\n"
            if len(rows) > MAX:  # one more layer: by topic (memory) or in runs of MAX
                if gslug.split("--")[0] == "memory":
                    keyed = [(TOPICS["files"].get(n, "?"), r) for n, r in zip(names, rows)]
                    order = list(TOPICS["topics"]) + ["?"]
                    title_of = dict(TOPICS["topics"], **{"?": "Not yet sorted"})
                else:
                    keyed = [(f"{i // MAX + 1:02d}", r) for i, r in enumerate(rows)]
                    order = sorted({k for k, _ in keyed})
                    title_of = {k: f"Documents {(int(k) - 1) * MAX + 1}-{min(int(k) * MAX, len(rows))}" for k in order}
                links = []
                for k in order:
                    part = [r for kk, r in keyed if kk == k]
                    if not part:
                        continue
                    tname = f"{gslug}--{slugify(title_of[k])}.md"
                    (idx / tname).write_text(f"# {gtitle} › {title_of[k]}\n\n<!-- built by ops/build_indexes.py; do not "
                                             f"edit by hand -->\n{len(part)} documents.\n\n" + "\n".join(part) + "\n",
                                             encoding="utf-8")
                    links.append(f"- [{title_of[k]}]({tname}): {len(part)} documents")
                body += f"{len(rows)} documents; pick a topic:\n\n" + "\n".join(links) + "\n"
            else:
                body += f"Category index of `context/` ({len(rows)} documents). Open a document; a split one opens at its own index.\n\n"
                body += "\n".join(rows) + "\n"
            if dups:
                body += (f"\nNot listed, identical to a copy listed earlier ({len(dups)}): " +
                         "; ".join(x.split("/")[-1] + " (= " + x.split(" = ")[1] + ")" for x in dups) + "\n")
            (idx / f"{gslug}.md").write_text(body, encoding="utf-8")
            sub_rows.append((gslug, gtitle, len(rows), len(dups)))
        if len(groups) > 1:
            body = f"# {title}\n\n<!-- built by ops/build_indexes.py; do not edit by hand -->\n{what[0].upper() + what[1:]}.\n\n"
            body += "Pick a group:\n\n" + "\n".join(
                f"- [{t}]({s}.md): {n} documents" + (f", {k} identical copies not listed again" if k else "")
                for s, t, n, k in sub_rows) + "\n"
            (idx / f"{slug}.md").write_text(body, encoding="utf-8")
        top_rows.append(f"| [{title}](_index/{slug}.md) | {what} | {sum(n for _, _, n, _ in sub_rows)} |")
    readme = ("# context/: raw material — start here\n\n"
              "Copied verbatim and never edited. The "
              "compiled pages (`INDEX.md`) cite these files; come here only for a source a page cites or a fact no page "
              "holds. Find it in short steps, never by reading a whole file: this table → the category's index → a "
              "split file's own `README.md` (its parts with their original line ranges) → the one part you need. Large "
              "files are split by `ops/split_large.py`; these indexes are built by `ops/build_indexes.py`.\n\n"
              "| Category | What is in it | Documents |\n|---|---|---|\n" + "\n".join(top_rows) + "\n")
    (ctx / "README.md").write_text(readme, encoding="utf-8")
    print(f"{len(docs)} documents in {len(CATEGORIES)} categories; indexes: {len(list(idx.glob('*.md')))} files")
    for f in sorted(idx.glob("*.md")):
        print(f"  {f.name}: {f.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
