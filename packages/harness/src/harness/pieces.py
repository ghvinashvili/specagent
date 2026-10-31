"""harness/pieces.py — the material of a stage, cut into pieces and chosen by script.

A role session starts with the pieces of the repository its job needs in its cached system prompt (pack.material),
so that it neither searches for them nor opens them. Choosing them costs the manager no turn and no token: this
module cuts every file at its natural seams (the sections of a document, the top-level definitions of code, the
top-level keys of a table) and chooses the pieces of a stage from the texts the stage already holds (its brief, its
assignment and its inputs), in this order:

1. every place they cite as `path:line` or `path:first-last`, as the piece of its file that holds it, the pieces
   cited most first;
2. every file they name, whole, when it is short enough;
3. the pieces whose words match the brief best (BM25), within RELATED_CHARS.

pack.material gives them after the stage's inputs and the pieces its brief and its assignment list, while they fit.
Only files the session could open itself are chosen: tracked, text, not closed to its type, `context/` only for a
type that receives it. No model takes part, so the same texts give the same pieces; `harness material` shows them.
"""

from __future__ import annotations

import ast
import fnmatch
import math
import re
import subprocess
from collections import Counter
from pathlib import Path

from .gitcall import GIT

MAX_PIECE_LINES = 160  # a stretch without a seam that is longer than this is cut into parts of this length
SMALL_FILE_LINES = 400  # a file a stage's text names is given whole up to this length
MAX_FILE_BYTES = 1_500_000  # larger files are not cut; a session opens them itself
RELATED_CHARS = 40_000  # what the pieces that only match the words of the job may add, about 10,000 tokens
RELATED_SHARE = 0.35  # a matching piece scores at least this share of the best match
TEXT_SUFFIXES = {
    ".md", ".txt", ".py", ".pyi", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".sh", ".html", ".css", ".sql", ".rs", ".go", ".java", ".c", ".h", ".cpp",
}  # fmt: skip
CITED = re.compile(r"(?<![\w/.-])((?:[\w.-]+/)*[\w-][\w.-]*\.[A-Za-z0-9]+):(\d+)(?:-(\d+))?")
NAMED = re.compile(r"(?<![\w/.-])((?:[\w.-]+/)*[\w-][\w.-]*\.[A-Za-z0-9]+)(?![\w/-])")  # any file path in a text
WORD = re.compile(r"[^\W\d_]\w{2,}")
# Files the word match leaves alone. The wiki reaches a type through its pack; evaluations and the knowledge graph
# only when a task names them (CLAUDE.md); `.claude/` holds the configuration of sessions, not the project; a
# generated document repeats its source; a changelog and a lock file match every job and help none. A stage still
# gets any of them that its texts cite or name.
RELATED_SKIP = (
    "wiki/**", "evals/**", "graphify-out/**", ".claude/**", "docs/generated/**", "CHANGELOG.md", "**/CHANGELOG.md",
    "*.lock", "**/*.lock",
)  # fmt: skip
STOP = frozenset({  # words every job uses; they tell no piece from another
    "the", "and", "for", "with", "that", "this", "from", "are", "not", "was", "but", "has", "have", "had", "its",
    "into", "all", "any", "can", "each", "every", "one", "two", "who", "what", "when", "where", "which", "while",
    "will", "would", "should", "could", "may", "must", "shall", "then", "than", "they", "them", "their", "there",
    "these", "those", "also", "only", "more", "most", "some", "such", "other", "same", "over", "under", "after",
    "before", "about", "between", "without", "within", "upon", "via", "per", "you", "your", "our", "out", "use",
    "used", "uses", "using", "new", "old", "does", "did", "done", "being", "been", "were", "how", "why", "yes"
})  # fmt: skip
Piece = tuple[str, int, int, str]  # path, first line, last line, title


def _seams(path: str, lines: list[str]) -> list[int]:
    """The line numbers (1-based) where a new piece of the file begins."""
    suffix = Path(path).suffix.lower()
    seams: list[int] = []
    if suffix == ".md":
        fence = False
        for n, line in enumerate(lines, 1):
            if line.lstrip().startswith("```"):
                fence = not fence
            elif not fence and re.match(r"^#{1,6}\s", line):
                seams.append(n)
    elif suffix in (".py", ".pyi"):
        try:
            tree = ast.parse("\n".join(lines))
        except (SyntaxError, ValueError):
            return []
        after_definition = False
        for node in tree.body:  # a definition starts a piece, and so does the first statement after one
            first = min([node.lineno, *[d.lineno for d in getattr(node, "decorator_list", [])]])
            definition = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            if definition or after_definition:
                seams.append(first)
            after_definition = definition
    elif suffix in (".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"):
        top = re.compile(
            r"^(export\s+)?(default\s+)?(async\s+)?(function\*?\s|class\s|const\s+\w+\s*=\s*(async\s*)?(\(|function))"
        )
        seams = [n for n, line in enumerate(lines, 1) if top.match(line)]
    elif suffix in (".yaml", ".yml"):
        seams = [n for n, line in enumerate(lines, 1) if re.match(r"^[A-Za-z_][\w.-]*\s*:", line)]
    elif suffix == ".toml":
        seams = [n for n, line in enumerate(lines, 1) if line.startswith("[")]
    return sorted({s for s in seams if s > 0})


def cut_text(path: str, text: str) -> list[Piece]:
    """The pieces of one file: from each seam to the line before the next, the lines before the first seam as a piece
    of their own, and every piece longer than MAX_PIECE_LINES cut into parts of that length."""
    lines = text.splitlines()
    if not lines:
        return []
    starts = [1, *[s for s in _seams(path, lines) if s > 1]]
    out: list[Piece] = []
    for i, first in enumerate(starts):
        last = (starts[i + 1] - 1) if i + 1 < len(starts) else len(lines)
        while last >= first and not lines[last - 1].strip() and last > first:
            last -= 1  # trailing blank lines belong to nobody
        for a in range(first, last + 1, MAX_PIECE_LINES):
            b = min(a + MAX_PIECE_LINES - 1, last)
            title = next((ln.strip() for ln in lines[a - 1 : b] if ln.strip()), "")[:80]
            out.append((path, a, b, title))
    return out


def tracked(root: Path) -> list[str]:
    """The files of the repository: what git tracks, or every file outside hidden and environment directories."""
    res = subprocess.run([*GIT, "-C", str(root), "ls-files"], capture_output=True, text=True, check=False)
    if res.returncode == 0 and res.stdout.strip():
        return sorted(res.stdout.split("\n")[:-1] if res.stdout.endswith("\n") else res.stdout.split("\n"))
    skip = {".git", ".venv", "node_modules", "__pycache__"}
    return sorted(
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and not skip & set(p.relative_to(root).parts)
    )


def readable(root: Path, rel: str, closed: list[str], context: bool) -> bool:
    """Whether a session of the type may be given this file: it exists, it is text, it is not closed to the type,
    and it is under `context/` only for a type that may receive the material of a run."""
    p = root / rel
    if not p.is_file() or p.suffix.lower() not in TEXT_SUFFIXES or p.stat().st_size > MAX_FILE_BYTES:
        return False
    if not context and (rel == "context" or rel.startswith("context/")):
        return False
    return not any(fnmatch.fnmatch(rel, pat) for pat in closed)


def _text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


def _terms(text: str) -> Counter:
    """The words of a text, an identifier also by its parts (`stage_material`: stage, material)."""
    out: Counter = Counter()
    for w in WORD.findall(text.lower()):
        parts = [x for x in w.split("_") if len(x) > 2]
        out.update(x for x in ([w, *parts] if len(parts) > 1 else [w]) if x not in STOP)
    return out


def related(root: Path, files: list[str], query: str, budget: int = RELATED_CHARS) -> list[Piece]:
    """The pieces of `files` whose words match `query` best (BM25), best first, until `budget` characters."""
    want = set(_terms(query))
    if not want:
        return []
    docs: list[tuple[Piece, Counter, int]] = []
    for rel in files:
        text = _text(root, rel)
        lines = text.splitlines()
        for piece in cut_text(rel, text):
            body = "\n".join(lines[piece[1] - 1 : piece[2]])
            docs.append((piece, _terms(body + " " + rel.replace("/", " ")), len(body)))
    if not docs:
        return []
    n = len(docs)
    avg = sum(sum(t.values()) for _, t, _ in docs) / n or 1.0
    df = Counter(w for _, t, _ in docs for w in want if w in t)
    scored = []
    for piece, t, size in docs:
        length = sum(t.values()) or 1
        s = 0.0
        for w in want:
            f = t.get(w, 0)
            if f:
                idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
                s += idf * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * length / avg))
        if s > 0:
            scored.append((s, piece, size))
    if not scored:
        return []
    scored.sort(key=lambda x: (-x[0], x[1][0], x[1][1]))
    floor = scored[0][0] * RELATED_SHARE
    out, used = [], 0
    for s, piece, size in scored:
        if s < floor or used + size > budget:
            continue
        out.append(piece)
        used += size
    return out


def select(
    root: Path,
    closed: list[str],
    context: bool,
    texts: list[str],
    query: str,
    skip: set[str] = frozenset(),
    run_material: bool = True,
    budget: int = RELATED_CHARS,
) -> list[tuple[str, int, int | None, str]]:
    """The pieces the harness gives a stage on its own: (path, first line, last line or None for the whole file,
    why), in the order they claim room. `texts` are what the stage holds (its brief and assignment without their
    Material lists, and its inputs); `query` is what its job is about (the brief without its list); `skip` are the
    files it gets anyway (its pack). `context` says whether its type may receive `context/`; `run_material` whether
    the stage receives it: a stage that works from earlier notes gets the places of `context/` they cite, not more."""

    def wide(rel: str) -> bool:
        return run_material or not (rel == "context" or rel.startswith("context/"))

    files = [rel for rel in tracked(root) if rel not in skip and readable(root, rel, closed, context)]
    known = set(files)
    cuts: dict[str, list[Piece]] = {}
    hits: dict[tuple[str, int, int], list[int]] = {}  # piece: [times cited, order of the first citation]
    for text in texts:
        for m in CITED.finditer(text):
            rel, a = m.group(1), int(m.group(2))
            b = max(a, int(m.group(3) or a))
            if rel not in known:
                continue
            if rel not in cuts:
                cuts[rel] = cut_text(rel, _text(root, rel))
            for _, first, last, _ in cuts[rel]:
                if first <= b and last >= a:
                    hits.setdefault((rel, first, last), [0, len(hits)])[0] += 1
    out: list[tuple[str, int, int | None, str]] = [
        (rel, a, b, "cited") for rel, a, b in sorted(hits, key=lambda k: (-hits[k][0], hits[k][1]))
    ]
    named: list[str] = []
    seen: set[str] = set()
    for text in texts:  # every short file a text names, whole, in the order they are named
        for m in NAMED.finditer(text):
            rel = m.group(1)
            if rel in seen or rel not in known or not wide(rel):
                continue
            seen.add(rel)
            if len(_text(root, rel).splitlines()) <= SMALL_FILE_LINES:
                named.append(rel)
    out += [(rel, 1, None, "named") for rel in named]
    pool = [rel for rel in files if wide(rel) and not any(fnmatch.fnmatch(rel, pat) for pat in RELATED_SKIP)]
    out += [(rel, first, last, "related") for rel, first, last, _ in related(root, pool, query, budget)]
    return out
