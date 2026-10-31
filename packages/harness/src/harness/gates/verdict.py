"""harness/gates/verdict.py — the synthesizer stage gate in a council run: five sections, every statement tied to an input."""

from __future__ import annotations

from pathlib import Path

from ._common import check, has_sections, input_names, sections, statements, text

REQUIRED = ["where they agree", "where they clash", "blind spots", "recommendation", "first step"]


def synthesis_checks(run_dir: Path, stage_dir: Path, name: str) -> list[dict]:
    """Shared by verdict (council) and synthesize (research)."""
    doc = text(stage_dir, f"output/{name}")
    missing = has_sections(doc, REQUIRED)
    names = input_names(run_dir, stage_dir)
    keys = (
        set(names)
        | {Path(n).name for n in names}
        | {Path(n).parts[0] + "/" + Path(n).parts[1] for n in names if len(Path(n).parts) > 2}
    )
    lines = statements(doc)
    uncited = [s[:70] for s in lines if not any(k in s for k in keys)]
    return [
        check(f"{name} exists", bool(doc)),
        check(f"{name} has the five sections", not missing, "missing: " + ", ".join(missing)),
        check("the stage had inputs to cite", bool(names)),
        check("every statement names the input it comes from", bool(lines) and not uncited, "; ".join(uncited[:3])),
    ]


def named_inputs(item: str, names: list[str]) -> set[str]:
    """The inputs an item names: by its path under input/, by its shard directory (`advise/02`), or by its file name
    when no other input has that name."""
    counts: dict[str, int] = {}
    for n in names:
        counts[Path(n).name] = counts.get(Path(n).name, 0) + 1
    out = set()
    for n in names:
        parts = Path(n).parts
        keys = {n} | ({parts[0] + "/" + parts[1]} if len(parts) > 2 else set())
        keys |= {Path(n).name} if counts[Path(n).name] == 1 else set()
        if any(k in item for k in keys):
            out.add(n)
    return out


def synthesis_content(run_dir: Path, stage_dir: Path, name: str) -> list[dict]:
    """Part 3 of specs/001-chat-depth, shared by verdict and synthesize: every input is named at least once (method
    step 8), and every item under Where they clash names two different inputs."""
    doc = text(stage_dir, f"output/{name}")
    names = input_names(run_dir, stage_dir)
    unnamed = [n for n in names if not named_inputs(doc, [n])]
    clash = next((b for h, b in sections(doc).items() if h.startswith("where they clash")), "")
    one_sided = [s[:70] for s in statements(clash) if len(named_inputs(s, names)) < 2]
    return [
        check("every input is named at least once", bool(doc) and not unnamed, ", ".join(unnamed[:5])),
        check("every item of Where they clash names two different inputs", not one_sided, "; ".join(one_sided[:3])),
    ]


def content_checks(repo: Path, run_dir: Path, stage_dir: Path, events: list[dict] | None) -> list[dict]:
    """Part 3 of specs/001-chat-depth on verdict.md: every input is named, both sides of every clash are named."""
    return synthesis_content(run_dir, stage_dir, "verdict.md")


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    return synthesis_checks(run_dir, stage_dir, "verdict.md")
