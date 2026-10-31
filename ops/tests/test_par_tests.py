"""par-tests.sh (spec B3): one test command over several paths, 4 at a time, each run's output in its own file and one
line per run in a log, so slow test files run in the time of the slowest (an earlier project of the owner: 157 s one
after another, 63 s at once).

  python3 -m pytest -q -p no:cacheprovider ops/tests/test_par_tests.py
"""

import os
import pathlib
import re
import subprocess

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "par-tests.sh"
# A fake test command, `bash runner.sh <marks> <want> <path>`: it marks its start, waits until <want> runs have started
# (at most 3 s), writes how many it saw, prints its path and fails for a path with "bad" in it.
RUNNER = """#!/bin/bash
touch "$1/start-$(basename "$3")"
for _ in $(seq 30); do
  [ "$(ls "$1" | grep -c '^start-')" -ge "$2" ] && break
  sleep 0.1
done
ls "$1" | grep -c '^start-' > "$1/seen-$(basename "$3")"
echo "ran $3"
case "$3" in *bad*) exit 3 ;; esac
"""


def run(tmp: pathlib.Path, want: int, paths: list[str], jobs: str = "") -> subprocess.CompletedProcess:
    """Run par-tests.sh in tmp with the out prefix "run" and the fake command; PAR_JOBS only when jobs is given."""
    (tmp / "runner.sh").write_text(RUNNER, encoding="utf-8")
    (tmp / "marks").mkdir()
    env = {k: v for k, v in os.environ.items() if k != "PAR_JOBS"} | ({"PAR_JOBS": jobs} if jobs else {})
    command = f"bash {tmp / 'runner.sh'} {tmp / 'marks'} {want}"
    return subprocess.run(
        ["bash", str(SCRIPT), "run", command, *paths],
        cwd=tmp,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def seen(tmp: pathlib.Path) -> list[str]:
    """How many runs had started when each run stopped waiting, sorted."""
    return sorted(p.read_text(encoding="utf-8").strip() for p in (tmp / "marks").glob("seen-*"))


def test_four_paths_run_at_once_each_with_its_output_file_and_its_log_line(tmp_path):
    paths = ["tests/a_test.py", "tests/b_test.py", "tests/bad_test.py", "tests/d_test.py"]
    out = run(tmp_path, 4, paths)
    assert out.returncode == 1, out.stdout + out.stderr  # one run failed
    assert seen(tmp_path) == ["4", "4", "4", "4"]  # all four were running at once
    log = (tmp_path / "run.log").read_text(encoding="utf-8").splitlines()
    assert len(log) == 5 and re.fullmatch(r"done: 1 failed of 4 in \d+ s", log[4])
    rows = sorted(re.findall(r"^(\d): exit (\d+) in \d+ s: (\S+)$", "\n".join(log[:4]), re.MULTILINE))
    assert rows == [("1", "0", paths[0]), ("2", "0", paths[1]), ("3", "3", paths[2]), ("4", "0", paths[3])]
    for n, path in enumerate(paths, 1):
        assert (tmp_path / f"run-{n}.txt").read_text(encoding="utf-8") == f"ran {path}\n"


def test_par_jobs_sets_how_many_run_at_once(tmp_path):
    out = run(tmp_path, 3, ["a_test.py", "b_test.py", "c_test.py"], jobs="2")
    assert out.returncode == 0, out.stdout + out.stderr
    assert seen(tmp_path) == ["2", "2", "3"]  # two at once; the third started when one had ended
    assert (tmp_path / "run.log").read_text(encoding="utf-8").splitlines()[-1].startswith("done: 0 failed of 3 in ")


def test_a_missing_argument_is_a_usage_error(tmp_path):
    out = subprocess.run(
        ["bash", str(SCRIPT), "run", "true"], cwd=tmp_path, capture_output=True, text=True, timeout=60, check=False
    )
    assert out.returncode == 2
    assert 'usage: par-tests.sh <out prefix> "<test command>" <path> [<path> ...]' in out.stdout
    assert not (tmp_path / "run.log").exists()
