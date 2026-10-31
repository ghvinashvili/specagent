"""The plan fixer and the translator are role types (spec 3.2, answer 13a; manager-build Task 1): agent files the
harness accepts with one check rule per step, contracts, need-to-know rows, a description that selects each type for
its own work while the older types still select themselves, and their contract lines in docs/llms.txt."""

import re
from pathlib import Path

import pytest
import yaml
from harness import catalog, select
from harness.gates import steps

ROOT = Path(__file__).resolve().parents[3]
NEW = ("plan-fixer", "translator")
TITLES = {"plan-fixer": "Plan fixer", "translator": "Translator"}
AGENT_HEADINGS = [
    "## Purpose",
    "## Receives",
    "## Returns",
    "## Working method",
    "## When you stop",
    "## What you never do",
]


def test_both_types_load_with_their_model_class_and_the_harness_finds_no_problem_in_them():
    types = catalog.load_types(ROOT)
    assert {n: (types[n]["model"], types[n]["effort"]) for n in NEW} == {
        "plan-fixer": ("opus", "max"),
        "translator": ("sonnet", "max"),
    }
    assert [p for p in catalog.validate_types(ROOT) if p.split(":")[0] in NEW] == []
    assert [p for p in steps.problems(ROOT) if p.split(":")[0] in NEW] == []


@pytest.mark.parametrize("name", NEW)
def test_the_agent_file_and_the_contract_have_their_headings_and_one_check_rule_per_step(name):
    body = (ROOT / ".claude" / "agents" / f"{name}.md").read_text(encoding="utf-8").split("\n---\n", 1)[1]
    assert re.findall(r"(?m)^#{1,2} .*", body) == [f"# {TITLES[name]}", *AGENT_HEADINGS]
    method = body.split("\n## Working method\n", 1)[1].split("\n## ", 1)[0]
    numbered = re.findall(r"(?m)^\d+\. ", method)
    assert len(numbered) >= 3 and method.count("<!-- check: ") == len(numbered)
    contract = (ROOT / "docs" / "roles" / "types" / f"{name}.md").read_text(encoding="utf-8")
    headings = re.findall(r"(?m)^#{1,2} .*", contract)
    assert headings == [f"# {name} — contract", "## Receives", "## Returns", "## When it stops", "## Never"]


def test_need_to_know_lets_each_type_see_only_what_its_work_needs():
    types = yaml.safe_load((ROOT / "docs" / "roles" / "need-to-know.yaml").read_text(encoding="utf-8"))["types"]
    assert {n: {k: types[n][k] for k in ("may_receive", "outputs_of")} for n in NEW} == {
        "plan-fixer": {"may_receive": ["brief", "spec"], "outputs_of": ["planner", "critic", "verifier"]},
        "translator": {"may_receive": ["brief"], "outputs_of": ["writer", "synthesizer"]},
    }


@pytest.mark.parametrize(
    ("text", "role_type"),
    [
        ("answer the open findings on the written plan tasks before they are built", "plan-fixer"),
        ("render the finished report for a reader in another language", "translator"),
    ],
)
def test_a_request_for_the_work_selects_the_type(text, role_type):
    assert select.select_type(ROOT, text)["role_type"] == role_type


@pytest.mark.parametrize("name", ["planner", "critic", "writer", *NEW])
def test_each_types_own_use_when_sentence_still_selects_it(name):
    use_when = catalog.load_types(ROOT)[name]["description"].split("Use when: ", 1)[1].split(". ", 1)[0]
    assert select.select_type(ROOT, use_when)["role_type"] == name


def test_llms_txt_lists_both_contracts():
    lines = (ROOT / "docs" / "llms.txt").read_text(encoding="utf-8").splitlines()
    assert [n for n in NEW if f"- [{n}](roles/types/{n}.md): contract" not in lines] == []
