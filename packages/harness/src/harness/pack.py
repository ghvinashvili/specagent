"""harness/pack.py — the knowledge pack: what a role type is given up front instead of searching for it.

The store is the wiki (`wiki/`, written by the librarian and checked against `context/`). A pack is only a way of
delivering it: the pages whose `audience` names the type, plus the files its row in docs/roles/need-to-know.yaml
lists, concatenated in a fixed order by this script. No model takes part, so nothing is lost or rephrased here.
The launcher writes the pack to `<stage dir>/pack.md` and passes it with `--append-system-prompt-file`, so it follows
the agent file in the system prompt. That is the only place where two sessions share it in the prompt cache: the
cache is read at a breakpoint, Claude Code sets one at the end of the system prompt, and the first message of a
session also carries run-specific text (measured on 2026-10-01: with the pack in the first message the second
session of a type read 4,831 tokens from the cache, the tools and the agent file, and wrote the pack again).
"""

from __future__ import annotations

import fnmatch
import hashlib
import re
from pathlib import Path

import yaml

from . import access

CHARS_PER_TOKEN = 4  # estimate for the budget check only; the real count is in the session's usage
# What the material of one stage adds to its system prompt at most. The material a job names is given whole, so that
# the session searches for nothing and misses nothing; the budget is only the ceiling: about 500,000 tokens, half of
# a 1,000,000-token window, and about 80,000 on a model with a 200,000-token window (SMALL_WINDOW). The other half is
# room for the work. Every request reads the whole prompt again from the cache. What does not fit is named in the
# section and by `harness material` before the launch: the manager splits the stage instead of letting it search. Of
# the budget, what the harness adds on its own (pieces.select: what the stage's texts cite and name, and what matches
# its job) takes at most AUTO_MAX_CHARS. Choices of this repository, to adjust after measuring sessions
# (`harness cache-report`).
MATERIAL_MAX_CHARS = 2_000_000
AUTO_MAX_CHARS = 200_000
SMALL_WINDOW = {"haiku": (320_000, 100_000)}  # model: (material, what the harness adds), for a 200,000-token window
AUTO = ("cited", "named", "related")  # the reasons pieces.select gives; every other piece was asked for
MATERIAL_HEADING = re.compile(r"^##\s+Material\s*$", re.IGNORECASE)
# The line of the material that names the files that are not text: an image, a PDF. The meaning of a chart, a
# screenshot or a drawing is in the picture, which the prompt cannot hold: the session opens each with Read.
NOT_TEXT = "Not text, so not in this section; open each with Read and account for it like any other file"
DESCRIPTION = re.compile(r"\s[—–-]\s|(?<=`):\s")  # where the description of a listed piece begins
PIECE = re.compile(r"^(?P<path>[^:]+?)(?::(?P<first>\d+)(?:-(?P<last>\d+))?)?$")  # `path`, `path:12`, `path:12-40`


def _front(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    head, _, body = text[4:].partition("\n---\n")
    return (yaml.safe_load(head) or {}), body


def pages(root: Path, role_type: str) -> list[Path]:
    """Wiki pages for the type: `audience` contains the type or `all`, and the page is `verified`. A draft, a
    disputed and a stale page are left out: an outdated statement beside a current one is worse than a missing one."""
    out = []
    for p in sorted((root / "wiki").rglob("*.md")) if (root / "wiki").exists() else []:
        fm, _ = _front(p.read_text(encoding="utf-8"))
        aud = fm.get("audience") or []
        if (role_type in aud or "all" in aud) and fm.get("status") == "verified":
            out.append(p)
    return out


def build(root: Path, policy: dict, role_type: str) -> str:
    """The pack text, or an empty string when the type has no pack. Byte-identical for identical files."""
    parts = []
    for rel in access.pack_files(policy, role_type):
        if not (root / rel).is_file():
            raise access.AccessError(f"type {role_type}: pack file {rel} does not exist (docs/roles/need-to-know.yaml)")
        parts.append(f"### {rel}\n\n{(root / rel).read_text(encoding='utf-8').strip()}")
    for p in pages(root, role_type):
        parts.append(f"### {p.relative_to(root).as_posix()}\n\n{p.read_text(encoding='utf-8').strip()}")
    if not parts:
        return ""
    body = "\n\n".join(parts)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]
    head = (
        "# Knowledge pack\n\n"
        f"pack: {digest}\n\n"
        "This is the project knowledge for your type, complete as far as it goes. Use it instead of searching for the\n"
        "same facts. It holds rules, decisions and sources; for the content of code and for anything that changes,\n"
        "the files on disk win. If a fact your task needs is not here and not in your inputs, list it in\n"
        "`open_questions`; do not fill it in from memory."
    )
    return head + "\n\n" + body + "\n"


def material_paths(text: str) -> list[str]:
    """The pieces a text lists under `## Material`: the inline code of each item before its description
    (`- `a.md`, `b/`, `c.py:120-260` — what they are`). A piece is a file, a directory or a range of lines of a file.
    URLs and placeholders are left out."""
    out: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = bool(MATERIAL_HEADING.match(line))
            continue
        if inside and line.lstrip().startswith(("-", "*")):
            head = DESCRIPTION.split(line.lstrip()[1:], 1)[0]  # the pieces stand before their description
            for item in re.findall(r"`([^`]+)`", head):
                if "://" not in item and "<" not in item and item not in out:
                    out.append(item)
    return out


def pieces(root: Path, item: str) -> list[tuple[str, int, int | None]]:
    """The files of one listed piece, each as (path, first line, last line or None for the end of the file)."""
    m = PIECE.match(item.strip())
    if not m:
        return []
    p = root / m.group("path")
    first = int(m.group("first") or 1)
    last = int(m.group("last") or m.group("first")) if m.group("first") else None
    if p.is_dir():
        return [(f.relative_to(root).as_posix(), 1, None) for f in sorted(p.rglob("*")) if f.is_file()]
    return [(p.relative_to(root).as_posix(), first, last)] if p.is_file() else []


def piece_problem(root: Path, item: str) -> str | None:
    """Why a listed piece cannot be given, or None."""
    found = pieces(root, item)
    if not found:
        return f"material `{item}` does not exist"
    name, first, last = found[0]
    if last is not None:
        n = len((root / name).read_text(encoding="utf-8", errors="replace").splitlines())
        if first < 1 or last < first or last > n:
            return f"material `{item}`: the file has {n} lines"
    return None


def without_material(text: str) -> str:
    """A text without its `## Material` section: what it says beside the pieces it lists."""
    out, inside = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = bool(MATERIAL_HEADING.match(line))
        if not inside:
            out.append(line)
    return "\n".join(out)


def in_prompt(root: Path, policy: dict, role_type: str) -> set[str]:
    """The repository files a session of the type already has in its system prompt: the role rules, the files of
    its pack and its wiki pages. The material does not give them a second time."""
    rel = policy["defaults"].get("role_rules")
    out = {rel} if rel else set()
    out |= set(access.pack_files(policy, role_type))
    return out | {p.relative_to(root).as_posix() for p in pages(root, role_type)}


def _runs(nums: set[int], lines: list[str]) -> list[tuple[int, int]]:
    """The given lines of one file as ranges; two ranges with only empty lines between them are one."""
    out: list[tuple[int, int]] = []
    for n in sorted(nums):
        if out and all(not lines[k - 1] for k in range(out[-1][1] + 1, n)):
            out[-1] = (out[-1][0], n)
        else:
            out.append((n, n))
    return out


def material_parts(
    root: Path,
    policy: dict,
    role_type: str,
    brief_items: list[str],
    own_items: list[str] = (),
    inputs: list[tuple[str, Path]] = (),
    context: bool = True,
    extra: list[tuple] = (),
    model: str | None = None,
) -> dict:
    """What a stage needs, given in its system prompt so that it is read from the prompt cache on every request
    instead of being found and opened file by file. Returns the section (`text`), what it gives and why (`given`)
    and what did not fit (`left_out`).

    The pieces are taken in the order of their claim, while they fit: the stage's inputs from earlier stages
    (`inputs`: name under input/, path), the pieces the brief names (`brief_items`, for a stage that receives the
    material of the run), the pieces its assignment names (`own_items`), then the pieces the harness chose
    (`extra`: path, first line, last line or None, reason, as pieces.select returns them), which together take at
    most AUTO_MAX_CHARS. The budget is the one of the stage's `model` (budget). A file a stage gets in several pieces is given once, its ranges joined; a file already in
    the system prompt (pack, role rules), a path the type may not read and `context/` for a type that may not
    receive it are not given at all. The inputs and listed pieces that did not fit are named; of the pieces the
    script chose, the cited and named ones are counted and the ones chosen for their words are dropped silently.

    The section is compact and loses nothing: every line is given exactly, after its number and a tab, and an empty
    line is left out with its number. The same pieces give the same bytes, so two sessions of a stage share them in
    the cache."""
    limit, auto_limit = budget(model)
    row = access.type_row(policy, role_type)
    closed = access.unreadable(row, root)
    known = in_prompt(root, policy, role_type)

    def open_to_type(name: str) -> bool:
        shut = any(fnmatch.fnmatch(name, pat) for pat in closed)
        return not shut and (context or not (name == "context" or name.startswith("context/")))

    wanted = [(f"input/{name}", path, 1, None, "input") for name, path in sorted(inputs)]
    wanted += [(n, root / n, a, b, "brief") for item in brief_items for n, a, b in pieces(root, item)]
    wanted += [(n, root / n, a, b, "assignment") for item in own_items for n, a, b in pieces(root, item)]
    wanted += [(n, root / n, a, b, why) for n, a, b, why in extra]
    lines_of: dict[str, list[str] | None] = {}
    taken: dict[str, set[int]] = {}
    why_of: dict[str, list[str]] = {}
    left: list[str] = []  # every piece that did not fit, for `harness material`
    asked: list[str] = []  # of them, the inputs and the listed pieces: the section names them
    not_text: list[str] = []  # images, PDFs and other files that are not text: the session opens each itself
    used = auto = 0
    for label, path, first, last, why in wanted:
        if why != "input" and (label in known or not open_to_type(label)):
            continue
        if label not in lines_of:
            try:
                lines_of[label] = path.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError):
                lines_of[label] = None
        lines = lines_of[label]
        piece = label if (first == 1 and last is None) else f"{label}:{first}-{last}"
        if lines is None:  # not text (an image, a PDF): it cannot be in the prompt; the session opens it itself
            if why != "related" and label not in not_text:
                not_text.append(label)
            continue
        end = len(lines) if last is None else min(last, len(lines))
        new = [n for n in range(first, end + 1) if n not in taken.get(label, ())]
        if not new and label in taken:
            continue
        cost = sum(len(str(n)) + 2 + len(lines[n - 1]) for n in new if lines[n - 1])
        cost += 0 if label in taken else len(label) + 8
        if used + cost > limit or (why in AUTO and auto + cost > auto_limit):
            if why != "related" and piece not in left:
                left.append(piece)
                asked += [] if why in AUTO else [piece]
            continue
        taken.setdefault(label, set()).update(new)
        why_of.setdefault(label, [])
        if why not in why_of[label]:
            why_of[label].append(why)
        used += cost
        auto += cost if why in AUTO else 0
    blocks, given = [], []
    for label, nums in taken.items():  # in the order of their claim
        lines = lines_of[label] or []
        if all(n in nums for n, line in enumerate(lines, 1) if line):
            spans = [(label, 1, len(lines))]
        else:
            spans = [(f"{label}:{a}-{b}", a, b) for a, b in _runs(nums, lines)]
        for name, a, b in spans:
            body = "\n".join(f"{n}\t{lines[n - 1]}" for n in range(a, b + 1) if lines[n - 1])
            blocks.append(f"### {name}\n\n{body or '(empty)'}")
            given.append({"piece": name, "why": why_of[label]})
    if not blocks and not not_text:
        return {"text": "", "given": [], "left_out": left, "does_not_fit": asked, "not_text": []}
    head = (
        "# Material\n\n"
        "The pieces of the repository and the inputs your stage needs, as they were when this session started. Every\n"
        "line is given exactly as the file has it, after its number and a tab; an empty line is left out with its\n"
        "number. Work from here and give a location as `path:line`; open a file only for what is not here."
    )
    tail = [NOT_TEXT + ": " + ", ".join(f"`{n}`" for n in not_text)] if not_text else []
    tail += ["Not here, open it yourself: " + ", ".join(f"`{n}`" for n in asked)] if asked else []
    missed = len(left) - len(asked)  # a cited place the inputs already locate; naming each would only repeat them
    if missed:
        tail.append(
            f"Not here either: {missed} more piece{'s' if missed > 1 else ''} cited or named in your brief, "
            "assignment or inputs; open them where those point."
        )
    text = "\n\n".join([head, *blocks, *tail]) + "\n"
    return {"text": text, "given": given, "left_out": left, "does_not_fit": asked, "not_text": not_text}


def budget(model: str | None) -> tuple[int, int]:
    """The material budget of a stage on `model` and the part of it the harness may fill on its own, in characters."""
    return SMALL_WINDOW.get(str(model), (MATERIAL_MAX_CHARS, AUTO_MAX_CHARS))


def material(*args, **kw) -> str:
    """The material section of a stage's system prompt (material_parts takes the same arguments)."""
    return material_parts(*args, **kw)["text"]


def rules(root: Path, policy: dict) -> str:
    """The rules of every role session (`role_rules` in the policy), as the file has them."""
    rel = policy["defaults"].get("role_rules")
    return (root / rel).read_text(encoding="utf-8").strip() if rel else ""


def supplement(root: Path, policy: dict, role_type: str) -> str:
    """The text appended to the type's system prompt: the role rules, then the type's knowledge pack. Both are
    files of the repository joined in a fixed order, so two sessions of one type get the same bytes."""
    parts = [t.strip() for t in (rules(root, policy), build(root, policy, role_type)) if t.strip()]
    return "\n\n".join(parts) + "\n" if parts else ""


def report(root: Path, policy: dict, max_tokens: int | None = None) -> dict:
    """Size of every type's pack against the budget in docs/quality/context-budget.yaml (`pack_max_tokens`)."""
    if max_tokens is None:
        budget = yaml.safe_load((root / "docs" / "quality" / "context-budget.yaml").read_text(encoding="utf-8"))
        max_tokens = budget["limits"]["pack_max_tokens"]["value"]
    rows = []
    for role_type in sorted(policy["types"]):
        text = build(root, policy, role_type)
        tokens = len(text) // CHARS_PER_TOKEN
        rows.append(
            {
                "role_type": role_type,
                "pages": len(pages(root, role_type)),
                "estimated_tokens": tokens,
                "over": tokens > max_tokens,
            }
        )
    return {"ok": not any(r["over"] for r in rows), "max_tokens": max_tokens, "packs": rows}
