"""Requirement 5 of specs/005-spec-writer-rule: the role catalogue (`harness catalog`) and `harness validate` refuse a
spec-writer type whose output sections include a data model, interfaces or tests; they belong to the planner.
(The other half of the requirement, the warning for a spec file over its size, is in test_docs_layers.py.)
Run: `uv run pytest -q packages/harness/tests/test_spec_writer_check.py`."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from harness import catalog
from harness.gates import spec as spec_gate

ROOT = Path(__file__).resolve().parents[3]
AGENT = ".claude/agents/spec-writer.md"
CONTRACT = "docs/roles/types/spec-writer.md"
TERMS = ["data model", "interfaces", "tests"]
# The two lines that list the spec's sections, as the files have them.
AGENT_LIST = "Intent; Requirements;"
CONTRACT_LIST = "intent, requirements,"
GATE = "the spec stage's gate (gates/spec.py `REQUIRED`)"
TAIL = "; a data model, interfaces and tests are the planner's, not a spec's"


@pytest.fixture
def make_root(tmp_path: Path):
    """A root that holds the role-type schema, a policy that limits no model, and the spec-writer's agent file and
    contract as the repository has them, each with the replacements given (old text -> new text)."""

    def make(agent: dict[str, str] | None = None, contract: dict[str, str] | None = None) -> Path:
        root = tmp_path / "repo"
        (root / "schemas").mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / "schemas" / "role-type.schema.json", root / "schemas")
        (root / "docs" / "roles" / "types").mkdir(parents=True, exist_ok=True)
        policy = root / "docs" / "roles" / "need-to-know.yaml"
        policy.write_text("schema_version: 1\ndefaults: {}\n", encoding="utf-8")
        (root / ".claude" / "agents").mkdir(parents=True, exist_ok=True)
        for rel, edits in ((AGENT, agent or {}), (CONTRACT, contract or {})):
            text = (ROOT / rel).read_text(encoding="utf-8")
            for old, new in edits.items():
                assert text.count(old) == 1, f"{rel}: the test's edit must hit the text once: {old!r}"
                text = text.replace(old, new)
            (root / rel).write_text(text, encoding="utf-8")
        return root

    return make


def returns(rel: str) -> str:
    """The `## Returns` section of a file of the repository: its heading to the next `## `."""
    return (ROOT / rel).read_text(encoding="utf-8").split("\n## Returns\n", 1)[1].split("\n## ", 1)[0]


def test_the_spec_writer_of_the_repository_returns_the_skeleton_and_is_not_refused():
    assert returns(AGENT).count("Intent; Requirements; Limits; Done; Out of scope") == 1
    assert returns(CONTRACT).count("intent, requirements, limits, done, out of scope") == 1
    assert [p for p in catalog.validate_types(ROOT) if p.startswith("spec-writer:")] == []


def test_the_planner_names_interfaces_and_tests_among_what_it_returns_and_the_check_leaves_it_alone():
    assert "interfaces" in returns(".claude/agents/planner.md").lower()
    assert "tests" in returns("docs/roles/types/planner.md").lower()
    assert [p for p in catalog.validate_types(ROOT) if p.startswith("planner:")] == []


def test_the_words_outside_returns_are_no_problem_for_the_spec_writer(make_root):
    """The instruction forbids the words (Purpose, Working method, What you never do) and only Returns lists output."""
    text = (ROOT / AGENT).read_text(encoding="utf-8")
    outside = text.replace(returns(AGENT), "").lower()
    assert all(term in outside for term in TERMS)
    assert catalog.validate_types(make_root()) == []


@pytest.mark.parametrize("term", TERMS)
def test_a_spec_writer_whose_agent_file_lists_a_planners_section_is_refused(make_root, term):
    named = term.capitalize()
    root = make_root(agent={AGENT_LIST: f"Intent; Requirements; {named};"})
    assert catalog.validate_types(root) == [f"spec-writer: {AGENT} `## Returns` names {named!r}{TAIL}"]


@pytest.mark.parametrize("term", TERMS)
def test_a_spec_writer_whose_contract_lists_a_planners_section_is_refused(make_root, term):
    root = make_root(contract={CONTRACT_LIST: f"intent, requirements, {term},"})
    assert catalog.validate_types(root) == [f"spec-writer: {CONTRACT} `## Returns` names {term!r}{TAIL}"]


def test_a_sentence_in_returns_that_asks_for_a_planners_section_is_refused_however_it_is_worded(make_root):
    root = make_root(agent={"- `result.json`.\n": "- A Data Model section that names the tables.\n- `result.json`.\n"})
    assert catalog.validate_types(root) == [f"spec-writer: {AGENT} `## Returns` names 'Data Model'{TAIL}"]


# V2: the pattern once read "data model" with exactly one space, so a hyphen or a wrapped line passed it.
DATA_MODEL_WORDINGS = [("data-model", "data-model"), ("data\n  model", "data model")]


@pytest.mark.parametrize(("wording", "reported"), DATA_MODEL_WORDINGS)
def test_a_hyphen_or_a_line_break_inside_data_model_in_the_agent_file_is_refused(make_root, wording, reported):
    root = make_root(agent={"- `result.json`.\n": f"- A {wording} section that names the tables.\n- `result.json`.\n"})
    assert catalog.validate_types(root) == [f"spec-writer: {AGENT} `## Returns` names {reported!r}{TAIL}"]


@pytest.mark.parametrize(("wording", "reported"), DATA_MODEL_WORDINGS)
def test_a_hyphen_or_a_line_break_inside_data_model_in_the_contract_is_refused(make_root, wording, reported):
    root = make_root(contract={CONTRACT_LIST: f"intent, requirements, {wording},"})
    assert catalog.validate_types(root) == [f"spec-writer: {CONTRACT} `## Returns` names {reported!r}{TAIL}"]


@pytest.mark.parametrize("rel", [AGENT, CONTRACT])
def test_a_spec_writer_file_without_a_returns_section_is_refused_so_the_check_never_reads_nothing(make_root, rel):
    edit = {"\n## Returns\n": "\n## Output\n"}
    root = make_root(**{"agent" if rel == AGENT else "contract": edit})
    assert catalog.validate_types(root) == [f"spec-writer: {rel} has no `## Returns` section"]


def test_a_spec_stage_gate_that_requires_a_planners_section_is_refused(make_root, monkeypatch):
    monkeypatch.setattr(spec_gate, "REQUIRED", [*spec_gate.REQUIRED, "interfaces", "tests"])
    assert catalog.validate_types(make_root()) == [
        f"spec-writer: {GATE} names 'interfaces'{TAIL}",
        f"spec-writer: {GATE} names 'tests'{TAIL}",
    ]


def test_every_place_that_names_one_is_a_problem_of_its_own(make_root):
    root = make_root(
        agent={AGENT_LIST: "Intent; Requirements; Interfaces;"}, contract={CONTRACT_LIST: "intent, tests,"}
    )
    assert catalog.validate_types(root) == [
        f"spec-writer: {AGENT} `## Returns` names 'Interfaces'{TAIL}",
        f"spec-writer: {CONTRACT} `## Returns` names 'tests'{TAIL}",
    ]


def test_the_role_catalogue_refuses_the_type_and_writes_nothing(make_root):
    root = make_root(agent={AGENT_LIST: "Intent; Requirements; Tests;"})
    out = catalog.write_catalog(root)
    assert out == {"ok": False, "problems": [f"spec-writer: {AGENT} `## Returns` names 'Tests'{TAIL}"]}
    assert not (root / "docs" / "generated").exists()
    assert catalog.write_catalog(make_root())["ok"] is True


def test_harness_validate_and_the_catalogue_report_the_refusal_on_the_repository_itself(monkeypatch):
    """The same entries the CLI runs, on the real files; the gate's list is the one thing a test may change in memory."""
    assert catalog.validate_repository(ROOT)["problems"] == []
    monkeypatch.setattr(spec_gate, "REQUIRED", [*spec_gate.REQUIRED, "tests"])
    refusal = f"spec-writer: {GATE} names 'tests'{TAIL}"
    out = catalog.validate_repository(ROOT)
    assert (out["ok"], out["problems"]) == (False, [refusal])
    assert catalog.write_catalog(ROOT) == {"ok": False, "problems": [refusal]}
