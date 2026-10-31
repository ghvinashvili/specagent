"""clean_jobs_tmp.py (spec B11): the `tmp` folders of finished background jobs under ~/.claude/jobs/<id>/, found from
`claude agents --json --all`; a dry run by default, `--apply` removes them. Live sessions, jobs finished less than
`--hours` ago, a job whose session lives on under another id, and a `tmp` that is a symlink are left alone.

  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests/test_clean_jobs_tmp.py
"""

import os
import pathlib
import shutil
import time

from transcript_home import Home

HOUR = 3600


def jobs_dir(home: Home) -> pathlib.Path:
    return home.root / "home" / ".claude" / "jobs"


def job(
    home: Home,
    ident: str,
    state: str,
    *,
    pid: int | None = None,
    session: str = "",
    size: int = 1000,
    age: float = 48 * HOUR,
) -> pathlib.Path:
    """A row of `claude agents --json --all` and its folder: state.json `age` seconds old, `size` bytes under tmp/."""
    row = {
        "id": ident,
        "name": f"demo/{ident}",
        "sessionId": session or f"s-{ident}",
        "state": state,
        "kind": "background",
        "cwd": "/work",
        "startedAt": 1_761_000_000_000,
    }
    if pid is not None:
        row["pid"] = pid
    home.rows.append(row)
    home.save_rows()
    folder = jobs_dir(home) / ident
    (folder / "tmp" / "sub").mkdir(parents=True)
    (folder / "tmp" / "sub" / "blob.bin").write_bytes(b"x" * size)
    (folder / "state.json").write_text("{}\n", encoding="utf-8")
    then = time.time() - age
    os.utime(folder / "state.json", (then, then))
    return folder


def test_a_dry_run_lists_the_tmp_folders_of_finished_jobs_and_removes_nothing(tmp_path):
    home = Home(tmp_path)
    job(home, "aaaa0001", "done", size=2_500_000)
    job(home, "aaaa0002", "failed")
    job(home, "aaaa0003", "stopped")
    job(home, "aaaa0004", "idle", pid=4242, session="shared")  # a live session
    job(home, "aaaa0005", "done", age=HOUR)  # finished an hour ago: kept for 24 hours
    job(home, "aaaa0006", "done", session="shared")  # its session lives on as aaaa0004
    job(home, "aaaa0007", "blocked")  # waits for a permission: not finished
    home.rows.append({"name": "an interactive session", "sessionId": "s-int", "state": "idle", "kind": "interactive"})
    home.save_rows()
    r = home.run("clean_jobs_tmp.py")
    assert r.returncode == 0, r.stderr
    jobs = jobs_dir(home)
    assert r.stdout.splitlines() == [
        f"would remove {jobs / 'aaaa0001' / 'tmp'} (done, demo/aaaa0001, 2.5 MB)",
        f"would remove {jobs / 'aaaa0002' / 'tmp'} (failed, demo/aaaa0002, 0.0 MB)",
        f"would remove {jobs / 'aaaa0003' / 'tmp'} (stopped, demo/aaaa0003, 0.0 MB)",
        "total: 3 folders, 2.5 MB; nothing removed without --apply",
    ]
    assert [n for n in range(1, 8) if not (jobs / f"aaaa000{n}" / "tmp" / "sub" / "blob.bin").is_file()] == []
    assert home.claude_calls() == ["agents --json --all"]


def test_apply_removes_only_those_folders_and_keeps_each_job_s_state(tmp_path):
    home = Home(tmp_path)
    job(home, "bbbb0001", "done", size=1_200_000)
    job(home, "bbbb0002", "idle", pid=4343)
    r = home.run("clean_jobs_tmp.py", "--apply")
    assert r.returncode == 0, r.stderr
    jobs = jobs_dir(home)
    assert r.stdout.splitlines() == [
        f"removed {jobs / 'bbbb0001' / 'tmp'} (done, demo/bbbb0001, 1.2 MB)",
        "total: 1 folders, 1.2 MB removed",
    ]
    assert not (jobs / "bbbb0001" / "tmp").exists() and (jobs / "bbbb0001" / "state.json").is_file()
    assert (jobs / "bbbb0002" / "tmp" / "sub" / "blob.bin").is_file()


def test_a_symlinked_tmp_is_skipped_and_a_row_whose_id_is_not_a_job_id_is_ignored(tmp_path):
    home = Home(tmp_path)
    outside = tmp_path / "outside"
    (outside / "keep").mkdir(parents=True)
    folder = job(home, "cccc0001", "done")
    shutil.rmtree(folder / "tmp")
    (folder / "tmp").symlink_to(outside, target_is_directory=True)
    home.rows.append({"id": "../../../outside", "name": "x", "sessionId": "s-x", "state": "done", "kind": "background"})
    home.save_rows()
    r = home.run("clean_jobs_tmp.py", "--apply")
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines() == [f"skipped {folder / 'tmp'}: a symlink", "total: 0 folders, 0.0 MB removed"]
    assert (outside / "keep").is_dir() and (folder / "tmp").is_symlink()


def test_hours_sets_how_long_ago_a_job_must_have_finished(tmp_path):
    home = Home(tmp_path)
    job(home, "dddd0001", "done", age=2 * HOUR)
    r = home.run("clean_jobs_tmp.py")
    assert r.stdout.splitlines() == ["total: 0 folders, 0.0 MB; nothing removed without --apply"]
    r = home.run("clean_jobs_tmp.py", "--hours", "1")
    assert r.stdout.splitlines() == [
        f"would remove {jobs_dir(home) / 'dddd0001' / 'tmp'} (done, demo/dddd0001, 0.0 MB)",
        "total: 1 folders, 0.0 MB; nothing removed without --apply",
    ]


def test_a_failed_listing_or_a_missing_jobs_folder_exits_2(tmp_path):
    home = Home(tmp_path)
    jobs_dir(home).mkdir(parents=True)
    (home.stub / "agents.json").write_text("not a list\n", encoding="utf-8")
    r = home.run("clean_jobs_tmp.py")
    assert (r.returncode, r.stdout) == (2, "")
    assert r.stderr == "clean_jobs_tmp.py: claude agents --json --all failed or did not print a JSON list\n"
    home.save_rows()
    missing = tmp_path / "nowhere"
    r = home.run("clean_jobs_tmp.py", "--jobs", str(missing))
    assert (r.returncode, r.stdout, r.stderr) == (2, "", f"clean_jobs_tmp.py: no jobs folder {missing}\n")
