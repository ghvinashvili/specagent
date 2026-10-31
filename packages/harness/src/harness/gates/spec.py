"""harness/gates/spec.py — the spec-writer stage gate: the skeleton has its five sections, every criterion is met by a requirement, nothing is left to clarify."""

from __future__ import annotations

import re
from pathlib import Path

from ._common import OPEN_MARKER, check, has_sections, table_rows, text
from .story import criteria

REQUIRED = ["intent", "requirements", "limits", "done", "out of scope"]


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    spec = text(stage_dir, "output/spec.md")
    missing = has_sections(spec, REQUIRED)
    numbers = criteria(text(run_dir / "stages" / "story", "output/story.md"))
    mapped = {m for row in table_rows(spec) for m in re.findall(r"\d+", row[0])}
    unmapped = [n for n in numbers if n not in mapped]
    return [
        check("spec.md exists", bool(spec)),
        check("spec.md has the required sections", not missing, "missing: " + ", ".join(missing)),
        check("the story has numbered criteria to map", bool(numbers)),
        check(
            "every acceptance criterion has a row in the mapping table",
            not unmapped,
            "criteria: " + ", ".join(unmapped),
        ),
        check("no [NEEDS CLARIFICATION: ...] marker is left", not OPEN_MARKER.search(spec)),
    ]
