"""harness/gates/classify.py — the classifier stage gate: one label from the fixed list of the pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from .. import state
from ._common import check, result


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    labels = (state.load_table(root, manifest.get("pipeline", "default")).get("routes") or {}).get("labels", {})
    label = result(stage_dir).get("label") or {}
    return [
        check("the pipeline defines route labels", bool(labels)),
        check("label.value is one of the route labels", label.get("value") in labels, str(label.get("value"))),
        check("label.confidence is given", isinstance(label.get("confidence"), (int, float))),
    ]
