"""harness/gates/digest.py — the quarantine-reader stage gate: a digest and nothing else."""

from __future__ import annotations

from pathlib import Path

from ._common import check, result


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    res = result(stage_dir)
    produced = [p.name for p in (stage_dir / "output").iterdir()] if (stage_dir / "output").is_dir() else []
    return [
        check("result.json has a digest block", isinstance(res.get("digest"), dict)),
        check("outputs is empty", res.get("outputs") == []),
        check("no file was written to output/", not produced, ", ".join(produced[:5])),
    ]
