"""Attack tests for the input-copy boundary of run 20261009-022929-fix-w1-revise (R13; plan D7). Each asserts a
promise the plan makes, by the names the plan gives (access.put_copy, launch.record_work, gates._common.as_copied,
access.unit_record). New file, self-contained on tmp_path; no read of evals/baseline, the main checkout, the runs
root or a network host. A writer may not change this file."""

from __future__ import annotations

import hashlib
import stat
from pathlib import Path

from harness import access, launch
from harness.gates import _common

WRITABLE = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH


def test_put_copy_writes_read_only_and_returns_the_sha256(tmp_path: Path):
    """access.put_copy writes a copy read-only (no write bit for anyone) and returns the sha256 of the bytes."""
    dst = tmp_path / "a" / "x.txt"
    sha = access.put_copy(dst, b"hello\n")
    assert sha == hashlib.sha256(b"hello\n").hexdigest()
    assert dst.read_bytes() == b"hello\n"
    assert not dst.stat().st_mode & WRITABLE


def test_put_copy_replaces_a_read_only_target_in_place(tmp_path: Path):
    """D7: on a recheck or a resume the target may already exist read-only; put_copy replaces it, not appends."""
    dst = tmp_path / "x.txt"
    access.put_copy(dst, b"one\n")
    access.put_copy(dst, b"two\n")
    assert dst.read_bytes() == b"two\n" and not dst.stat().st_mode & WRITABLE


def test_put_copy_does_not_follow_a_link(tmp_path: Path):
    """D7: a session may plant a link where a copy goes; put_copy removes the link and writes a real file, leaving
    the link's target untouched."""
    target = tmp_path / "target.txt"
    target.write_text("SECRET-TARGET\n", encoding="utf-8")
    link = tmp_path / "copy.txt"
    link.symlink_to(target)
    access.put_copy(link, b"new\n")
    assert not link.is_symlink() and link.read_text() == "new\n"
    assert target.read_text() == "SECRET-TARGET\n"


def test_record_work_indexes_the_patch_with_its_sha256_and_as_copied_accepts_it(tmp_path: Path):
    """R13/D7: launch.record_work records the change patch among the unit's input copies with its sha256 under
    <run>/_access/<unit>.inputs.json, replacing any earlier entry of the same name; gates._common.as_copied returns
    the patch bytes for that entry."""
    run = tmp_path / "run"
    sd = run / "stages" / "verify"
    patch = sd / "input" / "work" / "changes.patch"
    sha = access.put_copy(patch, b"diff --git a/x b/x\n+two\n")
    assert not patch.stat().st_mode & WRITABLE  # the patch itself is read-only (work.prepare uses put_copy)
    prepared = {
        "worktree": "r1-verify",
        "path": str(run),
        "base": "aaa",
        "commit": "bbb",
        "patch": str(patch),
        "sha256": sha,
        "from": [],
    }
    index = launch.record_work(run, sd, prepared, index=[{"as": "brief.md", "sha256": "0"}])
    entries = [e for e in index if e.get("as") == "work/changes.patch"]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["sha256"] == sha and entry["source"].startswith("git diff ")
    assert _common.as_copied(sd, entry) == patch.read_bytes()
    # written to <run>/_access, which a role session cannot read
    on_disk = access.unit_record(run, sd, "inputs")
    assert on_disk.is_file() and on_disk.parent.name == "_access"


def test_record_work_replaces_an_earlier_patch_entry_rather_than_duplicating_it(tmp_path: Path):
    """D7: a recheck or a resume records the new patch; the index names it once, not twice."""
    run = tmp_path / "run"
    sd = run / "stages" / "verify"
    patch = sd / "input" / "work" / "changes.patch"
    sha1 = access.put_copy(patch, b"+two\n")
    prepared = {"base": "a", "commit": "b", "patch": str(patch), "sha256": sha1}
    launch.record_work(run, sd, prepared, index=[])
    sha2 = access.put_copy(patch, b"+three\n")
    prepared2 = {"base": "a", "commit": "c", "patch": str(patch), "sha256": sha2}
    index = launch.record_work(run, sd, prepared2)  # index=None -> read from disk
    entries = [e for e in index if e.get("as") == "work/changes.patch"]
    assert len(entries) == 1 and entries[0]["sha256"] == sha2
