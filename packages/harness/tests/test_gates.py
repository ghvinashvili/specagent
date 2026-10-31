"""Tests for the stage gates: each gate passes a well-formed result and names what is wrong in a broken one.
Run from the repository root: `uv run pytest -q packages/harness/tests/test_gates.py`."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from harness.gates import _common

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "docs" / "roles" / "stages.yaml").is_file())
LOC = "`context/sample.txt:3`"
NO_PAGES = {"docs": "none — a fixture of the write gate's other checks"}  # ADR-0027: code without pages


def failed(stage: str, root: Path, run: Path, sd: Path) -> list[str]:
    module = importlib.import_module(f"harness.gates.{stage}")
    return [c["name"] for c in module.checks(root, run, sd) if not c["passed"]]


def put(base: Path, files: dict) -> None:
    for rel, content in files.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")


def tasks(*items: dict) -> dict:
    return {
        "schema_version": 1,
        "stage": "x",
        "tasks": [
            {"id": f"T{i:03d}", "category": "c", "description": "d", "steps": ["s"], "passes": False, **t}
            for i, t in enumerate(items, 1)
        ],
    }


def res(**extra) -> dict:
    return {
        "schema_version": 1,
        "run_id": "r",
        "stage": "x",
        "role_type": "t",
        "status": "complete",
        "outputs": [],
        "summary": "s",
        "evidence": [],
        "open_questions": [],
        **extra,
    }


@pytest.fixture()
def run(tmp_path: Path) -> Path:
    run = tmp_path / "runs" / "20261001-000000-demo"
    (run / "stages").mkdir(parents=True)
    (run / "_access").mkdir()
    return run


def test_every_stage_of_every_table_has_a_gate_module():
    tables = [ROOT / "docs/roles/stages.yaml", *sorted((ROOT / "docs/roles/pipelines").glob("*.yaml"))]
    for t in tables:
        for row in yaml.safe_load(t.read_text(encoding="utf-8"))["stages"]:
            assert callable(importlib.import_module(f"harness.gates.{row['id']}").checks), row["id"]


def _common_failures(run: Path, sd: Path) -> list[str]:
    from harness import gates

    return [c["name"] for c in gates.common_checks(ROOT, run, sd, "read") if not c["passed"]]


def test_an_output_path_is_read_from_the_stage_directory(run):
    sd = run / "stages/read"
    put(sd, {"output/notes.md": "n", "output/empty.md": ""})
    put(run / "stages/plan", {"output/plan.md": "p"})

    def result(*paths, kind="notes"):
        put(sd, {"result.json": res(stage="read", outputs=[{"path": p, "kind": kind} for p in paths])})
        return _common_failures(run, sd)

    assert result("output/notes.md") == []  # as the session sees it from its stage directory
    assert result("stages/read/output/notes.md") == []  # the same file, named from the run directory
    assert result("output/missing.md") == ["output exists: output/missing.md"]
    assert result("output/empty.md") == ["output exists: output/empty.md"]
    # another stage's file is not this stage's output, however the path is written
    assert result("../plan/output/plan.md") == ["output exists: ../plan/output/plan.md"]
    assert result("stages/plan/output/plan.md") == ["output exists: stages/plan/output/plan.md"]
    assert result("src/app.py", kind="code") == []  # code lives on the branch; the write gate looks there


def test_plan(run):
    sd = run / "stages/plan"
    plan = (
        "# Plan\n## Goal\ng\n## Requirements\n1. r\n## Phase -1 gates\nok\n## Current state\n"
        + LOC
        + "\n## Decisions\nnone\n## Approach\nchange `src/app.py`\n## Trial\nbuilt and ran it\n"
        + "## Reference output\nnone: nothing is printed\n## Risks\nr\n## Out of scope\no\n"
    )
    ran = res(evidence=[{"claim": "the trial passes", "how_checked": "ran", "command": "pytest -q", "exit_code": 0}])
    trial = "--- a/src/app.py\n+++ b/src/app.py\n@@ -1 +1 @@\n-A = 1\n+A = 2\n"
    put(
        sd,
        {
            "output/plan.md": plan,
            "output/trial/trial.patch": trial,
            "result.json": ran,
            "tasks.json": tasks({}, {"depends_on": ["T001"]}),
        },
    )
    assert failed("plan", ROOT, run, sd) == []
    # naming the marker is not an open question (seen live: "No `[NEEDS CLARIFICATION]` markers exist")
    put(sd, {"output/plan.md": plan + "\n- No `[NEEDS CLARIFICATION]` markers exist.\n"})
    assert failed("plan", ROOT, run, sd) == []
    put(sd, {"tasks.json": ""})
    (sd / "tasks.json").unlink()
    put(sd, {"output/tasks.json": tasks({})})  # the task list in the wrong place: the gate says where it belongs
    module = importlib.import_module("harness.gates.plan")
    missing = next(c for c in module.checks(ROOT, run, sd) if c["name"] == "tasks.json exists")
    assert not missing["passed"] and "beside result.json" in missing["detail"]
    (sd / "output/tasks.json").unlink()
    put(
        sd,
        {
            "output/plan.md": plan.replace("## Risks\nr\n", "") + "[NEEDS CLARIFICATION: x]",
            "tasks.json": tasks({"depends_on": ["T002"]}, {"depends_on": ["T001"], "steps": []}),
        },
    )
    assert failed("plan", ROOT, run, sd) == [
        "plan.md has the required sections",
        "no [NEEDS CLARIFICATION: ...] marker is left",
        "every task has at least one step",
        "the dependency graph has no cycle",
    ]


def test_plan_gate_asks_for_the_traces_of_a_design_that_was_built_and_run(run):
    """A plan is refused when its author did not try the design, left a reader's question undecided, or changed a
    file in the trial that the plan does not name."""
    sd = run / "stages/plan"
    head = "# Plan\n## Goal\ng\n## Requirements\n1. r\n## Phase -1 gates\nok\n## Current state\n" + LOC + "\n"
    tail = "## Reference output\nnone: nothing is printed\n## Risks\nr\n## Out of scope\no\n"
    plan = (
        head
        + "## Decisions\n- Q1: three, by `context/sample.txt:3`\n## Approach\nchange `src/app.py`\n## Trial\nran it\n"
        + tail
    )
    ran = res(evidence=[{"claim": "the trial passes", "how_checked": "ran", "command": "pytest -q", "exit_code": 0}])
    trial = "--- a/src/app.py\n+++ b/src/app.py\n@@ -1 +1 @@\n-A = 1\n+A = 2\n"
    files = {"output/plan.md": plan, "output/trial/trial.patch": trial, "result.json": ran, "tasks.json": tasks({})}
    put(sd, {**files, "input/read/questions.md": "How often is an upload retried?\nWhich status ends the retry?\n"})
    assert failed("plan", ROOT, run, sd) == ["every question of the reader is decided under Decisions"]
    undecided = next(c for c in importlib.import_module("harness.gates.plan").checks(ROOT, run, sd) if not c["passed"])
    assert undecided["detail"] == "Q2"  # the first question has its decision
    put(sd, {"output/plan.md": plan.replace("- Q1:", "- Q1 and Q2:")})
    assert failed("plan", ROOT, run, sd) == []
    # a decision under a sub-heading of Decisions is still a decision
    put(sd, {"output/plan.md": plan.replace("- Q1: three", "### Retries\n- Q1: three\n### Status\n- Q2: 500")})
    assert failed("plan", ROOT, run, sd) == []
    put(sd, {"result.json": res()})  # no command was run
    assert failed("plan", ROOT, run, sd) == ["the design was tried before the plan was written"]
    put(sd, {"result.json": ran, "output/trial/trial.patch": trial.replace("src/app.py", "lib/other.py")})
    assert failed("plan", ROOT, run, sd) == ["every file the trial changed is named in the plan"]
    (sd / "output/trial/trial.patch").unlink()
    assert failed("plan", ROOT, run, sd) == ["the design was tried before the plan was written"]
    # headings numbered in levels are still the sections; a list of questions is counted by its items
    numbered = plan.replace("## Decisions", "### 4.1 Decisions").replace("## Trial", "## A.2 Trial")
    put(sd, {"output/plan.md": numbered, "output/trial/trial.patch": trial})
    put(sd, {"input/read/questions.md": "# Questions\n\nWhat the material leaves open:\n- How often?\n"})
    assert failed("plan", ROOT, run, sd) == []
    put(sd, {"input/read/questions.md": "none\n", "output/plan.md": plan.replace("- Q1: three, by", "none, see")})
    assert failed("plan", ROOT, run, sd) == []
    (sd / "output/trial/trial.patch").unlink()
    put(sd, {"input/read/questions.md": "How often is an upload retried?\nWhich status ends the retry?\n"})
    # a design that cannot be run says so in its first words, where the human who approves the plan reads it
    put(
        sd,
        {"output/plan.md": plan.replace("- Q1:", "- Q1, Q2:").replace("ran it", "Nothing to run: the work is a text.")},
    )
    assert failed("plan", ROOT, run, sd) == []


def test_plan_gate_refuses_a_plan_that_pastes_the_code_instead_of_specifying_it(run):
    """A plan is read by the human who approves it and by the verifier. The code its author tried is delivered
    beside it as the trial patch, which the writer receives; pasted into the plan it turns a specification into a
    listing. Excerpts stay possible, and an exact reference output is what its section is for."""
    sd = run / "stages/plan"
    name = "the plan specifies the work instead of pasting its code"
    head = "# Plan\n## Goal\ng\n## Requirements\n1. r\n## Phase -1 gates\nok\n## Current state\n" + LOC + "\n"
    spec = "\n".join(f"- `step_{n}(table) -> list`: rule {n} of the layout, by `src/app.py:{n}`." for n in range(1, 61))
    plan = (
        head
        + "## Decisions\nnone\n## Approach\nchange `src/app.py`\n"
        + spec
        + "\n## Trial\nran it\n## Reference output\nnone: nothing is printed\n## Risks\nr\n## Out of scope\no\n"
    )
    ran = res(evidence=[{"claim": "the trial passes", "how_checked": "ran", "command": "pytest -q", "exit_code": 0}])
    trial = "--- a/src/app.py\n+++ b/src/app.py\n@@ -1 +1 @@\n-A = 1\n+A = 2\n"
    put(sd, {"output/plan.md": plan, "output/trial/trial.patch": trial, "result.json": ran, "tasks.json": tasks({})})
    assert failed("plan", ROOT, run, sd) == []
    excerpt = "```python\n" + "\n".join(f"x{n} = {n}" for n in range(40)) + "\n```\n"
    put(sd, {"output/plan.md": plan.replace("## Trial", excerpt + "## Trial")})  # an excerpt is no listing
    assert failed("plan", ROOT, run, sd) == []
    listing = "```python\n" + "\n".join(f"def f{n}(): return {n}" for n in range(400)) + "\n```\n"
    put(sd, {"output/plan.md": plan.replace("## Trial", listing + "## Trial")})
    assert failed("plan", ROOT, run, sd) == [name]
    module = importlib.import_module("harness.gates.plan")
    why = next(c for c in module.checks(ROOT, run, sd) if c["name"] == name)["detail"]
    assert why.startswith("400 of ") and "output/trial/trial.patch" in why
    # the same listing as the reference output is an exact result, not pasted code
    put(sd, {"output/plan.md": plan.replace("none: nothing is printed", "the file as written:\n" + listing)})
    assert failed("plan", ROOT, run, sd) == []


def test_frame(run):
    sd = run / "stages/frame"
    put(sd, {"output/question.md": "q", "tasks.json": tasks({}, {})})
    assert failed("frame", ROOT, run, sd) == []
    put(sd, {"tasks.json": tasks({})})
    assert failed("frame", ROOT, run, sd) == ["two to seven tasks"]
    put(sd, {"tasks.json": tasks({}, {"depends_on": ["T001"]})})
    assert failed("frame", ROOT, run, sd) == ["the tasks are independent"]


def test_research_and_investigate(run):
    sd = run / "stages/research"
    put(sd, {"output/findings.md": f"# Findings\n- the parser lives here {LOC}\n", "output/questions.md": "none\n"})
    assert failed("research", ROOT, run, sd) == []
    put(sd, {"output/findings.md": "- the parser is probably in src\n"})
    assert failed("research", ROOT, run, sd) == ["every statement has a `path:line` locator"]
    put(sd, {"output/findings.md": f"- x {LOC}\n", "tasks.json": tasks({"passes": True, "evidence": "ran"})})
    assert failed("investigate", ROOT, run, sd) == []


def test_story_spec_validate_accept_files(run):
    story = (
        "## Story\ns\n## Acceptance criteria\n1. a\n2. b\n## Edge cases\ne\n## Out of scope\no\n## Open questions\nq\n"
    )
    put(run / "stages/story", {"output/story.md": story})
    assert failed("story", ROOT, run, run / "stages/story") == []
    put(run / "stages/x", {"output/story.md": story.replace("## Out of scope\no\n", "").replace("2. b", "3. b")})
    assert failed("story", ROOT, run, run / "stages/x") == [
        "story.md has the required sections",
        "the criteria are numbered 1..n without gaps",
    ]

    spec = "## Intent\n## Requirements\n## Limits\n## Done\n## Out of scope\n| Criterion | Requirement |\n|---|---|\n| 1 | R1 |\n| 2 | R2 |\n"
    put(run / "stages/spec", {"output/spec.md": spec})
    assert failed("spec", ROOT, run, run / "stages/spec") == []
    put(run / "stages/spec", {"output/spec.md": spec.replace("| 2 | R2 |\n", "")})
    assert failed("spec", ROOT, run, run / "stages/spec") == [
        "every acceptance criterion has a row in the mapping table"
    ]
    # the skeleton is the whole document (spec 005): a technical brief's sections do not make a spec
    put(run / "stages/spec", {"output/spec.md": spec.replace("## Limits\n", "").replace("## Done\n", "")})
    assert failed("spec", ROOT, run, run / "stages/spec") == ["spec.md has the required sections"]
    put(run / "stages/spec", {"output/spec.md": "", "output/technical-brief.md": spec})
    assert "spec.md exists" in failed("spec", ROOT, run, run / "stages/spec")

    findings = f"1. Critical: the limit is not enforced {LOC}\n\n| Criterion | State |\n|---|---|\n| 1 | conforms |\n| 2 | deviates (1) |\n"
    put(run / "stages/validate", {"output/findings.md": findings})
    assert failed("validate", ROOT, run, run / "stages/validate") == []
    put(run / "stages/validate", {"output/findings.md": findings.replace(LOC, "somewhere")})
    assert failed("validate", ROOT, run, run / "stages/validate") == ["every finding has a `path:line` locator"]


def test_verify_and_wikicheck(run):
    sd = run / "stages/verify"
    report = "# Report\n1. claim A: `pytest -q`, exit 0. confirmed\n2. claim B: could not check, no network\n## Beyond the claims\nlint clean\n"
    put(
        sd,
        {
            "output/report.md": report,
            "result.json": res(
                evidence=[{"claim": "A", "how_checked": "ran", "command": "pytest -q", "exit_code": 0}],
                verdict={"decision": "accept", "reasons": ["1"]},
            ),
        },
    )
    assert failed("verify", ROOT, run, sd) == []
    put(
        sd,
        {
            "output/report.md": report.replace(" confirmed", ""),
            "result.json": res(evidence=[{"claim": "A", "how_checked": "read"}]),
        },
    )
    assert failed("verify", ROOT, run, sd) == [
        "every entry states confirmed, refuted or could not check",
        "every evidence entry has a command",
        "result.json proposes a verdict",
        "the verdict proposal is accept, revise or reject",
    ]
    put(
        run / "stages/ingest",
        {"output/changes.md": "- created wiki/concepts/dedupe.md\n- updated wiki/sources/samples.md\n"},
    )
    wc = run / "stages/wikicheck"
    put(
        wc,
        {
            "output/report.md": report + "wiki/concepts/dedupe.md\n",
            "result.json": json.loads((sd / "result.json").read_text()),
        },
    )
    assert "every changed page is in the report" in failed("wikicheck", ROOT, run, wc)


def test_critique_refute_challenge(run):
    sd = run / "stages/critique"
    table = (
        "# Critique\n| No. | Location | Says | Correct | Source | Severity |\n|---|---|---|---|---|---|\n"
        "| 1 | work/doc.md section 2, line 14 | x | y | `docs/a.md:3` | must fix |\n\nCoverage: read work/doc.md completely.\n"
    )
    put(sd, {"output/critique.md": table, "result.json": res()})
    put(run / "_access", {"critique.inputs.json": [{"as": "brief.md"}, {"as": "work/doc.md"}, {"as": "work/notes.md"}]})
    assert failed("critique", ROOT, run, sd) == ["every input file is named in the critique"]
    put(
        sd,
        {
            "output/critique.md": table.replace("completely.", "and work/notes.md completely.").replace(
                "must fix", "serious"
            )
        },
    )
    assert failed("critique", ROOT, run, sd) == ["every severity is blocks, must fix or minor"]
    put(run / "stages/analyze", {"output/proposals/001.md": "p", "output/proposals/002.md": "p"})
    ch = run / "stages/challenge"
    put(
        ch,
        {
            "output/critique.md": table.replace("work/doc.md section 2", "proposals/001.md section 2"),
            "result.json": res(),
        },
    )
    assert failed("challenge", ROOT, run, ch) == ["every proposal has an entry"]


def test_reviewing_gates_ask_for_work_of_the_reviewer_s_own(run):
    """Where the work is code, a verifier leaves the checks it wrote itself and has an entry for every task the
    author claims, and a critic has run the work at least once: a review that only read is not what a reviewer
    sent to do the job would deliver."""
    patch = "--- a/src/app.py\n+++ b/src/app.py\n@@ -1 +1 @@\n-A = 1\n+A = 2\n"
    sd = run / "stages/verify"
    report = "# Report\n1. T001 passes: `pytest -q`, exit 0. confirmed\n## Beyond the claims\nlint clean\n"
    ran = [{"claim": "A", "how_checked": "ran", "command": "pytest -q", "exit_code": 0}]
    put(
        sd,
        {
            "output/report.md": report,
            "result.json": res(evidence=ran, verdict={"decision": "accept", "reasons": ["1"]}),
            "input/work/changes.patch": patch,
            "input/work/01/tasks.json": tasks({"passes": True, "evidence": "e"}, {"passes": True, "evidence": "e"}),
        },
    )
    assert failed("verify", ROOT, run, sd) == [
        "every task of the author has its entry in the report",
        "the verifier's own checks are kept under output/checks/",
    ]
    module = importlib.import_module("harness.gates.verify")
    missing = next(c for c in module.checks(ROOT, run, sd) if c["name"].startswith("every task of the author"))
    assert missing["detail"] == "T002"
    put(
        sd,
        {"output/report.md": report.replace("## Beyond", "2. T002 passes: read `src/app.py:1`. confirmed\n## Beyond")},
    )
    put(sd, {"output/checks/content_check.py": "print('ok')\n"})
    assert failed("verify", ROOT, run, sd) == []

    cd = run / "stages/critique"
    table = (
        "# Critique\n| No. | Location | Says | Correct | Source | Severity |\n|---|---|---|---|---|---|\n"
        "| 1 | work/changes.patch line 5 | x | y | `docs/a.md:3` | minor |\n\nCoverage: read work/changes.patch.\n"
    )
    put(cd, {"output/critique.md": table, "result.json": res(), "input/work/changes.patch": patch})
    put(run / "_access", {"critique.inputs.json": [{"as": "brief.md"}, {"as": "work/changes.patch"}]})
    assert failed("critique", ROOT, run, cd) == [
        "the critic ran the work: an evidence entry with command and exit code"
    ]
    put(cd, {"result.json": res(evidence=ran)})
    assert failed("critique", ROOT, run, cd) == []


def test_a_critique_is_read_by_the_header_row_of_its_table(run):
    """Item 2: the critique gate finds a finding's location, source and severity by the headers of its table, with
    four, five or six columns and in any order; a table without a Severity column fails the gate."""
    sd = run / "stages/critique"
    put(run / "_access", {"critique.inputs.json": [{"as": "work/doc.md"}]})
    coverage = "\n\nCoverage: read work/doc.md completely.\n"
    four = (
        "| No. | Location | Finding | Severity |\n| --- | --- | --- | --- |\n"
        "| 1 | a.py:3 | the loop never ends | blocks |\n"
    )
    put(sd, {"output/critique.md": "# Critique\n" + four + coverage, "result.json": res()})
    assert failed("critique", ROOT, run, sd) == [
        "every finding has a source",
        "every blocks finding has its evidence entry in result.json",
    ]
    five = (
        "| No. | Location | Says | Source | Severity |\n|---|---|---|---|---|\n"
        "| 1 | a.py:3 | x | `docs/a.md:3` | blocks |\n"
    )
    put(sd, {"output/critique.md": "# Critique\n" + five + coverage})
    assert failed("critique", ROOT, run, sd) == ["every blocks finding has its evidence entry in result.json"]
    turned = (
        "| Severity | No. | Source (path and line) | Location in the work (section and line) |\n"
        "| --- | --- | --- | --- |\n| **must fix** | 1 | `docs/a.md:3` | work/doc.md line 4 |\n"
    )
    put(sd, {"output/critique.md": "# Critique\n" + turned + coverage})
    assert failed("critique", ROOT, run, sd) == []
    put(sd, {"output/critique.md": "# Critique\n" + four.replace("Severity", "Level") + coverage})
    assert failed("critique", ROOT, run, sd) == ["critique.md has a findings table with a Severity column"]


def test_judge_digest_classify_review_advise(run):
    put(run / "stages/judge", {"result.json": res(verdict={"decision": "revise", "reasons": ["entry 2 refuted"]})})
    assert failed("judge", ROOT, run, run / "stages/judge") == []
    put(run / "stages/judge", {"result.json": res()})
    assert len(failed("judge", ROOT, run, run / "stages/judge")) == 2

    digest = {"source": "x", "items": [], "embedded_instructions": []}
    put(run / "stages/digest", {"result.json": res(digest=digest)})
    assert failed("digest", ROOT, run, run / "stages/digest") == []
    put(
        run / "stages/digest",
        {"result.json": res(digest=digest, outputs=[{"path": "a", "kind": "other"}]), "output/a.md": "x"},
    )
    assert failed("digest", ROOT, run, run / "stages/digest") == ["outputs is empty", "no file was written to output/"]

    put(run, {"manifest.json": {"pipeline": "intake"}})
    put(run / "stages/classify", {"result.json": res(label={"value": "feature", "confidence": 0.9})})
    assert failed("classify", ROOT, run, run / "stages/classify") == []
    put(run / "stages/classify", {"result.json": res(label={"value": "bug", "confidence": 0.9})})
    assert failed("classify", ROOT, run, run / "stages/classify") == ["label.value is one of the route labels"]

    for shard in ("01", "02"):
        (run / "stages/advise" / shard).mkdir(parents=True)
    put(run / "stages/review", {"result.json": res(ranking={"order": ["02", "01"]})})
    assert failed("review", ROOT, run, run / "stages/review") == []
    put(run / "stages/review", {"result.json": res(ranking={"order": ["02", "02"]})})
    assert failed("review", ROOT, run, run / "stages/review") == ["ranking.order names every candidate exactly once"]

    sd = run / "stages/advise/01"
    put(sd, {"output/answer.md": "word " * 200, "tasks.json": tasks({"category": "Contrarian", "passes": True})})
    assert failed("advise", ROOT, run, sd) == []
    put(sd, {"output/answer.md": "As the contrarian I say " + "word " * 40})
    assert failed("advise", ROOT, run, sd) == [
        "answer.md has 150 to 300 words",
        "the answer does not name its perspective",
    ]


def test_verdict_and_synthesize(run):
    sd = run / "stages/verdict"
    put(
        run / "_access",
        {"verdict.inputs.json": [{"as": "brief.md"}, {"as": "advice/01/answer.md"}, {"as": "review/result.json"}]},
    )
    doc = (
        "## Where they agree\n- both keep the queue (advice/01/answer.md)\n## Where they clash\n- cost (review/result.json)\n"
        "## Blind spots\n- none named (review/result.json)\n## Recommendation\n- keep it (advice/01)\n## First step\n- measure (advice/01)\n"
    )
    put(sd, {"output/verdict.md": doc})
    assert failed("verdict", ROOT, run, sd) == []
    put(
        sd,
        {
            "output/verdict.md": doc.replace("- measure (advice/01)", "- measure it next week").replace(
                "## Blind spots\n- none named (review/result.json)\n", ""
            )
        },
    )
    assert failed("verdict", ROOT, run, sd) == [
        "verdict.md has the five sections",
        "every statement names the input it comes from",
    ]


def test_analyze(run):
    sd = run / "stages/analyze"
    headings = "".join(
        f"## {h}\nx\n"
        for h in (
            "Evidence",
            "Diagnosis",
            "Proposed change",
            "Regression case",
            "Cost of the change",
            "Version",
            "Rollback",
        )
    )
    put(
        sd,
        {
            "output/taxonomy.md": "t",
            "output/proposals/001.md": "# Change proposal: x\n"
            + headings
            + "see 20260930-101500-demo/stages/write/gate.json\n",
        },
    )
    assert failed("analyze", ROOT, run, sd) == []
    put(sd, {"output/proposals/002.md": "# Change proposal: y\n## Evidence\nit often fails\n"})
    assert failed("analyze", ROOT, run, sd) == [
        "every proposal has the sections of templates/change-proposal.md",
        "every proposal names a run file",
    ]


class Repo:
    """A small git repository with a main branch and a checked-out work branch."""

    def __init__(self, root: Path):
        self.root = root

    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-C", str(self.root), "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
            check=True,
            capture_output=True,
        )

    def commit_and_return_to_main(self, files: dict, message: str) -> None:
        put(self.root, files)
        self.git("add", "-A")
        self.git("commit", "-qm", message)
        self.git("checkout", "-q", "main")


def report_of(repo: Repo, branch: str = "work-1") -> str:
    """What a writer states about its work: the commits of its branch and an entry per task."""
    args = ["git", "-C", str(repo.root), "rev-parse", "--short=7", branch]
    head = subprocess.run(args, capture_output=True, text=True, check=True).stdout.strip()
    return f"# Report\n\n## Commits\n- {head} feat: a\n\n## Tasks\n- T001: done; `pytest -q` ended with 0\n"


@pytest.fixture()
def repo(tmp_path: Path, monkeypatch) -> Repo:
    r = Repo(tmp_path / "repo")
    put(
        r.root,
        {
            "README.md": "x\n",
            "src/app.py": "A = 1\n",
            "tests/test_app.py": "def test_a():\n    assert True\n",
            "wiki/index.md": "# Index\n",
            "wiki/log.md": "# Log\n",
            "context/raw.txt": "raw\n",
            "schemas/wiki-page.schema.json": (ROOT / "schemas/wiki-page.schema.json").read_text(encoding="utf-8"),
            "docs/roles/need-to-know.yaml": (ROOT / "docs/roles/need-to-know.yaml").read_text(encoding="utf-8"),
            "docs/roles/stages.yaml": 'version: 1\nstages:\n  - {id: write, inputs: ["plan:tasks.json"]}\n',
            ".claude/agents/writer.md": "x\n",
            "packages/legacy/old.py": "A = 1\n",
        },
    )
    r.git("init", "-q", "-b", "main")
    r.git("add", "-A")
    r.git("commit", "-qm", "init")
    r.git("checkout", "-qb", "work-1")
    monkeypatch.setattr(
        _common, "TEST_CMD", [sys.executable, "-c", "pass"]
    )  # the gate's test command, replaced by a no-op
    # the gate runs a branch's suite in a sandbox (gates/_sandbox.py), which a test machine may not be able to start:
    # here it runs the test command as it is; test_gate_sandbox.py tests the sandbox itself
    from harness.gates import _sandbox

    monkeypatch.setattr(_sandbox, "problem", lambda root, tree, tmp=None: None)
    monkeypatch.setattr(_sandbox, "command", lambda root, tree, argv, tmp=None: list(argv))
    return r


def test_write_gate_on_a_branch(repo, run):
    repo.commit_and_return_to_main({"src/app.py": "A = 2\n"}, "feat: a")
    sd = run / "stages/write/01"
    put(run, {"stages/plan/tasks.json": tasks(NO_PAGES)})
    put(sd, {"report.md": report_of(repo)})
    ev = [{"claim": "T001", "how_checked": "ran", "command": "pytest -q", "exit_code": 0}]
    put(
        sd,
        {
            "tasks.json": tasks({"passes": True, "evidence": "pytest -q: 1 passed"}),
            "result.json": res(summary="branch work-1, 1 commit", evidence=ev),
        },
    )
    assert failed("write", repo.root, run, sd) == []
    code = [{"path": "src/app.py", "kind": "code"}, {"path": "src/gone.py", "kind": "code"}]
    put(sd, {"result.json": res(summary="branch work-1, 1 commit", evidence=ev, outputs=code)})
    assert failed("write", repo.root, run, sd) == ["every output of kind code exists on the branch"]
    put(sd, {"result.json": res(summary="branch work-1, 1 commit", evidence=ev, outputs=code[:1])})
    assert failed("write", repo.root, run, sd) == []
    put(sd, {"tasks.json": tasks({"passes": True, "evidence": ""}), "result.json": res(summary="done", evidence=ev)})
    assert failed("write", repo.root, run, sd) == [
        "every passed task carries evidence",
        "result.json names the branch of the work",
    ]


def test_write_gate_asks_for_the_report_the_verifier_checks(repo, run):
    """The author states its work in `report.md`: the commits, an entry per task, what it decided and noticed. The
    session that verifies the work checks those statements one by one; without the report it has the task list
    alone (seen live: a verifier with the report wrote 75 entries, one without it 17)."""
    name = "report.md states the work: its commits and every task"
    repo.commit_and_return_to_main({"src/app.py": "A = 2\n"}, "feat: a")
    sd = run / "stages/write/02"
    put(run, {"stages/plan/tasks.json": tasks(NO_PAGES)})
    ev = [{"claim": "T001", "how_checked": "ran", "command": "pytest -q", "exit_code": 0}]
    files = {
        "tasks.json": tasks({"passes": True, "evidence": "pytest -q: 1 passed"}),
        "result.json": res(summary="branch work-1, 1 commit", evidence=ev),
    }
    put(sd, files)
    assert failed("write", repo.root, run, sd) == [name]
    module = importlib.import_module("harness.gates.write")
    why = next(c for c in module.checks(repo.root, run, sd) if c["name"] == name)["detail"]
    assert why == "report.md is missing beside tasks.json"
    put(sd, {"report.md": "# Report\n\nEverything works.\n"})
    assert next(c for c in module.checks(repo.root, run, sd) if c["name"] == name)["detail"] == "no entry for T001"
    put(sd, {"report.md": "# Report\n\n- T001: done\n"})
    why = next(c for c in module.checks(repo.root, run, sd) if c["name"] == name)["detail"]
    assert why == "none of the commits of the branch is named"
    put(sd, {"report.md": report_of(repo)})
    assert failed("write", repo.root, run, sd) == []


def test_write_gate_takes_a_command_that_is_meant_to_fail_and_records_what_the_harness_ran(repo, run):
    # seen live: a writer showed that `map --check` exits 1 on a stale file, and the gate refused the entry
    repo.commit_and_return_to_main({"src/app.py": "A = 2\n"}, "feat: a")
    sd = run / "stages/write/01"
    put(run, {"stages/plan/tasks.json": tasks(NO_PAGES)})
    put(sd, {"report.md": report_of(repo)})
    meant = {
        "claim": "the check reports a stale file",
        "how_checked": "changed one",
        "command": "check",
        "exit_code": 1,
    }
    files = {"tasks.json": tasks({"passes": True, "evidence": "e"})}
    name = "every evidence entry names its command, and the command ended as it should"
    put(sd, {**files, "result.json": res(summary="branch work-1", evidence=[meant])})
    assert failed("write", repo.root, run, sd) == [name]
    put(sd, {**files, "result.json": res(summary="branch work-1", evidence=[{**meant, "expected_exit_code": 1}])})
    assert failed("write", repo.root, run, sd) == []
    put(sd, {**files, "result.json": res(summary="branch work-1", evidence=[{"claim": "c", "how_checked": "read it"}])})
    assert failed("write", repo.root, run, sd) == [name]
    ran = json.loads((sd / "checks.json").read_text(encoding="utf-8"))
    assert [c["exit_code"] for c in ran["checks"]] == [0] and ran["checks"][0]["command"].endswith("-c pass")


def test_write_gate_asks_for_a_test_that_was_seen_to_fail(repo, run):
    """A branch that changes tests carries one run that failed on purpose: the author broke the behaviour and the
    test caught it. The stop hook holds a session to the same checks without the suite the gate runs outside."""
    repo.commit_and_return_to_main({"src/app.py": "A = 2\n", "tests/test_app.py": "def test_a():\n    assert 2\n"}, "x")
    sd = run / "stages/write/01"
    put(run, {"stages/plan/tasks.json": tasks(NO_PAGES)})
    put(sd, {"report.md": report_of(repo)})
    passed = {"claim": "T001", "how_checked": "ran", "command": "pytest -q", "exit_code": 0}
    broken = {"claim": "the test fails without the change", "how_checked": "reverted A", "command": "pytest -q"}
    files = {"tasks.json": tasks({"passes": True, "evidence": "e"})}
    name = "a test was seen to fail when the behaviour is broken"
    put(sd, {**files, "result.json": res(summary="branch work-1", evidence=[passed])})
    assert failed("write", repo.root, run, sd) == [name]
    caught = [passed, {**broken, "exit_code": 1, "expected_exit_code": 1}]
    put(sd, {**files, "result.json": res(summary="branch work-1", evidence=caught)})
    assert failed("write", repo.root, run, sd) == []
    module = importlib.import_module("harness.gates.write")
    (sd / "checks.json").unlink()
    held = module.session_checks(repo.root, run, sd)
    assert all(c["passed"] for c in held) and not any("passes on the branch" in c["name"] for c in held)
    assert not (sd / "checks.json").exists()  # what the harness ran is recorded by the gate, not by the hook


def test_write_gate_refuses_a_branch_that_touches_hidden_or_closed_paths(repo, run):
    # seen live: inside the sandbox git reports the files a type may not read as deleted, and `git add -A` stages that
    repo.root.joinpath(".claude/agents/writer.md").unlink()
    put(repo.root, {"docs/handoff/note.md": "x\n", "evals/cases/c.md": "x\n"})  # closed to every role; to a writer
    repo.commit_and_return_to_main({"src/app.py": "A = 2\n", "packages/legacy/old.py": "A = 2\n"}, "feat: a")
    put(run, {"brief.md": "# Brief\n\n## Constraints\n- Do not touch: `packages/legacy/`, `docs/adr`\n"})
    sd = run / "stages/write/01"
    put(sd, {"report.md": report_of(repo)})
    ev = [{"claim": "T001", "how_checked": "ran", "command": "pytest -q", "exit_code": 0}]
    put(
        sd,
        {
            "tasks.json": tasks({"passes": True, "evidence": "pytest -q: 1 passed"}),
            "result.json": res(summary="branch work-1", evidence=ev, role_type="writer"),
        },
    )
    module = importlib.import_module("harness.gates.write")
    scope = next(c for c in module.checks(repo.root, run, sd) if c["name"].startswith("the branch stays out"))
    assert not scope["passed"]
    for path in (".claude/agents/writer.md", "docs/handoff/note.md", "evals/cases/c.md", "packages/legacy/old.py"):
        assert path in scope["detail"]
    assert "src/app.py" not in scope["detail"]


def test_a_branch_that_moves_a_closed_file_out_is_refused(repo, run):
    """Found on 2026-10-04: git names a moved file by its new path only, so a hook moved into src/ passed."""
    repo.git("mv", ".claude/agents/writer.md", "src/writer.md")
    repo.commit_and_return_to_main({}, "refactor: move")
    put(run, {"brief.md": "# Brief\n\n## Constraints\n- Do not touch: `packages/legacy/`\n"})
    scope = _common.scope_check(repo.root, run, res(role_type="writer"), "work-1")
    assert not scope["passed"] and ".claude/agents/writer.md" in scope["detail"]


@pytest.mark.parametrize(
    "path",
    [".claude/skills/\u00e9t\u00e9/SKILL.md", ".CLAUDE/settings.json", ".Mcp.json", "packages/x/.claude/skills/s/SKILL.md",
     "src/.mcp.json", "packages/y/.claude"],
)  # fmt: skip
def test_a_closed_path_is_found_however_git_spells_it(repo, run, path):
    """git quotes a name with an unusual character, and a file system that ignores case reads `.CLAUDE/` as
    `.claude/`: the scope check compares the names git gives with -z, in lower case."""
    repo.commit_and_return_to_main({path: "{}\n"}, "feat: config")
    scope = _common.scope_check(repo.root, run, res(role_type="writer"), "work-1")
    assert not scope["passed"] and path in scope["detail"]


def test_a_closed_name_that_is_no_utf_8_is_found(repo, run):
    """A file name git stores as bytes that are not UTF-8 is read all the same, and refused under `.claude/`."""
    name = b".claude/skills/\xff/SKILL.md"
    (repo.root / ".claude/skills/\udcff").mkdir(parents=True)  # the same bytes, as Python spells them
    (repo.root / ".claude/skills/\udcff/SKILL.md").write_text("x\n", encoding="utf-8")
    repo.commit_and_return_to_main({}, "feat: skill")
    scope = _common.scope_check(repo.root, run, res(role_type="writer"), "work-1")
    assert not scope["passed"] and name.decode("utf-8", "surrogateescape") in _common.changed_files(repo.root, "work-1")


def test_a_brief_that_opens_the_hooks_lets_a_branch_change_the_hook_scripts_only(repo, run):
    """ADR-0015: a writer reads what a subagent reads; a run that changes the hook scripts says so in its brief. The
    rest of .claude/ stays closed: a session that enters a checkout reads its settings, skills and agents there."""
    put(repo.root, {".claude/hooks/guard.py": "y\n", ".claude/settings.json": "{}\n", "docs/handoff/note.md": "x\n"})
    repo.root.joinpath(".claude/agents/writer.md").write_text("y\n", encoding="utf-8")
    repo.root.joinpath("docs/roles/stages.yaml").write_text("version: 1\nstages: []  # changed\n", encoding="utf-8")
    repo.commit_and_return_to_main({"src/app.py": "A = 2\n"}, "feat: a")
    writer = res(summary="branch work-1", role_type="writer")
    put(run, {"brief.md": "# Brief\n\n## Constraints\n- Do not touch: `packages/legacy/`\n"})
    closed = _common.scope_check(repo.root, run, writer, "work-1")
    assert not closed["passed"] and ".claude/hooks/guard.py" in closed["detail"]
    assert "docs/roles/stages.yaml" not in closed["detail"]  # a writer is not blind: the stage table is its to read
    put(run, {"brief.md": "# Brief\n\n## Constraints\n- Do not touch: `packages/legacy/`\n- Hooks: open\n"})
    opened = _common.scope_check(repo.root, run, writer, "work-1")
    assert ".claude/hooks/guard.py" not in opened["detail"]
    for path in (".claude/agents/writer.md", ".claude/settings.json", "docs/handoff/note.md"):
        assert not opened["passed"] and path in opened["detail"], path


def test_write_gate_finds_a_credential_and_failing_tests(repo, run, monkeypatch):
    repo.commit_and_return_to_main({"src/app.py": 'API_KEY = "abcdefghijklmnopqrstuvwxyz0123"\n'}, "feat: key")
    monkeypatch.setattr(_common, "TEST_CMD", [sys.executable, "-c", "raise SystemExit(1)"])
    sd = run / "stages/write/01"
    put(run, {"stages/plan/tasks.json": tasks(NO_PAGES)})
    put(sd, {"report.md": report_of(repo)})
    put(
        sd,
        {
            "tasks.json": tasks({"passes": True, "evidence": "e"}),
            "result.json": res(
                summary="work-1", evidence=[{"claim": "c", "how_checked": "h", "command": "c", "exit_code": 0}]
            ),
        },
    )
    names = failed("write", repo.root, run, sd)
    assert names == [
        f"`{sys.executable} -c raise SystemExit(1)` passes on the branch",
        "no credential in the branch diff",
    ]
    assert json.loads((sd / "checks.json").read_text(encoding="utf-8"))["checks"][0]["exit_code"] == 1


def test_accept_gate_refuses_product_code(repo, run):
    repo.commit_and_return_to_main(
        {"tests/test_more.py": "def test_b():\n    assert True\n", "src/app.py": "A = 3\n"}, "test: b"
    )
    put(run / "stages/story", {"output/story.md": "## Acceptance criteria\n1. a\n"})
    sd = run / "stages/accept"
    put(
        sd,
        {
            "output/acceptance.md": "| Criterion | Status | Test |\n|---|---|---|\n| 1 | passed | test_b |\n",
            "result.json": res(
                summary="tests on work-1",
                evidence=[{"claim": "1", "how_checked": "ran", "command": "pytest", "exit_code": 0}],
            ),
        },
    )
    assert failed("accept", repo.root, run, sd) == ["the branch changes test files only"]


def test_ingest_gate(repo, run):
    repo.commit_and_return_to_main({"wiki/concepts/dedupe.md": "x\n", "context/raw.txt": "changed\n"}, "docs: wiki")
    sd = run / "stages/ingest"
    put(sd, {"output/changes.md": "- created wiki/concepts/dedupe.md\n", "result.json": res(summary="branch work-1")})
    names = failed("ingest", repo.root, run, sd)
    assert "context/ is not in the diff" in names and "the branch changes wiki/ only" in names


def _reader_case(tmp_path: Path, change=lambda text: text) -> list[dict]:
    """The read gate over the reference notes of the reader eval case, optionally altered."""
    from harness.gates import read

    fixture = ROOT / "evals/regression/reader-quotes-locations/fixture"
    reference = ROOT / "evals/baseline/reader-quotes-locations/run/stages/read/output"
    out = tmp_path / "stages/read/output"
    out.mkdir(parents=True, exist_ok=True)
    (out / "notes.md").write_text(change((reference / "notes.md").read_text(encoding="utf-8")), encoding="utf-8")
    (out / "questions.md").write_text("What happens on status 500?\n", encoding="utf-8")
    return read.checks(fixture, tmp_path, tmp_path / "stages/read")


def test_read_gate_accepts_notes_whose_quotes_stand_at_their_lines(tmp_path: Path):
    assert all(c["passed"] for c in _reader_case(tmp_path))


def test_every_type_accounts_for_every_file_of_its_material(tmp_path: Path):
    from harness import gates
    from harness import pack as pack_mod
    from harness.gates import _common

    sd = tmp_path / "stages/plan"
    (sd / "output").mkdir(parents=True)
    pack = "# Knowledge pack\n\n### CLAUDE.md\n\n# Material\n\nThe pieces.\n\n### src/a.py\n\n1\tx\n\n"
    (sd / "pack.md").write_text(pack + "### docs/b.md:3-9\n\n3\ty\n\n### docs/c.md\n\n1\tz\n", encoding="utf-8")
    (sd / "output/plan.md").write_text("# Plan\n\n## src/a.py\n\nsteps\n", encoding="utf-8")
    assert _common.unaccounted_material(sd) == ["docs/b.md", "docs/c.md"]  # the pack is not material; a heading counts
    (sd / "output/plan.md").write_text(
        "# Plan\n\n## src/a.py\n\n## Coverage\n\n| `docs/b.md` | none |\n", encoding="utf-8"
    )
    (sd / "output/coverage.md").write_text("| `docs/c.md` | nothing the plan needs |\n", encoding="utf-8")
    assert _common.unaccounted_material(sd) == []  # a Coverage section and output/coverage.md both count
    (sd / "output/coverage.md").unlink()
    failing = [c for c in gates.common_checks(ROOT, tmp_path, sd, "plan") if c["name"].startswith("every file")]
    assert failing[0]["passed"] is False and failing[0]["detail"].startswith("docs/c.md")
    assert _common.material_files(tmp_path / "stages/read") == []  # no pack, no material, no check
    (sd / "pack.md").write_text(pack + f"{pack_mod.NOT_TEXT}: `img/chart.png`\n", encoding="utf-8")
    assert _common.material_files(sd) == ["src/a.py", "img/chart.png"]  # a picture is material to account for
    assert not any(c["name"].startswith("every file") for c in gates.common_checks(ROOT, tmp_path, tmp_path / "x", "x"))


def test_a_type_that_writes_no_file_is_not_asked_to_account_for_its_material(tmp_path: Path):
    from harness import gates

    manifest = {"stages": [{"id": "judge", "role_type": "judge"}, {"id": "plan", "role_type": "planner"}]}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    pack = "# Knowledge pack\n\n# Material\n\nThe pieces.\n\n### input/verify/report.md\n\n1\tx\n"
    for stage in ("judge", "plan"):
        (tmp_path / "stages" / stage).mkdir(parents=True)
        (tmp_path / "stages" / stage / "pack.md").write_text(pack, encoding="utf-8")

    def names(stage: str) -> list[str]:
        return [c["name"] for c in gates.common_checks(ROOT, tmp_path, tmp_path / "stages" / stage, stage)]

    assert "every file of the material is accounted for" not in names("judge")  # its tools hold no Write
    assert "every file of the material is accounted for" in names("plan")  # a planner writes, and accounts


@pytest.mark.parametrize(
    "stages, agent",
    [
        (None, None),  # no manifest
        ([{"id": "other", "role_type": "judge"}], None),  # the manifest does not name the stage
        ([{"id": "s", "role_type": "ghost"}], None),  # the type has no agent file
        ([{"id": "s", "role_type": "free"}], "---\nname: free\n---\n# Free\n"),  # no tools list: every tool
        ([{"id": "s", "role_type": "shell"}], "---\nname: shell\ntools: Read, Bash\n---\n"),  # Bash writes too
    ],
)
def test_the_material_check_stays_unless_the_type_surely_cannot_write(tmp_path: Path, stages, agent):
    from harness import gates

    repo, run = tmp_path / "repo", tmp_path / "run"
    if agent:
        name = stages[0]["role_type"]
        (repo / ".claude/agents").mkdir(parents=True)
        (repo / ".claude/agents" / f"{name}.md").write_text(agent, encoding="utf-8")
    (run / "stages/s").mkdir(parents=True)
    if stages is not None:
        (run / "manifest.json").write_text(json.dumps({"stages": stages}), encoding="utf-8")
    pack = "# Knowledge pack\n\n# Material\n\nThe pieces.\n\n### input/verify/report.md\n\n1\tx\n"
    (run / "stages/s/pack.md").write_text(pack, encoding="utf-8")
    names = [c["name"] for c in gates.common_checks(repo, run, run / "stages/s", "s")]
    assert "every file of the material is accounted for" in names


def test_read_gate_fails_a_quote_that_is_not_at_its_line(tmp_path: Path):
    moved = _reader_case(tmp_path, lambda t: t.replace("`context/sample.txt:2`", "`context/sample.txt:7`"))
    assert [c["name"] for c in moved if not c["passed"]] == ["every quote stands at its stated location"]


def test_read_gate_fails_a_changed_quote_and_an_entry_without_location(tmp_path: Path):
    changed = _reader_case(tmp_path / "a", lambda t: t.replace('three times."', 'five times."'))
    assert not next(c for c in changed if c["name"].startswith("every quote"))["passed"]
    bare = _reader_case(tmp_path / "b", lambda t: t.replace(" `context/sample.txt:3`", " context/sample.txt:3"))
    assert not next(c for c in bare if c["name"].startswith("every entry"))["passed"]


def test_read_gate_reads_an_entry_that_continues_on_indented_lines(tmp_path: Path):
    from harness.gates import read

    body = '- A fact.\n  Quote: "A failed upload is retried at most three times."\n  `context/sample.txt:2`\n- Next.\n'
    assert len(read.entries(body)) == 2 and "`context/sample.txt:2`" in read.entries(body)[0]


def test_read_gate_reads_a_quote_that_contains_double_quotes(tmp_path: Path):
    # seen live: quoted code has its own double quotes, and the fact before it may quote a word as well
    from harness.gates import read

    src = tmp_path / "src.py"
    src.write_text('a = 1\nstore = Store(tmp_path / "store")\nit = "seems"\n', encoding="utf-8")
    entry = '- The store is made at `tmp_path / "store"`. Quote: "store = Store(tmp_path / "store")" `src.py:2`'
    quote, location = read.parts(entry)
    assert quote == 'store = Store(tmp_path / "store")' and location.group(0) == "`src.py:2`"
    assert read.misplaced(entry, [tmp_path]) is None
    assert read.misplaced(entry.replace('/ "store")"', '/ "other")"'), [tmp_path]) == (
        "`src.py:2`: the quote is not at that place"
    )
    assert read.parts('- A fact with "a quoted passage" `src.py:1`')[0] == "a quoted passage"  # no `Quote:` word
    assert "seems" not in read.own_voice('- It is set. Quote: "it = "seems"" `src.py:3`')


def test_read_gate_asks_for_the_record_of_every_probe(tmp_path: Path):
    """What a command showed is a fact of the notes only with its record: the file that holds what was run and what
    came back. A reader that probed nothing says so."""
    name = "every probe has its record under output/probes/"
    none = "## Probes\n\nnone: the material is one text file; nothing in it can be run.\n"
    absent = _reader_case(tmp_path / "a", lambda t: t.replace(none, ""))
    assert not next(c for c in absent if c["name"] == name)["passed"]
    entry = "## Probes\n\n- Does the tool accept an empty list? It exits 2. `output/probes/empty-list.txt`\n"
    unrecorded = _reader_case(tmp_path / "b", lambda t: t.replace(none, entry))
    assert next(c for c in unrecorded if c["name"] == name)["detail"] == "probes/empty-list.txt: no such file"
    record = tmp_path / "c/stages/read/output/probes/empty-list.txt"
    record.parent.mkdir(parents=True)
    record.write_text("$ tool --list ''\nerror: empty list\nexit 2\n", encoding="utf-8")
    recorded = _reader_case(tmp_path / "c", lambda t: t.replace(none, entry))
    assert next(c for c in recorded if c["name"] == name)["passed"]
    bare = _reader_case(tmp_path / "d", lambda t: t.replace(none, "## Probes\n\n- It exits 2.\n"))
    assert "no file under output/probes/ is named" in next(c for c in bare if c["name"] == name)["detail"]


def test_read_gate_takes_a_probe_record_as_a_source_with_located_facts(tmp_path: Path):
    """A probe is not one line of summary. Its record is a source of the notes: a section headed by the record's
    path, one item per fact the command showed, each quoted from the record at its line. Seen live on 2026-10-02:
    a reader ran twenty probes and wrote twenty lines, where another wrote 139 located facts out of twelve."""
    name = "every probe record is a source section of the notes"
    none = "## Probes\n\nnone: the material is one text file; nothing in it can be run.\n"
    entry = "## Probes\n\n- Does the tool accept an empty list? Exit code 2. `output/probes/empty-list.txt`\n"
    section = (
        "## output/probes/empty-list.txt\n\n"
        '- An empty list is refused. Quote: "error: empty list" `output/probes/empty-list.txt:2`\n'
        '- The command exits with 2. Quote: "exit 2" `output/probes/empty-list.txt:3`\n\n'
    )

    def case(sub: str, change) -> list[dict]:
        record = tmp_path / sub / "stages/read/output/probes/empty-list.txt"
        record.parent.mkdir(parents=True)
        record.write_text("$ tool --list ''\nerror: empty list\nexit 2\n", encoding="utf-8")
        return _reader_case(tmp_path / sub, change)

    summary_only = case("a", lambda t: t.replace(none, entry))
    failed = next(c for c in summary_only if c["name"] == name)
    assert not failed["passed"] and "no section of the notes is headed by this record" in failed["detail"]
    assert all(c["passed"] for c in case("b", lambda t: t.replace(none, section + entry)))
    # a heading that is the record's path without `output/` is still a source, not the list of probes
    short = section.replace("## output/probes/", "## probes/").replace("`output/probes/", "`probes/")
    assert all(c["passed"] for c in case("c", lambda t: t.replace(none, short + entry)))
    # and what it quotes is looked up in the record like any other quote
    misquoted = case("d", lambda t: t.replace(none, section.replace("exit 2", "exit 0") + entry))
    wrong = next(c for c in misquoted if c["name"] == "every quote stands at its stated location")
    assert not wrong["passed"] and "empty-list.txt:3" in wrong["detail"]
    assert all(c["passed"] for c in _reader_case(tmp_path / "e"))  # no probe, no section asked for


def test_read_gate_asks_a_contradiction_for_two_texts_at_their_places(tmp_path: Path):
    """A contradiction is shown, not told: the texts that disagree, each quoted, each with its location. The order
    of quote and location is free, and a quote may hold double quotes itself."""
    name = "every contradiction shows two texts at their places"
    none = "## Contradictions\nnone\n"
    both = (
        "## Contradictions\n"
        '1. How often an upload is retried. `context/sample.txt:2`: "A failed upload is retried at most three times."'
        ' against "A response with status 503 is always retried." `context/sample.txt:6`\n'
    )
    assert all(c["passed"] for c in _reader_case(tmp_path / "a", lambda t: t.replace(none, both)))
    nested = (
        "## Contradictions\n"
        "1. How often an upload is retried.\n"
        '   - Text A: "A failed upload is retried at most three times." `context/sample.txt:2`\n'
        '   - Text B: "A response with status 503 is always retried." `context/sample.txt:6`\n'
    )
    assert all(c["passed"] for c in _reader_case(tmp_path / "b", lambda t: t.replace(none, nested)))
    one = both.replace(' against "A response with status 503 is always retried." `context/sample.txt:6`', "")
    told = next(c for c in _reader_case(tmp_path / "c", lambda t: t.replace(none, one)) if c["name"] == name)
    assert not told["passed"] and "fewer than two texts stand at a stated location" in told["detail"]
    moved = both.replace("`context/sample.txt:6`", "`context/sample.txt:1`")
    assert not next(c for c in _reader_case(tmp_path / "d", lambda t: t.replace(none, moved)) if c["name"] == name)[
        "passed"
    ]
    beyond = both.replace("`context/sample.txt:6`", "`context/sample.txt:60`")
    out_of_file = next(c for c in _reader_case(tmp_path / "e", lambda t: t.replace(none, beyond)) if c["name"] == name)
    assert "the file has 9 lines" in out_of_file["detail"]


def test_read_gate_reads_a_quote_that_holds_quotes_in_a_contradiction(tmp_path: Path):
    from harness.gates import read

    (tmp_path / "a.md").write_text('title\nversion: "3.0"\n', encoding="utf-8")
    (tmp_path / "b.md").write_text("The release is 3.0.1, as the origin file says.\n", encoding="utf-8")
    body = (
        '1. The version. `a.md:2`: "version: "3.0"" against `b.md:1`: "The release is 3.0.1, as the origin file says."'
    )
    assert read.unsupported(body, [tmp_path]) == []
    assert read.unsupported("none", [tmp_path]) == []
    assert read.own("probes") and read.own("probes (commands run)") and not read.own("probes/p1.txt")
    assert read.own("contradictions", "contradictions") and not read.own("coverage", "contradictions")


def test_read_gate_ignores_opinion_words_inside_a_quote(tmp_path: Path):
    quoted = _reader_case(tmp_path, lambda t: t + '\n- Extra. Quote: "it seems to be retried" `missing/file.txt:1`\n')
    assert next(c for c in quoted if c["name"].startswith("no opinion"))["passed"]


# --- wave 1 of the fixes of 2026-10-04: a gate opens nothing outside the stage and returns no text from there ---


def test_the_read_gate_opens_no_location_outside_its_bases_and_no_closed_path(run: Path, tmp_path: Path):
    """03/F06: every base was joined with the location, so `..` left it and an absolute path replaced it, and the
    file's length and whether a text stood at a line came back to the session. A path the stage's type may not read
    (its repo_deny) is not opened either."""
    from harness.gates import read

    root = tmp_path / "repo"
    secret = tmp_path / "outside" / "secret.txt"
    put(tmp_path, {"outside/secret.txt": "".join(f"token-{n}\n" for n in range(1, 8))})
    put(root, {"context/sample.txt": "one\ntwo\n", "docs/handoff/note.md": "CLOSED NOTE\n",
               "docs/roles/need-to-know.yaml": (ROOT / "docs/roles/need-to-know.yaml").read_text(encoding="utf-8")})  # fmt: skip
    put(run, {"manifest.json": {"stages": [{"id": "read", "role_type": "reader"}]}})
    sd = run / "stages/read"
    cases = {"`../outside/secret.txt:99`": "x", f"`{secret}:3`": "token-3", f"`{secret}:4`": "token-3",
             "`docs/handoff/note.md:1`": "CLOSED NOTE", "`docs/handoff/note.md:9`": "CLOSED NOTE"}  # fmt: skip
    entries = "".join(f'- e{n}. Quote: "{q} is quoted here" {loc}\n' for n, (loc, q) in enumerate(cases.items()))
    put(sd, {"output/notes.md": f"## context/sample.txt\n\n{entries}\n## Contradictions\nnone\n## Probes\nnone\n"
             "## Coverage\nall\n", "output/questions.md": "none\n"})  # fmt: skip
    found = {c["name"]: c for c in read.checks(root, run, sd)}
    detail = found["every quote stands at its stated location"].get("detail", "")
    assert "the file has" not in detail and "not at that place" not in detail
    assert read.opened(root, "../outside/secret.txt") is None and read.opened(root, str(secret)) is None
    assert read.opened(root, "docs/handoff/note.md", ["docs/handoff/**"]) is None
    assert read.opened(root, "context/sample.txt", ["docs/handoff/**"]) == ["one", "two"]
    # the closed path in another checkout, a link out of the base or onto a closed path, and `..` that stays inside
    put(root, {".claude/worktrees/other/docs/handoff/note.md": "CLOSED COPY\n"})
    (root / "context/out.txt").symlink_to(secret)
    (root / "context/handoff.md").symlink_to(root / "docs/handoff/note.md")
    closed = read.closed_paths(root, run, sd)
    assert "docs/handoff/**" in closed and read.closed_paths(root, run, run / "stages/plan") == []  # not in the run
    for rel in (".claude/worktrees/other/docs/handoff/note.md", "context/out.txt", "context/handoff.md"):
        assert read.opened(root, rel, closed) is None, rel
    assert read.opened(root, "context/../context/sample.txt", closed) == ["one", "two"]


def test_a_file_of_a_stage_that_is_a_link_out_of_it_is_not_read(run: Path, tmp_path: Path):
    """03/F32 and item 7d: `text` followed a link out of the stage directory and a check put the first lines of what
    it found into its detail, which reaches the session through poll's resume message and the stop hook."""
    from harness import gates
    from harness.gates import plan, research

    outside = tmp_path / "closed.txt"
    outside.write_text("- id: plan  # secret note\n", encoding="utf-8")
    secret_json = tmp_path / "closed.json"
    secret = {"tasks": "SECRET-JSON", "summary": "SECRET-JSON", "status": "escalated"}
    secret_json.write_text(json.dumps(secret), encoding="utf-8")
    sd = run / "stages/research"
    put(sd, {"output/questions.md": "none\n"})
    (sd / "output/findings.md").symlink_to(outside)
    (sd / "result.json").symlink_to(secret_json)
    (sd / "tasks.json").symlink_to(secret_json)
    assert _common.text(sd, "output/findings.md") == "" and _common.result(sd) == {}
    shown = json.dumps(research.findings_checks(sd) + gates.common_checks(ROOT, run, sd, "research"))
    shown += json.dumps(plan.tasks_checks(ROOT, sd)[0])
    assert "secret note" not in shown and "SECRET-JSON" not in shown
    assert not next(c for c in gates.common_checks(ROOT, run, sd, "research") if c["name"] == "result.json exists")[
        "passed"
    ]
    # a link is no file of the stage wherever it points, and neither is a path that leaves the stage directory
    put(run, {"brief.md": "SECRET BRIEF\n"})
    put(tmp_path, {"linked/x.md": "SECRET LINKED\n"})
    (sd / "output/inside.md").symlink_to(sd / "output/questions.md")
    (sd / "output/dir").symlink_to(tmp_path / "linked", target_is_directory=True)
    assert _common.stage_file(sd, "output/questions.md") == sd / "output/questions.md"
    refused = ["output/inside.md", "output/dir/x.md", "../../brief.md", str(outside), "output", "", "absent.md"]
    assert [rel for rel in [*refused, "a" * 300] if _common.stage_file(sd, rel) is not None] == []  # 300: OSError
    assert not [name for name, body in _common.stage_texts(sd) if "SECRET" in body or name != "output/questions.md"]
    # what a pack.md that is a link names is another file's material: it is not read
    put(tmp_path, {"other-pack.md": "# Knowledge pack\n\n# Material\n\n### docs/SECRET-NAME.md\n\n1\tx\n"})
    (sd / "pack.md").symlink_to(tmp_path / "other-pack.md")
    assert _common.material_files(sd) == [] and "docs/SECRET-NAME.md" not in _common.prompt_files(sd)
    # the verdict takes no status from the linked result: no `escalate` read from a file outside the stage
    root = tmp_path / "repo"
    shutil.copytree(ROOT / "schemas", root / "schemas")
    put(tmp_path / "runs", {".harness-runs": ""})  # the runs root of `root` is the one that holds `run`
    verdict = gates.run_gate(root, run.name, "research", None)
    assert verdict["next"] == "retry" and "SECRET" not in json.dumps(verdict)


def test_the_write_gate_records_its_checks_over_the_sandboxs_empty_file(tmp_path: Path):
    """The sandbox leaves an empty, read-only checks.json in a writer's stage directory (the mount point of its
    denyWrite rule): the gate's record replaces it."""
    from harness.gates import write

    sd = tmp_path / "stage"
    sd.mkdir()
    (sd / "checks.json").write_text("", encoding="utf-8")
    (sd / "checks.json").chmod(0o444)
    write.record_checks(sd, [{"name": "suite", "passed": True}])
    assert json.loads((sd / "checks.json").read_text(encoding="utf-8"))["checks"][0]["exit_code"] == 0


def test_the_gate_takes_a_checks_json_only_as_the_launcher_copied_it(run: Path):
    """01/F17: the gate took any input checks.json as what the harness ran; a verifier could chmod its copy and
    rewrite exit 1 as 0. A copy counts only with the sha256 the launcher recorded in `<run>/_access/`."""
    import hashlib

    real = json.dumps({"schema_version": 1, "checks": [{"command": "uv run pytest -q", "exit_code": 1}]})
    put(run / "stages/write/01", {"checks.json": real})
    sd = run / "stages/verify"
    put(sd, {"input/work/01/checks.json": real})
    index = [{"as": "work/01/checks.json", "source": str(run / "stages/write/01/checks.json"),
              "sha256": hashlib.sha256(real.encode()).hexdigest()}]  # fmt: skip
    put(run / "_access", {"verify.inputs.json": index})
    assert [r["exit_code"] for r in _common.harness_runs(sd)] == [1]
    (sd / "input/work/01/checks.json").write_text(real.replace('"exit_code": 1', '"exit_code": 0'), encoding="utf-8")
    assert [r["exit_code"] for r in _common.harness_runs(sd)] == [1]  # the source, unchanged, gives the record
    put(sd, {"input/work/02/checks.json": real.replace('"exit_code": 1', '"exit_code": 0')})  # no input of the stage
    assert [r["exit_code"] for r in _common.harness_runs(sd)] == [1]
    # a copy replaced by a link, then the source changed as well, an index entry without its source, no index at all
    forged = run / "forged.json"
    forged.write_text(real.replace('"exit_code": 1', '"exit_code": 0'), encoding="utf-8")
    (sd / "input/work/01/checks.json").unlink()
    (sd / "input/work/01/checks.json").symlink_to(forged)
    assert [r["exit_code"] for r in _common.harness_runs(sd)] == [1]  # the link is not read; the source holds
    (run / "stages/write/01/checks.json").write_text(forged.read_text(encoding="utf-8"), encoding="utf-8")
    assert _common.harness_runs(sd) == []  # neither holds what the launcher copied
    put(run / "_access", {"verify.inputs.json": [{k: v for k, v in index[0].items() if k != "source"}]})
    assert _common.harness_runs(sd) == []
    (run / "_access/verify.inputs.json").unlink()
    (sd / "input/work/01/checks.json").unlink()
    put(sd, {"input/work/01/checks.json": real})
    assert sorted(r["exit_code"] for r in _common.harness_runs(sd)) == [0, 1]  # a run without an index: as before


def by_name(checks: list[dict]) -> dict[str, bool]:
    return {c["name"]: c["passed"] for c in checks}


def head(repo: Repo, rev: str = "main") -> str:
    args = ["git", "-C", str(repo.root), "rev-parse", rev]
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout.strip()


GOOD_CRITIQUE = (
    "| No. | Location | Finding | Source | Severity |\n| --- | --- | --- | --- | --- |\n"
    "| 1 | `plan.md:3` | the guard reads the command's text | `python3 probe.py` exit 0 | blocks |\n"
    "\nCoverage: brief.md, plan.md, tasks.json; T001 T002 read.\n"
)
PROVEN = {"claim": "attack#1: `sh -c` passes the guard", "how_checked": "ran", "command": "python3 probe.py",
          "exit_code": 0}  # fmt: skip
ATTACK_CHECKS = (
    "result.json proposes accept or revise",
    "revise names a blocks or must fix finding, accept none",
    "every blocks or must fix finding has its evidence entry in result.json",
    "output/tests/ holds attack tests under their repository paths",
    "every attack test is a new file a writer may add",
    "every task of the plan is named in the critique",
    "output/summary.md is a one-page summary in English",
)


def attack_dir(repo: Repo, run: Path, decision="revise", critique=GOOD_CRITIQUE, summary="The plan changes the guard.\n",
               tests=("tests/test_attack_x.py",), evidence=(PROVEN,)) -> Path:  # fmt: skip
    put(run, {"manifest.json": {"base_commit": head(repo)}})
    sd = run / "stages/attack"
    files = {
        "input/plan/tasks.json": {"tasks": [{"id": "T001"}, {"id": "T002"}]},
        "output/critique.md": critique,
        "output/summary.md": summary,
        "result.json": res(
            stage="attack",
            role_type="critic",
            evidence=list(evidence),
            verdict={"decision": decision, "reasons": ["attack#1"]},
        ),
    }
    put(sd, {**files, **{f"output/tests/{t}": "def test_x():\n    assert True\n" for t in tests}})
    return sd


def test_the_attack_gate_takes_a_proven_revise_with_new_tests_and_an_english_summary(repo, run):
    from harness.gates import attack

    got = by_name(attack.checks(repo.root, run, attack_dir(repo, run)))
    assert all(got[name] for name in ATTACK_CHECKS), {n: got[n] for n in ATTACK_CHECKS}


@pytest.mark.parametrize(
    ("kw", "failing"),
    [({"decision": "accept"}, "revise names a blocks or must fix finding, accept none"),
     ({"decision": "reject"}, "result.json proposes accept or revise"),
     ({"evidence": ()}, "every blocks or must fix finding has its evidence entry in result.json"),
     ({"evidence": ({**PROVEN, "claim": "the guard"},)}, "every blocks or must fix finding has its evidence entry in result.json"),
     ({"tests": ()}, "output/tests/ holds attack tests under their repository paths"),
     ({"tests": ("tests/helpers.py", "tests/conftest.py")}, "output/tests/ holds attack tests under their repository paths"),
     ({"tests": ("tests/test_app.py",)}, "every attack test is a new file a writer may add"),
     ({"tests": (".claude/tests/test_x.py",)}, "every attack test is a new file a writer may add"),
     ({"summary": "The plan changes the guard " + chr(0x10D0) + ".\n"}, "output/summary.md is a one-page summary in English"),
     ({"summary": "a" * 6001}, "output/summary.md is a one-page summary in English"),
     ({"summary": " \n"}, "output/summary.md is a one-page summary in English"),
     ({"critique": GOOD_CRITIQUE.replace("T002", "")}, "every task of the plan is named in the critique")],
)  # fmt: skip
def test_the_attack_gate_names_what_is_missing(repo, run, kw, failing):
    from harness.gates import attack

    assert by_name(attack.checks(repo.root, run, attack_dir(repo, run, **kw)))[failing] is False


def test_an_attack_without_tests_passes_with_its_reason(repo, run):
    from harness.gates import attack

    critique = GOOD_CRITIQUE + "\nNo attack test: the plan changes documents only.\n"
    sd = attack_dir(repo, run, critique=critique, tests=())
    assert by_name(attack.checks(repo.root, run, sd))["output/tests/ holds attack tests under their repository paths"]


VERIFY_REPORT = "1. T001 works\n\nResult: refuted — `python3 x.py` exit 1\n\n2. T002 holds\n\nResult: confirmed\n\n## Beyond the claims\nnone\n"  # fmt: skip
PROOFS = ("the verdict proposal is accept, revise or reject", "revise or reject rests on a refuted entry, accept on none",
          "every refuted entry has its evidence entry in result.json")  # fmt: skip


@pytest.mark.parametrize(
    ("decision", "claim", "failing"),
    [("revise", "verify#1: a folder is made", []),
     ("reject", "verify#1: a folder is made", []),
     ("accept", "verify#1: a folder is made", [PROOFS[1]]),
     ("revise", "a folder is made", [PROOFS[2]]),
     ("replan", "verify#1: a folder is made", [PROOFS[0], PROOFS[1]])],
)  # fmt: skip
def test_a_verifiers_proposal_rests_on_proven_refuted_entries(run, decision, claim, failing):
    sd = run / "stages/verify"
    ev = [{"claim": claim, "how_checked": "ran", "command": "python3 x.py", "exit_code": 1}]
    put(sd, {"output/report.md": VERIFY_REPORT, "result.json": res(evidence=ev, verdict={"decision": decision, "reasons": ["verify#1"]})})  # fmt: skip
    got = by_name(importlib.import_module("harness.gates.verify").checks(ROOT, run, sd))
    assert [n for n in PROOFS if not got[n]] == failing


def test_a_report_whose_entry_numbers_repeat_is_refused(run):
    """A numbered step at the start of a line inside an entry reads as an entry of its own, and the gate and the loop
    would each take another entry 1: the gate refuses a number that repeats, so that both read one report alike."""
    sd = run / "stages/verify"
    report = ("1. T001 refuses a link\n\nResult: refuted — `python3 x.py` exit 1\n\nSteps I ran:\n"
              "1. ran x.py, confirmed it fails\n\n2. T002 refuses `..`\n\nResult: refuted — `python3 y.py` exit 1\n\n"
              "## Beyond the claims\nnone\n")  # fmt: skip
    ev = [{"claim": "verify#1 verify#2", "how_checked": "ran", "command": "python3 x.py", "exit_code": 1}]
    put(sd, {"output/report.md": report, "result.json": res(evidence=ev, verdict={"decision": "revise", "reasons": ["verify#1"]})})  # fmt: skip
    got = by_name(importlib.import_module("harness.gates.verify").checks(ROOT, run, sd))
    assert got["every entry has a number of its own"] is False


def test_a_wiki_check_proves_a_page_by_reading_it(run):
    """A statement of a page is checked by opening its source: no command, so no proof checks (gates/wikicheck.py)."""
    put(run / "stages/ingest", {"output/changes.md": "- created wiki/concepts/dedupe.md\n"})
    wc = run / "stages/wikicheck"
    ev = [{"claim": "page 1", "how_checked": "opened the source"}]
    put(wc, {"output/report.md": VERIFY_REPORT + "wiki/concepts/dedupe.md\n",
             "result.json": res(evidence=ev, verdict={"decision": "revise", "reasons": ["wikicheck#1"]})})  # fmt: skip
    names = by_name(importlib.import_module("harness.gates.wikicheck").checks(ROOT, run, wc))
    assert not set(PROOFS) & set(names)


def test_a_judge_may_replan_and_cite_a_place_in_the_change(run):
    from harness.gates import judge

    sd = run / "stages/judge"
    reasons = ["`input/work/changes.patch:12` reads the flag a second way"]
    put(sd, {"result.json": res(verdict={"decision": "replan", "reasons": reasons})})
    assert by_name(judge.checks(ROOT, run, sd))["verdict.decision is accept, revise, replan or reject"]
    assert by_name(judge.content_checks(ROOT, run, sd, None))["every reason names its source as `<stage>#<n>`"]


GIVEN = "def test_given():\n    assert True\n"
TRIAL_TEST = "def test_trial():\n    assert True\n"
TRIAL_PATCH = (
    "diff --git a/tests/test_trial.py b/tests/test_trial.py\nnew file mode 100644\n--- /dev/null\n"
    "+++ b/tests/test_trial.py\n@@ -0,0 +1,2 @@\n+def test_trial():\n+    assert True\n"
    "diff --git a/tests/test_app.py b/tests/test_app.py\n--- a/tests/test_app.py\n+++ b/tests/test_app.py\n"
    "@@ -1,2 +1,2 @@\n def test_a():\n-    assert True\n+    assert 1\n"
)


def sha(text: str | bytes) -> str:
    return hashlib.sha256(text if isinstance(text, bytes) else text.encode()).hexdigest()


def given_rig(repo: Repo, run: Path, given: str = GIVEN, trial: str | bytes = TRIAL_PATCH) -> Path:
    """A writer's stage whose inputs hold a critic's attack test and a planner's trial (the launcher's index too)."""
    sd = run / "stages/write"
    stages = [{"id": "plan", "role_type": "planner"}, {"id": "attack", "role_type": "critic"}]
    put(run, {"manifest.json": {"base_commit": head(repo), "stages": stages}})
    put(sd, {"input/attack/tests/tests/test_given.py": given, "input/attack/tests/escape.py": "X = 1\n"})
    (sd / "input/plan/trial/trial.patch").parent.mkdir(parents=True)
    (sd / "input/plan/trial/trial.patch").write_bytes(trial if isinstance(trial, bytes) else trial.encode())
    index = [
        {"source": str(run / "stages/attack/output/tests/tests/test_given.py"), "as": "attack/tests/tests/test_given.py",
         "sha256": sha(given)},
        {"source": str(run / "stages/attack/output/tests/../../../../outside/test_x.py"), "as": "attack/tests/escape.py",
         "sha256": sha("X = 1\n")},
        {"source": str(run / "stages/plan/output/trial/trial.patch"), "as": "plan/trial/trial.patch",
         "sha256": sha(trial)},
    ]  # fmt: skip
    put(run, {"_access/write.inputs.json": index})
    return sd


def critic_files(run: Path, sd: Path, files: dict[str, str]) -> None:
    """More of a critic's output/tests/ among a writer's inputs, each with its entry in the launcher's index."""
    index = json.loads((run / "_access/write.inputs.json").read_text(encoding="utf-8"))
    for rel, body in files.items():
        put(sd, {f"input/attack/tests/{rel}": body})
        index.append(
            {"source": str(run / "stages/attack/output/tests" / rel), "as": f"attack/tests/{rel}", "sha256": sha(body)}
        )
    put(run, {"_access/write.inputs.json": index})


def test_a_critic_test_under_a_folder_named_stages_is_protected(repo, run):
    """The stage of an input is the folder under the run's own stages/, not the last folder of that name in its path."""
    sd = given_rig(repo, run)
    critic_files(run, sd, {"tests/stages/test_s.py": GIVEN})
    given, problem = _common.protected_tests(repo.root, run, sd)
    assert problem == "" and given.get("tests/stages/test_s.py") == GIVEN.encode()


def test_a_trial_test_whose_name_is_no_utf8_is_read_as_the_file_system_reads_it(repo, run):
    """git gives the names in bytes; the gate reads them as the file system does (os.fsdecode), as changed_paths."""
    patch = (b'diff --git "a/tests/test_\\377.py" "b/tests/test_\\377.py"\nnew file mode 100644\n--- /dev/null\n'
             b'+++ "b/tests/test_\\377.py"\n@@ -0,0 +1,2 @@\n+def test_x():\n+    assert True\n')  # fmt: skip
    given, problem = _common.protected_tests(repo.root, run, given_rig(repo, run, trial=patch))
    assert problem == "" and given.get(os.fsdecode(b"tests/test_\xff.py")) == b"def test_x():\n    assert True\n"


def test_the_protected_tests_are_the_trials_new_tests_and_the_critics_attack_tests(repo, run):
    given, problem = _common.protected_tests(repo.root, run, given_rig(repo, run))
    assert problem == "" and given == {
        "tests/test_given.py": GIVEN.encode(),
        "tests/test_trial.py": TRIAL_TEST.encode(),
    }


def writer_result(repo: Repo, sd: Path) -> None:
    ev = [{"claim": "T001", "how_checked": "ran", "command": "pytest -q", "exit_code": 0}]
    put(sd, {"report.md": report_of(repo), "tasks.json": tasks({"passes": True, "evidence": "pytest -q: 1 passed"}),
             "result.json": res(summary="branch work-1", evidence=ev, role_type="writer")})  # fmt: skip


GIVEN_ON_BRANCH = "the plan's and the critic's tests are on the branch as given"
GIVEN_RAN = "the plan's and the critic's tests run and pass as given"


def test_the_write_gate_names_a_protected_test_the_branch_changed(repo, run):
    sd = given_rig(repo, run)
    repo.commit_and_return_to_main({"tests/test_given.py": GIVEN, "tests/test_trial.py": TRIAL_TEST}, "test: given")
    writer_result(repo, sd)
    write = importlib.import_module("harness.gates.write")
    assert by_name(write.checks(repo.root, run, sd, suite=False))[GIVEN_ON_BRANCH]
    repo.git("checkout", "-q", "work-1")
    repo.commit_and_return_to_main({"tests/test_given.py": "def test_given():\n    pass\n"}, "test: weaker")
    writer_result(repo, sd)
    got = next(c for c in write.checks(repo.root, run, sd, suite=False) if c["name"] == GIVEN_ON_BRANCH)
    assert not got["passed"] and "tests/test_given.py" in got["detail"]


WEAK_GIVEN = "def test_given():\n    pass\n"
WEAK_TRIAL = TRIAL_PATCH.replace("+    assert True\n", "+    pass\n", 1)


@pytest.mark.parametrize(
    ("copy", "changed", "on_branch", "source"),
    [("attack/tests/tests/test_given.py", WEAK_GIVEN, {"tests/test_given.py": WEAK_GIVEN}, True),
     ("attack/tests/tests/test_given.py", WEAK_GIVEN, {"tests/test_given.py": WEAK_GIVEN}, False),
     ("plan/trial/trial.patch", WEAK_TRIAL, {"tests/test_trial.py": "def test_trial():\n    pass\n"}, False)],
)  # fmt: skip
def test_a_protected_test_counts_only_as_the_launcher_copied_it(repo, run, copy, changed, on_branch, source):
    """The write gate runs outside the sandbox: a writer that changes its copy under input/ and its branch alike does
    not pass, as only the bytes with the sha256 of the launcher's index count, the copy's or else the source's."""
    sd = given_rig(repo, run)
    if source:
        put(run / "stages/attack", {"output/tests/tests/test_given.py": GIVEN})
    (sd / "input" / copy).write_text(changed, encoding="utf-8")
    files = {"tests/test_given.py": GIVEN, "tests/test_trial.py": TRIAL_TEST, **on_branch}
    repo.commit_and_return_to_main(files, "test: given")
    writer_result(repo, sd)
    write = importlib.import_module("harness.gates.write")
    got = next(c for c in write.checks(repo.root, run, sd, suite=False) if c["name"] == GIVEN_ON_BRANCH)
    assert not got["passed"] and Path(copy).name in got["detail"]


@pytest.mark.parametrize(
    ("files", "ran", "kept"),
    [({}, True, True),
     ({"conftest.py": "import pytest\n\n\ndef pytest_collection_modifyitems(items):\n    for i in items:\n"
       "        if 'given' in i.nodeid:\n            i.add_marker(pytest.mark.skip(reason='no'))\n"}, True, True),
     ({"tests/test_given.py": "def test_other():\n    assert True\n"}, True, False)],
)  # fmt: skip
def test_the_write_gate_runs_the_protected_tests_as_given_and_by_name(repo, run, monkeypatch, files, ran, kept):
    """The given tests go over the branch's copies and run once more by name in the base's configuration: a
    conftest.py of the branch that skips them in its own suite cannot keep them from running there, and a branch that
    replaces one is named by the check of its copies."""
    monkeypatch.setattr(_common, "TEST_CMD", [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"])
    sd = given_rig(repo, run)
    repo.commit_and_return_to_main({"tests/test_given.py": GIVEN, "tests/test_trial.py": TRIAL_TEST, **files}, "t")
    writer_result(repo, sd)
    got = by_name(importlib.import_module("harness.gates.write").checks(repo.root, run, sd))
    assert (got[GIVEN_RAN], got[GIVEN_ON_BRANCH]) == (ran, kept)
    assert got[f"`{' '.join(_common.TEST_CMD)}` passes on the branch"]


SUPPORT = {"tests/conftest.py": "import pytest\n\n\n@pytest.fixture\ndef one():\n    return 1\n",
           "tests/helpers.py": "ONE = 1\n", "tests/data/case.json": "{}\n"}  # fmt: skip


def test_a_given_file_that_is_no_test_module_goes_over_the_branch_and_is_not_run_by_name(repo, run, monkeypatch):
    """A conftest.py, a helper or a data file among the given files is kept as given, and only the test modules run
    by name: pytest collects no test case from the others, and a check that waited for one would never pass."""
    monkeypatch.setattr(_common, "TEST_CMD", [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"])
    uses = "def test_given(one):\n    assert one == 1\n"
    sd = given_rig(repo, run, given=uses)
    critic_files(run, sd, SUPPORT)
    repo.commit_and_return_to_main({"tests/test_given.py": uses, "tests/test_trial.py": TRIAL_TEST, **SUPPORT}, "t")
    writer_result(repo, sd)
    got = by_name(importlib.import_module("harness.gates.write").checks(repo.root, run, sd))
    assert got[GIVEN_ON_BRANCH] and got[GIVEN_RAN]


def test_a_given_test_the_bases_python_files_leave_out_still_runs_by_name(repo, run, monkeypatch):
    """pytest collects a file named on its command line whatever `python_files` says: a given test named as pytest
    names tests runs by name where the base's configuration names other files, and its failure is seen there."""
    monkeypatch.setattr(_common, "TEST_CMD", [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"])
    repo.git("checkout", "-q", "main")
    put(repo.root, {"pytest.ini": "[pytest]\npython_files = check_*.py\n"})
    repo.git("add", "-A")
    repo.git("commit", "-qm", "build: the project's test names")
    repo.git("checkout", "-qB", "work-1")
    failing = "def test_given():\n    assert False\n"
    sd = given_rig(repo, run, given=failing)
    repo.commit_and_return_to_main({"tests/test_given.py": failing, "tests/test_trial.py": TRIAL_TEST}, "t")
    writer_result(repo, sd)
    got = by_name(importlib.import_module("harness.gates.write").checks(repo.root, run, sd))
    assert got[GIVEN_ON_BRANCH] and got[GIVEN_RAN] is False


ASYNC_GIVEN = "import pytest\n\n\n@pytest.mark.anyio\nasync def test_given():\n    assert True\n"


@pytest.mark.parametrize(("locked", "ran"), [(True, True), (False, False)])
def test_the_protected_run_loads_the_plugins_of_the_bases_lock_and_no_other(repo, run, monkeypatch, locked, ran):
    """No plugin loads by itself in the protected run (one the work installs could report a failing given test as
    passed); those of the base's dependency set (uv.lock) are named with -p, so a given test that needs one runs."""
    pytest.importorskip("anyio")
    monkeypatch.setattr(_common, "TEST_CMD", [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"])
    lock = 'version = 1\n\n[[package]]\nname = "anyio"\nversion = "4.4.0"\n'
    repo.git("checkout", "-q", "main")
    put(repo.root, {"uv.lock": lock if locked else "version = 1\n"})
    repo.git("add", "-A")
    repo.git("commit", "-qm", "build: lock")
    repo.git("checkout", "-qB", "work-1")
    sd = given_rig(repo, run, given=ASYNC_GIVEN)
    files = {"tests/test_given.py": ASYNC_GIVEN, "tests/test_trial.py": TRIAL_TEST, "uv.lock": lock}
    repo.commit_and_return_to_main(files, "t")
    writer_result(repo, sd)
    got = by_name(importlib.import_module("harness.gates.write").checks(repo.root, run, sd))
    assert got[GIVEN_ON_BRANCH] and got[GIVEN_RAN] is ran


def test_a_file_where_a_given_tests_folder_should_be_fails_the_gate_and_does_not_break_it(repo, run):
    """The branch holds a file at `tests/new`, a given test lives at `tests/new/test_n.py`: the gate names what it could
    not place instead of raising (an exception in a gate stops the poll of every run)."""
    sd = given_rig(repo, run)
    critic_files(run, sd, {"tests/new/test_n.py": GIVEN})
    files = {"tests/test_given.py": GIVEN, "tests/test_trial.py": TRIAL_TEST, "tests/new": "x\n"}
    repo.commit_and_return_to_main(files, "t")
    writer_result(repo, sd)
    got = {c["name"]: c for c in importlib.import_module("harness.gates.write").checks(repo.root, run, sd)}
    suite = got[f"`{' '.join(_common.TEST_CMD)}` passes on the branch"]
    assert not got[GIVEN_ON_BRANCH]["passed"] and not suite["passed"] and "tests/new" in suite["detail"]


def test_a_protected_test_is_never_written_through_a_link_the_branch_holds(repo, run, monkeypatch, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    sd = given_rig(repo, run)
    repo.git("rm", "-rq", "tests")
    (repo.root / "tests").symlink_to(outside)
    repo.commit_and_return_to_main({}, "chore: tests elsewhere")
    writer_result(repo, sd)
    got = next(
        c for c in importlib.import_module("harness.gates.write").checks(repo.root, run, sd) if c["name"] == GIVEN_RAN
    )
    assert not got["passed"] and "link" in got["detail"] and not any(outside.iterdir())


def test_a_protected_path_is_never_read_as_an_option():
    """A path is given to pytest after `--`, and none of its parts may start with a dash."""
    assert not _common.given_path("-p/tests/test_x.py") and not _common.given_path("tests/--co/test_x.py")
    assert _common.given_path("tests/test_x.py")


FORGE = (
    "import pytest\n\n\n@pytest.hookimpl(hookwrapper=True)\ndef pytest_runtest_makereport(item, call):\n"
    "    outcome = yield\n    outcome.get_result().outcome = 'passed'\n"
)


def test_the_protected_tests_run_with_the_bases_configuration(repo, run, monkeypatch):
    """A conftest.py the branch adds could report a failing given test as passed: the given tests run once more in a
    checkout whose conftest.py files and pytest configuration are the base's."""
    monkeypatch.setattr(_common, "TEST_CMD", [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"])
    reads = "from pathlib import Path\n\n\ndef test_given():\n    assert Path('src/app.py').read_text() == 'A = 1\\n'\n"
    sd = given_rig(repo, run, given=reads)
    files = {
        "tests/test_given.py": reads,
        "tests/test_trial.py": TRIAL_TEST,
        "src/app.py": "A = 2\n",
        "conftest.py": FORGE,
    }
    repo.commit_and_return_to_main(files, "feat: break it and hide it")
    writer_result(repo, sd)
    got = by_name(importlib.import_module("harness.gates.write").checks(repo.root, run, sd))
    assert got[GIVEN_ON_BRANCH] and got[GIVEN_RAN] is False


def test_a_skip_or_a_failure_of_a_given_test_is_read_from_its_test_case():
    xml = (
        '<testsuites><testsuite><testcase classname="tests.test_given" name="test_a"/>'
        '<testcase classname="tests.test_given" name="test_b"><skipped message="x"/></testcase>'
        '<testcase classname="tests.sub.test_more.TestX" name="test_c"/></testsuite></testsuites>'
    )
    files = ["tests/sub/test_more.py", "tests/test_given.py", "tests/test_none.py"]
    assert _common.given_missing(xml, files) == ["tests/test_given.py", "tests/test_none.py"]
    assert _common.given_missing("not xml", ["tests/test_given.py"]) == ["tests/test_given.py"]


def test_a_pytest_configuration_the_branch_adds_below_the_root_is_not_read(repo, run, monkeypatch):
    """pytest looks for its configuration from the common folder of the given files upwards: a `tests/pytest.ini` of
    the branch would load a plugin that reports the failing given test as passed. The protected run names the base's
    configuration with -c, and plugins installed by the work do not load by themselves."""
    monkeypatch.setattr(_common, "TEST_CMD", [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"])
    reads = "from pathlib import Path\n\n\ndef test_given():\n    assert Path('src/app.py').read_text() == 'A = 1\\n'\n"
    sd = given_rig(repo, run, given=reads)
    files = {"tests/test_given.py": reads, "tests/test_trial.py": TRIAL_TEST, "src/app.py": "A = 2\n",
             "tests/pytest.ini": "[pytest]\npythonpath = .\naddopts = -p forge\n", "tests/forge.py": FORGE}  # fmt: skip
    repo.commit_and_return_to_main(files, "feat: break it and hide it below the root")
    writer_result(repo, sd)
    got = by_name(importlib.import_module("harness.gates.write").checks(repo.root, run, sd))
    assert got[GIVEN_ON_BRANCH] and got[GIVEN_RAN] is False


def test_the_base_configuration_removes_a_conftest_of_another_case(repo):
    """A file system that ignores case reads `tests/Conftest.py` as `conftest.py`."""
    repo.commit_and_return_to_main({"tests/Conftest.py": FORGE}, "test: a conftest by another name")
    config = _common.base_config(repo.root, head(repo), "work-1")
    assert config["tests/Conftest.py"] is None


def test_the_protected_run_takes_the_bases_pytest_options_in_a_file_of_its_own(repo):
    """The options of the base's pyproject.toml go into an ini file the protected run names with -c; the branch's
    pyproject.toml (its dependencies, its workspace) stays as the branch has it."""
    repo.git("checkout", "-q", "main")
    put(
        repo.root,
        {"pyproject.toml": '[tool.pytest.ini_options]\ntestpaths = ["packages", "tests"]\nxfail_strict = true\n'},
    )
    repo.git("add", "-A")
    repo.git("commit", "-qm", "build: pytest options")
    config = _common.pytest_config(repo.root, head(repo))
    assert config == {
        ".harness-pytest.ini": b"[pytest]\ntestpaths =\n    packages\n    tests\nxfail_strict =\n    true\n"
    }
    assert _common.pytest_config(repo.root, head(repo, "HEAD~1")) == {".harness-pytest.ini": b"[pytest]\n"}
