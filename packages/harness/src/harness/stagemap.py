"""Stage maps: one Mermaid flowchart per stage table (docs/roles/stages.yaml and docs/roles/pipelines/*.yaml),
written to docs/generated/maps/<name>.md, a page GitHub and Obsidian draw as it stands: no renderer, no plugin
(wiki/decisions/diagrams-are-mermaid-text.md). The chart follows the table by rule: a box per stage in the order of
the table, with its role type and its tags; a diamond after each stage a human approves, from which the stages that
wait for it start; a dashed arrow from a reviewer to the stage its verdict `revise` returns the work to; a double box
per place a route label leads to (a pipeline, or `escalate`). Node ids are positional (`s<i>`, `h<i>`, `r<j>`): a stage id may be a Mermaid
keyword such as `end` or hold `--`, which is an arrow."""

from __future__ import annotations

from pathlib import Path

import yaml

from . import access

MAPS_DIR = Path("docs/generated/maps")
INDENT = "    "
LEGEND = (
    "A box is a stage: its id, its role type and its tags (per task, one call, blind reviewer). A diamond is a human "
    "approval; the stages after it start once it is given. A dashed arrow is a reviewer's verdict `revise` returning "
    "the work. A double box is where a route label leads: the pipeline of that name, or `escalate`, which asks the "
    "human."
)


def tables(root: Path) -> dict[str, Path]:
    """Map name -> stage table path: `default` first, then every pipeline by file stem."""
    found = {"default": root / "docs" / "roles" / "stages.yaml"}
    for path in sorted((root / "docs" / "roles" / "pipelines").glob("*.yaml"), key=lambda p: p.stem):
        found[path.stem] = path
    return found


def map_path(root: Path, name: str) -> Path:
    """Where the map of table `name` is written."""
    return root / MAPS_DIR / f"{name}.md"


def stage_ranks(stages: list[dict]) -> dict[str, int]:
    """Level of every stage: 0 without `depends_on`, else 1 + the highest level of its dependencies."""
    by_id = {s["id"]: s for s in stages}
    ranks: dict[str, int] = {}
    open_path: list[str] = []  # the stages whose level is being worked out; meeting one again is a cycle

    def rank(stage_id: str) -> int:
        if stage_id in open_path:
            raise ValueError(
                "depends_on forms a cycle: " + " -> ".join([*open_path[open_path.index(stage_id) :], stage_id])
            )
        if stage_id not in ranks:
            open_path.append(stage_id)
            deps = by_id[stage_id].get("depends_on") or []
            ranks[stage_id] = 1 + max(rank(d) for d in deps) if deps else 0
            open_path.pop()
        return ranks[stage_id]

    for stage in stages:
        rank(stage["id"])
    return ranks


def order_problems(stages: list[dict]) -> list[str]:
    """What is wrong with the order of a stage table: a stage id used twice, a `depends_on` entry that names no stage
    of the table or is listed twice, a cycle. `harness validate` reports them for every table."""
    ids = [s["id"] for s in stages]
    problems = [f"stage id {i!r} is used twice" for i in sorted({i for i in ids if ids.count(i) > 1})]
    for stage in stages:
        deps = stage.get("depends_on") or []
        problems += [
            f"stage {stage['id']} depends on {d!r}, which is not a stage of this table" for d in deps if d not in ids
        ]
        problems += [
            f"stage {stage['id']} lists {d!r} twice in depends_on"
            for d in sorted({d for d in deps if deps.count(d) > 1})
        ]
    if not problems:
        try:
            stage_ranks(stages)
        except ValueError as exc:
            problems.append(str(exc))
    return problems


def map_problems(table: dict) -> list[str]:
    """What keeps a table from becoming a map: the problems of its order, and a return or a route that starts or
    ends at no stage of the table (an arrow to a node nobody declared)."""
    stages = table["stages"]
    ids = [s["id"] for s in stages]
    problems = order_problems(stages)
    for stage in stages:
        back = (stage.get("returns_to") or {}).get("stage")
        if back is not None and back not in ids:
            problems.append(f"stage {stage['id']} returns to {back!r}, which is not a stage of this table")
    routes = table.get("routes")
    if routes and routes.get("stage") not in ids:
        problems.append(f"the routes start at {routes.get('stage')!r}, which is not a stage of this table")
    return problems


def _text(piece: str) -> str:
    """A label piece as Mermaid reads it between quotes or bars: a quote or a bar would end the label."""
    return piece.replace('"', "#quot;").replace("|", "#124;")


def _tags(stage: dict, policy: dict) -> list[str]:
    tags = []
    if stage.get("parallel") == "per_task":
        tags.append("per task")
    if stage.get("mode") == "print":
        tags.append("one call")
    if access.type_row(policy, stage["role_type"])["blind"]:
        tags.append("blind reviewer")
    return tags


def _targets(table: dict) -> list[str]:
    """The places the route labels lead to, each once, in the order of the labels."""
    return list(dict.fromkeys((table.get("routes") or {}).get("labels", {}).values()))


def _nodes(table: dict, policy: dict) -> list[str]:
    """A box per stage, a diamond right after each stage a human approves, then a double box per route target."""
    lines = []
    for i, stage in enumerate(table["stages"], start=1):
        tags = _tags(stage, policy)
        pieces = [stage["id"], stage["role_type"], *([", ".join(tags)] if tags else [])]
        lines.append(f'{INDENT}s{i}["{"<br/>".join(_text(p) for p in pieces)}"]')
        if stage.get("approval") == "human":
            lines.append(f'{INDENT}h{i}{{"human approval"}}')
    lines += [f'{INDENT}r{j}[["{_text(t)}"]]' for j, t in enumerate(_targets(table), start=1)]
    return lines


def _edges(table: dict) -> list[str]:
    """Each dependency (from the diamond when the stage waited for is approved), each approval, each return, each
    route label."""
    stages = table["stages"]
    box = {s["id"]: i for i, s in enumerate(stages, start=1)}
    human = {s["id"] for s in stages if s.get("approval") == "human"}

    def leaving(stage_id: str) -> str:
        return f"h{box[stage_id]}" if stage_id in human else f"s{box[stage_id]}"

    lines = []
    for i, stage in enumerate(stages, start=1):
        for dep in stage.get("depends_on") or []:
            lines.append(f"{INDENT}{leaving(dep)} {'-->|approved|' if dep in human else '-->'} s{i}")
        if stage["id"] in human:
            lines.append(f"{INDENT}s{i} --> h{i}")
    for stage in stages:
        if stage.get("returns_to"):
            lines.append(f"{INDENT}s{box[stage['id']]} -.->|revise| s{box[stage['returns_to']['stage']]}")
    routes, targets = table.get("routes") or {}, _targets(table)
    for label, target in routes.get("labels", {}).items():
        lines.append(f"{INDENT}{leaving(routes['stage'])} -->|{_text(label)}| r{targets.index(target) + 1}")
    return lines


def flowchart(table: dict, policy: dict) -> str:
    """The Mermaid flowchart of one stage table, without a trailing newline. A table with a map problem raises
    ValueError naming every problem."""
    problems = map_problems(table)
    if problems:
        raise ValueError("; ".join(problems))
    return "\n".join(["flowchart TD", *_nodes(table, policy), *_edges(table)])


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def render_map(root: Path, name: str) -> str:
    """The text of docs/generated/maps/<name>.md for the table as it is now."""
    path = tables(root)[name]
    chart = flowchart(yaml.safe_load(path.read_text(encoding="utf-8")), access.load_policy(root))
    head = f"Generated by `harness map` from `{_rel(root, path)}`; edit the table, not this page."
    return f"# Stage map: {name}\n\n{head} {LEGEND}\n\n```mermaid\n{chart}\n```\n"


def _render_all(root: Path) -> tuple[dict[str, str], list[str]]:
    texts, problems = {}, []
    for name, path in tables(root).items():
        try:
            texts[name] = render_map(root, name)
        except (OSError, yaml.YAMLError, KeyError, TypeError, ValueError, access.AccessError) as exc:
            problems.append(f"{_rel(root, path)}: cannot map the table ({exc})")
    return texts, problems


def _orphans(root: Path) -> list[Path]:
    """Every file of the maps folder no table writes: the map of a removed table, or a map of an earlier form."""
    folder = root / MAPS_DIR
    if not folder.is_dir():
        return []
    kept = {map_path(root, name).name for name in tables(root)}
    return sorted(p for p in folder.iterdir() if p.is_file() and p.name not in kept)


def write_maps(root: Path) -> dict:
    """Write every map; remove the files no table produces. Nothing is written when a table does not map."""
    texts, problems = _render_all(root)
    if problems:
        return {"ok": False, "problems": problems}
    (root / MAPS_DIR).mkdir(parents=True, exist_ok=True)
    written = []
    for name, text in texts.items():
        map_path(root, name).write_text(text, encoding="utf-8")
        written.append(_rel(root, map_path(root, name)))
    removed = []
    for orphan in _orphans(root):
        orphan.unlink()
        removed.append(_rel(root, orphan))
    return {"ok": True, "written": written, "removed": removed}


def check_maps(root: Path) -> dict:
    """Compare the committed maps with what the tables give now; writes nothing."""
    texts, problems = _render_all(root)
    stale, missing = [], []
    for name, text in texts.items():
        path = map_path(root, name)
        if not path.is_file():
            missing.append(_rel(root, path))
        elif path.read_text(encoding="utf-8") != text:
            stale.append(_rel(root, path))
    stale += [_rel(root, p) for p in _orphans(root)]
    out = {"ok": not (stale or missing or problems), "checked": list(texts), "stale": stale, "missing": missing}
    if problems:
        out["problems"] = problems
    return out


def docs_problems(root: Path) -> list[str]:
    """One message per stale, missing or orphaned map, for `harness docs-check`."""
    result = check_maps(root)
    names = {_rel(root, map_path(root, n)): n for n in tables(root)}
    problems = list(result.get("problems", []))
    for rel in result["missing"]:
        problems.append(f"{rel} is missing; run `harness map`")
    for rel in result["stale"]:
        if rel in names:
            table = _rel(root / "docs" / "roles", tables(root)[names[rel]])
            problems.append(f"{rel} does not match docs/roles/{table}; run `harness map`")
        else:
            problems.append(f"{rel} has no stage table; run `harness map`")
    return problems
