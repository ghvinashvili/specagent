"""harness/gates/critique.py — the critic stage gate: every finding located and graded, every input covered."""

from __future__ import annotations

from pathlib import Path

from ._common import check, critique_table, input_names, result, text

SEVERITIES = {"blocks", "must fix", "minor"}


def critique_checks(run_dir: Path, stage_dir: Path) -> list[dict]:
    """Shared by critique, refute and challenge: the three stages a critic serves. The findings are the rows of the
    table with a Severity column, each cell found by its column's header (_common.critique_table)."""
    doc = text(stage_dir, "output/critique.md")
    table = critique_table(doc)
    rows = table or []
    no_location = [r["no"] for r in rows if not r["location"]]
    bad_severity = [r["no"] for r in rows if r["severity"] not in SEVERITIES]
    no_source = [r["no"] for r in rows if not r["source"]]
    # every file the stage was given is named: in a finding, or in the coverage line as read and clean
    uncovered = [n for n in input_names(run_dir, stage_dir) if n not in doc and Path(n).name not in doc]
    blocking = [r["no"] for r in rows if r["severity"] == "blocks"]
    evidence = result(stage_dir).get("evidence", [])
    shown = len(evidence)
    inp = stage_dir / "input"
    code = any(inp.rglob("changes.patch")) if inp.is_dir() else False
    ran = [e for e in evidence if e.get("command") and "exit_code" in e]
    return [
        check("critique.md exists", bool(doc)),
        check("critique.md has a findings table with a Severity column", table is not None),
        check("every finding has a location in the work", not no_location, ", ".join(no_location)),
        check("every finding has a source", not no_source, ", ".join(no_source)),
        check("every severity is blocks, must fix or minor", not bad_severity, ", ".join(bad_severity)),
        check("critique.md has a coverage line", "coverage" in doc.lower()),
        check("every input file is named in the critique", not uncovered, ", ".join(uncovered[:5])),
        check(
            "every blocks finding has its evidence entry in result.json",
            shown >= len(blocking),
            f"{len(blocking)} blocks rows, {shown} evidence entries",
        ),
        # work that can be run is run: a review of code that never executed it has only read it
        check("the critic ran the work: an evidence entry with command and exit code", bool(ran) or not code),
        check("result.json has a summary", bool(result(stage_dir).get("summary"))),
    ]


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    return critique_checks(run_dir, stage_dir)
