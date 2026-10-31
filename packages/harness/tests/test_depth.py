"""Part 3 of specs/001-chat-depth (every `path:line`, every evidence command, the content of the judge, researcher,
and synthesizer gates) and part 7 (warn and enforce, HANDOFF.md, `harness steps`).
Run: `uv run pytest -q packages/harness/tests/test_depth.py`."""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import subprocess
from pathlib import Path

import pytest
from harness import cli, gates, launch, poll, state
from harness.gates import _common, investigate, judge, read, research, synthesize, verdict

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file() and (p / "specs").is_dir())
APPENDIX = Path(__file__).parent / "fixtures" / "transcripts" / "appendix.jsonl"
CONSTITUTION = (ROOT / "specs" / "constitution.md").read_text(encoding="utf-8")
SID = "11111111-2222-3333-4444-555555555555"


def git(repo: Path, *args: str) -> str:
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"}
    run = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True, env=env)
    return run.stdout.strip()


def put(base: Path, files: dict) -> None:
    for rel, content in files.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")


def res(**extra) -> dict:
    base = {"schema_version": 1, "run_id": "r", "stage": "x", "role_type": "t", "status": "complete", "outputs": [],
            "summary": "s", "evidence": [], "open_questions": []}  # fmt: skip
    return {**base, **extra}


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A repository whose first commit is the run's base; a later commit removes a file the stage cited."""
    root = tmp_path / "repo"
    files = {"packages/a/src/a.py": "".join(f"x{i} = {i}\n" for i in range(5)), "docs/x.md": "one\ntwo\nthree\n",
             "specs/constitution.md": CONSTITUTION, "AGENTS.md": "a\n" * 12, "packages/a/AGENTS.md": "a\nb\n",
             "packages/b/src/a.py": "a\n" * 9}  # fmt: skip
    put(root, files)
    git(root, "init", "-q", "-b", "main")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "base")
    return root


def unit(tmp_path: Path, repo: Path, stage: str, role_type: str, files: dict, mode: str = "warn") -> tuple:
    """A run directory with one unit: manifest (base commit, the stage's type and mode), state (one session id)."""
    run_dir = tmp_path / "runs" / "20261003-000000-demo"
    entry = {"id": stage, "role_type": role_type, "steps": mode}
    put(run_dir, {"manifest.json": {"base_commit": git(repo, "rev-parse", "HEAD"), "stages": [entry]},
                  "state.json": {"stages": {stage: {"session_ids": [SID]}}}})  # fmt: skip
    put(run_dir / "stages" / stage, files)
    return run_dir, run_dir / "stages" / stage


def test_a_path_line_names_an_existing_file_and_line(tmp_path: Path, repo: Path):
    notes = (
        "- a. `packages/a/src/a.py:3` and `src/a.py:5` from the package directory\n"
        "- b. `docs/x.md:1-3` is a range; `docs/x.md:2-4` runs past the end\n"
        "- c. `packages/a/src/a.py:9`; `missing.py:1`; `input/read/notes.md:2`\n"
        "- d. `pypi.org:443`, `03:02:21`, `http://localhost:8080` and `v1.2:3` are no paths\n"
        '- e. Quote: "the spec cites `manager.md:33`" `docs/x.md:2`\n'
        "- f. `packages/a/src/new.py:2` exists in the stage's checkout only\n"
        "- g. `AGENTS.md:10`: the root's file, not the package's; `src/a.py:8`: one of two `src/a.py` has it\n"
        "- h. without inline code: docs/x.md:3 holds, docs/x.md:5 does not; http://x.org/docs/x.md:9 is a link\n"
    )
    found = res(summary="see `docs/x.md:7`", open_questions=["docs/x.md:8 is past the end (no backticks in JSON)"])
    run_dir, sd = unit(tmp_path, repo, "read", "reader", {"output/notes.md": notes, "input/read/notes.md": "1\n2\n",
                       "result.json": found})  # fmt: skip
    git(repo, "rm", "-q", "docs/x.md")
    git(repo, "commit", "-q", "-m", "later: HEAD moves on")  # the run is checked at its base, not at HEAD
    put(
        repo / ".claude" / "worktrees" / launch.worktree_name(run_dir.name, "read", None),
        {"packages/a/src/new.py": "a\nb\n"},
    )
    bad = _common.locator_problems(repo, run_dir, sd)
    assert bad == [
        "`docs/x.md:2-4` in output/notes.md: the file has 3 lines",
        "`packages/a/src/a.py:9` in output/notes.md: the file has 5 lines",
        "`missing.py:1` in output/notes.md: no such file",
        "`docs/x.md:5` in output/notes.md: the file has 3 lines",
        "`docs/x.md:7` in result.json: the file has 3 lines",
        "`docs/x.md:8` in result.json: the file has 3 lines",
    ]
    assert _common.locator_check(repo, run_dir, sd)["name"] == "every `path:line` names an existing file and line"
    assert _common.locators("") == [] and _common.locators("`a.md:`, :3, a.md:x") == []  # empty and malformed


def bash(seq: int, command: str, exit_code: int | None = 0, denied: bool = False) -> dict:
    return {"seq": seq, "tool": "Bash", "command": command, "exit_code": exit_code, "output": "", "denied": denied,
            "background": False, "cwd": "/repo"}  # fmt: skip


def test_an_evidence_command_was_run_as_the_entry_says(tmp_path: Path):
    sd = tmp_path / "stage"
    events = [bash(1, "uv run pytest -q packages/a", 1), bash(2, "uv run pytest -q packages/a"),
              bash(3, "uv run ruff check .", None, denied=True)]  # fmt: skip

    def failed(*entries: dict) -> str:
        put(sd, {"result.json": res(evidence=[{"claim": "c", "how_checked": "h", **e} for e in entries])})
        found = _common.evidence_check(sd, events)
        return "" if found["passed"] else found["detail"]

    assert (
        failed({"command": "uv  run pytest -q\npackages/a", "exit_code": 1}, {"command": "uv run pytest -q packages/a"})
        == ""
    )
    assert failed({"command": "uv run pytest -q packages/a", "exit_code": 2}) == (
        "`uv run pytest -q packages/a`: ended with 0, 1, the entry says 2"
    )
    assert failed({"command": "uv run ruff check ."}) == "`uv run ruff check .`: not run in the session"  # refused
    assert (
        failed({"command": "pytest -q tests/test_x.py", "exit_code": 0})
        == "`pytest -q tests/test_x.py`: not run in the session"
    )
    assert failed({"claim": "a statement checked by reading"}) == ""  # no command, nothing to find
    # what the harness ran outside the session, as checks.json gave it to the stage (the verifier's method)
    put(sd, {"input/write/01/checks.json": {"schema_version": 1, "ran": "by the harness", "checks": [
        {"command": "uv run pytest -q", "exit_code": 0, "output_tail": "286 passed"}]}})  # fmt: skip
    events.clear()
    assert failed({"command": "uv run pytest -q", "exit_code": 0}) == ""
    assert (
        failed({"command": "uv run pytest -q", "exit_code": 1}) == "`uv run pytest -q`: ended with 0, the entry says 1"
    )
    assert failed({"command": "uv run pytest -q packages/a"}) == "`uv run pytest -q packages/a`: not run in the session"
    put(sd, {"input/write/02/checks.json": "not json"})  # an unreadable checks.json is left out
    assert failed({"command": "uv run pytest -q", "exit_code": 0}) == ""
    # the commands an evidence command or a `ran:` rule is matched against: one source, `types` names none
    assert _common.project_command(sd, "test") == _common.TEST_CMD and _common.project_command(sd, "types") is None
    with pytest.raises(ValueError, match="no command kind 'build'"):
        _common.project_command(sd, "build")


REPORT = "# Report\n1. Claim A.\n   Result: confirmed\n2. Claim B.\n   Result: refuted, the test asserts nothing\n3. Claim C.\n   could not check: no network\n## Beyond the claims\n"
CRITIQUE = (
    "| No. | Location | Says | Correct | Source | Severity |\n| --- | --- | --- | --- | --- | --- |\n"
    "| 1 | a.py:3 | x | y | spec.md:2 | blocks |\n| 2 | a.py:5 | x | y | spec.md:3 | minor |\n"
)
FINDINGS = (
    "## Findings\n1. Critical: `a.py:3` the criterion 2 is not met\n2. Minor: `a.py:4` naming\n| 1 | conforms |\n"
)
ACCEPTANCE = (
    "| No. | Status | Test | Command |\n| --- | --- | --- | --- |\n| 1 | passed | t1 | c |\n"
    "| 2 | not coverable | - | - |\n| 3 | failed | t3 | c |\n"
)


def judge_unit(tmp_path: Path, repo: Path, reports: dict[str, tuple[str, str]], verdict_: dict, open_q: list[str]):
    run_dir, sd = unit(tmp_path, repo, "judge", "judge", {"result.json": res(verdict=verdict_, open_questions=open_q)})
    index = []
    for stage, (name, text) in reports.items():
        put(sd / "input" / stage, {name: text})
        index.append({"source": str(run_dir / "stages" / stage / "output" / name), "as": f"{stage}/{name}"})
    put(run_dir / "_access", {"judge.inputs.json": index})
    return {c["name"]: c for c in judge.content_checks(repo, run_dir, sd, None)}


def test_judge_reasons_cite_entries_that_exist_and_accept_answers_every_blocking_finding(tmp_path: Path, repo: Path):
    default = {"verify": ("report.md", REPORT), "critique": ("critique.md", CRITIQUE)}
    ok = judge_unit(tmp_path, repo, default, {"decision": "accept", "reasons": ["verify#3 is not needed for the goal"]},
                    ["verify#2 is unsupported: no command", "critique#1 has no evidence"])  # fmt: skip
    assert all(c["passed"] for c in ok.values()), ok
    bare = judge_unit(
        tmp_path, repo, default, {"decision": "revise", "reasons": ["the test is weak", "verify#9 x"]}, []
    )
    assert not bare["every reason names its source as `<stage>#<n>`"]["passed"]
    assert bare["every cited entry exists in its report"]["detail"] == "verify#9"
    # the rule holds an accept only: a revise with the same findings unanswered passes it
    assert bare["accept leaves no finding of the reports unanswered"]["passed"]
    early = judge_unit(tmp_path, repo, default, {"decision": "accept", "reasons": ["critique#2 is minor"]}, [])
    # the blocking findings outside open_questions first, then the unchecked ones outside the reasons
    assert early["accept leaves no finding of the reports unanswered"]["detail"] == "verify#2, critique#1, verify#3"
    assert not early["accept leaves no finding of the reports unanswered"]["passed"]
    factory = {"accept": ("acceptance.md", ACCEPTANCE), "validate": ("findings.md", FINDINGS)}
    sf = judge_unit(tmp_path, repo, factory, {"decision": "accept", "reasons": ["validate#2 is naming only"]}, [])
    assert sf["accept leaves no finding of the reports unanswered"]["detail"] == "accept#3, validate#1, accept#2"
    assert not sf["accept leaves no finding of the reports unanswered"]["passed"]
    empty = judge_unit(tmp_path, repo, {}, {"decision": "reject", "reasons": []}, [])  # no reasons, no reports
    assert [c["passed"] for c in empty.values()] == [False, True, True]


CRITIQUE_4 = (
    "| No. | Location | Finding | Severity |\n| --- | --- | --- | --- |\n"
    "| 1 | a.py:3 | the loop never ends | blocks |\n| 2 | a.py:5 | x is wrong | must fix |\n"
    "| 3 | a.py:7 | naming | minor |\n"
)
CRITIQUE_5 = (
    "| No. | Location | Says | Source | Severity |\n| --- | --- | --- | --- | --- |\n"
    "| 1 | a.py:3 | x | spec.md:2 | blocks |\n| 2 | a.py:5 | x | spec.md:3 | must fix |\n"
    "| 3 | a.py:7 | x | spec.md:4 | minor |\n"
)


def test_the_judge_reads_a_critique_of_four_or_five_columns_by_its_header_row(tmp_path: Path, repo: Path):
    """Item 2: accept sees every blocks and must fix row of a critique, whatever its width: the severity is the
    column headed Severity, read by the parser the critique gate uses."""
    for table in (CRITIQUE_4, CRITIQUE_5):
        assert judge.critique_rows(table) == {1: "blocks", 2: "must fix", 3: "minor"}
        verdict_ = {"decision": "accept", "reasons": ["critique#3 is naming only"]}
        found = judge_unit(tmp_path, repo, {"critique": ("critique.md", table)}, verdict_, [])
        assert found["every cited entry exists in its report"]["passed"]
        accept = found["accept leaves no finding of the reports unanswered"]
        assert not accept["passed"] and accept["detail"] == "critique#1, critique#2"


def test_a_researcher_cites_only_lines_it_read_or_was_given(tmp_path: Path, repo: Path):
    findings = "- One. `packages/a/src/a.py:3`\n- Two. `docs/x.md:3`\n"
    run_dir, sd = unit(tmp_path, repo, "research", "researcher", {"output/findings.md": findings,
                       "pack.md": "# Knowledge pack\n\n# Material\n\n### docs/x.md\n\n1\tone\n"})  # fmt: skip
    short = {"seq": 1, "tool": "Read", "file": "/repo/packages/a/src/a.py", "ok": True, "offset": 1, "limit": 2,
             "start": None, "lines": None, "cwd": "/repo"}  # fmt: skip
    (c,) = research.content_checks(repo, run_dir, sd, [short])
    assert not c["passed"] and c["detail"] == "`packages/a/src/a.py:3`"
    (c,) = research.content_checks(repo, run_dir, sd, [{**short, "start": 1, "lines": 5}])
    assert c["passed"] and c["name"] == "every cited line was read in the session"
    assert research.content_checks(repo, run_dir, sd, None) == []  # no transcript: nothing to compare
    assert investigate.content_checks is research.content_checks  # the investigate stage runs it too


def test_a_synthesis_names_every_input_and_both_sides_of_a_clash(tmp_path: Path, repo: Path):
    doc = ("## Where they agree\n- all say x (`advise/01/answer.md`, `advise/02/answer.md`)\n## Where they clash\n"
           "- advise/01 says y, advise/02 says z\n- one side only: advise/01\n- answer.md alone names neither\n"
           "## Blind spots\n## Recommendation\n## First step\n")  # fmt: skip
    run_dir, sd = unit(tmp_path, repo, "verdict", "synthesizer", {"output/verdict.md": doc})
    names = ["frame/question.md", "advise/01/answer.md", "advise/02/answer.md"]
    put(run_dir / "_access", {"verdict.inputs.json": [{"source": "s", "as": n} for n in names]})
    found = {c["name"]: c for c in verdict.content_checks(repo, run_dir, sd, None)}
    assert found["every input is named at least once"]["detail"] == "frame/question.md"
    assert found["every item of Where they clash names two different inputs"]["detail"] == (
        "- one side only: advise/01; - answer.md alone names neither"
    )  # a file name two inputs share names neither of them
    named = synthesize.content_checks(repo, run_dir, sd, None)[0]  # it reads briefing.md, which this stage lacks
    assert not named["passed"] and named["detail"] == ", ".join(names)


CLASH_HEADER = "| Point | One side | Other side |\n"
CLASH_TABLE = CLASH_HEADER + "| --- | --- | --- |\n| the cost | advise/01: low | advise/02: high |\n"


def test_the_header_row_of_a_table_is_no_statement(tmp_path: Path, repo: Path):
    """Item 4: the header row of a table (the row the separator follows) states nothing, so neither the synthesizer
    gate's own check nor the clash check counts it. Rows without a separator below them are no header."""
    assert _common.statements(CLASH_TABLE) == ["| the cost | advise/01: low | advise/02: high |"]
    bare = CLASH_TABLE.replace("| --- | --- | --- |\n", "")
    assert _common.statements(bare) == bare.splitlines()
    agree = "## Where they agree\n- all keep the queue (frame/question.md, advise/01, advise/02)\n"
    rest = (
        "## Blind spots\n- none (advise/01)\n## Recommendation\n- keep (advise/02)\n"
        "## First step\n- measure (advise/01)\n"
    )
    doc = agree + "## Where they clash\n" + CLASH_TABLE + rest
    run_dir, sd = unit(tmp_path, repo, "verdict", "synthesizer", {"output/verdict.md": doc})
    names = ["frame/question.md", "advise/01/answer.md", "advise/02/answer.md"]
    put(run_dir / "_access", {"verdict.inputs.json": [{"source": "s", "as": n} for n in names]})
    assert [c for c in verdict.content_checks(repo, run_dir, sd, None) if not c["passed"]] == []
    assert [c for c in verdict.checks(repo, run_dir, sd) if not c["passed"]] == []


def test_every_content_check_says_what_it_checks():
    """Item 6: the public `content_checks` of every gate that has one carries a docstring (.claude/rules/python.md)."""
    for module in (judge, research, investigate, synthesize, verdict):
        assert inspect.getdoc(module.content_checks), module.__name__


NOTES = (
    '## a.md\n\n- A fact. Quote: "nothing to check here" `missing.md:1`\n\n## Contradictions\n\nnone\n\n'
    "## Probes\n\nnone: the material is a text.\n\n## Coverage\n\n| Source | Coverage |\n| --- | --- |\n| a.md | read |\n"
)


@pytest.fixture()
def finished(tmp_path: Path, small_config, monkeypatch):
    """A run of the small configuration whose read stage finished: complete result, notes with a location that
    names no file, its session's transcript (the appendix lines) and a reader whose step 1 has a rule."""
    root = small_config(tmp_path / "repo")
    put(root, {".claude/agents/reader.md": "---\nname: reader\n---\n## Working method\n\n"
               "1. Keep progress. <!-- check: wrote: progress.md -->\n2. Read. <!-- check: read: plan.md -->\n"})  # fmt: skip
    brief = tmp_path / "brief.md"
    brief.write_text("# Project brief — demo\n\n## Goal of this run\nNotes.\n", encoding="utf-8")
    run_id = state.create_run(root, "demo", brief, [])["run_id"]
    run_dir = state.runs_root(root) / run_id
    st = state.load(root, run_dir / "state.json", "run-state")
    st["stages"]["read"].update(status="done", attempts=1, session_ids=[SID])
    st["stages"]["plan"].update(status="stopped", attempts=1, session_ids=["22222222-0000-0000-0000-000000000000"])
    state.save(root, run_dir / "state.json", st, "run-state")
    put(run_dir / "stages" / "read", {"output/notes.md": NOTES, "output/questions.md": "none\n",
        "result.json": res(stage="read", role_type="reader", run_id=run_id)})  # fmt: skip
    config = tmp_path / "config"
    put(config / "projects" / "p", {f"{SID}.jsonl": APPENDIX.read_text(encoding="utf-8")})
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
    return root, run_id, run_dir


def test_warn_records_the_new_checks_beside_the_verdict(finished):
    root, run_id, _ = finished
    verdict_ = gates.run_gate(root, run_id, "read", None)
    advisory = {c["name"]: c for c in verdict_["advisory"]}
    assert verdict_["passed"] and verdict_["steps_mode"] == "warn"
    assert not advisory["every `path:line` names an existing file and line"]["passed"]
    assert advisory["step 1: wrote: progress.md"]["detail"] == "fail: no file progress.md in the stage directory"
    assert advisory["step 2: read: plan.md"]["passed"]  # the appendix's first call reads plan.md


def test_the_handoff_lists_the_failing_advisory_checks(finished):
    root, run_id, run_dir = finished
    state.write_handoff(root, run_id)
    assert "## Gate warnings\n- none\n" in (run_dir / "HANDOFF.md").read_text(encoding="utf-8")  # no gate yet
    gates.run_gate(root, run_id, "read", None)
    state.write_handoff(root, run_id)
    handoff = (run_dir / "HANDOFF.md").read_text(encoding="utf-8")
    assert "## Gate warnings\n- read: every `path:line` names an existing file and line — `missing.md:1`" in handoff
    assert "- read: step 1: wrote: progress.md — fail: no file progress.md in the stage directory" in handoff
    assert "step 2: read: plan.md" not in handoff  # a passing advisory check is no warning
    assert handoff.index("## What was produced") < handoff.index("## Gate warnings") < handoff.index("## Waiting")


def test_enforce_fails_the_stage_on_a_new_check_in_both_entry_points(finished):
    root, run_id, run_dir = finished
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    next(s for s in manifest["stages"] if s["id"] == "read")["steps"] = "enforce"
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    verdict_ = gates.run_gate(root, run_id, "read", None)
    failing = [c["name"] for c in verdict_["checks"] if not c["passed"]]
    assert not verdict_["passed"] and "advisory" not in verdict_ and "step 1: wrote: progress.md" in failing
    held = gates.preview(root, run_id, "read", None)  # the stop hook's entry point holds the session to the same
    assert [c["name"] for c in held["failing"]] == failing


LONG = "a" * 256 + "/f.py"  # a first component of 256 characters: one more than a file name may have
LONG_ENTRY = f'- Another fact. Quote: "nothing to check either" `{LONG}:1`\n'


def test_a_location_the_gate_cannot_stat_is_recorded_beside_the_verdict(finished):
    """Item 1: a `path:line` whose path the system refuses to look up (a component over 255 characters) names no
    file the gate can find. The gate records its verdict instead of raising, in both entry points and in poll, and in
    warn the new check that names the location fails no stage."""
    root, run_id, run_dir = finished
    sd = run_dir / "stages" / "read"
    put(sd, {"output/notes.md": NOTES.replace("`missing.md:1`\n", "`missing.md:1`\n" + LONG_ENTRY)})
    put(run_dir / "stages" / "plan", {"output/plan.md": f"- see `{LONG}:1`\n"})
    assert _common.locator_problems(root, run_dir, sd) == [
        "`missing.md:1` in output/notes.md: no such file",
        f"`{LONG}:1` in output/notes.md: no such file",
    ]
    verdict_ = gates.run_gate(root, run_id, "read", None)
    advisory = {c["name"]: c for c in verdict_["advisory"]}
    assert verdict_["passed"] and not advisory["every `path:line` names an existing file and line"]["passed"]
    assert gates.preview(root, run_id, "read", None)["ok"]
    plan = poll.gate_now(root, run_id, "plan")  # a gate whose own checks open no cited path
    assert plan["unit_status"] == "gate_failed"
    assert not {c["name"]: c for c in plan["advisory"]}["every `path:line` names an existing file and line"]["passed"]
    st = state.load(root, run_dir / "state.json", "run-state")
    st["stages"]["read"].update(status="launched", job_ids=["j1"])
    state.save(root, run_dir / "state.json", st, "run-state")
    poll.poll(root, run_id, listing=[{"id": "j1", "sessionId": SID, "state": "done"}])
    assert state.load(root, run_dir / "state.json", "run-state")["stages"]["read"]["status"] == "done"


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads every folder")
def test_a_location_in_a_closed_folder_is_recorded_beside_the_verdict(finished):
    """Item 1: a `path:line` under a folder the gate may not enter names no file the gate can find, in the new
    check and in the read gate's own quote check alike; nothing raises."""
    root, run_id, run_dir = finished
    plan_sd, read_sd = run_dir / "stages" / "plan", run_dir / "stages" / "read"
    put(plan_sd, {"output/plan.md": "- see `locked/f.py:1`\n", "locked/f.py": "x\n"})
    put(read_sd, {"output/notes.md": NOTES.replace("missing.md:1", "locked/f.py:1"), "locked/f.py": "x\n"})
    for sd in (plan_sd, read_sd):
        (sd / "locked").chmod(0)
    try:
        bad = _common.locator_problems(root, run_dir, plan_sd)
        plan = poll.gate_now(root, run_id, "plan")
        own = {c["name"]: c["passed"] for c in read.checks(root, run_dir, read_sd)}
    finally:
        for sd in (plan_sd, read_sd):
            (sd / "locked").chmod(0o755)
    assert bad == ["`locked/f.py:1` in output/plan.md: no such file"]
    assert plan["unit_status"] == "gate_failed" and own["every quote stands at its stated location"]


def test_the_read_gate_s_own_checks_name_what_they_cannot_stat(finished):
    """Item 1, the read gate's own checks: a quote at a location the system refuses to look up is not checked there
    (the new check names the location), and a probe record the system refuses is no record."""
    root, _, run_dir = finished
    sd = run_dir / "stages" / "read"
    notes = NOTES.replace("`missing.md:1`\n", "`missing.md:1`\n" + LONG_ENTRY)
    notes = notes.replace("none: the material is a text.", f"- a probe, `output/probes/{'b' * 256}.txt`")
    put(sd, {"output/notes.md": notes, "output/probes/kept.txt": "x\n"})
    found = {c["name"]: c for c in read.checks(root, run_dir, sd)}
    assert found["every quote stands at its stated location"]["passed"]
    assert found["every probe has its record under output/probes/"]["detail"] == f"probes/{'b' * 256}.txt: no such file"


def test_harness_steps_reads_a_finished_run_names_a_session_without_transcript_and_writes_nothing(
    finished, capsys, monkeypatch
):
    root, _, run_dir = finished
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))  # the rules are the agent files of the checkout it runs in

    def snapshot() -> dict:
        return {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(run_dir.rglob("*")) if p.is_file()}

    before = snapshot()
    out = gates.review(root, run_dir)
    assert snapshot() == before
    names = [(r["unit"], r["name"], r["passed"]) for r in out["rows"]]
    assert ("read", "step 1: wrote: progress.md", False) in names and ("read", "step 2: read: plan.md", True) in names
    assert out["no_transcript"] == [{"unit": "plan", "session": "22222222-0000-0000-0000-000000000000"}]
    assert ("plan", "the session's transcript was found", False) in names
    assert cli.main(["steps", "--run-dir", str(run_dir)]) == 0
    assert json.loads(capsys.readouterr().out)["failed"] == out["failed"]
    assert gates.review(root, run_dir.parent / "absent")["status"] == "no_run"
