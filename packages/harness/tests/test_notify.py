"""What the human is told after a poll (harness/notify.py), and `harness poll --all-active` beside a run it cannot
read. Built on the small configuration, so a role session runs these tests as the write gate does."""

from __future__ import annotations

import json
import shutil
import threading

import pytest
from harness import launch, notify, poll, state

BRIEF = "# Project brief — demo\n\n## Goal of this run\nNotes.\n\n## Constraints\n- Budget: 10 minutes per stage\n"
BLOCKED = {"action": "attention", "stage": "read", "waitingFor": "permission prompt", "job_id": "j1"}


@pytest.fixture()
def run(tmp_path, small_config, monkeypatch):
    monkeypatch.setattr(state, "claude_version", lambda: "test")
    root = small_config(tmp_path / "repo")
    brief = tmp_path / "brief.md"
    brief.write_text(BRIEF, encoding="utf-8")
    run_id = state.create_run(root, "demo", brief, [])["run_id"]
    return root, run_id, state.runs_root(root) / run_id


@pytest.fixture()
def sent(monkeypatch):
    """The lines `notify.send` was asked to send, in order."""
    lines: list[tuple[str, str]] = []
    monkeypatch.setattr(notify, "send", lambda root, kind, line: lines.append((kind, line)) or True)
    return lines


@pytest.mark.parametrize("text", ["", '["attention:read::", "appro', '{"not": "a list"}'])
def test_an_unreadable_record_of_what_was_told_counts_as_empty_and_is_written_again(run, sent, text):
    """02/F09: an empty, cut or foreign logs/notified.json neither raises nor hides an action."""
    root, run_id, run_dir = run
    seen = run_dir / "logs" / "notified.json"
    seen.write_text(text, encoding="utf-8")
    out = {"ok": True, "run_id": run_id, "status": "waiting_human", "actions": [BLOCKED]}
    assert notify.after_poll(root, out) is out
    assert [kind for kind, _ in sent] == ["attention"]
    assert json.loads(seen.read_text(encoding="utf-8")) == ["attention:read::"]


def test_a_unit_that_needs_the_human_again_is_announced_again(run, sent):
    """02/F10: an action is forgotten once a poll no longer prints it, so the next block of the unit is announced."""
    root, run_id, _ = run
    for actions in ([BLOCKED], [BLOCKED], [], [BLOCKED]):
        notify.after_poll(root, {"ok": True, "run_id": run_id, "status": "running", "actions": actions})
    assert [kind for kind, _ in sent] == ["attention", "attention"]


def test_a_finished_run_is_announced_once(run, sent):
    root, run_id, _ = run
    for _ in range(3):
        notify.after_poll(root, {"ok": True, "run_id": run_id, "status": "done", "actions": []})
    assert [kind for kind, _ in sent] == ["done"]


def test_a_paused_or_aborted_poll_announces_nothing_and_forgets_nothing(run, sent):
    root, run_id, run_dir = run
    notify.after_poll(root, {"ok": True, "run_id": run_id, "status": "waiting_human", "actions": [BLOCKED]})
    notify.after_poll(root, {"ok": True, "run_id": run_id, "status": "running", "paused": {"at": None}, "actions": []})
    notify.after_poll(root, {"ok": True, "run_id": run_id, "status": "aborted", "actions": []})
    notify.after_poll(root, {"ok": True, "run_id": run_id, "status": "waiting_human", "actions": [BLOCKED]})
    assert [kind for kind, _ in sent] == ["attention"]
    assert json.loads((run_dir / "logs" / "notified.json").read_text(encoding="utf-8")) == ["attention:read::"]


def test_two_polls_at_once_announce_an_action_once(run, sent, monkeypatch):
    """The record is read, changed and written under its one lock: two polls that see one action tell it once."""
    root, run_id, _ = run
    out = {"ok": True, "run_id": run_id, "status": "waiting_human", "actions": [BLOCKED]}
    both, real = threading.Barrier(2, timeout=1), notify._seen

    def read_together(path):
        found = real(path)
        try:
            both.wait()  # without the lock both polls read the record before either writes it
        except threading.BrokenBarrierError:
            pass  # with it the other poll waits for the lock, so nobody comes
        return found

    monkeypatch.setattr(notify, "_seen", read_together)
    threads = [threading.Thread(target=notify.after_poll, args=(root, out)) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert [kind for kind, _ in sent] == ["attention"]


def test_poll_all_names_a_run_it_cannot_read_and_polls_the_others(run, monkeypatch):
    """02/F26: one run whose state.json does not parse stops nothing."""
    root, run_id, run_dir = run
    good = state.load(root, run_dir / "state.json", "run-state")
    good["stages"]["read"].update(
        status="launched", attempts=1, session_ids=["s1"], job_ids=["j1"], started_at=state.now()
    )
    state.save(root, run_dir / "state.json", good, "run-state")
    bad = state.runs_root(root) / "20261004-000000-bad"
    bad.mkdir()
    (bad / "state.json").write_text('{"status": "running", "stag', encoding="utf-8")
    blocked = [
        {"id": "j1", "sessionId": "s1", "state": "blocked", "status": "waiting", "waitingFor": "permission prompt"}
    ]
    monkeypatch.setattr(launch, "listing", lambda root: blocked)
    out = poll.poll_all(root)
    assert [r["run_id"] for r in out["runs"]] == [run_id] and out["runs"][0]["actions"][0]["action"] == "attention"
    assert [u["run_id"] for u in out["unreadable"]] == ["20261004-000000-bad"]
    assert out["unreadable"][0]["why"].startswith("JSONDecodeError")


def test_poll_all_names_a_run_whose_poll_raised_and_polls_the_others(run, monkeypatch):
    """One run whose gate raises (a file where a given test's folder should be) stops nothing: the error is named
    under `failed`, and the other runs are polled all the same."""
    root, run_id, run_dir = run
    shutil.copytree(run_dir, state.runs_root(root) / "20261004-000000-other")

    def fake(root, rid, rows):
        if rid == run_id:
            raise FileExistsError(17, "File exists")
        return {"ok": True, "run_id": rid, "actions": []}

    monkeypatch.setattr(launch, "listing", lambda root: [])
    monkeypatch.setattr(poll, "poll", fake)
    out = poll.poll_all(root)
    assert [r["run_id"] for r in out["runs"]] == ["20261004-000000-other"]
    assert out["failed"] == [{"run_id": run_id, "why": "FileExistsError: [Errno 17] File exists"}]


@pytest.mark.parametrize("action", ["loop_cap", "no_progress", "rejected", "replan"])
def test_a_loop_that_stops_is_announced_to_the_human(run, sent, action):
    """specs/002-run-loop: a loop that stops for the human tells the human, as an approval does."""
    root, run_id, _ = run
    stop = {"action": action, "stage": "read"}
    notify.after_poll(root, {"ok": True, "run_id": run_id, "status": "waiting_human", "actions": [stop]})
    assert [kind for kind, _ in sent] == [action]
