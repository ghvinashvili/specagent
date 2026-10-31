"""specs/002-run-loop: the loops inside a run (harness/rounds.py), the table's `loop` block and `returns_to`.
Run: `uv run pytest -q packages/harness/tests/test_rounds.py`."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import jsonschema
import pytest
import yaml
from harness import access, launch, poll, resume, rounds, state

ROOT = next(
    p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file() and (p / "schemas").is_dir()
)
BRIEF = "# Project brief — demo\n\n## Goal of this run\nA loop.\n"
COMMON = {"mode": "bg", "model": "opus", "effort": "max", "output": "output/", "approval": "none",
          "permission_mode": "acceptEdits", "max_minutes": 30, "max_attempts": 2}  # fmt: skip
TYPES = {"plan": "planner", "attack": "critic", "write": "writer", "verify": "verifier", "judge": "judge"}


def loop_table() -> dict:
    """plan, attack (back to plan), write, verify (back to write), judge (print, back to write)."""
    back_to_write = {"stage": "write", "counter": "work"}
    return {
        "version": 1,
        "loop": {"counters": {"plan": 3, "work": 3}, "max_runs": {"write": 5}},
        "stages": [
            {**COMMON, "id": "plan", "role_type": "planner", "inputs": ["brief"], "gate": "plan"},
            {**COMMON, "id": "attack", "role_type": "critic", "depends_on": ["plan"], "inputs": ["brief"],
             "gate": "attack", "approval": "human", "returns_to": {"stage": "plan", "counter": "plan"}},
            {**COMMON, "id": "write", "role_type": "writer", "depends_on": ["attack"], "inputs": ["brief"],
             "gate": "write"},
            {**COMMON, "id": "verify", "role_type": "verifier", "depends_on": ["write"],
             "inputs": ["brief", "write:report.md"],
             "gate": "verify", "returns_to": back_to_write},
            {**COMMON, "id": "judge", "role_type": "judge", "depends_on": ["verify"], "inputs": ["brief"],
             "gate": "judge", "mode": "print", "approval": "human", "returns_to": back_to_write},
        ],
        "no_match": {"action": "escalate", "message": "no table fits"},
    }  # fmt: skip


@pytest.fixture()
def looped(tmp_path: Path, copy_config, monkeypatch):
    """A copy of the repository's configuration whose default table is loop_table(), and one run made from it."""
    monkeypatch.setattr(state, "claude_version", lambda: "test")  # tests never call the claude binary
    root = tmp_path / "repo"
    copy_config(ROOT, root)
    for name in ("CLAUDE.md", "AGENTS.md"):  # the pack files of need-to-know.yaml: a recheck writes its pack again
        shutil.copy(ROOT / name, root / name)
    (root / "docs/roles/stages.yaml").write_text(yaml.safe_dump(loop_table(), sort_keys=False), encoding="utf-8")
    brief = tmp_path / "brief.md"
    brief.write_text(BRIEF, encoding="utf-8")
    run_id = state.create_run(root, "loop", brief, [])["run_id"]
    return root, run_id, state.runs_root(root) / run_id


def test_a_run_keeps_the_loop_block_and_returns_to_of_its_table(looped):
    _, _, run_dir = looped
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    st = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert manifest["loop"] == {"counters": {"plan": 3, "work": 3}, "max_runs": {"write": 5}}
    by_id = {s["id"]: s for s in manifest["stages"]}
    assert by_id["verify"]["returns_to"] == {"stage": "write", "counter": "work"}
    assert "returns_to" not in by_id["write"]
    assert st["loop"] == {"rounds": {}, "history": []}


def test_the_schemas_take_rework_recheck_round_start_a_stop_and_replan(looped):
    root, run_id, run_dir = looped
    st = state.load(root, run_dir / "state.json", "run-state")
    st["stages"]["write"].update(status="rework", round_start=1)
    st["stages"]["verify"]["status"] = "recheck"
    st["loop"]["rounds"]["work"] = 1
    st["loop"]["history"].append(
        {
            "round": 1,
            "counter": "work",
            "from": "verify",
            "to": "write",
            "items": 2,
            "signature": "x",
            "at": state.now(),
        }
    )
    st["loop"]["moving"] = {"round": 1, "target": "write", "units": ["write", "verify"]}
    st["loop"]["stop"] = {"action": "loop_cap", "stage": "judge", "at": state.now(), "detail": "work 3 of 3"}
    state.save(root, run_dir / "state.json", st, "run-state")  # raises when the schema refuses it
    doc = {"schema_version": 1, "run_id": run_id, "stage": "judge", "role_type": "judge", "status": "complete",
           "outputs": [], "summary": "s", "evidence": [], "open_questions": [],
           "verdict": {"decision": "replan", "reasons": ["verify#1 shows the plan cannot hold"]}}  # fmt: skip
    jsonschema.validate(doc, state.schema(root, "stage-result"))


REPORT = (
    "1. T001 parses the flag\n\nResult: confirmed — `uv run pytest -q` exit 0\n\n"
    "2. T002 refuses `..` in a run id\n\nResult: refuted — `python3 probe.py` exit 1: a folder was made\n"
)
CRITIQUE = (
    "| No. | Location | Finding | Source | Severity |\n| --- | --- | --- | --- | --- |\n"
    "| 1 | plan.md:3 | the guard reads the command's text | `python3 bypass.py` exit 0 | blocks |\n"
    "| 2 | plan.md:9 | a word | plan.md:9 | minor |\n| 3 | plan.md:12 | no owner of the pause flag | plan.md:12 | must fix |\n"
    "\nCoverage: plan.md\n"
)


def test_downstream_is_every_stage_after_the_target_in_table_order():
    stages = loop_table()["stages"]
    assert rounds.downstream(stages, "write") == ["verify", "judge"]
    assert rounds.downstream(stages, "plan") == ["attack", "write", "verify", "judge"]


def test_validate_names_a_loop_that_cannot_work():
    table = loop_table()
    table["stages"][3]["returns_to"] = {"stage": "judge", "counter": "work"}  # verify back to a later stage
    table["stages"][4]["returns_to"] = {"stage": "write", "counter": "nowhere"}
    table["stages"][2]["parallel"] = "per_task"
    problems = rounds.loop_problems(table)
    assert any("verify returns to 'judge'" in p for p in problems)
    assert any("'nowhere'" in p for p in problems)
    assert any("judge returns to write, and write runs per task" in p for p in problems)
    assert rounds.loop_problems(loop_table()) == []


def test_validate_names_a_reviewer_or_a_stage_after_the_target_that_runs_per_task():
    table = loop_table()
    table["stages"][3]["parallel"] = "per_task"  # verify: the reviewer of write, and a stage after write
    problems = rounds.loop_problems(table)
    assert any("verify returns to write, and verify runs per task" in p for p in problems)
    assert any("judge returns to write, and verify runs per task" in p for p in problems)


def test_the_findings_sent_back_are_the_proven_ones_whole(tmp_path: Path):
    run_dir = tmp_path / "run"
    (run_dir / "stages/verify/output").mkdir(parents=True)
    (run_dir / "stages/attack/output").mkdir(parents=True)
    (run_dir / "stages/verify/output/report.md").write_text(REPORT, encoding="utf-8")
    (run_dir / "stages/attack/output/critique.md").write_text(CRITIQUE, encoding="utf-8")
    verify = {"id": "verify", "role_type": "verifier"}
    attack = {"id": "attack", "role_type": "critic"}
    assert [i.splitlines()[0] for i in rounds.blocking_items(run_dir, verify)] == ["2. T002 refuses `..` in a run id"]
    rows = rounds.blocking_items(run_dir, attack)
    assert len(rows) == 2 and "blocks" in rows[0] and "must fix" in rows[1]


def test_a_report_that_is_a_link_sends_nothing_back(tmp_path: Path):
    run_dir = tmp_path / "run"
    (run_dir / "stages/verify/output").mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere.md"
    elsewhere.write_text(REPORT, encoding="utf-8")
    (run_dir / "stages/verify/output/report.md").symlink_to(elsewhere)
    assert rounds.blocking_items(run_dir, {"id": "verify", "role_type": "verifier"}) == []


def test_the_signature_ignores_numbers_case_and_spacing():
    a = rounds.signature(["2. T002 refuses `..`\n\nResult: refuted", "| 4 | plan.md:3 | x | y | blocks |"])
    b = rounds.signature(["| 9 | plan.md:3 | x | y | blocks |", "7.  t002 REFUSES `..`\nother text"])
    assert a == b and a != rounds.signature(["2. T003 something else"])


def stage_files(run_dir: Path, *sids: str) -> None:
    for sid in sids:
        (run_dir / f"stages/{sid}/output").mkdir(parents=True)
        (run_dir / f"stages/{sid}/result.json").write_text("{}", encoding="utf-8")
        (run_dir / f"stages/{sid}/gate.json").write_text("{}", encoding="utf-8")


def test_archive_moves_a_reviewers_result_and_output_and_copies_the_reworkers_report(tmp_path: Path):
    run_dir = tmp_path / "run"
    stage_files(run_dir, "verify", "write")
    (run_dir / "stages/verify/output/report.md").write_text(REPORT, encoding="utf-8")
    (run_dir / "stages/write/report.md").write_text("# report\n", encoding="utf-8")
    rounds.archive(run_dir, "verify", 1, reviewer=True)
    rounds.archive(run_dir, "write", 1, reviewer=False)
    v, w = run_dir / "stages/verify", run_dir / "stages/write"
    assert (v / "rounds/1/output/report.md").is_file() and not any((v / "output").iterdir())
    assert not (v / "result.json").exists() and (v / "rounds/1/gate.json").is_file()
    assert (w / "rounds/1/report.md").is_file() and (w / "report.md").is_file() and not (w / "result.json").exists()
    assert rounds.last_round(v) == 1 and rounds.last_round(tmp_path) == 0
    rounds.archive(run_dir, "verify", 1, reviewer=True)  # again, as after a crash: nothing moves twice
    assert (v / "rounds/1/output/report.md").is_file() and not (v / "rounds/1/output/output").exists()


def test_archive_never_follows_a_link_a_session_planted(tmp_path: Path):
    run_dir = tmp_path / "run"
    stage_files(run_dir, "verify", "write")
    outside = tmp_path / "outside"
    outside.mkdir()
    (run_dir / "stages/verify/rounds").symlink_to(outside)  # the reviewer's rounds/ leads out of the run
    secret = tmp_path / "secret.txt"
    secret.write_text("SECRET\n", encoding="utf-8")
    (run_dir / "stages/write/report.md").symlink_to(secret)  # a copy would read through the link
    rounds.archive(run_dir, "verify", 1, reviewer=True)
    rounds.archive(run_dir, "write", 1, reviewer=False)
    assert not any(outside.iterdir()) and not (run_dir / "stages/verify/rounds").is_symlink()
    assert (run_dir / "stages/verify/rounds/1/result.json").is_file()
    assert not (run_dir / "stages/write/rounds/1/report.md").exists()


def test_the_rework_message_replaces_a_planted_link_and_moves_nothing(looped, tmp_path: Path):
    root, _, run_dir = looped
    manifest = state.load(root, run_dir / "manifest.json", "run-manifest")
    st = state.load(root, run_dir / "state.json", "run-state")
    for sid in ("plan", "attack", "write", "verify"):
        st["stages"][sid].update(status="done", gate="pass", attempts=1)
    stage_files(run_dir, "write", "verify")
    target = tmp_path / "bashrc"
    target.write_text("keep\n", encoding="utf-8")
    (run_dir / "stages/write/rework.md").symlink_to(target)
    verify = next(s for s in manifest["stages"] if s["id"] == "verify")
    rounds.send_back(run_dir, manifest, st, verify, ["2. T002 refuses `..`"], 1)
    rework = run_dir / "stages/write/rework.md"
    assert target.read_text(encoding="utf-8") == "keep\n" and not rework.is_symlink()
    assert rework.read_text(encoding="utf-8").startswith("Round 2.")
    assert st["loop"]["moving"] == {"round": 1, "target": "write", "units": ["write", "verify"]}
    assert (run_dir / "stages/verify/result.json").is_file()  # moved only once the state holds the round
    assert [st["stages"][s]["status"] for s in ("write", "verify", "judge")] == ["rework", "recheck", "pending"]
    assert rounds.move_round(run_dir, st) and "moving" not in st["loop"]
    assert (run_dir / "stages/verify/rounds/1/result.json").is_file()


def finish(root: Path, run_dir: Path, sid: str, decision: str | None = None, files: dict | None = None, **unit) -> None:
    """A unit that ran and passed its gate, with its result and the files it wrote. Its approval stays as the run
    has it unless `unit` sets one."""
    st = state.load(root, run_dir / "state.json", "run-state")
    st["stages"][sid].update({"status": "done", "gate": "pass", "attempts": 1, "session_ids": [f"s-{sid}"], **unit})
    state.save(root, run_dir / "state.json", st, "run-state")
    stage_dir = run_dir / "stages" / sid
    (stage_dir / "output").mkdir(parents=True, exist_ok=True)
    doc = {"schema_version": 1, "run_id": run_dir.name, "stage": sid, "role_type": TYPES[sid], "status": "complete",
           "outputs": [], "summary": "s", "evidence": [], "open_questions": []}  # fmt: skip
    if decision:
        doc["verdict"] = {"decision": decision, "reasons": ["verify#2 is refuted: a folder is made for `..`"]}
    (stage_dir / "result.json").write_text(json.dumps(doc), encoding="utf-8")
    for rel, body in (files or {}).items():
        (stage_dir / rel).write_text(body, encoding="utf-8")


def through_write(root: Path, run_dir: Path) -> None:
    """plan, attack (accepted, and the human approved the plan) and write passed."""
    finish(root, run_dir, "plan")
    finish(root, run_dir, "attack", "accept", {"output/critique.md": "no rows\n"}, approval="approved")
    finish(root, run_dir, "write", files={"report.md": "# report\n"})


def unit(root: Path, run_dir: Path, sid: str) -> dict:
    return state.load(root, run_dir / "state.json", "run-state")["stages"][sid]


def kinds(out: dict) -> list[str]:
    return [a["action"] for a in out["actions"]]


def test_a_verifier_that_refutes_sends_the_work_back_and_the_stages_after_it_wait(looped):
    root, run_id, run_dir = looped
    through_write(root, run_dir)
    finish(root, run_dir, "verify", "revise", {"output/report.md": REPORT})
    out = poll.poll(root, run_id, listing=[])
    assert unit(root, run_dir, "write")["status"] == "rework" and unit(root, run_dir, "verify")["status"] == "recheck"
    st = state.load(root, run_dir / "state.json", "run-state")
    assert st["loop"]["rounds"] == {"work": 1} and st["loop"]["history"][0]["items"] == 1
    assert "moving" not in st["loop"]  # the files moved once the state held the round
    assert "rework" in kinds(out) and "recheck" not in kinds(out)  # verify waits until write passed again
    message = (run_dir / "stages/write/rework.md").read_text(encoding="utf-8")
    assert "T002 refuses `..`" in message and "T001 parses" not in message and message.startswith("Round 2.")
    assert (run_dir / "stages/verify/rounds/1/output/report.md").is_file()
    assert not (run_dir / "stages/verify/result.json").exists()


def test_a_second_poll_takes_the_same_verdict_once(looped):
    root, run_id, run_dir = looped
    through_write(root, run_dir)
    finish(root, run_dir, "verify", "revise", {"output/report.md": REPORT})
    poll.poll(root, run_id, listing=[])
    again = poll.poll(root, run_id, listing=[])
    st = state.load(root, run_dir / "state.json", "run-state")
    assert st["loop"]["rounds"] == {"work": 1} and len(st["loop"]["history"]) == 1
    assert kinds(again).count("rework") == 1


def test_a_round_survives_a_crash_between_the_state_and_the_files(looped, monkeypatch):
    root, run_id, run_dir = looped
    through_write(root, run_dir)
    finish(root, run_dir, "verify", "revise", {"output/report.md": REPORT})
    real = rounds.archive

    def crash(*args, **kwargs):
        monkeypatch.setattr(rounds, "archive", real)
        raise OSError("the poll was killed here")

    monkeypatch.setattr(rounds, "archive", crash)
    with pytest.raises(OSError):
        poll.poll(root, run_id, listing=[])
    st = state.load(root, run_dir / "state.json", "run-state")
    assert st["loop"]["moving"]["round"] == 1 and unit(root, run_dir, "verify")["status"] == "recheck"
    out = poll.poll(root, run_id, listing=[])
    st = state.load(root, run_dir / "state.json", "run-state")
    assert "moving" not in st["loop"] and len(st["loop"]["history"]) == 1 and "rework" in kinds(out)
    assert (run_dir / "stages/verify/rounds/1/result.json").is_file()
    assert not (run_dir / "stages/verify/result.json").exists()


def test_a_recheck_is_asked_once_the_rework_passed(looped):
    root, run_id, run_dir = looped
    through_write(root, run_dir)
    finish(root, run_dir, "verify", "revise", {"output/report.md": REPORT})
    poll.poll(root, run_id, listing=[])
    finish(root, run_dir, "write", files={"report.md": "# report\n\n## Round 2\n"}, attempts=2, round_start=1)
    out = poll.poll(root, run_id, listing=[])
    assert {"action": "recheck", "stage": "verify"} in out["actions"] and "rework" not in kinds(out)


def test_a_judge_that_revises_sends_the_work_back_with_what_it_cites(looped):
    root, run_id, run_dir = looped
    through_write(root, run_dir)
    finish(root, run_dir, "verify", "accept", {"output/report.md": REPORT})
    finish(root, run_dir, "judge", "revise")
    poll.poll(root, run_id, listing=[])
    assert [unit(root, run_dir, s)["status"] for s in ("write", "verify", "judge")] == ["rework", "recheck", "recheck"]
    assert unit(root, run_dir, "judge")["approval"] == "pending"
    assert unit(root, run_dir, "verify")["approval"] == "not_required"
    message = (run_dir / "stages/write/rework.md").read_text(encoding="utf-8")
    assert "verify#2 is refuted" in message and "## What the findings cite" in message and "T002 refuses" in message


def test_a_critic_that_attacks_the_plan_sends_it_back_to_the_planner(looped):
    root, run_id, run_dir = looped
    finish(root, run_dir, "plan")
    finish(root, run_dir, "attack", "revise", {"output/critique.md": CRITIQUE})
    out = poll.poll(root, run_id, listing=[])
    assert unit(root, run_dir, "plan")["status"] == "rework" and unit(root, run_dir, "attack")["status"] == "recheck"
    assert unit(root, run_dir, "write")["status"] == "pending"  # never launched: untouched
    message = (run_dir / "stages/plan/rework.md").read_text(encoding="utf-8")
    assert "reads the command's text" in message and "no owner of the pause flag" in message and "a word" not in message
    assert "approval" not in kinds(out)


def at_a_bound(root: Path, run_dir: Path, setup: str) -> None:
    st = state.load(root, run_dir / "state.json", "run-state")
    if setup == "cap":
        st["loop"]["rounds"]["work"] = 3
    elif setup == "runs":
        st["stages"]["write"]["attempts"] = 5
    else:
        items = rounds.blocking_items(run_dir, {"id": "verify", "role_type": "verifier"})
        st["loop"]["history"].append({"round": 1, "counter": "work", "from": "verify", "to": "write", "items": 1,
                                      "signature": rounds.signature(items), "at": state.now()})  # fmt: skip
    state.save(root, run_dir / "state.json", st, "run-state")


@pytest.mark.parametrize(("setup", "expected"), [("cap", "loop_cap"), ("runs", "loop_cap"), ("same", "no_progress")])
def test_the_loop_stops_for_the_human(looped, setup: str, expected: str):
    root, run_id, run_dir = looped
    through_write(root, run_dir)
    finish(root, run_dir, "verify", "revise", {"output/report.md": REPORT})
    at_a_bound(root, run_dir, setup)
    out = poll.poll(root, run_id, listing=[])
    assert expected in kinds(out) and "approval" in kinds(out) and out["status"] == "waiting_human"
    assert unit(root, run_dir, "write")["status"] == "done" and unit(root, run_dir, "verify")["approval"] == "pending"
    st = state.load(root, run_dir / "state.json", "run-state")
    assert st["loop"]["stop"]["action"] == expected and st["loop"]["stop"]["stage"] == "verify"
    assert "gate" not in kinds(poll.poll(root, run_id, listing=[]))


def test_the_human_answers_a_stop_with_an_approval_and_the_run_goes_on(looped):
    root, run_id, run_dir = looped
    through_write(root, run_dir)
    finish(root, run_dir, "verify", "revise", {"output/report.md": REPORT})
    at_a_bound(root, run_dir, "cap")
    assert "loop_cap" in kinds(poll.poll(root, run_id, listing=[]))
    assert state.approve(root, run_id, "verify", "approved")["ok"]
    out = poll.poll(root, run_id, listing=[])
    st = state.load(root, run_dir / "state.json", "run-state")
    assert "stop" not in st["loop"] and not set(kinds(out)) & set(rounds.STOP_ACTIONS)
    assert out["status"] != "waiting_human" and st["loop"]["rounds"] == {"work": 3}


@pytest.mark.parametrize(("decision", "action"), [("replan", "replan"), ("reject", "rejected")])
def test_replan_and_reject_of_the_judge_stop_for_the_human(looped, decision: str, action: str):
    root, run_id, run_dir = looped
    through_write(root, run_dir)
    finish(root, run_dir, "verify", "accept", {"output/report.md": REPORT})
    finish(root, run_dir, "judge", decision)
    out = poll.poll(root, run_id, listing=[])
    assert action in kinds(out) and out["status"] == "waiting_human" and "rework" not in kinds(out)
    assert unit(root, run_dir, "write")["status"] == "done"


def test_a_verifiers_reject_is_a_proposal_for_the_judge(looped):
    root, run_id, run_dir = looped
    through_write(root, run_dir)
    finish(root, run_dir, "verify", "reject", {"output/report.md": REPORT})
    out = poll.poll(root, run_id, listing=[])
    assert not {"rejected", "rework", "approval"} & set(kinds(out)) and out["status"] != "waiting_human"
    assert unit(root, run_dir, "verify")["approval"] == "not_required"


def test_a_gate_action_for_a_reviewer_sent_back_is_dropped(looped, monkeypatch):
    root, run_id, run_dir = looped
    through_write(root, run_dir)
    finish(root, run_dir, "verify", "revise", {"output/report.md": REPORT})
    st = state.load(root, run_dir / "state.json", "run-state")
    st["stages"]["verify"].update(status="launched", gate="pending")
    state.save(root, run_dir / "state.json", st, "run-state")
    monkeypatch.setattr(poll.gates, "run_gate", lambda *a, **k: {"passed": True, "next": "advance"})
    out = poll.poll(root, run_id, listing=[{"id": "j", "sessionId": "s-verify", "state": "done"}])
    assert "gate" not in kinds(out) and "rework" in kinds(out)


def test_retries_count_within_the_round(looped):
    root, run_id, run_dir = looped
    st = state.load(root, run_dir / "state.json", "run-state")
    st["stages"]["plan"].update(status="failed", attempts=3, round_start=2, session_ids=["s-plan"])
    state.save(root, run_dir / "state.json", st, "run-state")
    assert "resume" in kinds(poll.poll(root, run_id, listing=[]))
    st = state.load(root, run_dir / "state.json", "run-state")
    st["stages"]["plan"]["round_start"] = 0
    state.save(root, run_dir / "state.json", st, "run-state")
    assert "max_attempts" in kinds(poll.poll(root, run_id, listing=[]))


def test_retries_stop_at_the_stages_max_runs(looped):
    root, run_id, run_dir = looped
    st = state.load(root, run_dir / "state.json", "run-state")
    st["stages"]["write"].update(status="failed", attempts=5, round_start=4, session_ids=["s-write"])
    state.save(root, run_dir / "state.json", st, "run-state")
    out = poll.poll(root, run_id, listing=[])
    assert {"action": "max_attempts", "stage": "write", "why": "failed", "attempts": 5, "max_runs": 5} in out["actions"]


class FakeClaude:
    """subprocess.run for `claude ...`: records the call and succeeds; every other program runs for real."""

    def __init__(self, real):
        self.real, self.calls = real, []

    def __call__(self, cmd, *args, **kwargs):
        if not cmd or cmd[0] != "claude":
            return self.real(cmd, *args, **kwargs)
        self.calls.append([str(c) for c in cmd])
        out = json.dumps({"structured_output": None}) if "-p" in cmd else ("[]" if cmd[1:2] == ["agents"] else "")
        return subprocess.CompletedProcess(cmd, 0, out, "")


@pytest.fixture()
def fake(monkeypatch):
    stand_in = FakeClaude(subprocess.run)
    monkeypatch.setattr(subprocess, "run", stand_in)
    monkeypatch.setattr(launch, "session_of", lambda *a, **k: None)
    return stand_in


def in_round(root: Path, run_dir: Path) -> None:
    """write in rework with its message, verify in recheck: the state after a verifier's revise."""
    through_write(root, run_dir)
    finish(root, run_dir, "verify", "revise", {"output/report.md": REPORT})
    poll.poll(root, run_dir.name, listing=[])


def test_resume_rework_delivers_the_findings_and_starts_a_round(looped, fake):
    root, run_id, run_dir = looped
    in_round(root, run_dir)
    out = resume.resume(root, run_id, "write", rework=True)
    assert out["ok"] and out["attempts"] == 2, out
    u = unit(root, run_dir, "write")
    assert u["round_start"] == 1 and u["status"] == "launched"
    assert fake.calls[-1][-1].startswith("Round 2.") and "T002 refuses" in fake.calls[-1][-1]


def test_a_unit_in_a_loop_is_never_resumed_or_launched_plainly(looped, fake):
    root, run_id, run_dir = looped
    in_round(root, run_dir)
    assert resume.resume(root, run_id, "write")["status"] == "in_rework"
    assert launch.launch(root, run_id, "write")["status"] == "in_rework"
    assert resume.resume(root, run_id, "plan", rework=True)["status"] == "not_in_rework"
    assert resume.resume(root, run_id, "verify", rework=True)["status"] == "blocked-by:write"


def test_no_round_is_resumed_while_its_files_are_moving(looped, fake):
    root, run_id, run_dir = looped
    in_round(root, run_dir)
    st = state.load(root, run_dir / "state.json", "run-state")
    st["loop"]["moving"] = {"round": 1, "target": "write", "units": ["write", "verify"]}
    state.save(root, run_dir / "state.json", st, "run-state")
    assert resume.resume(root, run_id, "write", rework=True)["status"] == "round_moving"


def test_write_runs_are_bounded_across_rounds(looped, fake):
    root, run_id, run_dir = looped
    in_round(root, run_dir)
    st = state.load(root, run_dir / "state.json", "run-state")
    st["stages"]["write"]["attempts"] = 5
    state.save(root, run_dir / "state.json", st, "run-state")
    assert resume.resume(root, run_id, "write", rework=True)["status"] == "max_runs"
    st["stages"]["write"].update(status="failed", round_start=4)
    state.save(root, run_dir / "state.json", st, "run-state")
    assert resume.resume(root, run_id, "write")["status"] == "max_runs"  # a retry is a start too


def test_a_recheck_rebuilds_its_inputs_and_material_and_asks_for_the_whole_check(looped, fake):
    root, run_id, run_dir = looped
    in_round(root, run_dir)
    finish(root, run_dir, "write", files={"report.md": "# report\n\n## Round 2\n"}, attempts=2, round_start=1)
    stage_dir = run_dir / "stages/verify"
    (stage_dir / "input").mkdir(exist_ok=True)
    (stage_dir / "input/stale.txt").write_text("old\n", encoding="utf-8")
    (stage_dir / "pack.md").write_text("old pack\n", encoding="utf-8")
    out = resume.resume(root, run_id, "verify", rework=True)
    assert out["ok"], out
    assert not (stage_dir / "input/stale.txt").exists() and (stage_dir / "input/brief.md").is_file()
    assert "## Round 2" in (stage_dir / "input/work/report.md").read_text(encoding="utf-8")
    assert (stage_dir / "pack.md").read_text(encoding="utf-8") != "old pack\n"
    assert fake.calls[-1][-1].startswith("Round 2.") and "from the start" in fake.calls[-1][-1]


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True,
                          capture_output=True, text=True)  # fmt: skip
    return done.stdout.strip()


def test_a_recheck_reads_the_new_change_in_its_material(looped, fake):
    """The checkout and changes.patch of the new round come before pack.md is written again."""
    root, run_id, run_dir = looped
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "base")
    git(root, "checkout", "-qb", "worktree-wr")
    (root / "added.py").write_text("NEW = 2\n", encoding="utf-8")
    git(root, "add", "added.py")
    git(root, "commit", "-qm", "work")
    git(root, "checkout", "-q", "-")
    in_round(root, run_dir)
    finish(root, run_dir, "write", files={"report.md": "# report\n"}, attempts=2, round_start=1)
    result = run_dir / "stages/write/result.json"
    result.write_text(json.dumps({**json.loads(result.read_text(encoding="utf-8")), "summary": "on worktree-wr"}))
    assert resume.resume(root, run_id, "verify", rework=True)["ok"]
    stage_dir = run_dir / "stages/verify"
    assert "NEW = 2" in (stage_dir / "input/work/changes.patch").read_text(encoding="utf-8")
    assert "NEW = 2" in (stage_dir / "pack.md").read_text(encoding="utf-8")


def test_a_plain_resume_indexes_the_patch_it_writes_again_with_its_sha256(looped, fake):
    """R13 of run 20261009-022929-fix-w1-revise (docs/decisions/0018): the work changed while a reviewing unit was
    stopped, and a resume that is no round writes its patch again (launch.prepare_work): read-only, and named once in
    the unit's index with the sha256 of its bytes, so the gate takes the copy the session reads."""
    root, run_id, run_dir = looped
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "base")
    git(root, "checkout", "-qb", "worktree-wr")
    (root / "added.py").write_text("NEW = 2\n", encoding="utf-8")
    git(root, "add", "added.py")
    git(root, "commit", "-qm", "work")
    git(root, "checkout", "-q", "-")
    through_write(root, run_dir)
    result = run_dir / "stages/write/result.json"
    result.write_text(json.dumps({**json.loads(result.read_text(encoding="utf-8")), "summary": "on worktree-wr"}))
    by_id, stage_dir = {s["id"]: s for s in loop_table()["stages"]}, run_dir / "stages/verify"
    name = launch.worktree_name(run_id, "verify", None)
    launch.stage_inputs(root, access.load_policy(root), by_id, run_dir, by_id["verify"], stage_dir, name)
    st = state.load(root, run_dir / "state.json", "run-state")
    st["stages"]["verify"].update(status="stopped", attempts=1, session_ids=["s-verify"])  # launched, then stopped
    state.save(root, run_dir / "state.json", st, "run-state")
    git(root, "checkout", "-q", "worktree-wr")
    (root / "added.py").write_text("NEW = 3\n", encoding="utf-8")
    git(root, "commit", "-qam", "again")
    git(root, "checkout", "-q", "-")
    assert resume.resume(root, run_id, "verify", message="go on")["ok"]
    patch = stage_dir / "input/work/changes.patch"
    assert "NEW = 3" in patch.read_text(encoding="utf-8") and not patch.stat().st_mode & 0o222
    index = json.loads((run_dir / "_access/verify.inputs.json").read_text(encoding="utf-8"))
    entries = [e for e in index if e["as"] == "work/changes.patch"]
    assert len(entries) == 1 and entries[0]["sha256"] == hashlib.sha256(patch.read_bytes()).hexdigest()


def test_a_single_writer_gets_the_whole_task_list_and_verify_takes_it(looped, fake, monkeypatch):
    """One writer session (no `parallel`) keeps the planner's tasks as its own tasks.json, as a shard keeps its part."""
    root, run_id, run_dir = looped
    table = loop_table()
    table["stages"][2]["inputs"] = ["brief", "plan:tasks.json"]
    table["stages"][3]["inputs"] = ["brief", "write:tasks.json"]
    (root / "docs/roles/stages.yaml").write_text(yaml.safe_dump(table, sort_keys=False), encoding="utf-8")
    through_write(root, run_dir)
    task = {"category": "code", "description": "d", "steps": ["s"], "depends_on": [], "passes": False}
    tasks = {"schema_version": 1, "stage": "plan", "tasks": [{"id": "T001", **task}, {"id": "T002", **task}]}
    state.save(root, run_dir / "stages/plan/tasks.json", tasks, "tasks")
    st = state.load(root, run_dir / "state.json", "run-state")
    st["stages"]["write"].update(status="pending", gate="pending", attempts=0, session_ids=[])
    state.save(root, run_dir / "state.json", st, "run-state")
    monkeypatch.setattr(launch, "status", lambda *args: {"ok": True, "status": "ready"})
    assert launch.launch(root, run_id, "write")["ok"]
    own = json.loads((run_dir / "stages/write/tasks.json").read_text(encoding="utf-8"))
    assert [t["id"] for t in own["tasks"]] == ["T001", "T002"] and own["stage"] == "write"
    policy, by_id = access.load_policy(root), {s["id"]: s for s in table["stages"]}
    access.materialize_inputs(policy, by_id, run_dir, by_id["verify"], run_dir / "stages/verify")
    assert (run_dir / "stages/verify/input/work/tasks.json").is_file()


def test_a_recheck_never_writes_its_pack_through_a_link_the_session_planted(looped, fake, tmp_path: Path):
    """resume runs outside the sandbox: a pack.md the session turned into a link is replaced, never followed."""
    root, run_id, run_dir = looped
    in_round(root, run_dir)
    finish(root, run_dir, "write", files={"report.md": "# report\n"}, attempts=2, round_start=1)
    outside = tmp_path / "bashrc"
    outside.write_text("keep\n", encoding="utf-8")
    pack = run_dir / "stages/verify/pack.md"
    pack.unlink(missing_ok=True)
    pack.symlink_to(outside)
    assert resume.resume(root, run_id, "verify", rework=True)["ok"]
    assert outside.read_text(encoding="utf-8") == "keep\n" and not pack.is_symlink() and pack.stat().st_size > 0


def test_a_resume_never_logs_through_a_link_the_session_planted(looped, fake, tmp_path: Path):
    """The launcher's log folder of a stage is the harness's: a link a session put in its place is replaced."""
    root, run_id, run_dir = looped
    in_round(root, run_dir)
    outside = tmp_path / "ssh"
    outside.mkdir()
    logs = run_dir / "stages/write/logs"
    shutil.rmtree(logs, ignore_errors=True)
    logs.symlink_to(outside)
    assert resume.resume(root, run_id, "write", rework=True)["ok"]
    assert not any(outside.iterdir()) and not logs.is_symlink() and (logs / "launch.txt").is_file()


@pytest.mark.parametrize("name", ["stages.yaml", "pipelines/fix.yaml"])
def test_the_work_tables_attack_the_plan_and_loop(name: str):
    table = yaml.safe_load((ROOT / "docs/roles" / name).read_text(encoding="utf-8"))
    by_id = {s["id"]: s for s in table["stages"]}
    assert table["loop"] == {"counters": {"plan": 3, "work": 3}, "max_runs": {"write": 5}}
    assert by_id["attack"]["role_type"] == "critic" and by_id["attack"]["approval"] == "human"
    assert by_id["attack"]["returns_to"] == {"stage": "plan", "counter": "plan"}
    assert by_id["write"]["depends_on"] == ["attack"] and "parallel" not in by_id["write"]
    assert "plan:tasks.json" in by_id["write"]["inputs"] and "attack:output/" in by_id["write"]["inputs"]
    assert by_id["verify"]["returns_to"] == by_id["judge"]["returns_to"] == {"stage": "write", "counter": "work"}
    assert "critique" not in by_id and by_id["plan"]["approval"] == "none"
    assert all((s["model"], s["effort"]) == ("opus", "max") for s in table["stages"])
    assert rounds.loop_problems(table) == []


def test_every_table_runs_opus_max_but_the_fixed_types():
    for path in [ROOT / "docs/roles/stages.yaml", *sorted((ROOT / "docs/roles/pipelines").glob("*.yaml"))]:
        for s in yaml.safe_load(path.read_text(encoding="utf-8"))["stages"]:
            if s["role_type"] not in state.FIXED_TYPES:
                assert (s["model"], s["effort"]) == ("opus", "max"), f"{path.name}: {s['id']}"


def handoff(root: Path, run_id: str, run_dir: Path) -> str:
    state.write_handoff(root, run_id)
    return (run_dir / "HANDOFF.md").read_text(encoding="utf-8")


def test_handoff_lists_the_rounds_and_the_loop_resume(looped):
    root, run_id, run_dir = looped
    in_round(root, run_dir)
    text = handoff(root, run_id, run_dir)
    assert "## Rounds" in text and "round 2: `verify` sent 1 finding(s) back to `write`" in text
    assert f"harness resume --run {run_id} --stage write --rework" in text.split("## Next steps")[1]


def test_handoff_in_a_later_round_names_no_unit_out_of_attempts(looped):
    """In round 2 write has used as many attempts as max_attempts allows a round: it waits for its rework, not for
    the human."""
    root, run_id, run_dir = looped
    in_round(root, run_dir)
    st = state.load(root, run_dir / "state.json", "run-state")
    st["stages"]["write"].update(attempts=2, round_start=1)
    st["stages"]["verify"]["attempts"] = 2
    state.save(root, run_dir / "state.json", st, "run-state")
    text = handoff(root, run_id, run_dir)
    assert "attempts used" not in text and "--stage write --rework" in text.split("## Next steps")[1]


def test_handoff_names_the_stop_of_a_loop_and_how_to_answer_it(looped):
    root, run_id, run_dir = looped
    through_write(root, run_dir)
    finish(root, run_dir, "verify", "revise", {"output/report.md": REPORT})
    at_a_bound(root, run_dir, "cap")
    poll.poll(root, run_id, listing=[])
    waiting = handoff(root, run_id, run_dir).split("## Waiting on a human")[1].split("## Next steps")[0]
    assert "the loop stopped at `verify`: loop_cap" in waiting
    assert f"harness approve --run {run_id} --stage verify --decision approved" in waiting
