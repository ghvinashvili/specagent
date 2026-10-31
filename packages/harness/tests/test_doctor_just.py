"""harness doctor names `just` (D11 of the plan index; lessons.md "Read first" 4): an optional item whose fix names
the commands that install it; its absence never fails the machine's check."""

from __future__ import annotations

import shutil
from pathlib import Path

from harness import doctor

REPO = Path(__file__).resolve().parents[3]
REAL_WHICH = shutil.which


def which_with_just(found: str | None):
    """shutil.which as on this machine, except that `just` is at `found` (None: not installed)."""
    return lambda name, *args, **kwargs: found if name == "just" else REAL_WHICH(name, *args, **kwargs)


def test_a_missing_just_is_an_optional_item_that_names_how_to_install_it(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", which_with_just(None))
    item = doctor.just_item()
    assert (item["name"], item["ok"], item["required"]) == ("just is on PATH", False, False)
    assert "uv tool install rust-just" in item["fix"] and "python3 ops/bootstrap.py --wait" in item["fix"]
    monkeypatch.setattr(doctor.shutil, "which", which_with_just("/opt/tools/just"))
    item = doctor.just_item()
    assert (item["ok"], item["detail"]) == (True, "/opt/tools/just") and "fix" not in item


def test_the_doctor_lists_the_just_item_once(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", which_with_just(None))
    items = [c for c in doctor.check(REPO)["checks"] if c["name"] == "just is on PATH"]
    assert len(items) == 1 and items[0]["ok"] is False and items[0]["required"] is False
