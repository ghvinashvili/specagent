"""harness/gates/wikicheck.py — the verifier's stage in a wiki-ingest run: every changed page is in the report."""

from __future__ import annotations

import re
from pathlib import Path

from ._common import check, text
from .verify import checks as verify_checks

PAGE = re.compile(r"wiki/(?:concepts|entities|sources)/[a-z0-9-]+\.md")


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    report = text(stage_dir, "output/report.md")
    changed = sorted(set(PAGE.findall(text(run_dir / "stages" / "ingest", "output/changes.md"))))
    # a report names a page by its path or, after the first mention, by its file name
    absent = [p for p in changed if p not in report and Path(p).name not in report]
    return [
        *verify_checks(root, run_dir, stage_dir, commands=False),
        check("the ingest stage changed at least one page", bool(changed)),
        check("every changed page is in the report", not absent, ", ".join(absent[:5])),
    ]
