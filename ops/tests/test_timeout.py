"""ops/timeout.py: timeout(1) for a system that has none (macOS, found by the macOS workflow: par-tests.sh ran nothing
there). It keeps timeout(1)'s exits: 124 past the limit, the command's own otherwise.

  python3 -m pytest -q -p no:cacheprovider ops/tests/test_timeout.py
"""

from __future__ import annotations

import importlib.util
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "timeout.py"


def limited(*args: str) -> tuple[subprocess.CompletedProcess, float]:
    t = time.monotonic()
    done = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True, timeout=60, check=False
    )
    return done, time.monotonic() - t


def test_a_command_within_its_limit_keeps_its_exit_and_its_output():
    done, _ = limited("5", "sh", "-c", "echo ran; exit 3")
    assert (done.returncode, done.stdout) == (3, "ran\n")


def test_a_command_past_its_limit_is_stopped_with_124():
    done, took = limited("0.5", "sleep", "30")
    assert done.returncode == 124 and took < 10


def test_a_command_that_ignores_sigterm_is_killed_after_the_grace():
    done, took = limited("-k", "0.5", "0.5", "sh", "-c", "trap '' TERM; sleep 30")
    assert done.returncode == 124 and took < 10


def test_the_whole_group_is_stopped_not_only_the_command(tmp_path):
    """par-tests.sh runs `uv run pytest`: the limit reaches the children too."""
    mark = tmp_path / "mark"
    done, _ = limited("0.5", "sh", "-c", f"(sleep 2; touch {mark}) & wait")
    time.sleep(3)
    assert done.returncode == 124 and not mark.exists()


@pytest.mark.parametrize("sig", [signal.SIGTERM, signal.SIGINT, signal.SIGHUP])
def test_a_signal_to_the_wrapper_reaches_the_command(tmp_path, sig):
    """V1 of the macos-windows run: Ctrl-C on a script stopped the wrapper, and its command, in a session of its own,
    went on with no limit at all."""
    mark = tmp_path / "mark"
    proc = subprocess.Popen([sys.executable, "-I", str(SCRIPT), "30", "sh", "-c", f"sleep 2; touch {mark}"])
    time.sleep(0.5)
    proc.send_signal(sig)
    assert proc.wait(timeout=10) == 128 + sig
    time.sleep(2.5)
    assert not mark.exists()


def test_a_grace_of_0_is_no_kill():
    done, took = limited("-k", "0", "0.5", "sh", "-c", "trap '' TERM; sleep 2")
    assert done.returncode == 124 and took >= 1.5  # waited for the command, never killed it


@pytest.mark.parametrize(("text", "want"), [("90", 90.0), ("0.5", 0.5), ("2m", 120.0), ("1h", 3600.0), ("1d", 86400.0)])
def test_a_duration_is_read_as_timeout_1_reads_it(text, want):
    spec = importlib.util.spec_from_file_location("ops_timeout", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.seconds(text) == want


@pytest.mark.parametrize("args", [[], ["5"], ["x", "true"], ["-k"], ["-k", "1", "5"]])
def test_a_wrong_call_is_a_usage_error(args):
    done, _ = limited(*args)
    assert done.returncode == 125 and "usage: timeout.py" in done.stderr


def test_a_command_that_is_not_found_exits_127():
    done, _ = limited("5", "no-such-command-here")
    assert done.returncode == 127
