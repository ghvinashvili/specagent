"""harness map: one Mermaid flowchart per stage table, written to docs/generated/maps/<name>.md. No Claude, no
renderer."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest
import yaml
from harness import access, catalog, cli, stagemap

ROOT = Path(__file__).resolve().parents[3]
MAP_NAMES = ["default", "council", "fix", "intake", "learning", "research", "software-factory", "wiki-ingest"]
EDGE = re.compile(r"    (\w+) (-->|-\.->)(?:\|([^|]*)\|)? (\w+)")
NODE = re.compile(r'    (\w+)(\[\[|\[|\{)"(.*)"(\]\]|\]|\})')
SHAPES = {"[": ("stage", "]"), "{": ("decision", "}"), "[[": ("table", "]]")}


def make_root(tmp_path: Path) -> Path:
    """A temporary repository root with copies of the stage tables, the access table and the docs index."""
    root = tmp_path / "repo"
    (root / "docs" / "generated").mkdir(parents=True)
    shutil.copytree(ROOT / "docs" / "roles" / "pipelines", root / "docs" / "roles" / "pipelines")
    for rel in (
        "docs/roles/stages.yaml",
        "docs/roles/need-to-know.yaml",
        "docs/llms.txt",
        "docs/generated/role-types.md",
    ):
        shutil.copy(ROOT / rel, root / rel)
    return root


def _snapshot(directory: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted(directory.iterdir())}


def _table(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _row(stage_id: str, deps: list[str] | None = None, role_type: str = "writer", **more) -> dict:
    row = {"id": stage_id, "role_type": role_type, "mode": "bg", "approval": "none", **more}
    if deps:
        row["depends_on"] = deps
    return row


def _chain(n: int) -> dict:
    return {"version": 1, "stages": [_row(f"s{i}", [f"s{i - 1}"] if i else None) for i in range(n)]}


def _chart(name: str) -> str:
    return stagemap.flowchart(_table(stagemap.tables(ROOT)[name]), access.load_policy(ROOT))


def parse(chart: str) -> tuple[dict[str, tuple[str, list[str]]], list[tuple[str, str, str | None, str]]]:
    """The nodes {id: (shape, label lines)} and the edges [(from, solid|dashed, label, to)] of a map's flowchart;
    a line that is neither fails the test."""
    first, *rest = chart.splitlines()
    assert first == "flowchart TD"
    nodes, edges = {}, []
    for line in rest:
        if edge := EDGE.fullmatch(line):
            edges.append((edge[1], "dashed" if edge[2] == "-.->" else "solid", edge[3], edge[4]))
            continue
        node = NODE.fullmatch(line)
        assert node and SHAPES[node[2]][1] == node[4], line
        nodes[node[1]] = (SHAPES[node[2]][0], node[3].split("<br/>"))
    return nodes, edges


def test_tables_lists_default_first_then_pipelines_by_stem():
    assert list(stagemap.tables(ROOT)) == MAP_NAMES


SAMPLE = {
    "version": 1,
    "stages": [
        _row("research", role_type="researcher", parallel="per_task"),
        _row("write", ["research"]),
        _row("review", ["write"], role_type="critic", approval="human", returns_to={"stage": "write", "counter": "w"}),
        _row("judge", ["review"], role_type="judge", mode="print", approval="human"),
    ],
}

SAMPLE_CHART = """\
flowchart TD
    s1["research<br/>researcher<br/>per task"]
    s2["write<br/>writer"]
    s3["review<br/>critic<br/>blind reviewer"]
    h3{"human approval"}
    s4["judge<br/>judge<br/>one call, blind reviewer"]
    h4{"human approval"}
    s1 --> s2
    s2 --> s3
    s3 --> h3
    h3 -->|approved| s4
    s4 --> h4
    s3 -.->|revise| s2"""


def test_a_table_becomes_this_flowchart():
    assert stagemap.flowchart(SAMPLE, access.load_policy(ROOT)) == SAMPLE_CHART


def test_a_routing_table_leads_each_label_to_the_table_it_names():
    table = {
        "version": 1,
        "stages": [_row("digest"), _row("classify", ["digest"], role_type="classifier")],
        "routes": {"stage": "classify", "labels": {"feature": "software-factory", "other": "escalate"}},
    }
    assert stagemap.flowchart(table, access.load_policy(ROOT)) == (
        "flowchart TD\n"
        '    s1["digest<br/>writer"]\n'
        '    s2["classify<br/>classifier"]\n'
        '    r1[["software-factory"]]\n'
        '    r2[["escalate"]]\n'
        "    s1 --> s2\n"
        "    s2 -->|feature| r1\n"
        "    s2 -->|other| r2"
    )


@pytest.mark.parametrize("name", MAP_NAMES)
def test_every_stage_table_yields_a_map_of_its_stages_in_order(name):
    stages = _table(stagemap.tables(ROOT)[name])["stages"]
    nodes, edges = parse(_chart(name))
    box = {s["id"]: f"s{i}" for i, s in enumerate(stages, start=1)}
    leaves = {s["id"]: f"h{i}" if s.get("approval") == "human" else f"s{i}" for i, s in enumerate(stages, start=1)}
    boxes = [label[:2] for shape, label in nodes.values() if shape == "stage"]
    assert boxes == [[s["id"], s["role_type"]] for s in stages]  # who does what, in the order of the table
    arrows = [(leaves[d], box[s["id"]]) for s in stages for d in s.get("depends_on") or []]
    assert [(a, b) for a, kind, _, b in edges if kind == "solid" and b in box.values()] == arrows
    gates = [(box[s["id"]], leaves[s["id"]]) for s in stages if s.get("approval") == "human"]
    assert [(a, b) for a, _, _, b in edges if nodes[b][0] == "decision"] == gates
    back = [(box[s["id"]], box[s["returns_to"]["stage"]]) for s in stages if s.get("returns_to")]
    assert [(a, b) for a, kind, _, b in edges if kind == "dashed"] == back
    page = stagemap.render_map(ROOT, name)
    source = stagemap.tables(ROOT)[name].relative_to(ROOT).as_posix()
    assert page.startswith(f"# Stage map: {name}\n\nGenerated by `harness map` from `{source}`")
    assert page.count("```mermaid\n") == 1 and page.endswith(f"```mermaid\n{_chart(name)}\n```\n")


def test_a_human_gate_is_a_decision_node_after_its_stage():
    nodes, edges = parse(_chart("default"))
    assert {n: label for n, (shape, label) in nodes.items() if shape == "decision"} == {
        "h3": ["human approval"],
        "h6": ["human approval"],
    }
    assert nodes["s3"][1][0] == "attack" and nodes["s4"][1][0] == "write" and nodes["s6"][1][0] == "judge"
    assert ("s3", "solid", None, "h3") in edges and ("h3", "solid", "approved", "s4") in edges
    assert [e for e in edges if e[0] == "s3" and e[3] == "s4"] == []  # write starts after the human, not after attack
    assert ("s6", "solid", None, "h6") in edges and [e for e in edges if e[0] == "h6"] == []  # the run ends there


def test_the_tags_say_per_task_one_call_and_blind_reviewer():
    nodes, _ = parse(_chart("software-factory"))
    tags = {label[0]: label[2:] for shape, label in nodes.values() if shape == "stage"}
    assert tags["write"] == ["per task"] and tags["judge"] == ["one call, blind reviewer"]
    assert tags["research"] == [] and tags["accept"] == ["blind reviewer"]


def test_a_return_is_a_dashed_arrow_labelled_revise():
    _, edges = parse(_chart("default"))
    assert [e for e in edges if e[1] == "dashed"] == [
        ("s3", "dashed", "revise", "s2"),  # attack -> plan
        ("s5", "dashed", "revise", "s4"),  # verify -> write
        ("s6", "dashed", "revise", "s4"),  # judge -> write
    ]


def test_the_intake_map_routes_every_label():
    labels = _table(stagemap.tables(ROOT)["intake"])["routes"]["labels"]
    nodes, edges = parse(_chart("intake"))
    routed = [(label, nodes[b][1]) for a, _, label, b in edges if nodes[b][0] == "table"]
    assert routed == [(label, [target]) for label, target in labels.items()]
    assert {a for a, _, _, b in edges if nodes[b][0] == "table"} == {"s2"}  # all from classify


def test_a_stage_named_like_a_mermaid_keyword_keeps_a_safe_node_id():
    # `end` closes a block in Mermaid and `--` is an arrow: a node is named by its position, the label keeps the id
    table = {"version": 1, "stages": [_row("end"), _row("class", ["end"]), _row("a--b", ["class"])]}
    nodes, edges = parse(stagemap.flowchart(table, access.load_policy(ROOT)))
    assert {n: label[0] for n, (_, label) in nodes.items()} == {"s1": "end", "s2": "class", "s3": "a--b"}
    assert [(a, b) for a, _, _, b in edges] == [("s1", "s2"), ("s2", "s3")]


def test_a_quote_or_a_bar_in_a_label_becomes_an_entity_code():
    table = {"version": 1, "stages": [_row("a")], "routes": {"stage": "a", "labels": {'say "x" | y': "research"}}}
    chart = stagemap.flowchart(table, access.load_policy(ROOT))
    assert chart.splitlines()[-1] == "    s1 -->|say #quot;x#quot; #124; y| r1"


def test_stage_ranks_follow_the_longest_dependency_path():
    stages = [_row("a"), _row("b", ["a"]), _row("c", ["a", "b"])]
    assert stagemap.stage_ranks(stages) == {"a": 0, "b": 1, "c": 2}


def test_render_map_is_deterministic_and_ends_with_a_newline():
    for name in stagemap.tables(ROOT):
        first = stagemap.render_map(ROOT, name)
        assert first == stagemap.render_map(ROOT, name)
        assert first.endswith("```\n") and not first.endswith("\n\n")


def test_write_maps_then_check_maps_is_ok(tmp_path):
    root = make_root(tmp_path)
    out = stagemap.write_maps(root)
    assert out["ok"] is True and out["removed"] == []
    assert "docs/generated/maps/default.md" in out["written"] and len(out["written"]) == 8
    check = stagemap.check_maps(root)
    assert check == {"ok": True, "checked": list(stagemap.tables(root)), "stale": [], "missing": []}


def test_a_second_write_gives_the_same_bytes(tmp_path):
    root = make_root(tmp_path)
    stagemap.write_maps(root)
    first = _snapshot(root / stagemap.MAPS_DIR)
    stagemap.write_maps(root)
    assert _snapshot(root / stagemap.MAPS_DIR) == first


def test_a_changed_map_is_stale(tmp_path):
    root = make_root(tmp_path)
    stagemap.write_maps(root)
    path = stagemap.map_path(root, "council")
    path.write_text(path.read_text(encoding="utf-8").replace("planner", "writer", 1), encoding="utf-8")
    check = stagemap.check_maps(root)
    assert check["ok"] is False
    assert check["stale"] == ["docs/generated/maps/council.md"]


def test_a_deleted_map_is_missing(tmp_path):
    root = make_root(tmp_path)
    stagemap.write_maps(root)
    stagemap.map_path(root, "intake").unlink()
    check = stagemap.check_maps(root)
    assert check["ok"] is False
    assert check["missing"] == ["docs/generated/maps/intake.md"]


def test_a_file_no_table_produces_is_stale_and_write_removes_it(tmp_path):
    # the old form of the maps too: a project made before the maps were Mermaid gets them removed by `harness map`
    root = make_root(tmp_path)
    stagemap.write_maps(root)
    for name in ("old.md", "default.workflow.json"):
        (root / stagemap.MAPS_DIR / name).write_text("{}", encoding="utf-8")
    stale = ["docs/generated/maps/default.workflow.json", "docs/generated/maps/old.md"]
    assert stagemap.check_maps(root)["stale"] == stale
    out = stagemap.write_maps(root)
    assert out["removed"] == stale
    assert sorted(p.name for p in (root / stagemap.MAPS_DIR).iterdir()) == sorted(f"{n}.md" for n in MAP_NAMES)
    assert stagemap.check_maps(root)["ok"] is True


def test_check_maps_writes_nothing(tmp_path):
    root = make_root(tmp_path)
    before_empty = (root / stagemap.MAPS_DIR).exists()
    stagemap.check_maps(root)
    assert before_empty is False and not (root / stagemap.MAPS_DIR).exists()
    stagemap.write_maps(root)
    stagemap.map_path(root, "council").write_text("changed", encoding="utf-8")
    stagemap.map_path(root, "intake").unlink()
    (root / stagemap.MAPS_DIR / "old.md").write_text("{}", encoding="utf-8")
    before = _snapshot(root / stagemap.MAPS_DIR)
    stagemap.check_maps(root)
    assert _snapshot(root / stagemap.MAPS_DIR) == before


def test_a_table_that_does_not_parse_writes_nothing(tmp_path):
    root = make_root(tmp_path)
    (root / "docs" / "roles" / "pipelines" / "council.yaml").write_text("version: 1\n", encoding="utf-8")
    out = stagemap.write_maps(root)
    assert out["ok"] is False and out["problems"]
    assert "docs/roles/pipelines/council.yaml" in out["problems"][0]
    assert not (root / stagemap.MAPS_DIR).exists()


def test_a_cycle_in_depends_on_is_a_reported_problem_not_a_traceback(tmp_path):
    # found by the critic of the run that wrote this module: the recursion had no guard
    root = make_root(tmp_path)
    table = _chain(3)
    table["stages"][0]["depends_on"] = ["s2"]
    (root / "docs" / "roles" / "pipelines" / "council.yaml").write_text(yaml.safe_dump(table), encoding="utf-8")
    with pytest.raises(ValueError, match="cycle: s0 -> s2 -> s1 -> s0"):
        stagemap.stage_ranks(table["stages"])
    out = stagemap.check_maps(root)
    assert out["ok"] is False and "cycle" in out["problems"][0]
    assert stagemap.write_maps(root)["ok"] is False


BROKEN_ORDER = {
    "stage id 'a' is used twice": [_row("a"), _row("a")],
    "stage b depends on 'zz', which is not a stage of this table": [_row("a"), _row("b", ["zz"])],
    "stage b lists 'a' twice in depends_on": [_row("a"), _row("b", ["a", "a"])],
    "depends_on forms a cycle: a -> b -> a": [_row("a", ["b"]), _row("b", ["a"])],
}


@pytest.mark.parametrize("message", BROKEN_ORDER)
def test_a_table_with_a_broken_order_is_named_and_gets_no_map(message, tmp_path):
    # found by the reviewers of an earlier implementation: a repeated entry gave two edges with one id, and the map
    # that `harness map` had written was wrong without a word
    stages = BROKEN_ORDER[message]
    assert stagemap.order_problems(stages) == [message]
    root = make_root(tmp_path)
    table = {"version": 1, "stages": stages}
    (root / "docs" / "roles" / "pipelines" / "council.yaml").write_text(yaml.safe_dump(table), encoding="utf-8")
    out = stagemap.write_maps(root)
    assert out["ok"] is False and message in out["problems"][0]
    assert out["problems"][0].startswith("docs/roles/pipelines/council.yaml: ")
    assert not (root / stagemap.MAPS_DIR).exists()


def test_a_return_or_a_route_to_no_stage_is_a_problem_of_the_map():
    returns = {"version": 1, "stages": [_row("a", returns_to={"stage": "zz", "counter": "work"})]}
    routes = {"version": 1, "stages": [_row("a")], "routes": {"stage": "zz", "labels": {"x": "research"}}}
    assert stagemap.map_problems(returns) == ["stage a returns to 'zz', which is not a stage of this table"]
    assert stagemap.map_problems(routes) == ["the routes start at 'zz', which is not a stage of this table"]
    with pytest.raises(ValueError, match="the routes start at 'zz'"):
        stagemap.flowchart(routes, access.load_policy(ROOT))


def test_the_real_tables_have_no_map_problem_and_validate_reports_an_order_problem(monkeypatch):
    for path in stagemap.tables(ROOT).values():
        assert stagemap.map_problems(_table(path)) == []
    assert catalog.validate_repository(ROOT)["problems"] == []
    monkeypatch.setattr(stagemap, "order_problems", lambda stages: ["stage id 'x' is used twice"])
    problems = catalog.validate_repository(ROOT)["problems"]
    assert "docs/roles/stages.yaml: stage id 'x' is used twice" in problems


def test_docs_problems_names_missing_stale_and_orphan_files(tmp_path):
    root = make_root(tmp_path)
    assert len(stagemap.docs_problems(root)) == 8
    stagemap.write_maps(root)
    assert stagemap.docs_problems(root) == []
    path = stagemap.map_path(root, "learning")
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    stagemap.map_path(root, "default").unlink()
    (root / stagemap.MAPS_DIR / "old.md").write_text("{}", encoding="utf-8")
    problems = stagemap.docs_problems(root)
    assert "docs/generated/maps/default.md is missing; run `harness map`" in problems
    assert (
        "docs/generated/maps/learning.md does not match docs/roles/pipelines/learning.yaml; run `harness map`"
        in problems
    )
    assert "docs/generated/maps/old.md has no stage table; run `harness map`" in problems
    assert len(problems) == 3


def test_a_stale_default_map_names_stages_yaml(tmp_path):
    root = make_root(tmp_path)
    stagemap.write_maps(root)
    stagemap.map_path(root, "default").write_text("x", encoding="utf-8")
    assert stagemap.docs_problems(root) == [
        "docs/generated/maps/default.md does not match docs/roles/stages.yaml; run `harness map`"
    ]


def _run_cli(monkeypatch, capsys, root: Path, *args: str) -> tuple[int, dict]:
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    code = cli.main(list(args))
    return code, json.loads(capsys.readouterr().out)


def test_cli_map_writes_the_eight_maps(tmp_path, monkeypatch, capsys):
    root = make_root(tmp_path)
    code, out = _run_cli(monkeypatch, capsys, root, "map")
    assert code == 0 and out["ok"] is True and len(out["written"]) == 8


def test_cli_map_check_finds_a_stale_map_and_writes_nothing(tmp_path, monkeypatch, capsys):
    root = make_root(tmp_path)
    _run_cli(monkeypatch, capsys, root, "map")
    code, out = _run_cli(monkeypatch, capsys, root, "map", "--check")
    assert code == 0 and out["ok"] is True
    path = stagemap.map_path(root, "wiki-ingest")
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    before = path.read_bytes()
    code, out = _run_cli(monkeypatch, capsys, root, "map", "--check")
    assert code == 1 and out["ok"] is False
    assert out["stale"] == ["docs/generated/maps/wiki-ingest.md"]
    assert path.read_bytes() == before


def test_cli_map_has_no_renderer(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(make_root(tmp_path)))
    with pytest.raises(SystemExit) as exc:
        cli.main(["map", "--render", str(tmp_path / "html")])
    assert exc.value.code == 2
    assert not hasattr(stagemap, "render_html") and not (tmp_path / "html").exists()


def test_docs_check_reports_the_maps(tmp_path, monkeypatch):
    root = make_root(tmp_path)
    text = (root / "docs" / "generated" / "role-types.md").read_text(encoding="utf-8")
    monkeypatch.setattr(catalog, "render_catalog", lambda _root: text)

    def about_maps() -> list[str]:
        return [p for p in catalog.docs_check(root)["problems"] if "docs/generated/maps/" in p]

    before = about_maps()
    assert len(before) == 8 and all("is missing" in p for p in before)
    stagemap.write_maps(root)
    assert about_maps() == []
    assert catalog.docs_check(root)["ok"] is True
    handoff = root / "docs" / "handoff" / "2026-10-02-1200-handoff.md"  # a session's notes, not a document
    handoff.parent.mkdir(parents=True)
    handoff.write_text("# Handoff\n\n[gone](missing.md)\n", encoding="utf-8")
    assert catalog.docs_check(root)["ok"] is True
    path = stagemap.map_path(root, "council")
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    stale = about_maps()
    assert len(stale) == 1 and "council.md does not match" in stale[0]


def test_readme_and_llms_txt_document_the_command_and_the_maps():
    readme = (ROOT / "packages" / "harness" / "README.md").read_text(encoding="utf-8")
    llms = (ROOT / "docs" / "llms.txt").read_text(encoding="utf-8")
    assert "`map [--check]`" in readme
    assert "(generated/maps/default.md)" in llms


def test_the_eight_committed_maps_match_their_tables():
    folder = ROOT / stagemap.MAPS_DIR
    assert sorted(p.name for p in folder.iterdir()) == sorted(f"{n}.md" for n in MAP_NAMES)
    assert stagemap.check_maps(ROOT) == {"ok": True, "checked": MAP_NAMES, "stale": [], "missing": []}
    assert [p for p in catalog.docs_check(ROOT)["problems"] if "docs/generated/maps" in p] == []
