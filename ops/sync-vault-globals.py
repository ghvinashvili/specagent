#!/usr/bin/env python3
"""Copy the global pages of a vault that every project should start with into the template's vault form (spec 006, R5).

Usage: sync-vault-globals.py --vault <path> [--template <form>]

--vault is the vault whose decisions/global/ is read (it is never written); --template is the vault form that is
written (default: templates/vault of this checkout). The script owns two folders of the form whole, decisions/global/
and context/measurements/ (their .md files), and the `## Decisions (global)` section of its INDEX.md: each run writes
them again from the vault, so a page that left the vault leaves the form, and a second run changes no byte.

A page is a candidate when it says `template: yes`, is not `decision_status: withdrawn`, and is `kind: order`, or
`kind: lesson` whose every `proof:` page exists in the vault; any other page is skipped. A candidate is copied with its
prose untouched and two frontmatter lines rewritten: `sources:` keeps the public URLs and the measurement pages that
travel, `proof:` keeps the measurement pages that travel (an order's `proof:` line that keeps none is dropped, a lesson
with none is refused). A measurement page travels with the page that cites it when it is a file of
context/measurements/ and holds nothing the template refuses. A page's closing `Related:` paragraph (links to go on
to, no rule) loses the entries whose page does not travel, and goes when none is left; the report names each entry
dropped. Any other link of a page must resolve in the form, or the page is refused.

The template refuses, in a page's name and text, a letter of a refused script (Georgian), a model name and an owner
marker (a project, a name, an e-mail address, a path under /home), and whatever the form's own ops/check_pages.py
refuses: a link that does not resolve, a quote of the owner, a size, a secret. A refused page is listed with its reason
and not written, and no page is edited to pass: the vault is the owner's, so the page is fixed there and the script
run again. The other pages are written.

Exit codes: 0 every candidate was carried; 1 some candidate was refused (the others were carried); 2 a usage error, or
a form that fails its own check for something that is not a page it was given (nothing is written).
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FORM = REPO / "templates" / "vault"
OWNED = ("decisions/global", "context/measurements")  # the folders of the form whose .md files the script writes whole
HEADING = re.compile(r"(?m)^## Decisions \(global\)\n(.*?)(?=^## |\Z)", re.DOTALL)
# the four model families, built from parts so that no file of the repo spells one: the pipeline skill's preflight.py
# holds the same four, and a test compares them
MODELS = ("fa" + "ble", "op" + "us", "son" + "net", "hai" + "ku")
MODEL = re.compile(r"\b(?:" + "|".join(MODELS) + r")\b", re.IGNORECASE)  # a flag such as `--model` is not a name
# what the template holds of the owner: the words of ops/tests/test_new_vault.py's OWNER (its projects, domain, folders,
# guide, home folder and account), a path under /home and an e-mail address; a test compares the words
OWNER = re.compile(
    r"(?i)trading|brooks|grantsdaily|gexhex|spoofing|zerogamma|design-record|structure-handoff|README\.ka|\btite\b"
    r"|ghvinashvili|/home/|[\w.+-]+@[\w-]+\.[\w.-]+"
)
ITEM = re.compile(r"[^\[\],\s]+")  # one entry of a one-line list, as check_pages.py reads `sources:` and `proof:`
ENTRY = re.compile(r"\[\[([^\]|#]+)[^\]]*\]\](?:\s*\([^()]*\))?")  # a link, as check_pages.py reads it, and its gloss
WRAP = 120  # the width a `Related:` paragraph is written again at when an entry goes
MEASUREMENT = re.compile(r"context/measurements/[^/]+\.md")
PROBLEM = re.compile(r"decisions/global/([^/:\s]+)\.md(?::(\d+))?: (.*)")  # a page's problem line of check_pages.py
SUMMARY = re.compile(r"\d+ pages checked, \d+ problems")


def usage(message: str) -> int:
    print(f"sync-vault-globals: {message}", file=sys.stderr)
    return 2


def scan(text: str, georgian: re.Pattern, where: str | None = None) -> str | None:
    """The first thing in the text that the template must not hold, with its line (or `where`), or None. A refused
    letter is never repeated in the report."""
    for pattern, what in (
        (georgian, "a letter of a refused script (Georgian)"),
        (MODEL, "a model name"),
        (OWNER, "an owner marker"),
    ):
        found = pattern.search(text)
        if found:
            place = where or f"line {text.count(chr(10), 0, found.start()) + 1}"
            return f"{place}: {what}" + ("" if pattern is georgian else f" `{found.group(0)}`")
    return None


def exists(vault: Path, rel: str) -> bool:
    """A proof page, as check_pages.py reads it: a file under the vault's context/."""
    context, target = (vault / "context").resolve(), (vault / rel).resolve()
    return rel.startswith("context/") and target.is_file() and target.is_relative_to(context)


def select(vault: Path, check) -> tuple[dict[str, str], dict[str, str]]:
    """The pages of the vault's decisions/global/ that the template may carry (name -> text), and the others skipped
    (name -> why)."""
    chosen, skipped = {}, {}
    for path in sorted((vault / "decisions" / "global").glob("*.md")):
        name = path.stem
        try:
            text = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            skipped[name] = "not UTF-8 text"
            continue
        fm = check.frontmatter(text)
        proofs = ITEM.findall(fm.get("proof", ""))
        if fm.get("template") != "yes":
            skipped[name] = f"`template: {fm['template']}`" if "template" in fm else "no `template:` line"
        elif fm.get("decision_status") == "withdrawn":
            skipped[name] = "withdrawn"
        elif fm.get("kind") == "order":
            chosen[name] = text
        elif fm.get("kind") != "lesson":
            skipped[name] = f"kind `{fm.get('kind', '')}` is neither `lesson` nor `order`"
        elif not proofs or not all(exists(vault, rel) for rel in proofs):
            skipped[name] = "a lesson without an existing proof page"
        else:
            chosen[name] = text
    return chosen, skipped


def blocked(vault: Path, rel: str, check) -> str | None:
    """Why a page named by `sources:` or `proof:` does not travel with the global page that cites it, or None."""
    path = vault / rel
    if not MEASUREMENT.fullmatch(rel):
        return "not a page of context/measurements/"
    if path.is_symlink() or not path.is_file():
        return "not a file of the vault"
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return "not UTF-8 text"
    found = scan(rel, check.GEORGIAN, "its name") or scan(text, check.GEORGIAN)
    secret = next((label for label, rx in check.PATTERNS.items() if rx.search(text)), None)
    return found or (f"secret pattern `{secret}` matches" if secret else None)


def with_line(text: str, key: str, kept: list[str] | None) -> str:
    """The page with its frontmatter line `key:` written as the list `kept` (None: the line deleted); nothing else
    changes."""
    head = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    if not head:
        return text
    lines = []
    for line in head.group(1).split("\n"):
        if ":" in line and line.partition(":")[0].strip() == key:
            if kept is not None:
                lines.append(f"{key}: [{', '.join(kept)}]")
        else:
            lines.append(line)
    return "---\n" + "\n".join(lines) + "\n---\n" + text[head.end() :]


def hook(title: str) -> str:
    """The INDEX hook from a page's title: one pair of YAML quotes around the title goes (V10)."""
    quoted = len(title) > 1 and title[0] == title[-1] and title[0] in "\"'"
    return title[1:-1] if quoted else title


def trim_related(text: str, travelling: set[str]) -> tuple[str, list[str]]:
    """The page without the entries of its `Related:` paragraph whose page does not travel, and the pages they named.
    The paragraph is a list of links, each with an optional gloss in parentheses, for the reader to go on to: it holds
    no rule, so an entry that leads nowhere in the template goes with its gloss, and a paragraph left with no entry goes
    with its blank line. The other entries keep their order; a paragraph that holds anything but entries, and every
    other link of the page, stay as they are."""
    head = re.match(r"---\n.*?\n---\n", text, re.DOTALL)
    start = head.end() if head else 0
    lines, out, dropped, i = text[start:].split("\n"), [], [], 0
    while i < len(lines):
        if not lines[i].startswith("Related:"):
            out.append(lines[i])
            i += 1
            continue
        end = i
        while end + 1 < len(lines) and lines[end + 1].strip():
            end += 1
        paragraph, i = "\n".join(lines[i : end + 1]), end + 1
        flat = " ".join(paragraph.split())  # one line, so that a gloss the writer wrapped is one piece
        entries = list(ENTRY.finditer(flat))
        if (
            not entries
            or ENTRY.sub("", flat.removeprefix("Related:")).strip(" ,;.")
            or all(m.group(1) in travelling for m in entries)
        ):
            out += paragraph.split("\n")  # prose, or every entry travels: as it was
            continue
        dropped += [m.group(1) for m in entries if m.group(1) not in travelling]
        kept = [m.group(0) for m in entries if m.group(1) in travelling]
        if kept:
            rebuilt = "Related: " + ", ".join(kept) + ("." if flat.endswith(".") else "")
            out += textwrap.fill(rebuilt, width=WRAP, break_long_words=False, break_on_hyphens=False).split("\n")
        elif out and not out[-1].strip():
            out.pop()
    return text[:start] + "\n".join(out), dropped


def prepare(vault: Path, text: str, check) -> tuple[str, list[str], str | None]:
    """A candidate as it goes to the template: its text with `sources:` and `proof:` reduced to what travels, the
    measurement pages that go with it, and why it cannot go (None when it can)."""
    fm = check.frontmatter(text)
    proofs, sources = ITEM.findall(fm.get("proof", "")), ITEM.findall(fm.get("sources", ""))
    why = {rel: blocked(vault, rel, check) for rel in dict.fromkeys(proofs + sources)}
    kept_proofs = [rel for rel in proofs if why[rel] is None]
    kept_sources = [rel for rel in sources if "://" in rel or why[rel] is None]
    if fm.get("kind") == "lesson" and not kept_proofs:
        reasons = "; ".join(f"{rel}: {why[rel]}" for rel in proofs)
        return (
            text,
            [],
            f"a lesson's proof page of context/measurements/ must travel with it, and none does ({reasons})",
        )
    out = text
    if kept_sources != sources:
        out = with_line(out, "sources", kept_sources)
    if kept_proofs != proofs:
        out = with_line(out, "proof", kept_proofs or None)
    return out, list(dict.fromkeys(kept_proofs + [rel for rel in kept_sources if "://" not in rel])), None


def index_with(index: str, lines: list[str]) -> str | None:
    """The INDEX text with the body of its `## Decisions (global)` section replaced by the lines (None: no such section).
    An empty selection leaves an empty section as it is."""
    section = HEADING.search(index)
    if not section:
        return None
    if not lines and not section.group(1).strip():
        return index
    body = "\n" + "".join(f"{line}\n" for line in lines) + ("\n" if lines else "")
    return index[: section.start(1)] + body + index[section.end(1) :]


def write(path: Path, data: bytes) -> None:
    if not path.is_file() or path.read_bytes() != data:  # an unchanged file is left alone, its time too
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def stage(form: Path, work: Path, pages: dict[str, str], proofs: dict[str, bytes], lines: list[str]) -> str | None:
    """The form copied to `work` with its owned folders emptied and the pages, proof pages and INDEX lines written;
    a message when the form has no section for them."""
    shutil.copytree(form, work, ignore=shutil.ignore_patterns("__pycache__"))
    for folder in OWNED:
        for old in (work / folder).glob("*.md"):
            old.unlink()
    for name, text in pages.items():
        write(work / "decisions" / "global" / f"{name}.md", text.encode("utf-8"))
    for rel, data in proofs.items():
        write(work / rel, data)
    index = index_with((work / "INDEX.md").read_text(encoding="utf-8"), lines)
    if index is None:
        return "the form's INDEX.md has no `## Decisions (global)` section"
    write(work / "INDEX.md", index.encode("utf-8"))
    return None


def mirror(work: Path, form: Path) -> None:
    """Make the form's owned folders and its INDEX.md the staged ones: stale pages go, changed files are written."""
    for folder in OWNED:
        want = {p.name for p in (work / folder).glob("*.md")}
        for old in (form / folder).glob("*.md"):
            if old.name not in want:
                old.unlink()
        for name in sorted(want):
            write(form / folder / name, (work / folder / name).read_bytes())
    write(form / "INDEX.md", (work / "INDEX.md").read_bytes())


def run_check(work: Path) -> tuple[int, list[str], str]:
    """The form's own check on the staged form: its exit code, its problem lines, its error output."""
    done = subprocess.run(
        [sys.executable, "-B", str(work / "ops" / "check_pages.py"), str(work)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
        check=False,
    )
    return done.returncode, [ln for ln in done.stdout.splitlines() if ln and not SUMMARY.fullmatch(ln)], done.stderr


class Stop(Exception):
    """A run that cannot go on and writes nothing: the message is what the usage error says."""


def resolvable(form: Path) -> set[str]:
    """The pages of the form, other than its global pages, that a link may name (the pages check_pages.py counts)."""
    return {
        p.stem
        for d in ("decisions", "concepts", "entities", "sources")
        for p in (form / d).rglob("*.md")
        if p.parent != form / "decisions" / "global"
    }


def settle(vault: Path, form: Path, check, ready: dict, refused: dict[str, str], tmp: Path):
    """Stage the pages not yet refused, with the `Related:` entries that lead nowhere taken out, and run the form's
    check on the stage. A page whose text holds what the template refuses, or that the check names, is refused (its
    reason goes into `refused`), and the stage is made again without it, until a run is clean. Returns that stage, the
    names of the pages it carries and the entries dropped from each page's `Related:` paragraph."""
    for attempt in range(len(ready) + 2):  # each round refuses at least one page, or the run is clean
        keep = [name for name in sorted(ready) if name not in refused]
        travelling = set(keep) | resolvable(form)
        pages, dropped, before = {}, {}, len(refused)
        for name in keep:
            pages[name], dropped[name] = trim_related(ready[name][0], travelling)
            if hit := scan(name, check.GEORGIAN, "slug") or scan(pages[name], check.GEORGIAN):
                refused[name] = hit
        if len(refused) != before:
            continue  # a page that left may have been named in a `Related:` paragraph: trim again
        proofs = {rel: (vault / rel).read_bytes() for name in keep for rel in ready[name][1]}
        titles = {name: hook(check.frontmatter(text).get("title") or name) for name, text in pages.items()}
        lines = [f"- [{name}](decisions/global/{name}.md): {titles[name]}" for name in keep]
        work = tmp / f"stage{attempt}"
        if message := stage(form, work, pages, proofs, lines):
            raise Stop(message)
        code, problems, errors = run_check(work)
        if code not in (0, 1):
            raise Stop(f"the form's check_pages.py failed ({errors.strip()[-300:]})")
        if not problems:
            return work, keep, dropped
        named: dict[str, list[str]] = {}
        for line in problems:
            found = PROBLEM.fullmatch(line)
            if not found or found.group(1) not in pages:
                raise Stop(f"the form fails its own check for more than the pages it was given: {line}")
            place = f"line {found.group(2)}: " if found.group(2) else ""
            named.setdefault(found.group(1), []).append(place + found.group(3))
        refused.update({name: "; ".join(texts) for name, texts in named.items()})
    raise Stop("no clean run after refusing the pages the check names")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Copy the global pages of a vault into the template's vault form.")
    ap.add_argument("--vault", type=Path, required=True, help="the vault whose decisions/global/ is read")
    ap.add_argument("--template", type=Path, default=FORM, help="the vault form that is written (default: %(default)s)")
    args = ap.parse_args(argv)
    vault, form = args.vault.resolve(), args.template.resolve()
    if vault == form:
        return usage("--vault is the template's vault form itself: name the vault whose pages are copied")
    if not (vault / "decisions" / "global").is_dir():
        return usage(f"{vault} has no decisions/global/ folder: --vault is the root of a vault")
    if not (form / "ops" / "check_pages.py").is_file():
        return usage(f"{form} is not a vault form: it has no ops/check_pages.py")
    sys.dont_write_bytecode = True  # the form's ops/ is imported below: leave no cache in it
    sys.path.insert(0, str(form / "ops"))
    import check_pages as check  # the form's own check, whichever form --template names

    candidates, skipped = select(vault, check)
    ready, refused = {}, {}
    for name, text in candidates.items():
        page, proofs, why = prepare(vault, text, check)
        if why:
            refused[name] = why
        else:
            ready[name] = (page, proofs)
    try:
        with tempfile.TemporaryDirectory(prefix="sync-vault-globals-") as tmp:
            work, carried, dropped = settle(vault, form, check, ready, refused, Path(tmp))
            mirror(work, form)
    except Stop as stop:
        return usage(f"{stop}; nothing written")
    for name in carried:
        gone = ", ".join(dict.fromkeys(dropped[name]))
        print(f"carried {name}" + (f" (dropped from Related: {gone})" if gone else ""))
    for label, group in (("refused", refused), ("skipped", skipped)):
        for name in sorted(group):
            print(f"{label} {name}: {group[name]}")
    print(f"{len(carried)} carried, {len(refused)} refused, {len(skipped)} skipped")
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
