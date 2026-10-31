"""harness/gates/analyze.py — the analyst stage gate: every proposal shows its evidence and follows the template."""

from __future__ import annotations

import re
from pathlib import Path

from ._common import check, has_sections, text

RUN_FILE = re.compile(r"[0-9]{8}-[0-9]{6}-[a-z0-9-]+/[^\s`)]+|stages/[a-z-]+/[^\s`)]+")


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    template = (root / "templates" / "change-proposal.md").read_text(encoding="utf-8")
    required = [h.lower() for h in re.findall(r"(?m)^## (.+?)\s*$", template)]
    proposals = sorted((stage_dir / "output" / "proposals").glob("*.md"))
    incomplete, unevidenced = [], []
    for p in proposals:
        doc = text(stage_dir, p.relative_to(stage_dir).as_posix())  # "" for a link out of the stage directory
        if has_sections(doc, required):
            incomplete.append(p.name)
        if not RUN_FILE.search(doc):
            unevidenced.append(p.name)
    return [
        check("taxonomy.md exists", bool(text(stage_dir, "output/taxonomy.md"))),
        check("every proposal has the sections of templates/change-proposal.md", not incomplete, ", ".join(incomplete)),
        check("every proposal names a run file", not unevidenced, ", ".join(unevidenced)),
    ]
