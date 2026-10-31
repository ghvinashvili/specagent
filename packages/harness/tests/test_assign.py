"""A role session is started with an assignment: what the manager would have written into the prompt of a subagent
for the same job. Without one nothing is launched. Run: `uv run pytest -q packages/harness/tests/test_assign.py`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from harness import access, gates, launch, pack, state
from harness.gates import _common

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "docs" / "roles" / "stages.yaml").is_file())
BRIEF = "# Project brief — demo\n\n## Goal of this run\nNotes.\n\n## Constraints\n- Budget: 10 minutes per stage\n"
GOOD = """# Assignment — read

## Goal
The planner designs the retry change from your notes alone and will not open the material again.

## Material
none: the brief names the whole material of this stage, and it is given with the brief.

## Deliver
- `output/notes.md`: one entry per fact about retries, waits and status codes, each with its quote and `path:line`.
- `output/questions.md`: what the goal needs and the material does not answer.

## Prove
Find every quote again at its line before you finish. Where the text does not say how the tool answers an input,
run the tool and keep the record:

```
# the command of a probe is kept as it was run
tool --list ''
```

## Done when
Every file under `context/` is read completely, and every entry has a quote that stands at its line.
"""


@pytest.fixture()
def run(tmp_path: Path, copy_config):
    """A copy of the repository's tables, schemas and configuration with one run that has launched nothing."""
    root = tmp_path / "repo"
    copy_config(ROOT, root)
    brief = tmp_path / "brief.md"
    brief.write_text(BRIEF, encoding="utf-8")
    run_id = state.create_run(root, "demo", brief, ["context"])["run_id"]
    return root, run_id, state.runs_root(root) / run_id


def given(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "assignment.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_a_stage_without_an_assignment_is_not_ready_and_is_not_launched(run, monkeypatch):
    root, run_id, _ = run

    def no_session(*args, **kwargs):
        raise AssertionError(f"a command was started: {args}")

    monkeypatch.setattr(launch.subprocess, "run", no_session)
    for out in (launch.status(root, run_id, "read"), launch.launch(root, run_id, "read")):
        assert out["ok"] is False and out["status"] == "no_assignment"
        assert "the stage has no assignment" in out["why"] and "subagent" in out["hint"]


def test_an_assignment_says_what_to_deliver_what_to_prove_and_when_the_stage_is_done(run, tmp_path: Path):
    root, run_id, run_dir = run
    thin = launch.assign(root, run_id, "read", given(tmp_path, "Read the material carefully and write good notes."))
    assert thin["status"] == "thin_assignment" and "`Deliver`, `Prove`, `Done when`" in thin["why"]
    hollow = GOOD.replace(GOOD[GOOD.index("## Prove") : GOOD.index("## Done when")], "## Prove\nBe careful.\n\n")
    assert "too little is said under `Prove`" in launch.assign(root, run_id, "read", given(tmp_path, hollow))["why"]
    assert not access.assignment_path(run_dir, "read").exists()  # a refused text is not stored
    stored = launch.assign(root, run_id, "read", given(tmp_path, GOOD))
    assert stored["ok"] and Path(stored["assignment"]) == run_dir / "assignments" / "read.md"
    assert launch.status(root, run_id, "read")["status"] == "ready"
    copied = launch.assign(root, run_id, "plan", given(tmp_path, GOOD))  # one text for every stage is no assignment
    assert copied["status"] == "thin_assignment" and "the text of stage read" in copied["why"]
    assert launch.assign(root, run_id, "nothing", given(tmp_path, GOOD))["status"] == "unknown_stage"
    assert launch.assign(root, run_id, "plan", tmp_path / "absent.md")["status"] == "unreadable"
    (run_dir / "brief.md").write_text(GOOD, encoding="utf-8")
    assert "repeats the brief" in launch.assignment_problem(run_dir, "plan", GOOD)


def test_the_material_of_an_assignment_names_pieces_that_can_be_given(run, tmp_path: Path):
    """The manager may add a piece by hand under `Material`: a file, a directory or a range of lines. A piece that
    does not exist, a range past the end of its file, and a file the stage's type may not read are refused when the
    assignment is stored, not found missing by the session."""
    root, run_id, _ = run
    (root / "context/tool").mkdir(parents=True)
    (root / "context/tool/a.md").write_text("one\ntwo\nthree\n", encoding="utf-8")
    with_pieces = GOOD.replace(
        "none: the brief names the whole material of this stage, and it is given with the brief.",
        "- `context/tool/a.md:2-3` — the two lines on waits\n- `context/tool/` — the rest of the tool's notes",
    )

    def why(text: str) -> str:
        return launch.assign(root, run_id, "read", given(tmp_path, text)).get("why", "")

    assert "material `context/tool/b.md` does not exist" in why(with_pieces.replace("tool/a.md:2-3", "tool/b.md"))
    assert "material `context/tool/a.md:2-9`: the file has 3 lines" in why(with_pieces.replace(":2-3", ":2-9"))
    (root / "docs/handoff").mkdir(parents=True, exist_ok=True)
    (root / "docs/handoff/notes.md").write_text("# Handoff\n", encoding="utf-8")  # closed to every role (ADR-0015)
    closed = with_pieces.replace("`context/tool/` — the rest", "`docs/handoff/notes.md` — the notes")
    assert "`docs/handoff/notes.md` is closed to the type of this stage" in why(closed)
    assert launch.assign(root, run_id, "read", given(tmp_path, with_pieces))["ok"]


def test_the_material_of_a_stage_can_be_seen_before_its_launch(run, tmp_path: Path):
    """`harness material` shows what a stage's session will get in its cached prompt and why, without a model."""
    root, run_id, _ = run
    (root / "context/tool").mkdir(parents=True)
    (root / "context/tool/a.md").write_text("one\n\nthree\n", encoding="utf-8")
    added = GOOD.replace(
        "none: the brief names the whole material of this stage, and it is given with the brief.",
        "- `context/tool/a.md` — the notes on waits",
    )
    assert launch.assign(root, run_id, "read", given(tmp_path, added))["ok"]
    out = launch.preview_material(root, run_id, "read")
    assert out["ok"] and {"piece": "context/tool/a.md", "why": ["assignment"]} in out["given"]
    assert out["estimated_tokens"] == out["chars"] // 4 > 0 and out["left_out"] == []
    assert launch.preview_material(root, run_id, "nothing")["status"] == "unknown_stage"


def test_a_stage_whose_listed_material_does_not_fit_is_not_launched(run, tmp_path: Path, monkeypatch):
    """Nothing a stage's texts list is left for its session to search for; a picture is named for it to open."""
    root, run_id, _ = run
    (root / "context/tool").mkdir(parents=True)
    (root / "context/tool/a.md").write_text("one\n\nthree\n", encoding="utf-8")
    (root / "context/tool/chart.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\xff\xfe")
    added = GOOD.replace(
        "none: the brief names the whole material of this stage, and it is given with the brief.",
        "- `context/tool/a.md` — the notes on waits\n- `context/tool/chart.png` — the chart the notes describe",
    )
    assert launch.assign(root, run_id, "read", given(tmp_path, added))["ok"]
    out = launch.preview_material(root, run_id, "read")
    assert out["not_text"] == ["context/tool/chart.png"] and out["does_not_fit"] == [] == out["left_out"]

    git = launch.subprocess.run

    def no_session(cmd, *args, **kwargs):  # the harness may ask git; it may not start a session
        if cmd[0] != "git":
            raise AssertionError(f"a command was started: {cmd}")
        return git(cmd, *args, **kwargs)

    monkeypatch.setattr(launch.subprocess, "run", no_session)
    monkeypatch.setattr(pack, "MATERIAL_MAX_CHARS", 10)  # the listed notes no longer fit
    refused = launch.launch(root, run_id, "read")
    assert refused["status"] == "material_does_not_fit" and refused["pieces"] == ["context/tool/a.md"]
    assert "split the stage" in refused["hint"]


def test_a_hard_run_raises_the_effort_of_the_stages_that_decide(tmp_path: Path, copy_config):
    root = tmp_path / "repo"
    copy_config(ROOT, root)
    brief = tmp_path / "brief.md"
    brief.write_text(BRIEF, encoding="utf-8")
    out = state.create_run(root, "hard", brief, effort={"read": "max"})
    stages = {s["id"]: s for s in json.loads((Path(out["run_dir"]) / "manifest.json").read_text())["stages"]}
    table = {s["id"]: s for s in state.load_table(root)["stages"]}
    assert stages["read"]["effort"] == "max" and stages["plan"]["effort"] == table["plan"]["effort"]
    bad = state.create_run(root, "bad", brief, effort={"nothing": "max", "read": "huge"})
    assert bad["status"] == "bad_effort" and set(bad["given"]) == {"nothing=max", "read=huge"}


def test_a_launched_stage_takes_no_new_assignment(run, tmp_path: Path):
    root, run_id, run_dir = run
    st = state.load(root, run_dir / "state.json", "run-state")
    st["stages"]["read"].update(status="launched", attempts=1, session_ids=["s1"])
    state.save(root, run_dir / "state.json", st, "run-state")
    out = launch.assign(root, run_id, "read", given(tmp_path, GOOD))
    assert out["status"] == "already_launched" and "resume --message" in out["hint"]
    assert launch.status(root, run_id, "read")["status"] == "ready"  # a started unit is not asked again


def test_the_first_message_carries_the_assignment_after_the_brief(run, tmp_path: Path):
    root, run_id, run_dir = run
    assert launch.assign(root, run_id, "read", given(tmp_path, GOOD))["ok"]
    policy = access.load_policy(root)
    table = state.load_table(root)
    stages = {s["id"]: s for s in table["stages"]}
    stage_dir = run_dir / "stages" / "read"
    index = access.materialize_inputs(policy, stages, run_dir, stages["read"], stage_dir)
    assert [e["as"] for e in index] == ["brief.md", "assignment.md"]
    manifest = state.load(root, run_dir / "manifest.json", "run-manifest")
    prompt = launch.render_prompt(root, policy, manifest, stages["read"], stage_dir, index, None)
    brief, assignment, stage = (prompt.index(h) for h in ("# Project brief", "## Assignment (", "## Stage"))
    assert brief < assignment < stage
    # the type's instruction and the role rules stand with the task, as a subagent receives its instruction
    own, rules = prompt.index("\n## Reader\n"), prompt.index("\n## Harness rules\n")
    assert prompt.startswith("# Your instruction\n") and own < rules < brief
    assert "\n### Working method\n" in prompt and "Complete the task fully" in prompt
    assert "### Deliver" in prompt and "\n## Deliver" not in prompt  # its headings stay inside its section
    assert "Assignment — read" not in prompt  # the section has its heading; the title of the file is not repeated
    assert "\n# the command of a probe is kept as it was run\n" in prompt  # a line of a code block is not a heading
    assert f"- {stage_dir / 'input' / 'assignment.md'}" in prompt
    assert _common.input_names(run_dir, stage_dir) == []  # what a stage was told is not material it has to cover


def test_a_reviewing_type_gets_its_assignment_without_the_lines_its_row_hides(run, tmp_path: Path):
    root, run_id, run_dir = run
    text = GOOD.replace("# Assignment — read", "# Assignment — attack") + "\n- Budget: 40 minutes for this stage\n"
    assert launch.assign(root, run_id, "attack", given(tmp_path, text))["ok"]
    policy = access.load_policy(root)
    row = {"id": "attack", "role_type": "critic", "inputs": ["brief"]}
    stage_dir = run_dir / "stages" / "attack"
    access.materialize_inputs(policy, {"attack": row}, run_dir, row, stage_dir)
    seen = (stage_dir / "input" / "assignment.md").read_text(encoding="utf-8")
    assert "Budget" not in seen and "## Deliver" in seen
    assert "Budget" in access.assignment_path(run_dir, "attack").read_text(encoding="utf-8")
    deny = access.stage_settings(policy, run_dir, row, stage_dir)["permissions"]["deny"]
    assert any(d.endswith("/assignments/**)") for d in deny)  # the manager's own text is closed to every role


def test_the_shards_of_a_stage_share_its_assignment(run, tmp_path: Path):
    root, run_id, run_dir = run
    assert launch.assign(root, run_id, "write", given(tmp_path, GOOD.replace("— read", "— write")))["ok"]
    policy = access.load_policy(root)
    row = {"id": "write", "role_type": "writer", "inputs": ["brief"]}
    for shard in ("01", "02"):
        stage_dir = run_dir / "stages" / "write" / shard
        index = access.materialize_inputs(policy, {"write": row}, run_dir, row, stage_dir)
        assert "assignment.md" in [e["as"] for e in index] and (stage_dir / "input" / "assignment.md").is_file()


def test_a_planner_gets_a_checkout_for_its_trial_and_the_next_stage_does_not_find_it(tmp_path: Path):
    import subprocess

    from harness import work

    root = tmp_path / "repo"
    root.mkdir()

    def git(*args: str):
        return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)

    git("init", "-q", "-b", "main")
    (root / "a.txt").write_text("one\n")
    git("add", ".")
    git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "base")
    policy = access.load_policy(ROOT)
    plan = {"id": "plan", "role_type": "planner", "inputs": ["brief"]}
    read = {"id": "read", "role_type": "reader", "inputs": ["brief"]}
    assert launch.worktree_of(root, policy, "r1", plan, None) == "r1-plan"
    assert launch.worktree_of(root, policy, "r1", read, None) is None
    git("worktree", "add", "-q", "-b", "worktree-r1-plan", str(root / ".claude" / "worktrees" / "r1-plan"), "main")
    assert work.drop_checkout(root, "r1-plan") is True
    assert not (root / ".claude" / "worktrees" / "r1-plan").exists()
    assert "worktree-r1-plan" not in git("branch", "--format=%(refname:short)").stdout
    assert work.drop_checkout(root, "r1-plan") is False  # nothing left to remove


def test_the_gate_can_be_asked_without_recording_anything(run):
    root, run_id, run_dir = run
    stage_dir = run_dir / "stages" / "read"
    (stage_dir / "output").mkdir(parents=True)
    out = gates.preview(root, run_id, "read", None)
    assert out["ok"] is False and out["failing"][0]["name"] == "result.json exists"
    assert not (stage_dir / "gate.json").exists()
    assert json.loads((run_dir / "state.json").read_text(encoding="utf-8"))["stages"]["read"]["gate"] == "pending"


def test_the_handoff_of_a_run_names_the_assignment_as_the_next_step(run, tmp_path: Path):
    root, run_id, run_dir = run
    state.write_handoff(root, run_id)
    first = (run_dir / "HANDOFF.md").read_text(encoding="utf-8")
    assert "Write the assignment of `read`" in first and f"harness assign --run {run_id} --stage read" in first
    assert launch.assign(root, run_id, "read", given(tmp_path, GOOD))["ok"]
    state.write_handoff(root, run_id)
    then = (run_dir / "HANDOFF.md").read_text(encoding="utf-8")
    assert "Write the assignment" not in then and f"`harness launch --run {run_id} --stage read`" in then


def test_the_shared_fixture_leaves_out_what_a_sandbox_hides(tmp_path: Path, copy_config):
    """Seen live: inside a role session `.claude/` holds entries nobody may read, and the copy of the fixtures failed."""
    src = tmp_path / "src"
    (src / ".claude" / "agents").mkdir(parents=True)
    (src / ".claude" / "agents" / "a.md").write_text("x", encoding="utf-8")
    hidden = src / ".claude" / "routines"
    hidden.mkdir()
    hidden.chmod(0)
    try:
        copy_config(src, tmp_path / "dst", parts=(".claude",))
    finally:
        hidden.chmod(0o755)
    assert (tmp_path / "dst" / ".claude" / "agents" / "a.md").read_text(encoding="utf-8") == "x"
