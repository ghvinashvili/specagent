#!/usr/bin/env python3
"""Check the compiled pages of the vault: links resolve, sources exist, frontmatter complete, no secrets, INDEX covers
every page. A global page is a lesson or an order, in neutral English (rules.md): it names its kind, a lesson its proof,
an order its review date, and it holds no quoted text of the owner and no Georgian letter; a global page and a
candidate in context/candidates/ are at most 4,000 bytes (the manager's lessons page: under 8,000, the limit of its
form), and a candidate is not past its review date. Exit 1 when anything is found. Deterministic; no model.

Usage: check_pages.py [vault-root] [--today YYYY-MM-DD]

A quote whose words are mostly not English is told by the English word list of the machine ($CHECK_PAGES_WORDS: one
word per line; else /usr/share/dict/american-english, words or british-english). With no list the check falls back to
the Georgian letters and a short list of Georgian words in Latin script.
"""

import argparse
import functools
import os
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect_memory import PATTERNS

PAGE_FIELDS = ["title", "type", "scope", "status", "updated", "audience", "sources"]
DECISION_FIELDS = ["decided", "by", "why", "decision_status", "would_change_if"]
SCOPE = re.compile(r"[a-z][a-z0-9-]*")  # `global`, or the name of one domain: its decisions live in decisions/<domain>/
KINDS = ("lesson", "order")  # a global page: a proven lesson, or the owner's standing order (rules.md)
MAX_BYTES = 4000  # a global page and a candidate: one rule, short enough to be read whole (rules.md)
LESSONS_PAGE = "decisions/global/manager-lessons.md"  # the one exception to MAX_BYTES: the manager's lessons page
LESSONS_BYTES = 8000  # it stays under this many bytes, the number its form states (forms/manager-lessons.md)
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
BLOCKS = ((0x10A0, 0x10FF), (0x1C90, 0x1CBF), (0x2D00, 0x2D2F))  # the three blocks the template refuses
GEORGIAN = re.compile("[" + "".join(f"{chr(lo)}-{chr(hi)}" for lo, hi in BLOCKS) + "]")
LEFT, RIGHT = chr(0x201C), chr(0x201D)  # curly double quotes
ANGLE_L, ANGLE_R = chr(0xAB), chr(0xBB)  # guillemets
CODE = re.compile(r"```.*?```|`[^`\n]*`", re.DOTALL)  # fenced blocks and inline spans: code, not prose
LOW = chr(0x201E)  # the opening mark of a low-high quote, closed by either curly double mark
QUOTE = re.compile(
    rf'"([^"\n]+)"|{LOW}([^{LEFT}{RIGHT}\n]+)[{LEFT}{RIGHT}]|{LEFT}([^{RIGHT}\n]+){RIGHT}'
    rf"|{ANGLE_L}([^{ANGLE_R}\n]+){ANGLE_R}|^>[ \t]*(.+)$",
    re.MULTILINE,
)
WORD = re.compile(r"[A-Za-z]{2,}")
WORD_LISTS = ("/usr/share/dict/american-english", "/usr/share/dict/words", "/usr/share/dict/british-english")
LATIN_SCRIPT = frozenset(  # the fallback where no English word list is installed: Georgian words in Latin script
    "ara diax minda unda gvinda gaaketet gaaketot gavaketot vici mgonia mgoni chemi chveni shen tqven ukve magram "
    "radgan kargi rogor aqvs aris iqos gamarjoba madloba sheicvala dawere".split()
)


def frontmatter(text: str) -> dict:
    m = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        if _:
            out[k.strip()] = v.strip()
    return out


@functools.cache
def english_words() -> frozenset[str] | None:
    """The English word list of the machine, lower-cased; None where there is none."""
    given = os.environ.get("CHECK_PAGES_WORDS")
    for name in WORD_LISTS if given is None else (given,):
        path = Path(name)
        if path.is_file():
            return frozenset(w.strip().lower() for w in path.read_text(encoding="utf-8", errors="replace").split())
    return None


def prose(text: str) -> str:
    """The text with its code blanked out, the line breaks kept so that a line number still holds."""
    return CODE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def not_english(quote: str) -> bool:
    """A quote with a Georgian letter, or three words or more of which most are not in the English word list (with no
    list: two words or more of which most are Georgian words in Latin script)."""
    if GEORGIAN.search(quote):
        return True
    found = [w.lower() for w in WORD.findall(quote)]
    words = english_words()
    if words is None:
        return len(found) >= 2 and 2 * sum(w in LATIN_SCRIPT for w in found) > len(found)
    return len(found) >= 3 and 2 * sum(w not in words for w in found) > len(found)


def size_problems(rel: str, path: Path) -> list[str]:
    """A global page and a candidate are at most MAX_BYTES bytes on disk (rules.md): one rule a page. The manager's
    lessons page is the one exception: it keeps the limit of its form, under LESSONS_BYTES bytes (a page of exactly that
    size is refused, as the pipeline skill's measurement of the page refuses it)."""
    size = path.stat().st_size
    if rel == LESSONS_PAGE:
        if size < LESSONS_BYTES:
            return []
        return [
            (
                f"{rel}: {size:,} bytes; the manager's lessons page stays under {LESSONS_BYTES:,} bytes"
                " (forms/manager-lessons.md): shorten its items"
            )
        ]
    if size <= MAX_BYTES:
        return []
    return [
        (
            f"{rel}: {size:,} bytes; a global page and a candidate are at most {MAX_BYTES:,} bytes:"
            " shorten it, or split it into pages that each hold one rule"
        )
    ]


def global_problems(rel: str, fm: dict, text: str, root: Path) -> list[str]:
    """What rules.md asks of a page of decisions/global/: a kind, the proof of a lesson, the review date of an order,
    and the rule in neutral English (no quoted text of the owner, no Georgian letter)."""
    problems = []
    kind = fm.get("kind", "")
    if not kind:
        problems.append(
            f"{rel}: a global page names its kind: `kind: lesson` (a found mistake or a measurement, with its proof)"
            " or `kind: order` (the owner's standing decision, with `review:`)"
        )
    elif kind not in KINDS:
        problems.append(f"{rel}: kind `{kind}` is neither `lesson` nor `order`")
    if kind == "order":
        if not DATE.fullmatch(fm.get("review", "")):
            problems.append(f"{rel}: an order carries `review: YYYY-MM-DD` (one year on)")
    elif kind == "lesson":  # its proof is mandatory whatever its date (rules.md): a measurement or a found mistake
        proofs = re.findall(r"[^\[\],\s]+", fm.get("proof", ""))
        if not proofs:
            problems.append(
                f"{rel}: a global decision names its proof: `proof: [context/<page>]` (a measurement or a found mistake)"
            )
        context = (root / "context").resolve()
        for pr in proofs:
            target = (root / pr).resolve()
            if not pr.startswith("context/") or not target.is_file() or not target.is_relative_to(context):
                problems.append(f"{rel}: proof `{pr}` is not an existing page under context/")
    if GEORGIAN.search(text):
        problems.append(
            f"{rel}: a letter of a refused script (Georgian) outside context/; the owner's words stay in"
            " context/owner-statements/ and are named in `sources:`"
        )
    for m in QUOTE.finditer(prose(text)):
        if not_english(next(g for g in m.groups() if g)):
            line = text.count("\n", 0, m.start()) + 1
            problems.append(
                f"{rel}:{line}: quoted text of the owner (a Georgian letter, or words mostly not English): state the"
                " rule in your own words; the quote stays in context/owner-statements/"
            )
    return problems


def candidate_problems(root: Path, today: str) -> list[str]:
    """A candidate waits in context/candidates/ for its proof; past its review date it is proved or deleted."""
    problems = []
    for p in sorted((root / "context" / "candidates").rglob("*.md")):
        if p.name == "README.md":
            continue
        rel = p.relative_to(root).as_posix()
        problems += size_problems(rel, p)
        review = frontmatter(p.read_text(encoding="utf-8", errors="replace")).get("review", "")
        if not DATE.fullmatch(review):
            problems.append(f"{rel}: a candidate carries `review: YYYY-MM-DD` (90 days from the day it moved)")
        elif review < today:
            problems.append(
                f"{rel}: candidate past its review date {review}: prove it (it moves to decisions/global/ with its"
                " proof) or delete it"
            )
    return problems


def main(root: Path, today: str) -> int:
    problems = []
    pages = [p for d in ("decisions", "concepts", "entities", "sources") for p in (root / d).rglob("*.md")]
    names = {p.stem: p for p in pages}
    index = (root / "INDEX.md").read_text(encoding="utf-8")
    for p in pages:
        rel = p.relative_to(root).as_posix()
        text = p.read_text(encoding="utf-8", errors="replace")
        fm = frontmatter(text)
        if not fm:
            problems.append(f"{rel}: no frontmatter")
            continue
        for k in PAGE_FIELDS + (DECISION_FIELDS if fm.get("type") == "decision" else []):
            if k not in fm:
                problems.append(f"{rel}: frontmatter lacks `{k}`")
        if not SCOPE.fullmatch(fm.get("scope", "")):
            problems.append(f"{rel}: scope `{fm.get('scope')}` is neither `global` nor a domain name")
        if fm.get("type") == "decision":
            want = f"decisions/{fm.get('scope')}/"
            if not rel.startswith(want):
                problems.append(f"{rel}: scope `{fm.get('scope')}` but not under {want}")
        if fm.get("type") == "decision" and fm.get("scope") == "global":
            problems += global_problems(rel, fm, text, root) + size_problems(rel, p)
        for src in re.findall(r"[^\[\],\s]+", fm.get("sources", "")):
            if "://" not in src and not (root / src).exists():  # a public URL is a source as well
                problems.append(f"{rel}: source `{src}` does not exist")
        for link in set(re.findall(r"\[\[([^\]|#]+)", text)):
            if link not in names:
                problems.append(f"{rel}: link [[{link}]] does not resolve")
        for label, rx in PATTERNS.items():
            if label in ("key-value",) and rx.search(text) or label not in ("key-value",) and rx.search(text):
                problems.append(f"{rel}: secret pattern `{label}` matches")
        if f"({rel})" not in index:
            problems.append(f"{rel}: not listed in INDEX.md")
    for m in re.finditer(r"\]\(([^)]+\.md)\)", index):
        if not (root / m.group(1)).exists():
            problems.append(f"INDEX.md: `{m.group(1)}` does not exist")
    problems += candidate_problems(root, today)
    for line in problems:
        print(line)
    print(f"{len(pages)} pages checked, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Check the compiled pages of the vault.")
    ap.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--today", default=date.today().isoformat(), help="the day a candidate's review date is held to")
    args = ap.parse_args()
    sys.exit(main(args.root, args.today))
