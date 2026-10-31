"""Untrusted text enters through one door. `harness inbox` copies a file into <runs root>/_inbox/<slug>/ without
printing it; `harness route` maps the classifier's label of an intake run to the next pipeline. No model is involved."""

from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

from . import state

SLUG = re.compile(r"[a-z0-9][a-z0-9-]*")


def add(root: Path, slug: str, file: Path) -> dict:
    src = file.expanduser().resolve()
    if not SLUG.fullmatch(slug):
        return {"ok": False, "status": "bad_slug"}
    if not src.is_file():
        return {"ok": False, "status": "not_a_file", "file": str(src)}
    dest_dir = state.runs_root(root) / "_inbox" / slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    shutil.copyfile(src, dest)  # size and hash come from the source: nothing reads the inbox copy back
    return {
        "ok": True,
        "path": str(dest),
        "bytes": src.stat().st_size,
        "sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
        "note": "untrusted text: only a quarantine-reader session opens this file",
    }


def route(root: Path, run_id: str) -> dict:
    run_dir = state.runs_root(root) / run_id
    manifest = state.load(root, run_dir / "manifest.json", "run-manifest")
    routes = state.load_table(root, manifest.get("pipeline", "default")).get("routes")
    if not routes:
        return {"ok": False, "status": "no_routes", "hint": "the run's pipeline has no `routes` table"}
    result = state.load(root, run_dir / "stages" / routes["stage"] / "result.json", "stage-result")
    label = result.get("label") or {}
    target = routes["labels"].get(label.get("value"), "escalate")
    digest = run_dir / "stages" / "digest" / "result.json"
    return {
        "ok": True,
        "label": label.get("value"),
        "confidence": label.get("confidence"),
        "pipeline": target,
        "digest": str(digest) if digest.exists() else None,
        "next": "ask the human"
        if target == "escalate"
        else f"write a brief whose material is the digest, then `harness run --pipeline {target}`",
    }
