"""The catalogue of what a role session loads (spec 3): every agent file, contract, example brief, skill (whole and by
its description line) and pinned ECC text in bytes and tokens; one role's start-up prefix checked against the bounds of
spec 3.8; every brief's domain section checked against its form (spec 4.6, 4.7).

  python3 -I scripts/manager/catalogue.py table [--checkout DIR]
  python3 -I scripts/manager/catalogue.py prefix FILE... [--skill NAME]... [--ecc NAME]... [--checkout DIR]
  python3 -I scripts/manager/catalogue.py briefs DIR [--checkout DIR]

Exit codes: 0 done; 1 a prefix over 13,000 tokens or a brief with a problem; 2 a folder or file that cannot be read.
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

SKILL_REL = ".claude/skills/running-specagent-pipelines"
ECC_DIR = ".claude/ecc/agents"
SECTION = "## Domain checklist and skills"
SLOT = "<!-- launch:"  # the paste slot's line starts with this
BYTES_PER_TOKEN = 4  # spec 3.1: about four bytes per token of English Markdown
PREFIX_SOFT = 10_000  # tokens; spec 3.8: within
PREFIX_HARD = 13_000  # tokens; spec 3.8: near up to here, over above
HALF_USE_MAX = 2_500  # tokens; spec 3.1 (line 227): an item half the sessions use earns a place only up to this
DOMAIN_MAX_LINES = 59  # spec 4.7 and 10.17: a domain section under 60 lines
SKILLS_MAX = 5  # docs/quality/context-budget.yaml:21-24
KINDS = ("type", "contract", "brief", "skill", "description", "ecc")
HEAD = "| name | bytes | tokens | half-use |\n| --- | ---: | ---: | --- |"
RANGE = re.compile(r"(\S+):(\d+)-(\d+)")  # one item of a `Spec:` line
SKILL_ITEM = re.compile(r"(\S+) \((.+)\)")  # one item of a `Skills:` line
SKILL_PATH = re.compile(r"\.claude/skills/[^/]+/SKILL\.md")


@dataclass(frozen=True)
class Item:
    """One file a role session may load, measured in bytes."""

    kind: str  # one of KINDS
    name: str  # file stem; for skill and description the skill's folder name
    path: str  # relative to the checkout, POSIX form
    size: int  # bytes; for description the frontmatter line with its newline


def default_checkout() -> Path:
    """The checkout this skill sits in (this file is .claude/skills/<skill>/scripts/manager/catalogue.py)."""
    return Path(__file__).resolve().parents[5]


def tokens(n: int) -> int:
    """Bytes to tokens: n / BYTES_PER_TOKEN rounded half up (spec 3.1)."""
    return (n + BYTES_PER_TOKEN // 2) // BYTES_PER_TOKEN


def verdict(t: int) -> str:
    """The verdict of spec 3.8 on a prefix of t tokens: within, near or over."""
    if t <= PREFIX_SOFT:
        return "within"
    return "near" if t <= PREFIX_HARD else "over"


def description_line(text: str) -> str:
    """The frontmatter's first `description:` line with a newline appended; "" when the frontmatter has none."""
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        return ""
    end = lines.index("---", 1)
    return next((line + "\n" for line in lines[1:end] if line.startswith("description:")), "")


def markdown_files(checkout: Path, folder: str, skip_readme: bool = False) -> list[Path]:
    """The `*.md` files of a folder of the checkout, sorted; README.md left out when skip_readme is set."""
    found = sorted((checkout / folder).glob("*.md"))
    return [p for p in found if p.is_file() and not (skip_readme and p.name == "README.md")]


def measure(checkout: Path) -> list[Item]:
    """Every agent file, contract, example brief, skill, skill description line and pinned ECC text, in bytes."""

    def item(kind: str, name: str, path: Path, size: int | None = None) -> Item:
        return Item(kind, name, path.relative_to(checkout).as_posix(), path.stat().st_size if size is None else size)

    items = [item("type", p.stem, p) for p in markdown_files(checkout, ".claude/agents")]
    items += [item("contract", p.stem, p) for p in markdown_files(checkout, "docs/roles/types")]
    items += [item("brief", p.stem, p) for p in markdown_files(checkout, f"{SKILL_REL}/example", skip_readme=True)]
    for path in sorted((checkout / ".claude" / "skills").glob("*/SKILL.md")):
        items.append(item("skill", path.parent.name, path))
        line = description_line(path.read_text(encoding="utf-8"))
        if line:
            items.append(item("description", path.parent.name, path, len(line.encode("utf-8"))))
    items += [item("ecc", p.stem, p) for p in markdown_files(checkout, ECC_DIR, skip_readme=True)]
    return sorted(items, key=lambda i: (KINDS.index(i.kind), i.name))


def row(item: Item) -> str:
    """One table row: name, bytes, tokens, and `over` when the item passes the half-use bound."""
    t = tokens(item.size)
    return f"| {item.name} | {item.size} | {t} | {'over' if t > HALF_USE_MAX else ''} |"


def table(items: list[Item]) -> str:
    """The catalogue as Markdown: a block per kind in KINDS order, a row per item and a total taken from the bytes."""
    blocks = []
    for kind in KINDS:
        group = [i for i in items if i.kind == kind]
        if group:
            total = sum(i.size for i in group)
            last = f"| total | {total} | {tokens(total)} |  |"
            blocks.append("\n".join([f"### {kind} ({len(group)})", HEAD, *map(row, group), last]))
    return "\n\n".join(blocks) + "\n"


def prefix(checkout: Path, files: list[Path], skills: list[str], ecc: list[str]) -> dict:
    """One role's start-up prefix: files whole, skills by their description line, ECC texts whole (spec 3.8)."""
    parts = [(str(path), len(Path(path).read_bytes())) for path in files]
    for name in skills:
        text = (checkout / ".claude" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        parts.append((f"{name} (description)", len(description_line(text).encode("utf-8"))))
    parts += [(f"{ECC_DIR}/{name}.md", len((checkout / ECC_DIR / f"{name}.md").read_bytes())) for name in ecc]
    size = sum(n for _, n in parts)
    return {"bytes": size, "tokens": tokens(size), "verdict": verdict(tokens(size)), "parts": parts}


def parse_spec(line: str) -> dict:
    """The ranges and the why of a `Spec:` line (spec 4.7); ValueError when the line is not in its form."""
    what, dash, why = line.removeprefix("Spec: ").partition(" — ")
    if not dash or not why.strip():
        raise ValueError("Spec: line without ` — <why>`")
    if what.strip() == "none":
        return {"ranges": [], "why": why.strip()}
    ranges = []
    for item in what.split(", "):
        found = RANGE.fullmatch(item.strip())
        if not found or not 1 <= int(found[2]) <= int(found[3]):
            raise ValueError(f"Spec range not <file>:<a>-<b>: {item}")
        ranges.append((found[1], int(found[2]), int(found[3])))
    return {"ranges": ranges, "why": why.strip()}


def parse_skills(line: str) -> dict:
    """The skills and their steps of a `Skills:` line (spec 4.6), or the why of `none`; ValueError out of form."""
    value = line.removeprefix("Skills: ")
    if value.startswith("none"):
        what, dash, why = value.partition(" — ")
        if what != "none" or not dash or not why.strip():
            raise ValueError("Skills: none without ` — <why>`")
        return {"skills": [], "why": why.strip()}
    skills = []
    for item in value.split("; "):
        found = SKILL_ITEM.fullmatch(item.strip())
        if not found:
            raise ValueError(f"Skills item not <path> (<step>): {item}")
        skills.append((found[1], found[2]))
    return {"skills": skills, "why": ""}


def range_problems(ranges: list[tuple[str, int, int]], checkout: Path) -> list[str]:
    """Each range's missing file or end past its file, then the ranges' size against the 60-line bound."""
    problems = []
    for path, a, b in ranges:
        file = checkout / path
        if not file.is_file():
            problems.append(f"Spec file missing: {path}")
        elif b > (count := len(file.read_bytes().splitlines())):
            problems.append(f"Spec range outside its file: {path}:{a}-{b} ({count} lines)")
    held = sum(b - a + 1 for _, a, b in ranges)
    if held > DOMAIN_MAX_LINES:
        problems.append(f"Spec ranges hold {held} lines (under {DOMAIN_MAX_LINES + 1})")
    return problems


def skill_problems(paths: list[str], checkout: Path) -> list[str]:
    """Each skill path outside .claude/skills/, missing or named again, then the count against SKILLS_MAX."""
    problems, seen = [], set()
    for path in paths:
        if not SKILL_PATH.fullmatch(path):
            problems.append(f"skill not under .claude/skills/: {path}")
        elif not (checkout / path).is_file():
            problems.append(f"skill missing: {path}")
        elif path in seen:
            problems.append(f"skill named twice: {path}")
        seen.add(path)
    if len(paths) > SKILLS_MAX:
        problems.append(f"{len(paths)} skills (at most {SKILLS_MAX})")
    return problems


def check_brief(text: str, checkout: Path) -> list[str]:
    """The problems of a brief's domain section (spec 4.6, 4.7), in the order of its form; [] when it holds."""
    lines = text.splitlines()
    count = lines.count(SECTION)
    if count != 1:
        return [f"{count} `{SECTION}` sections (one expected)" if count else f"no `{SECTION}` section"]
    start = lines.index(SECTION) + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    body = [line for line in lines[start:end] if line.strip()]
    specs = [line for line in body if line.startswith("Spec: ")]
    skills = [line for line in body if line.startswith("Skills: ")]
    problems = [
        f"{len(v)} `{k}` lines (one expected)" for k, v in (("Spec:", specs), ("Skills:", skills)) if len(v) != 1
    ]
    ranges = []
    if len(specs) == 1:
        try:
            ranges = parse_spec(specs[0])["ranges"]
        except ValueError as error:
            problems.append(str(error))
        else:
            problems += range_problems(ranges, checkout)
    if len(skills) == 1:
        try:
            problems += skill_problems([path for path, _ in parse_skills(skills[0])["skills"]], checkout)
        except ValueError as error:
            problems.append(str(error))
    slots = [line for line in body if line.startswith(SLOT)]
    other = [line for line in body if not line.startswith(("Spec: ", "Skills: ", SLOT))]
    if len(other) > DOMAIN_MAX_LINES:
        problems.append(f"domain section holds {len(other)} lines (under {DOMAIN_MAX_LINES + 1})")
    if ranges and not slots and not other:
        problems.append("Spec names ranges but the section holds neither the launch slot nor the pasted text")
    return problems


def check_briefs(folder: Path, checkout: Path) -> list[str]:
    """The problems of every `*-assignment.md` brief in a folder, each as `<file name>: <problem>`."""
    return [
        f"{path.name}: {problem}"
        for path in sorted(folder.glob("*-assignment.md"))
        for problem in check_brief(path.read_text(encoding="utf-8"), checkout)
    ]


def parser() -> argparse.ArgumentParser:
    """The command line: the subcommands table, prefix and briefs, each taking --checkout."""
    ap = argparse.ArgumentParser(prog="catalogue.py", description="The catalogue of what a role session loads.")
    sub = ap.add_subparsers(dest="command", required=True)
    helps = {
        "table": "print every item in bytes and tokens, a block per kind",
        "prefix": "add up one role's start-up prefix; exit 1 over 13,000 tokens",
        "briefs": "check the domain section of every *-assignment.md in DIR; exit 1 on a problem",
    }
    commands = {name: sub.add_parser(name, help=text) for name, text in helps.items()}
    commands["prefix"].add_argument("files", nargs="+", type=Path, metavar="FILE")
    commands["prefix"].add_argument("--skill", action="append", default=[], metavar="NAME")
    commands["prefix"].add_argument("--ecc", action="append", default=[], metavar="NAME")
    commands["briefs"].add_argument("folder", type=Path, metavar="DIR")
    for command in commands.values():
        command.add_argument("--checkout", type=Path, metavar="DIR", help="default: the checkout this skill sits in")
    return ap


def main(argv: list[str] | None = None) -> int:
    """Run one subcommand; exit 0 when done, 1 over 13,000 tokens or on a brief's problem, 2 on an unreadable path."""
    args = parser().parse_args(argv)
    checkout = args.checkout or default_checkout()
    for folder in (checkout, args.folder) if args.command == "briefs" else (checkout,):
        if not folder.is_dir():
            print(f"catalogue.py: no such folder: {folder}", file=sys.stderr)
            return 2
    try:
        if args.command == "table":
            print(table(measure(checkout)), end="")
            return 0
        if args.command == "prefix":
            found = prefix(checkout, args.files, args.skill, args.ecc)
            for label, size in found["parts"]:
                print(f"{size}\t{label}")
            print(f"total: {found['bytes']} bytes, {found['tokens']} tokens, {found['verdict']}")
            return 1 if found["verdict"] == "over" else 0
        problems = check_briefs(args.folder, checkout)
        print("\n".join(problems) or f"ok: {len(list(args.folder.glob('*-assignment.md')))} briefs checked")
        return 1 if problems else 0
    except (OSError, UnicodeDecodeError) as error:
        print(f"catalogue.py: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
