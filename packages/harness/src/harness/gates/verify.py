"""harness/gates/verify.py — the verifier stage gate: every claim checked by a command, every entry with a result."""

from __future__ import annotations

import json
from pathlib import Path

from ._common import check, report_entries, result, text, unproven
from .judge import verify_entries


def claimed_tasks(stage_dir: Path) -> list[str]:
    """The ids of the tasks the author says are done: every task list among the inputs."""
    ids: list[str] = []
    inp = stage_dir / "input"
    for path in sorted(inp.rglob("tasks.json")) if inp.is_dir() else []:
        try:
            ids += [t["id"] for t in json.loads(path.read_text(encoding="utf-8")).get("tasks", []) if "id" in t]
        except (json.JSONDecodeError, AttributeError, TypeError):
            continue
    return sorted(set(ids))


def depth_checks(stage_dir: Path, report: str) -> list[dict]:
    """A verification is the verifier's own: every task the author claims has its entry, and where the work is
    code, the checks the verifier wrote itself are kept, so that the next reader can run them again."""
    unchecked = [t for t in claimed_tasks(stage_dir) if t not in report]
    inp = stage_dir / "input"
    code = any(inp.rglob("changes.patch")) if inp.is_dir() else False
    own = stage_dir / "output" / "checks"
    kept = own.is_dir() and any(p.is_file() for p in own.rglob("*"))
    return [
        check("every task of the author has its entry in the report", not unchecked, ", ".join(unchecked[:8])),
        check("the verifier's own checks are kept under output/checks/", kept or not code),
    ]


def proof_checks(run_dir: Path, stage_dir: Path, report: str, res: dict) -> list[dict]:
    """A proposal that sends work back rests on refuted entries, and every refuted entry on a command it ran, named
    as `<stage>#<n>` in its evidence entry: only proven findings go back to the writer (harness/rounds.py). `reject`
    is a proposal for the judge, which alone stops a run."""
    decision = (res.get("verdict") or {}).get("decision")
    refuted = [str(n) for n, r in verify_entries(report).items() if r == "refuted"]
    lacking = unproven(res, stage_dir.relative_to(run_dir / "stages").parts[0], refuted)
    return [
        check("the verdict proposal is accept, revise or reject", decision in ("accept", "revise", "reject"), str(decision)),
        check("revise or reject rests on a refuted entry, accept on none",
              (decision in ("revise", "reject")) == bool(refuted), f"{len(refuted)} refuted, verdict {decision}"),
        check("every refuted entry has its evidence entry in result.json", not lacking,
              "no entry with a command, its exit code and `<stage>#<n>` in its claim for entry " + ", ".join(lacking[:8])),
    ]  # fmt: skip


def checks(root: Path, run_dir: Path, stage_dir: Path, commands: bool = True) -> list[dict]:
    """`commands`: every evidence entry names a command, and a proposal rests on proven entries (proof_checks). That
    holds for code; a statement of a document is checked by opening its source, so the wiki check asks only that an
    entry which names a command also has its exit code."""
    report = text(stage_dir, "output/report.md")
    res = result(stage_dir)
    evidence = res.get("evidence", [])
    entries = report_entries(report)
    without = [body.split("\n", 1)[0][:60] for _, found, body in entries if found is None]
    numbers = [n for n, _, _ in entries]
    twice = sorted({n for n in numbers if numbers.count(n) > 1})
    return [
        check("report.md exists", bool(report)),
        check("report.md has numbered entries", bool(entries)),
        check("every entry states confirmed, refuted or could not check", not without, "; ".join(without[:3])),
        check(
            "every entry has a number of its own",
            not twice,
            "a line that starts with a number starts an entry; entry " + ", ".join(map(str, twice[:6])) + " repeats",
        ),
        check("report.md has the section Beyond the claims", "beyond the claims" in report.lower()),
        *depth_checks(stage_dir, report),
        check("evidence[] is not empty", bool(evidence)),
        check("every evidence entry has a command", bool(evidence) and all(e.get("command") for e in evidence))
        if commands
        else check(
            "every evidence entry that names a command has its exit code",
            all("exit_code" in e for e in evidence if e.get("command")),
        ),
        check("result.json proposes a verdict", bool(res.get("verdict", {}).get("decision"))),
        *(proof_checks(run_dir, stage_dir, report, res) if commands else []),
    ]
