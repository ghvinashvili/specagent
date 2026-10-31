"""One writer at a time for a run's state.json (docs/decisions/0021-one-writer-at-a-time-for-run-and-loop-state.md):
every writer reads, changes and writes under the file's one lock, never while a session or a gate runs, and keeps
what another command wrote meanwhile; every write goes through a temporary file of its own. The pause switch
(docs/decisions/0023-one-pause-switch.md) stops launch, resume and poll. Built on the small configuration and a
stand-in for `claude`, so a role session collects and runs these tests as the write gate does."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
import yaml
from harness import gates, launch, pause, poll, resume, state, work

REPO = next(
    p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file() and (p / "schemas").is_dir()
)
BRIEF = "# Project brief — demo\n\n## Goal of this run\nNotes.\n\n## Constraints\n- Budget: 10 minutes per stage\n"


def update(root: Path, run_dir: Path, change) -> None:
    """Load state.json, let `change(st)` edit it, save it (a test's own write, before the command under test runs)."""
    st = state.load(root, run_dir / "state.json", "run-state")
    change(st)
    state.save(root, run_dir / "state.json", st, "run-state")


@pytest.fixture()
def run(tmp_path, small_config, monkeypatch):
    """A run of the small configuration: `read` (reader), then `plan` (planner)."""
    monkeypatch.setattr(state, "claude_version", lambda: "test")
    root = small_config(tmp_path / "repo")
    brief = tmp_path / "brief.md"
    brief.write_text(BRIEF, encoding="utf-8")
    run_id = state.create_run(root, "demo", brief, [])["run_id"]
    return root, run_id, state.runs_root(root) / run_id


HOLDER = (
    "import sys, time\nfrom pathlib import Path\nfrom harness import state\n"
    "with state.locked(Path(sys.argv[1])):\n    Path(sys.argv[2]).write_text('held')\n    time.sleep(60)\n"
)


def test_a_lock_left_by_a_process_that_died_stops_no_later_writer(tmp_path):
    target, marker = tmp_path / "state.json", tmp_path / "held"
    holder = subprocess.Popen([sys.executable, "-c", HOLDER, str(target), str(marker)])
    try:
        deadline = time.monotonic() + 30
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert marker.exists()
        taken = threading.Event()

        def take():
            with state.locked(target):
                taken.set()

        threading.Thread(target=take, daemon=True).start()
        assert not taken.wait(0.5)  # a live holder: the next writer waits
        holder.kill()  # SIGKILL: the holder runs no clean-up of its own
        holder.wait(timeout=30)
        assert taken.wait(10)  # the kernel let the lock go with its holder
        assert (tmp_path / "state.json.lock").is_file()  # the lock file stays and holds nothing
    finally:
        holder.kill()


def test_every_save_writes_through_a_temporary_file_of_its_own(run, monkeypatch):
    root, _, run_dir = run
    renamed: list[str] = []
    real = os.replace

    def spy(src, dst):
        renamed.append(Path(src).name)
        return real(src, dst)

    monkeypatch.setattr(os, "replace", spy)
    st = state.load(root, run_dir / "state.json", "run-state")
    state.save(root, run_dir / "state.json", st, "run-state")
    state.save(root, run_dir / "state.json", st, "run-state")
    assert len(renamed) == 2 and renamed[0] != renamed[1]
    assert all(n.startswith(f"state.json.{os.getpid()}.") and n.endswith(".tmp") for n in renamed)
    assert not list(run_dir.glob("*.tmp"))


WORKER = """import json, sys
from pathlib import Path
from harness import state
root, path, n = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
doc = json.loads(path.read_text(encoding="utf-8"))
doc["stages"]["read"]["note"] = "x" * (300 * n)
errors = 0
for _ in range(100):
    try:
        state.save(root, path, json.loads(json.dumps(doc)), "run-state")
    except Exception:
        errors += 1
print(errors)
"""


def test_writers_at_once_never_raise_and_a_reader_never_meets_half_a_file(run):
    root, _, run_dir = run
    path = run_dir / "state.json"
    workers = [
        subprocess.Popen(
            [sys.executable, "-c", WORKER, str(root), str(path), str(n)], stdout=subprocess.PIPE, text=True
        )
        for n in (1, 2, 3, 4)
    ]
    reads, unreadable = 0, 0
    while any(w.poll() is None for w in workers):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            unreadable += 1
        reads += 1
    errors = [int(w.communicate()[0].strip()) for w in workers]
    assert errors == [0, 0, 0, 0] and unreadable == 0 and reads > 0
    state.load(root, path, "run-state")  # the last save left a whole, valid file
    assert not list(run_dir.glob("*.tmp"))


def read_finished_plan_waiting(root: Path, run_dir: Path) -> None:
    """`read` launched as job j1 (its session has finished), `plan` done and waiting for the human's approval."""

    def change(st):
        st["stages"]["read"].update(
            status="launched", attempts=1, session_ids=["s1"], job_ids=["j1"], started_at=state.now()
        )
        st["stages"]["plan"].update(status="done", gate="pass", attempts=1, session_ids=["s2"], approval="pending")

    update(root, run_dir, change)


DONE = [{"id": "j1", "sessionId": "s1", "state": "done"}]


def test_an_approval_recorded_while_poll_gates_a_unit_is_kept(run, monkeypatch):
    """02/F01: poll writes back what it found, not the copy it read before the gate."""
    root, run_id, run_dir = run
    read_finished_plan_waiting(root, run_dir)

    def gate_meanwhile(*args, **kwargs):
        assert state.approve(root, run_id, "plan", "approved")["ok"]  # the human, while the gate runs
        return {"passed": True, "next": "advance"}

    monkeypatch.setattr(gates, "run_gate", gate_meanwhile)
    out = poll.poll(root, run_id, listing=DONE)
    st = state.load(root, run_dir / "state.json", "run-state")
    assert st["stages"]["plan"]["approval"] == "approved"
    assert st["stages"]["read"]["status"] == "done" and st["stages"]["read"]["gate"] == "pass"
    assert [a["action"] for a in out["actions"]] == ["gate"] and out["status"] == "done"


def test_a_run_aborted_while_poll_gates_a_unit_stays_aborted(run, monkeypatch):
    """02/F01: an abort recorded while poll gates is never undone; poll writes nothing to the aborted run."""
    root, run_id, run_dir = run
    read_finished_plan_waiting(root, run_dir)

    def abort_meanwhile(*args, **kwargs):
        with state.locked(run_dir / "state.json"):  # what `harness abort` records, the way it records it
            st = state.load(root, run_dir / "state.json", "run-state")
            st["aborted"] = {"at": state.now(), "reason": "the human stopped it", "from": st["status"]}
            st["status"] = "aborted"
            state.save(root, run_dir / "state.json", st, "run-state")
        return {"passed": True, "next": "advance"}

    monkeypatch.setattr(gates, "run_gate", abort_meanwhile)
    assert poll.poll(root, run_id, listing=DONE) == {"ok": True, "run_id": run_id, "status": "aborted", "actions": []}
    assert state.load(root, run_dir / "state.json", "run-state")["status"] == "aborted"
    assert state.refuse_aborted(root, run_id)["status"] == "run_aborted"


def test_poll_keeps_the_record_another_command_wrote_for_a_unit_meanwhile(run, monkeypatch):
    """A unit another command changed while poll gated it (a resume started its next attempt) keeps that command's
    record, and poll's actions for it are dropped: the next poll derives them from the unit as it is."""
    root, run_id, run_dir = run
    read_finished_plan_waiting(root, run_dir)

    def resumed_meanwhile(*args, **kwargs):
        with state.locked(run_dir / "state.json"):
            st = state.load(root, run_dir / "state.json", "run-state")
            st["stages"]["read"].update(status="launched", attempts=2, job_ids=["j1", "j2"], started_at=state.now())
            state.save(root, run_dir / "state.json", st, "run-state")
        return {"passed": False, "next": "retry"}

    monkeypatch.setattr(gates, "run_gate", resumed_meanwhile)
    out = poll.poll(root, run_id, listing=DONE)
    read = state.load(root, run_dir / "state.json", "run-state")["stages"]["read"]
    assert (read["status"], read["attempts"], read["job_ids"], read["gate"]) == ("launched", 2, ["j1", "j2"], "pending")
    assert [a for a in out["actions"] if a.get("stage") == "read"] == []


def test_poll_drops_its_actions_for_a_unit_another_command_changed_meanwhile(run, monkeypatch):
    """A stopped unit poll would resume, which another command resumed while poll gated another unit: poll changed
    nothing in it and still prints no action for it, as for every unit changed meanwhile (plan D3, ADR-0021); the
    next poll derives its actions from the unit as it is."""
    root, run_id, run_dir = run

    def change(st):
        st["stages"]["read"].update(status="stopped", attempts=1, session_ids=["s1"], job_ids=["j1"])
        st["stages"]["plan"].update(
            status="launched", attempts=1, session_ids=["s2"], job_ids=["j2"], started_at=state.now()
        )

    update(root, run_dir, change)

    def resumed_meanwhile(*args, **kwargs):
        with state.locked(run_dir / "state.json"):  # the manager resumes `read` while poll gates `plan`
            st = state.load(root, run_dir / "state.json", "run-state")
            st["stages"]["read"].update(status="launched", attempts=2, job_ids=["j1", "j3"], started_at=state.now())
            state.save(root, run_dir / "state.json", st, "run-state")
        return {"passed": True, "next": "advance"}

    monkeypatch.setattr(gates, "run_gate", resumed_meanwhile)
    out = poll.poll(root, run_id, listing=[{"id": "j2", "sessionId": "s2", "state": "done"}])
    st = state.load(root, run_dir / "state.json", "run-state")
    assert [(a["action"], a["stage"]) for a in out["actions"]] == [("gate", "plan")] and out["status"] == "running"
    assert (st["stages"]["read"]["status"], st["stages"]["read"]["attempts"]) == ("launched", 2)
    assert (st["stages"]["plan"]["status"], st["stages"]["plan"]["gate"]) == ("done", "pass")


def test_poll_merges_each_shard_of_a_stage_on_its_own(run, monkeypatch):
    """A sharded stage: the shard another command resumed while poll gated the other one keeps that command's record
    and loses poll's action, the gated shard takes poll's record, and the stage row is aggregated from the merge."""
    root, run_id, run_dir = run
    shard = {"status": "launched", "attempts": 1, "gate": "pending", "started_at": state.now()}

    def change(st):
        st["stages"]["read"].update(status="working", attempts=1, session_ids=["s1", "s2"])
        st["stages"]["read"]["shards"] = {
            "01": {**shard, "session_ids": ["s1"], "job_ids": ["j1"]},
            "02": {**shard, "session_ids": ["s2"], "job_ids": ["j2"]},
        }

    update(root, run_dir, change)

    def resumed_meanwhile(*args, **kwargs):
        with state.locked(run_dir / "state.json"):
            st = state.load(root, run_dir / "state.json", "run-state")
            st["stages"]["read"]["shards"]["01"].update(attempts=2, job_ids=["j1", "j3"], started_at=state.now())
            state.save(root, run_dir / "state.json", st, "run-state")
        return {"passed": True, "next": "advance"}

    monkeypatch.setattr(gates, "run_gate", resumed_meanwhile)
    out = poll.poll(root, run_id, listing=[{"id": "j2", "sessionId": "s2", "state": "done"}])  # j1's session is gone
    read = state.load(root, run_dir / "state.json", "run-state")["stages"]["read"]
    one, two = read["shards"]["01"], read["shards"]["02"]
    assert (one["status"], one["attempts"], one["job_ids"]) == ("launched", 2, ["j1", "j3"])
    assert (two["status"], two["gate"]) == ("done", "pass")
    assert (read["status"], read["attempts"]) == ("working", 2)
    assert [(a["action"], a.get("shard")) for a in out["actions"]] == [("gate", 2)] and out["status"] == "running"


def test_harness_gate_and_approve_wait_for_the_lock(run, monkeypatch):
    """Every writer takes the one lock around its read, change and write: while another holds it, nothing is written."""
    root, run_id, run_dir = run
    path = run_dir / "state.json"
    update(root, run_dir, lambda st: st["stages"]["read"].update(status="stopped", attempts=1))
    monkeypatch.setattr(gates, "run_gate", lambda *a, **k: {"passed": True, "next": "advance"})
    writers = [
        lambda: state.approve(root, run_id, "plan", "approved"),
        lambda: state.refreeze(root, run_id),
        lambda: poll.gate_now(root, run_id, "read"),
        lambda: poll.poll(root, run_id, listing=[]),
    ]
    for write in writers:
        before = path.read_bytes()
        with state.locked(path):
            t = threading.Thread(target=write)
            t.start()
            time.sleep(0.3)
            assert path.read_bytes() == before and t.is_alive()  # it waits for the lock
        t.join(timeout=30)
        assert not t.is_alive() and path.read_bytes() != before


def test_a_writer_that_finds_its_run_aborted_under_the_lock_writes_nothing(run, monkeypatch):
    """An abort recorded after a command's own check is seen again under the lock: approve and refreeze refuse, and
    the verdict of a gate is not recorded (docs/decisions/0010)."""
    root, run_id, run_dir = run
    path = run_dir / "state.json"

    def aborted(st):
        st["stages"]["read"].update(status="stopped", attempts=1)
        st["aborted"] = {"at": state.now(), "reason": "the human stopped it", "from": st["status"]}
        st["status"] = "aborted"

    update(root, run_dir, aborted)
    monkeypatch.setattr(gates, "run_gate", lambda *a, **k: {"passed": True, "next": "advance"})
    before = path.read_bytes()
    assert state.approve(root, run_id, "plan", "approved")["status"] == "run_aborted"
    assert state.refreeze(root, run_id)["status"] == "run_aborted"
    assert poll.gate_now(root, run_id, "read")["unit_status"] == "stopped"
    assert path.read_bytes() == before


def test_abort_keeps_what_was_written_while_its_sessions_stopped(run, monkeypatch):
    root, run_id, run_dir = run
    update(root, run_dir, lambda st: st["stages"]["plan"].update(approval="pending"))

    def clean_meanwhile(*args, **kwargs):
        assert state.approve(root, run_id, "plan", "approved")["ok"]
        return {"ok": True, "removed": [], "kept_branches": [], "salvaged": [], "not_removed": []}

    monkeypatch.setattr(work, "clean_checkouts", clean_meanwhile)
    monkeypatch.setattr(work, "remove_sessions", lambda st: [])
    out = work.abort_run(root, run_id, "the human stopped it")
    st = state.load(root, run_dir / "state.json", "run-state")
    assert out["ok"] and st["status"] == "aborted" and st["stages"]["plan"]["approval"] == "approved"


def test_a_second_abort_keeps_the_record_of_the_first(run, monkeypatch):
    """Two aborts at once: the one that takes the lock second keeps the record the first wrote."""
    root, run_id, run_dir = run

    def first_abort(*args, **kwargs):
        record = {"at": state.now(), "reason": "first", "from": "created"}
        update(root, run_dir, lambda st: st.update(aborted=record, status="aborted"))
        return {"ok": True, "removed": [], "kept_branches": [], "salvaged": [], "not_removed": []}

    monkeypatch.setattr(work, "clean_checkouts", first_abort)
    monkeypatch.setattr(work, "remove_sessions", lambda st: [])
    out = work.abort_run(root, run_id, "second")
    st = state.load(root, run_dir / "state.json", "run-state")
    assert out["ok"] and out["from"] == "created" and (st["status"], st["aborted"]["reason"]) == ("aborted", "first")


# --- launch and resume: a stand-in for `claude` and a configuration with a print stage ---

DEFAULTS = {
    "dirs": ["stage"],
    "blind": False,
    "brief_drop": [],
    "cache_ttl": "5m",
    "plugins": [],
    "mcp_servers": [],
    "pack_files": [],
    "repo_deny": [],
    "blind_deny": [],
    "home_deny": [],
    "never_copy": ["result.json", "progress.md", "prompt.md", "gate.json", "pack.md", "logs/**"],
    "user_instructions": [],
    "project_instructions": [],
    "project_plugins": [],
    "models": ["opus", "sonnet", "haiku"],
}
COMMON = {"mode": "bg", "model": "sonnet", "effort": "high", "output": "output/", "approval": "none",
          "permission_mode": "acceptEdits", "max_minutes": 30, "max_attempts": 3}  # fmt: skip
STAGES = [
    {**COMMON, "id": "read", "role_type": "reader", "inputs": ["brief"], "gate": "read", "approval": "human"},
    {**COMMON, "id": "judge", "role_type": "judge", "inputs": [], "gate": "judge", "mode": "print",
     "json_schema": "stage-result.schema.json"},
]  # fmt: skip
ASSIGNMENT = (
    "# Assignment — judge\n\n## Goal\nThe human decides on this verdict alone and will not open the reports again.\n\n"
    "## Deliver\n- `result.json`: the verdict with one reason per finding, each naming the entry it rests on.\n\n"
    "## Prove\nEvery reason cites an entry that exists in the reports, and every blocking finding is answered.\n\n"
    "## Done when\nThe verdict names every blocking finding and every reason cites an existing entry of a report.\n"
)


class FakeClaude:
    """subprocess.run for `claude ...`: `-p` returns `result` as structured output after calling `on_print`;
    `agents --json` lists nothing. Every other program runs for real."""

    def __init__(self, real):
        self.real, self.calls = real, []
        self.result: dict | None = None
        self.on_print = None

    def __call__(self, cmd, *args, **kwargs):
        if not cmd or cmd[0] != "claude":
            return self.real(cmd, *args, **kwargs)
        self.calls.append([str(c) for c in cmd])
        if "-p" in cmd:
            if self.on_print:
                self.on_print()
            doc = {"structured_output": self.result, "total_cost_usd": 0.25}
            return subprocess.CompletedProcess(cmd, 0, json.dumps(doc), "")
        return subprocess.CompletedProcess(cmd, 0, "[]" if cmd[1:2] == ["agents"] else "", "")


@pytest.fixture()
def rig(tmp_path, monkeypatch):
    """A run whose `read` stage passed and waits for the human's approval, and whose print stage `judge` has its
    assignment; `claude` is the stand-in."""
    root = tmp_path / "repo"
    shutil.copytree(REPO / "schemas", root / "schemas")
    roles = root / "docs" / "roles"
    roles.mkdir(parents=True)
    table = {"version": 1, "stages": STAGES, "no_match": {"action": "escalate", "message": "no table fits"}}
    (roles / "stages.yaml").write_text(yaml.safe_dump(table, sort_keys=False), encoding="utf-8")
    policy = {"schema_version": 1, "defaults": DEFAULTS, "types": {"reader": {"may_receive": ["brief"]},
              "judge": {"may_receive": [], "outputs_of": []}}}  # fmt: skip
    (roles / "need-to-know.yaml").write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
    agents = root / ".claude" / "agents"
    agents.mkdir(parents=True)
    for name, tools in (("reader", "Read, Glob, Grep, Bash, Write, Edit"), ("judge", "Read, StructuredOutput")):
        (agents / f"{name}.md").write_text(f"---\nname: {name}\ntools: {tools}\n---\n# {name}\n", encoding="utf-8")
    monkeypatch.setattr(state, "claude_version", lambda: "test")
    monkeypatch.setattr(launch, "wait_first_response", lambda *a, **k: False)
    monkeypatch.delenv("HARNESS_ROLE", raising=False)  # the test is the human here, also inside a role session
    fake = FakeClaude(subprocess.run)
    monkeypatch.setattr(subprocess, "run", fake)
    brief = tmp_path / "brief.md"
    brief.write_text(BRIEF, encoding="utf-8")
    run_id = state.create_run(root, "demo", brief, [])["run_id"]
    run_dir = state.runs_root(root) / run_id
    update(
        root,
        run_dir,
        lambda st: st["stages"]["read"].update(status="done", gate="pass", attempts=1, session_ids=["s1"]),
    )
    source = tmp_path / "assignment.md"
    source.write_text(ASSIGNMENT, encoding="utf-8")
    assert launch.assign(root, run_id, "judge", source)["ok"]
    fake.result = {"schema_version": 1, "run_id": run_id, "stage": "judge", "role_type": "judge", "status": "complete",
                   "outputs": [], "summary": "s", "evidence": [], "open_questions": [],
                   "verdict": {"decision": "accept", "reasons": ["r"]}}  # fmt: skip
    return root, run_id, run_dir, fake


def test_launch_and_resume_keep_an_approval_recorded_while_their_session_ran(rig):
    """01/F03: what launch and resume record is carried into state.json as it is after `claude` returned."""
    root, run_id, run_dir, fake = rig
    fake.on_print = lambda: state.approve(root, run_id, "read", "approved")  # the human, while judge runs
    assert launch.launch(root, run_id, "judge")["ok"]
    st = state.load(root, run_dir / "state.json", "run-state")
    assert st["stages"]["read"]["approval"] == "approved"
    assert (st["stages"]["judge"]["status"], st["stages"]["judge"]["attempts"]) == ("checkpointed", 1)
    assert st["cost"]["print_total_usd"] == 0.25 and st["current_stage"] == "judge"
    update(root, run_dir, lambda s: s["stages"]["read"].update(approval="pending"))
    assert resume.resume(root, run_id, "judge", message="check the reasons again")["ok"]
    st = state.load(root, run_dir / "state.json", "run-state")
    assert st["stages"]["read"]["approval"] == "approved" and st["stages"]["judge"]["attempts"] == 2
    assert st["cost"]["print_total_usd"] == 0.5


def test_a_launch_whose_run_was_aborted_meanwhile_writes_nothing(rig):
    root, run_id, run_dir, fake = rig

    def abort_meanwhile():
        with state.locked(run_dir / "state.json"):
            st = state.load(root, run_dir / "state.json", "run-state")
            st["aborted"] = {"at": state.now(), "reason": "the human stopped it", "from": st["status"]}
            st["status"] = "aborted"
            state.save(root, run_dir / "state.json", st, "run-state")

    fake.on_print = abort_meanwhile
    out = launch.launch(root, run_id, "judge")
    st = state.load(root, run_dir / "state.json", "run-state")
    assert not out["ok"] and out["status"] == "run_aborted"
    assert st["status"] == "aborted" and st["stages"]["judge"]["attempts"] == 0
    assert not launch.lock_path(run_dir, "judge", None).exists()


def test_a_wave_records_its_shards_in_the_state_file_as_it_is_when_it_splits(tmp_path, small_config, monkeypatch):
    """The split of a `parallel: per_task` stage writes its shard records into state.json as the file is under the
    lock, not into the copy launch read before it asked for the sandbox and the trust record."""
    monkeypatch.setattr(state, "claude_version", lambda: "test")
    root = small_config(tmp_path / "repo")
    write = {**COMMON, "id": "write", "role_type": "writer", "inputs": ["brief", "plan:tasks.json"], "gate": "write",
             "depends_on": ["plan"], "parallel": "per_task", "max_shards": 2}  # fmt: skip
    plan = {**COMMON, "id": "plan", "role_type": "planner", "inputs": ["brief"], "gate": "plan"}
    table = {"version": 1, "stages": [plan, write], "no_match": {"action": "escalate", "message": "no table fits"}}
    (root / "docs" / "roles" / "stages.yaml").write_text(yaml.safe_dump(table, sort_keys=False), encoding="utf-8")
    brief = tmp_path / "brief.md"
    brief.write_text(BRIEF, encoding="utf-8")
    run_id = state.create_run(root, "demo", brief, [])["run_id"]
    run_dir = state.runs_root(root) / run_id
    task = {"category": "code", "description": "d", "steps": ["s"], "depends_on": [], "passes": False}
    tasks = {"schema_version": 1, "stage": "plan", "tasks": [{"id": "T001", **task}, {"id": "T002", **task}]}
    (run_dir / "stages" / "plan").mkdir(parents=True, exist_ok=True)
    state.save(root, run_dir / "stages" / "plan" / "tasks.json", tasks, "tasks")
    real = launch.launch

    def asked_meanwhile(root, mode="bg"):
        assert state.approve(root, run_id, "plan", "approved")["ok"]  # the human, while launch asks for the sandbox
        return {"ok": True}

    def no_session(root, run_id, stage_id, shard=None):  # the wave itself runs; its shards start no session here
        return real(root, run_id, stage_id, shard) if shard is None else {"ok": True}

    monkeypatch.setattr(launch, "status", lambda *args: {"ok": True, "status": "ready"})
    monkeypatch.setattr(launch, "before_start", asked_meanwhile)
    monkeypatch.setattr(launch, "launch", no_session)
    out = launch.launch(root, run_id, "write")
    st = state.load(root, run_dir / "state.json", "run-state")
    assert out["ok"] and out["shards"] == 2 and sorted(st["stages"]["write"]["shards"]) == ["01", "02"]
    assert st["stages"]["plan"]["approval"] == "approved"


def test_commit_carries_what_a_launch_did_and_keeps_what_others_wrote_meanwhile(run):
    """launch.commit for one shard: its record, the ids it added, the escalation it marked answered, the print cost it
    added and the run's status go into state.json; its sibling shard, an approval, an escalation and a print cost
    recorded meanwhile stay."""
    root, _, run_dir = run
    empty = {"status": "pending", "attempts": 0, "session_ids": [], "job_ids": [], "gate": "pending"}

    def sharded(st):
        st["stages"]["read"]["shards"] = {"01": dict(empty), "02": dict(empty)}
        st["escalations"] = [{"id": "001", "stage": "read", "status": "open"}]

    update(root, run_dir, sharded)
    before = state.load(root, run_dir / "state.json", "run-state")
    after = json.loads(json.dumps(before))  # what the launch of shard 02 did to its copy
    after["stages"]["read"]["shards"]["02"].update(status="launched", attempts=1, session_ids=["s2"], job_ids=["j2"])
    after["stages"]["read"].update(status="launched", attempts=1, session_ids=["s2"], job_ids=["j2"])
    after["escalations"][0]["status"] = "answered"
    after["cost"] = {"print_total_usd": 0.25, "note": ""}
    after["status"], after["current_stage"] = "running", "read"

    def meanwhile(st):  # the launch of shard 01, the human and a poll, while shard 02's session started
        st["stages"]["read"]["shards"]["01"].update(status="launched", attempts=1, session_ids=["s1"], job_ids=["j1"])
        st["stages"]["read"].update(status="launched", attempts=1, session_ids=["s1"], job_ids=["j1"])
        st["stages"]["plan"]["approval"] = "approved"
        st["escalations"].append({"id": "002", "stage": "read", "status": "open"})
        st["cost"] = {"print_total_usd": 0.5, "note": ""}

    update(root, run_dir, meanwhile)
    assert launch.commit(root, run_dir, before, after, "read", 2) is not None
    st = state.load(root, run_dir / "state.json", "run-state")
    read = st["stages"]["read"]
    assert (read["shards"]["01"]["session_ids"], read["shards"]["02"]["session_ids"]) == (["s1"], ["s2"])
    assert read["shards"]["02"]["status"] == "launched"
    assert (read["session_ids"], read["job_ids"]) == (["s1", "s2"], ["j1", "j2"])
    assert [(e["id"], e["status"]) for e in st["escalations"]] == [("001", "answered"), ("002", "open")]
    assert st["cost"]["print_total_usd"] == 0.75 and st["stages"]["plan"]["approval"] == "approved"
    assert (st["status"], st["current_stage"]) == ("running", "read")


# --- the pause switch ---


def test_the_pause_switch_stops_launch_resume_and_poll_and_leaves_the_state_as_it_is(rig):
    root, run_id, run_dir, fake = rig
    assert pause.set_flag(root, "the machine goes to repair")["ok"]
    before = (run_dir / "state.json").read_bytes()
    out = launch.launch(root, run_id, "judge")
    assert not out["ok"] and out["status"] == "paused" and out["paused"]["reason"] == "the machine goes to repair"
    assert resume.resume(root, run_id, "judge", message="go on")["status"] == "paused"
    polled = poll.poll(root, run_id, listing=[])
    assert polled["paused"] and polled["actions"] == [] and poll.poll_all(root)["runs"] == []
    assert (run_dir / "state.json").read_bytes() == before and not any("-p" in c for c in fake.calls)
    held = pause.current(root)
    assert pause.lift(root) == {"ok": True, "lifted": True, "was": held}
    assert pause.current(root) is None and launch.launch(root, run_id, "judge")["ok"]  # the same work goes on


def test_watch_returns_at_once_while_the_switch_is_set(rig):
    """`harness watch` polls until the run needs the manager; while the switch is set it returns after one poll."""
    root, run_id, _, _ = rig
    assert pause.set_flag(root, "the human is away")["ok"]
    out = poll.watch(root, run_id, every=0, max_minutes=0)
    assert out["paused"]["reason"] == "the human is away" and out["watched"] and "timed_out" not in out


def test_a_role_session_neither_sets_nor_lifts_the_pause_switch(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setenv("HARNESS_ROLE", "writer")
    assert pause.set_flag(root, "a writer tidying up")["status"] == "role_session" and pause.current(root) is None
    monkeypatch.delenv("HARNESS_ROLE")
    assert pause.set_flag(root, "the human")["ok"]
    monkeypatch.setenv("HARNESS_ROLE", "writer")
    assert pause.lift(root)["status"] == "role_session" and pause.current(root)["reason"] == "the human"


def test_a_pause_flag_that_cannot_be_read_still_pauses(tmp_path, monkeypatch):
    monkeypatch.delenv("HARNESS_ROLE", raising=False)
    root = tmp_path / "repo"
    root.mkdir()
    pause.flag_path(root).parent.mkdir(parents=True)
    pause.flag_path(root).write_text('{"at": "2026-', encoding="utf-8")
    assert pause.refusal(root)["status"] == "paused" and "cannot be read" in pause.current(root)["reason"]
    assert pause.lift(root)["lifted"] and pause.current(root) is None
