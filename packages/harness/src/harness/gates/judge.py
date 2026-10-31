"""harness/gates/judge.py — the judge stage gate: a decision with reasons."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ._common import LOCATOR, check, critique_table, report_entries, result, stage_parts, table_rows

CITE = re.compile(r"\b([a-z][a-z0-9_-]*)#(\d+)\b")  # `verify#5`: the stage of a report and an entry or row of it
RANK = re.compile(r"\b(Critical|Important|Minor)\b")
STATE = re.compile(r"\b(conforms|deviates|not found)\b", re.IGNORECASE)
STATUS = re.compile(r"\b(passed|failed|not coverable)\b", re.IGNORECASE)
BLOCKING = {"refuted", "blocks", "must fix", "critical", "important", "failed"}  # accept only when unsupported
UNCHECKED = {"could not check", "not coverable"}  # accept only when the reasons name them


def verify_entries(text: str) -> dict[int, str]:
    """report.md of a verifier: entry number -> its result (_common.report_entries; its gate refuses a number twice)."""
    return {n: found for n, found, _ in report_entries(text) if found}


def critique_rows(text: str) -> dict[int, str]:
    """critique.md of a critic: row number (`No.`) -> its severity, read as the critique gate reads the table."""
    return {int(r["no"]): r["severity"] for r in critique_table(text) or [] if r["no"].isdigit()}


def validator_findings(text: str) -> dict[int, str]:
    """findings.md of a validator: finding number -> its rank. A finding is a list item or table row with a rank and
    no coverage state (gates/validate.py); its number is the one it starts with, else its place among the findings."""
    out: dict[int, str] = {}
    ranked = [(ln, RANK.search(ln)) for ln in text.splitlines() if not STATE.search(ln)]
    ranked = [(ln, r) for ln, r in ranked if r and re.match(r"^\s*([-*]|\d+[.)]|\|)", ln)]
    for i, (line, rank) in enumerate(ranked, 1):
        m = re.match(r"^\s*(?:\|\s*)?(\d+)[.)|\s]", line)
        out[int(m.group(1)) if m else i] = rank.group(1).lower()
    return out


def acceptance_rows(text: str) -> dict[int, str]:
    """acceptance.md of a test-verifier: criterion number -> passed, failed or not coverable."""
    out = {}
    for r in table_rows(text):
        status = STATUS.search(" ".join(r))
        if status and re.match(r"^\d+$", r[0].strip()):
            out[int(r[0])] = status.group(1).lower()
    return out


PARSERS = {
    "report.md": verify_entries,
    "critique.md": critique_rows,
    "findings.md": validator_findings,
    "acceptance.md": acceptance_rows,
}


def reports(run_dir: Path, stage_dir: Path) -> dict[str, dict[int, str]]:
    """The reports the judge received, by the stage that wrote them (from the launcher's index in `_access/`)."""
    name = "-".join(stage_dir.relative_to(run_dir / "stages").parts)
    index = run_dir / "_access" / f"{name}.inputs.json"
    out: dict[str, dict[int, str]] = {}
    for e in json.loads(index.read_text(encoding="utf-8")) if index.is_file() else []:
        parts = stage_parts(run_dir, e.get("source", ""))
        copy = stage_dir / "input" / e["as"]
        if len(parts) > 1 and parts[-1] in PARSERS and copy.is_file():
            out[parts[0]] = PARSERS[parts[-1]](copy.read_text(encoding="utf-8"))
    return out


def content_checks(repo: Path, run_dir: Path, stage_dir: Path, events: list[dict] | None) -> list[dict]:
    """Part 3 of specs/001-chat-depth: every reason names its source as `<stage>#<n>`, or a place of the change as
    `` `path:line` `` (a line of changes.patch, specs/002-run-loop), every citation names an entry
    or row that exists, and `accept` leaves no refuted entry, blocking or must-fix row, Critical or Important
    finding, or failed criterion outside open_questions, and no unchecked one outside the reasons."""
    res = result(stage_dir)
    verdict = res.get("verdict") or {}
    reasons = [str(r) for r in verdict.get("reasons", [])]
    found = reports(run_dir, stage_dir)
    sourceless = [r[:60] for r in reasons if not any(s in found for s, _ in CITE.findall(r)) and not LOCATOR.search(r)]
    cited = [(s, int(n)) for r in reasons for s, n in CITE.findall(r)]
    unknown = [f"{s}#{n}" for s, n in cited if n not in found.get(s, {})]
    open_ = {f"{s}#{n}" for q in res.get("open_questions", []) for s, n in CITE.findall(str(q))}
    named = {f"{s}#{n}" for s, n in cited}
    entries = [(f"{s}#{n}", c) for s, rows in found.items() for n, c in sorted(rows.items())]
    left = [k for k, c in entries if c in BLOCKING and k not in open_]
    left += [k for k, c in entries if c in UNCHECKED and k not in named]
    accept = verdict.get("decision") != "accept" or not left
    return [
        check("every reason names its source as `<stage>#<n>`", bool(reasons) and not sourceless, "; ".join(sourceless[:3])),
        check("every cited entry exists in its report", not unknown, ", ".join(unknown[:6])),
        check("accept leaves no finding of the reports unanswered", accept, ", ".join(left[:8])),
    ]  # fmt: skip


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    verdict = result(stage_dir).get("verdict") or {}
    return [
        check(
            "verdict.decision is accept, revise, replan or reject",
            verdict.get("decision") in ("accept", "revise", "replan", "reject"),
        ),
        check("verdict.reasons is not empty", bool(verdict.get("reasons"))),
    ]
