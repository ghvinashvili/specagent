"""harness/gates/review.py — the comparator stage gate: every candidate ranked exactly once."""

from __future__ import annotations

from pathlib import Path

from ._common import check, result


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    order = (result(stage_dir).get("ranking") or {}).get("order", [])
    shards = sorted(p.name for p in (run_dir / "stages" / "advise").glob("[0-9][0-9]") if p.is_dir())
    return [
        check("ranking.order exists", bool(order)),
        check(
            "ranking.order names every candidate exactly once",
            sorted(order) == shards,
            f"order {order}, candidates {shards}",
        ),
    ]
