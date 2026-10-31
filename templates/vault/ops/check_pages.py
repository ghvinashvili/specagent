#!/usr/bin/env python3
"""Check the compiled pages of the vault: links resolve, sources exist, frontmatter complete, no secrets, INDEX covers
every page. Exit 1 when anything is found. Deterministic; no model.

Usage: check_pages.py [vault-root]
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect_memory import PATTERNS  # noqa: E402

PAGE_FIELDS = ["title", "type", "scope", "status", "updated", "audience", "sources"]
DECISION_FIELDS = ["decided", "by", "why", "decision_status", "would_change_if"]
SCOPE = re.compile(r"[a-z][a-z0-9-]*")  # `global`, or the name of one domain: its decisions live in decisions/<domain>/


def frontmatter(text: str) -> dict:
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        if _:
            out[k.strip()] = v.strip()
    return out


def main(root: Path) -> int:
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
        for src in re.findall(r"[^\[\],\s]+", fm.get("sources", "")):
            if "://" not in src and not (root / src).exists():  # a public URL is a source as well
                problems.append(f"{rel}: source `{src}` does not exist")
        for link in set(re.findall(r"\[\[([^\]|#]+)", text)):
            if link not in names:
                problems.append(f"{rel}: link [[{link}]] does not resolve")
        for label, rx in PATTERNS.items():
            if label in ("key-value",) and rx.search(text):
                problems.append(f"{rel}: secret pattern `{label}` matches")
            elif label not in ("key-value",) and rx.search(text):
                problems.append(f"{rel}: secret pattern `{label}` matches")
        if f"({rel})" not in index:
            problems.append(f"{rel}: not listed in INDEX.md")
    for m in re.finditer(r"\]\(([^)]+\.md)\)", index):
        if not (root / m.group(1)).exists():
            problems.append(f"INDEX.md: `{m.group(1)}` does not exist")
    for line in problems:
        print(line)
    print(f"{len(pages)} pages checked, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]))
