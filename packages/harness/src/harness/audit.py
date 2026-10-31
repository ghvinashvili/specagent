"""Audits that need no model: the context budget (`harness audit`), skill usage (`harness skill-usage`) and the
instruction version rule (`harness version-check`)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import yaml

from . import catalog, state
from .gitcall import GIT

HOOK_SCRIPT = re.compile(r"\.claude/hooks/[\w.-]+")
# Files whose change alters what a session is told or allowed: a change needs a new docs/roles/VERSION.
INSTRUCTION = re.compile(
    r"^(packages/[^/]+/)?(CLAUDE\.md|AGENTS\.md|\.claude/(agents|skills|rules|hooks)/|\.claude/settings\.json|\.claude/loop\.md)"
    r"|^(plugins/|templates/|docs/roles/(stages\.yaml|pipelines/|auto-mode\.json))"
)
VERSION_FILE, CHANGELOG_FILE = "docs/roles/VERSION", "docs/roles/CHANGELOG.md"


def _words(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return (yaml.safe_load(text.split("---", 2)[1]) or {}) if text.startswith("---") else {}


def _memory_indexes(root: Path, globs: list[str]) -> list[dict]:
    """Each MEMORY.md the globs match with its size in bytes, sorted by its path as a string."""
    found = {str(p.relative_to(root)): p for pattern in globs for p in root.glob(pattern)}
    return [{"file": rel, "bytes": len(found[rel].read_bytes())} for rel in sorted(found)]


def context_audit(root: Path, ci: bool = False) -> dict:
    budget = yaml.safe_load((root / "docs" / "quality" / "context-budget.yaml").read_text(encoding="utf-8"))
    limits, findings = budget["limits"], []

    def check(name: str, value: int, where: str) -> None:
        if value > limits[name]["value"]:
            findings.append(
                {
                    "limit": name,
                    "severity": limits[name]["severity"],
                    "where": where,
                    "value": value,
                    "max": limits[name]["value"],
                }
            )

    files = []
    for path in sorted({p for pattern in budget["instruction_globs"] for p in root.glob(pattern)}):
        text, rel = path.read_text(encoding="utf-8"), str(path.relative_to(root))
        files.append({"file": rel, "lines": len(text.splitlines()), "words": _words(text)})
        check("instruction_file_max_lines", files[-1]["lines"], rel)
        check("instruction_file_max_words", files[-1]["words"], rel)
    memory = _memory_indexes(root, budget.get("memory_globs", []))
    for item in memory:  # spec B13: an index that agent memory loads at every start
        check("memory_index_max_bytes", item["bytes"], item["file"])

    settings = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
    injecting, per_prompt = [], 0
    for event, groups in settings.get("hooks", {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                per_prompt += event == "UserPromptSubmit"
                script = HOOK_SCRIPT.search(hook.get("command", ""))
                source = (
                    (root / script.group(0)).read_text(encoding="utf-8")
                    if script and (root / script.group(0)).is_file()
                    else ""
                )
                if "additionalContext" in source or "systemMessage" in source:
                    injecting.append({"event": event, "matcher": group.get("matcher", ""), "script": script.group(0)})
    check("per_prompt_hooks_max", per_prompt, ".claude/settings.json")

    mcp_file = root / ".mcp.json"
    servers = (
        sorted(json.loads(mcp_file.read_text(encoding="utf-8")).get("mcpServers", {})) if mcp_file.exists() else []
    )
    check("mcp_always_on_max", len(servers), ".mcp.json")

    preloaded = {name: fm.get("skills", []) for name, fm in catalog.load_types(root).items()}
    for name, skills in preloaded.items():
        check("preloaded_skills_per_type_max", len(skills), f".claude/agents/{name}.md")
    skills = [
        {
            "skill": p.parent.name,
            "file": str(p.relative_to(root)),
            "description_words": _words(str(_frontmatter(p).get("description", ""))),
        }
        for p in sorted(
            [
                *root.glob(".claude/skills/*/SKILL.md"),
                *root.glob("packages/*/.claude/skills/*/SKILL.md"),
                *root.glob("plugins/*/skills/*/SKILL.md"),
            ]
        )
    ]

    errors = [f for f in findings if f["severity"] == "error"]
    return {
        "ok": not errors if ci else True,
        "files": files,
        "memory_indexes": memory,
        "always_loaded_words": sum(f["words"] for f in files if f["file"] in budget["always_loaded"]),
        "hooks_injecting_context": injecting,
        "mcp_always_on": servers,
        "preloaded_skills": preloaded,
        "skills": skills,
        "findings": findings,
    }


def _skill_names(root: Path) -> set[str]:
    names = {
        p.parent.name
        for p in [*root.glob(".claude/skills/*/SKILL.md"), *root.glob("packages/*/.claude/skills/*/SKILL.md")]
    }
    for p in root.glob("plugins/*/skills/*/SKILL.md"):
        names |= {
            p.parent.name,
            f"{p.parents[2].name}:{p.parent.name}",
        }  # a plugin skill is also called as <plugin>:<skill>
    return names


def _used(record: dict, names: set[str]) -> str | None:
    """The skill a log record names. A typed command carries `command_name`; for a Skill tool call the hook stored the
    input as is, and the name is whichever of its values is a known skill."""
    if record.get("via") == "typed":
        return record.get("skill")
    values = [v for v in (record.get("tool_input") or {}).values() if isinstance(v, str)]
    return next((v for v in values if v in names), None)


def skill_usage(root: Path, runs: int = 20) -> dict:
    names, runs_root = _skill_names(root), state.runs_root(root)
    run_dirs = sorted(p for p in runs_root.glob("*-*") if (p / "state.json").exists())[
        -runs:
    ]  # run ids start with a timestamp
    logs = [log for d in run_dirs for log in d.glob("stages/**/logs/skills.jsonl")] + [
        runs_root / "_audit" / "skills.jsonl"
    ]
    used: dict[str, dict] = {}
    unmatched = 0
    for log in logs:
        for line in log.read_text(encoding="utf-8").splitlines() if log.exists() else []:
            record = json.loads(line)
            name = _used(record, names)
            if name is None:
                unmatched += 1
                continue
            entry = used.setdefault(name, {"model": 0, "typed": 0, "roles": []})
            entry[record["via"]] += 1
            if record.get("role") not in entry["roles"]:
                entry["roles"].append(record.get("role"))
    preloaded = sorted({s for fm in catalog.load_types(root).values() for s in fm.get("skills", [])})
    never = sorted(n for n in names if ":" not in n and n not in used and n not in preloaded)
    return {
        "ok": True,
        "runs": len(run_dirs),
        "used": used,
        "never_used": never,
        "preloaded": preloaded,
        "unmatched_records": unmatched,
    }


def version_check(root: Path, base: str) -> dict:
    """Instruction files changed since <base> require a new docs/roles/VERSION and a CHANGELOG heading for it."""
    diff = subprocess.run(
        [*GIT, "diff", "--name-only", f"{base}...HEAD"], cwd=root, capture_output=True, text=True, check=True
    )
    changed = diff.stdout.split()
    touched = [p for p in changed if INSTRUCTION.search(p)]
    if not touched:
        return {"ok": True, "status": "no_instruction_change"}
    version = (root / VERSION_FILE).read_text(encoding="utf-8").strip()
    problems = []
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        problems.append(f"{VERSION_FILE} must be MAJOR.MINOR.PATCH, found {version!r}")
    if VERSION_FILE not in changed:
        problems.append(f"instruction files changed and {VERSION_FILE} did not")
    if not re.search(
        rf"^## {re.escape(version)}(\s|$)", (root / CHANGELOG_FILE).read_text(encoding="utf-8"), re.MULTILINE
    ):
        problems.append(f"{CHANGELOG_FILE} has no heading for {version}")
    return {"ok": not problems, "version": version, "changed": touched, "problems": problems}
