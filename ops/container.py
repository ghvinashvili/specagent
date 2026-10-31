#!/usr/bin/env python3
"""Lay the project's folder out around this checkout.

    python3 ops/container.py

The checkout's parent is the container (owner, 2026-10-29: the runs, the experiments and the like live in one folder
with the repository). Beside the checkout it makes `runs/` marked `.harness-runs` (the runs root, `docs/roles/RUNS.md`),
`experiments/` (copies made for trials) and `docs/handoff/` (the manager's hand-over notes). It refuses a parent that
holds another checkout (that checkout would take the same runs root) and a `runs/` without the marker; running it
again changes nothing. `ops/new-project.py --container` gives a new project the same shape.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = ("runs/", "experiments/", "docs/handoff/")


def new_project():
    """`ops/new-project.py` as a module: its `checkout` test and `RUNS_MARKER` are the ones used here."""
    spec = importlib.util.spec_from_file_location("new_project", Path(__file__).resolve().parent / "new-project.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    np = new_project()
    container = ROOT.parent
    others = sorted(p.name for p in container.iterdir() if p != ROOT and np.checkout(p))
    if others:
        print(f"{container} holds another checkout ({', '.join(others)}); a project gets a container of its own")
        return 1
    runs, marker = container / "runs", container / "runs" / np.RUNS_MARKER
    if runs.exists() and not marker.exists():
        print(f"{runs} exists and is not a runs root (no {np.RUNS_MARKER}); choose another container")
        return 1
    runs.mkdir(exist_ok=True)
    if not marker.exists():
        marker.write_text(
            f"runs of the checkout {ROOT.name} beside this folder (harness state.runs_root)\n", encoding="utf-8"
        )
    (container / "experiments").mkdir(exist_ok=True)
    (container / "docs" / "handoff").mkdir(parents=True, exist_ok=True)
    print(f"{container}: {ROOT.name}/ (the checkout), " + ", ".join(FOLDERS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
