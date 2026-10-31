"""Choose a role type: the stage table decides for stages; descriptions decide for ad-hoc requests."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from . import catalog

WORD = re.compile(r"[a-z][a-z0-9-]{2,}")


def select_type(root: Path, request: str) -> dict:
    table = yaml.safe_load((root / "docs" / "roles" / "stages.yaml").read_text(encoding="utf-8"))
    by_stage = {r["id"]: r["role_type"] for r in table["stages"]}
    if request.strip() in by_stage:
        return {"ok": True, "role_type": by_stage[request.strip()], "by": "stage-table"}
    types = catalog.load_types(root)  # {name: frontmatter}
    words = set(WORD.findall(request.lower()))
    scored = []
    for name, fm in types.items():
        use_when = (
            fm["description"].split("Use when:", 1)[1].split("Never", 1)[0] if "Use when:" in fm["description"] else ""
        )
        hits = words & set(WORD.findall(use_when.lower()))
        scored.append((len(hits), name, sorted(hits)))
    scored.sort(reverse=True)
    best, runner = scored[0], (scored[1] if len(scored) > 1 else (0, None, []))
    if best[0] >= 2 and best[0] > runner[0]:
        return {"ok": True, "role_type": best[1], "by": "description", "matched": best[2]}
    return {
        "ok": False,
        "action": table["no_match"]["action"],
        "message": table["no_match"]["message"],
        "candidates": [{"role_type": n, "hits": h} for s, n, h in scored[:3]],
    }
