"""harness/gates/validate.py — the validator stage gate: every finding ranked and located, every criterion accounted for."""

from __future__ import annotations

import re
from pathlib import Path

from ._common import LOCATOR, check, text
from .story import criteria

SEVERITY = re.compile(r"\b(Critical|Important|Minor)\b")
STATE = re.compile(r"\b(conforms|deviates|not found)\b", re.IGNORECASE)


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    doc = text(stage_dir, "output/findings.md")
    findings = [
        line.strip()
        for line in doc.splitlines()
        if SEVERITY.search(line) and re.match(r"^\s*([-*]|\d+[.)]|\|)", line) and not STATE.search(line)
    ]
    unlocated = [f[:70] for f in findings if not LOCATOR.search(f)]
    coverage = [line for line in doc.splitlines() if line.strip().startswith("|") and STATE.search(line)]
    numbers = criteria(text(run_dir / "stages" / "story", "output/story.md"))
    return [
        check("findings.md exists", bool(doc)),
        check("every finding has a `path:line` locator", not unlocated, "; ".join(unlocated[:3])),
        check("the coverage table marks conforms, deviates or not found", bool(coverage)),
        check("the coverage table has a row per acceptance criterion at least", len(coverage) >= len(numbers)),
    ]
