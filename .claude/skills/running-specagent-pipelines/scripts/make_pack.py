#!/usr/bin/env python3
"""Build a role's startup pack: the standing orders a fresh session would otherwise read with tools at every start
(owner, 2026-10-25: cut what a session loads at start). Passed with --append-system-prompt-file, it is a cached prefix
that every session of the lane shares, and none of it is read again with tools. Since 2026-11-01 (owner) every lane
has one, built once before its first launch and passed by the agent's own `extra_prompt` in the watcher's config.
The pack holds no time stamp: built from unchanged files it is byte for byte the same, so the cache holds.

Usage: python3 -I make_pack.py [--no-note] <run-dir>/_packs.json [<role> ...]
  (writes <run-dir>/_pack-<role>.md for each role, every role of the config when none is named; prints each size)
The config's folder is the run folder; keys that start with `_` are comments. `roles` (required): role -> the file
names in the run folder; `name` (default: the run folder's name); `lessons` (default `lessons.md`); `sections`
(default "Read first" and "Known error classes"). A missing role, file, lessons file or section: one stderr line,
exit 2, and no pack is written.
`--no-note` leaves every file named `handoff-*.md` out of the packs ("stable first, unique last"): a hand-over note is
unique to one session and a pack holds only what is byte-identical across a role's sessions, so the note is read
after the pack, as the last item of the launch prompt. The hand-over rule (`_handoff-rule.md`) is the same for every
session and stays. With the option a note need not exist when the pack is built; a role left with no file is an error.
"""

import argparse
import json
import pathlib
import sys

PROG = "make_pack.py"
SECTIONS = ["Read first", "Known error classes"]
HEAD = """# Your standing orders (startup pack of {name}/{role})

These files of the run folder {run} are copied here in full, so you do not read them with tools: {files}, and the
{sections} of {lessons}. They are frozen at the lane's first launch. Lines added to {lessons} during the run carry
their date: read those dated on or after the run's first day. Everything else (the plan, the logs, the rest of
{lessons}, the spec) you read when a step needs it, by line ranges.{note}

"""
NO_NOTE = " Your hand-over note is not in this pack, as it belongs to one session: read it after the pack."


class PackError(Exception):
    """A role, a file, the lessons file or a section that the config names is missing."""


def quoted(titles: list[str]) -> str:
    """The section titles in quotes, joined as a list is in prose: "A", "A" and "B", "A", "B" and "C"."""
    names = [f'"{t}"' for t in titles]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def section(text: str, title: str) -> str | None:
    """Section `## <title>` (a heading line that is the title or starts with it and a space) up to the line before the
    next `## ` line, trailing whitespace stripped; None when no heading matches."""
    lines = text.split("\n")
    head = f"## {title}"
    for i, line in enumerate(lines):
        if line == head or line.startswith(head + " "):
            end = next((j for j in range(i + 1, len(lines)) if lines[j].startswith("## ")), len(lines))
            return "\n".join(lines[i:end]).rstrip()
    return None


def is_note(name: str) -> bool:
    """A role's hand-over note, `handoff-<role>.md` (`_handoff-rule.md` is the rule, the same for every session)."""
    base = pathlib.PurePath(name).name
    return base.startswith("handoff-") and base.endswith(".md")


def load(config: pathlib.Path, no_note: bool = False) -> dict:
    """The packs config with its defaults filled in; `run` is the config's folder. With `no_note` every role's file
    list is without its hand-over notes."""
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise PackError(f"cannot read {config}: {e}") from None
    if not isinstance(data, dict) or not isinstance(data.get("roles"), dict):
        raise PackError(f"{config} has no `roles` object")
    run = config.resolve().parent
    roles = {role: files for role, files in data["roles"].items() if not role.startswith("_")}
    if no_note:
        roles = {role: [name for name in files if not is_note(name)] for role, files in roles.items()}
    return {
        "run": run,
        "name": data.get("name", run.name),
        "roles": roles,
        "lessons": data.get("lessons", "lessons.md"),
        "sections": data.get("sections", SECTIONS),
        "no_note": no_note,
    }


def check(cfg: dict, roles: list[str]) -> str:
    """Raise PackError for the first missing role, file, lessons file or section, or a role with no file left; return
    the lessons file's text."""
    run = cfg["run"]
    for role in roles:
        if role not in cfg["roles"]:
            raise PackError(f"no role {role!r} in the config's `roles`")
    for role in roles:
        if not cfg["roles"][role]:
            raise PackError(
                f"role {role!r} has no file left to pack" + (" without its notes" if cfg["no_note"] else "")
            )
        for name in cfg["roles"][role]:
            if not (run / name).is_file():
                raise PackError(f"role {role!r} names {name}, which is not a file in {run}")
    lessons = run / cfg["lessons"]
    if not lessons.is_file():
        raise PackError(f"no lessons file {lessons}")
    text = lessons.read_text(encoding="utf-8")
    for title in cfg["sections"]:
        if section(text, title) is None:
            raise PackError(f"no section '## {title}' in {lessons}")
    return text


def build(cfg: dict, role: str, lessons: str) -> str:
    """The pack's text for one role: the head, each of its files in full, then the lessons sections."""
    run, files, titles = cfg["run"], cfg["roles"][role], cfg["sections"]
    sections = quoted(titles) + (" sections" if len(titles) > 1 else " section")
    out = [
        HEAD.format(
            name=cfg["name"],
            role=role,
            run=run,
            files=", ".join(files),
            sections=sections,
            lessons=cfg["lessons"],
            note=NO_NOTE if cfg["no_note"] else "",
        )
    ]
    for name in files:
        out.append(f"\n---\n\n## File: {name}\n\n" + (run / name).read_text(encoding="utf-8").rstrip() + "\n")
    body = "\n\n".join(section(lessons, title) or "" for title in titles)
    out.append(f"\n---\n\n## File: {cfg['lessons']} ({quoted(titles)} only)\n\n" + body + "\n")
    return "".join(out)


def main(argv: list[str] | None = None) -> int:
    """Check every role named, then write each pack whose text changed and print its size."""
    ap = argparse.ArgumentParser(prog=PROG, description="Build the startup packs a packs config names.")
    ap.add_argument("config", type=pathlib.Path, help="<run-dir>/_packs.json")
    ap.add_argument("roles", nargs="*", help="roles to build (default: every role of the config, in its order)")
    ap.add_argument(
        "--no-note",
        action="store_true",
        help="leave every file named handoff-*.md out of the packs (a note is unique to one session)",
    )
    args = ap.parse_args(argv)
    try:
        cfg = load(args.config, args.no_note)
        roles = args.roles or list(cfg["roles"])
        lessons = check(cfg, roles)
    except PackError as e:
        print(f"{PROG}: {e}", file=sys.stderr)
        return 2
    for role in dict.fromkeys(roles):
        text = build(cfg, role, lessons)
        path = cfg["run"] / f"_pack-{role}.md"
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
        print(f"{path.name}: {len(text.encode()) // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
