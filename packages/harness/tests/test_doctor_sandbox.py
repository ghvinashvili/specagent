"""harness doctor's sandbox items on each OS (docs/decisions/0029-a-checkout-sets-up-its-hooks-sandbox-and-graph.md):
the WSL2 path on native Windows, the seatbelt on macOS, bubblewrap, socat and a nested probe on Linux."""

from __future__ import annotations

import ast
import json
import shutil
import subprocess
from pathlib import Path

from harness import doctor

REPO = Path(__file__).resolve().parents[3]
REAL_WHICH = shutil.which
ON, OFF = {"sandbox": {"enabled": True}}, {"sandbox": {"enabled": False}}
WSL2 = ("the repository runs in WSL2", False, True)
LINUX = ("bubblewrap is on PATH", "socat is on PATH", "a sandboxed command can run (user namespace inside bubblewrap)")


def which(found: dict):
    """shutil.which as on this machine, except for the names in `found` (None: not installed)."""
    return lambda name, *args, **kwargs: found[name] if name in found else REAL_WHICH(name, *args, **kwargs)


def names(items: list[dict]) -> list[tuple]:
    return [(item["name"], item["ok"], item["required"]) for item in items]


def test_native_windows_gets_the_wsl2_item_whatever_its_settings(monkeypatch):
    assert [names(doctor.sandbox_items(settings, "win32")) for settings in ({}, ON, OFF)] == [[WSL2]] * 3
    monkeypatch.setattr(doctor, "_native_windows", lambda: True)
    [item] = doctor.sandbox_items(OFF)
    assert names([item]) == [WSL2] and item["detail"] == "native Windows" and "WSL2" in item["fix"]


def test_macos_with_the_sandbox_on_needs_sandbox_exec(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", which({"sandbox-exec": "/usr/bin/sandbox-exec"}))
    [item] = doctor.sandbox_items(ON, "darwin")
    assert names([item]) == [("sandbox-exec is on PATH", True, True)] and item["detail"] == "/usr/bin/sandbox-exec"
    monkeypatch.setattr(doctor.shutil, "which", which({"sandbox-exec": None}))
    [item] = doctor.sandbox_items(ON, "darwin")
    assert names([item]) == [("sandbox-exec is on PATH", False, True)] and "/usr/bin/sandbox-exec" in item["fix"]
    assert doctor.sandbox_items(OFF, "darwin") == [] and doctor.sandbox_items({}, "darwin") == []


def test_linux_with_the_sandbox_on_needs_bubblewrap_socat_and_a_nested_namespace(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", which({"bwrap": "/usr/bin/bwrap", "socat": "/usr/bin/socat"}))
    monkeypatch.setattr(doctor, "nested_userns", lambda bwrap: subprocess.CompletedProcess([bwrap], 0, "", ""))
    assert names(doctor.sandbox_items(ON, "linux")) == [(name, True, True) for name in LINUX]
    monkeypatch.setattr(doctor.shutil, "which", which({"bwrap": None, "socat": "/usr/bin/socat"}))
    assert names(doctor.sandbox_items(ON, "linux")) == [(LINUX[0], False, True), (LINUX[1], True, True)]
    assert doctor.sandbox_items(OFF, "linux") == [] and doctor.sandbox_items(ON, "freebsd14") == []


def test_the_platform_is_read_when_the_doctor_runs(monkeypatch):
    monkeypatch.setattr(doctor, "_native_windows", lambda: False)
    monkeypatch.setattr(doctor.sys, "platform", "darwin")
    monkeypatch.setattr(doctor.shutil, "which", which({"sandbox-exec": "/usr/bin/sandbox-exec"}))
    assert names(doctor.sandbox_items(ON)) == [("sandbox-exec is on PATH", True, True)]


def test_gh_and_just_are_the_optional_items():
    # node served a diagram renderer only; the maps are Mermaid text (wiki/decisions/diagrams-are-mermaid-text.md)
    items = doctor.optional_items()
    assert len(items) == 2 and all(item["required"] is False for item in items)
    assert items[0]["name"] == "gh is on PATH" and items[1]["name"] == "just is on PATH"


def test_check_takes_its_sandbox_items_from_its_settings_and_every_function_is_small(monkeypatch):
    seen = []

    def sentinel(settings, platform=None):
        seen.append(settings)
        return [doctor._item("sandbox sentinel", False)]

    monkeypatch.setattr(doctor, "sandbox_items", sentinel)
    monkeypatch.setattr(doctor, "optional_items", lambda: [doctor._item("optional sentinel", False, required=False)])
    report = doctor.check(REPO)
    got = [item["name"] for item in report["checks"]]
    assert seen == [json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))]
    assert got.count("sandbox sentinel") == 1 and got.count("optional sentinel") == 1
    assert not set(got) & {*LINUX, "gh is on PATH", "just is on PATH", WSL2[0]}
    assert report["ok"] is False and report["ok"] == all(item["ok"] for item in report["checks"] if item["required"])
    tree = ast.parse(Path(doctor.__file__).read_text(encoding="utf-8"))
    sizes = {f.name: f.end_lineno - f.lineno + 1 for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)}
    assert {name: sizes[name] for name in ("check", "sandbox_items", "optional_items") if sizes[name] >= 50} == {}
