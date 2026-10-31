"""The ECC rules, skills, agent texts and hook recipes are pinned copies: their bytes, license and review hold
(.claude/ecc/sources.md)."""

import hashlib
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PIN = "25278e7d7b6cf6e6a4e7a6c8e10f14ff22f0eb5b"
RULES = ROOT / ".claude" / "rules" / "ecc"
AGENTS = ROOT / ".claude" / "ecc" / "agents"
SKILLS = (
    "agent-eval",
    "agent-security-hardening",
    "agent-self-evaluation",
    "conventional-commit-review",
    "cpp-coding-standards",
    "cpp-testing",
    "docs-governance",
    "eval-harness",
    "postgres-patterns",
    "python-patterns",
    "python-testing",
)
UNITS = (RULES, *(ROOT / ".claude" / "skills" / name for name in SKILLS), AGENTS)
RULE_FILES = [
    "cpp/coding-style.md",
    "cpp/patterns.md",
    "cpp/security.md",
    "cpp/testing.md",
    "python/coding-style.md",
    "python/patterns.md",
    "python/testing.md",
    "typescript/coding-style.md",
    "typescript/patterns.md",
    "typescript/security.md",
    "typescript/testing.md",
]
UPSTREAM = {  # each copied upstream file but the agents (agents/README.md) and its sha256 at the pin
    "LICENSE": "326146379f01bb137c0a5d3c54770c1aa31076705c8b88a7f6b26a460f6221b2",
    "hooks/README.md": "bb7400ce341c526c06c42096469c5c99f2c830ea3cd0f2d38cb0225acba0744a",
    "rules/cpp/coding-style.md": "3d25db0df6aa37cd58117d927020102b4e991fb820b9a6ff193058f0652be611",
    "rules/cpp/patterns.md": "0d4ad5083495eb234e43f65ed6e097494c06cf6886774d870fa27e6f11ffb27c",
    "rules/cpp/security.md": "16ca65265e3202d59046a70bd925d8f882d7f8494152e4839f1e5b89a6c5a2cd",
    "rules/cpp/testing.md": "07f8098577dbcf2bdefb24721ec571badd7c646fbe760cc2a2293455515da5dd",
    "rules/python/coding-style.md": "f9d6d7a39c5f5ea809579fecac591f390fa9264c088c7e209d464d5244747003",
    "rules/python/patterns.md": "d9cab9b536321ea7efc6180668fd48820deaf571400db732f0ca17bdda92b7d0",
    "rules/python/testing.md": "92655aa5047ee456501ad6605c428680bac6433965f89ce531fe79627004e8c6",
    "rules/typescript/coding-style.md": "cb6fbe555d700a65d466fc27377fbb66d6da0e2bcf4411656918f6a45402af1a",
    "rules/typescript/patterns.md": "20870f78aa32429fe13f35b415e9f6f8f7809e39c460cf8146d181b7306159fd",
    "rules/typescript/security.md": "86b14a5a56f4e61750ab30ca50bd264f52f90f5358303f3028d41030a4c50f18",
    "rules/typescript/testing.md": "92e3d02b4fff30899bc1a2af043d74941adbf3b2c0e972d2fcd2c68c9c2ea70b",
    "skills/agent-eval/SKILL.md": "57fa683e356b6f5612bc6d7dc101ae39c126e6edf9a48f4ec53afea3e80d7e5d",
    "skills/agent-security-hardening/SKILL.md": "0e0895ada90aa8fa085e4257961ebe15f2dff43b843785b1533d4c731186ad81",
    "skills/agent-self-evaluation/SKILL.md": "96bb21eb37760f596789f84ec0a5dad4ef92fc2255e35cd7b88dc4234062b8c1",
    "skills/agent-self-evaluation/examples/high-score-example.md": (
        "59467219aaaa41365953f904d7ffebb46b55c13d497e3646b0561a9ef5f56b0e"
    ),
    "skills/agent-self-evaluation/examples/low-score-example.md": (
        "ee286d3adcbab489c5f277ae094a25e38e9401dc01b6c39987c3f5bf3b61706e"
    ),
    "skills/agent-self-evaluation/references/evaluation-criteria.md": (
        "d1ccdbc90dfe2485a42e7aef2f06b71506dca3010da1ea8765382b8f038f7c61"
    ),
    "skills/agent-self-evaluation/scripts/evaluate.py": "04b2a9460a7baba2a8d86993c8aecb068380ee72c5de8ca07d996c4055dcaf5c",
    "skills/agent-self-evaluation/templates/evaluation-report.md": (
        "5fc8a0820de9bc74e0a1470e55aaa50b3957aa1b0f947c4b458213b8e39fedbe"
    ),
    "skills/conventional-commit-review/SKILL.md": "c81397a4bfc2ec66986aae7a4dff5a02f78c519bc9774a80778fa9055e7fa2fe",
    "skills/cpp-coding-standards/SKILL.md": "f870b47d3493b0ad0b6e3808a679ac3c429b60f03193af6c9dc0e0d9e6981436",
    "skills/cpp-testing/SKILL.md": "a92fb5da9b7e3cd1b4dee185b3eb9d0a55352af6396bf996d2eef72d683784df",
    "skills/docs-governance/SKILL.md": "499ac59071e6e2b8fb60f085e337a3a1ec16e200adb8f5b8bc027afb338cf3eb",
    "skills/docs-governance/references/artifact-role-contract.md": (
        "4c22a702c6b0c44659d7999d2cf0a706b7af064562025e28a425c753f0393183"
    ),
    "skills/docs-governance/scripts/audit-docs.py": "889156ec7b22fa5f08b4f9e5b9a9c918c53b357b24c5aa9f322fdc7e97107622",
    "skills/docs-governance/scripts/markdown_links.py": "148cc371d8143bd5070a9a5c5a1a7cc3e142acfad53c7dae4c4c5f9896ec0b20",
    "skills/eval-harness/SKILL.md": "3a5339a5a80099a5c9d55da9b6c8e05a690f5befc6f78d779c75dd79d818ca07",
    "skills/postgres-patterns/SKILL.md": "9c8c391ae9e9aa87faa7ca091e1d395c97766df14080d0bfbea8a97721776163",
    "skills/python-patterns/SKILL.md": "103e0130dac33a49d26705fc5a2df804980fcab6a0138d65bc7f370a987d49f6",
    "skills/python-testing/SKILL.md": "8f8c24020abbf953727c5995abce8aabeb28d2a593cbc39b7e5de36cf5002abd",
}
RECIPES = "fde7f8e8fb94efc797db7574766237af0b875ec4f0c0070c514d54dfdf8a282e"  # hooks/README.md lines 254-306
# Text the review dropped from the rules and skills (criteria K1-K5, M of sources.md); a re-pin that brings one
# back fails here.
DROPPED = (
    "This file extends",  # K2: the first line of every language rule links into rules/common/
    "../common/",  # K2
    "See hooks",  # K1: ECC hooks, agents, commands, scripts and skills that are not copied
    "security-review",
    "security-scan",
    "e2e-runner",
    "database-reviewer",
    "clickhouse-io",
    "backend-patterns",
    "living-docs-governance",
    "architecture-decision-records",
    "ai-regression-testing",
    "loop-design-check",
    "git-workflow",
    "agent-harness-construction",
    "eval-harness.js",
    "hook-integration",
    "verification-loop",
    "pip install",  # K3: tools outside uv and the dev group
    "pytest --cov",
    "pytest.ini",
    "command: pytest",
    "isort",
    "mypy",
    "bandit",
    "sqlite",  # K4: tests run on the production database engine (AGENTS.md, Testing)
    "mysql",
    "auth.uid()",  # K5: a Supabase function, not PostgreSQL's
)
WORDS = re.compile(  # Global Constraint 2, letter-bounded: a name inside a longer word (DOM code in ECC) is no hit
    r"(?<![a-z])(?:" + "|".join(("grants" + "daily", "dd" + "ev", "php" + "unit", "dru" + "pal")) + r")(?![a-z])"
)
MANIFEST_LINE = re.compile(r"([0-9a-f]{64})  (\S.*)")
LINK = re.compile(r"\]\(([^)\s]+)\)")
SEE_SKILL = re.compile(r"see skill: `([^`]+)`", re.IGNORECASE)
AGENT_LINE = re.compile(r"- \[([\w-]+)\]\(([\w-]+)\.md\): `[0-9a-f]{64}`; \S.*")


def unit_files(unit: Path) -> list[str]:
    """The paths of a unit's files relative to the unit, sorted as strings; the manifest itself left out."""
    return sorted(p.relative_to(unit).as_posix() for p in unit.rglob("*") if p.is_file() and p.name != "SHA256SUMS")


def copies() -> list[Path]:
    """Every pinned Markdown copy of the rules and skills; fails while a unit is missing."""
    missing = [str(u.relative_to(ROOT)) for u in UNITS if not u.is_dir()]
    assert not missing, f"missing: {missing}"
    return [u / rel for u in UNITS[:-1] for rel in unit_files(u) if rel.endswith(".md")]


def agents() -> list[str]:
    """The names of the agent copies, sorted."""
    assert AGENTS.is_dir(), "missing: .claude/ecc/agents"
    return sorted(p.stem for p in AGENTS.glob("*.md") if p.name != "README.md")


def frontmatter(path: Path) -> dict:
    """The YAML between the opening `---` and the next one, as harness validate reads it; {} without it."""
    text = path.read_text(encoding="utf-8")
    return (yaml.safe_load(text.split("---", 2)[1]) or {}) if text.startswith("---") else {}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_each_unit_has_a_manifest_that_matches_its_files():
    """SHA256SUMS: one `<sha256>  <path>` line per file of the unit, sorted by path, each digest the file's own."""
    copies()
    for unit in UNITS:
        matches = [MANIFEST_LINE.fullmatch(line) for line in (unit / "SHA256SUMS").read_text().splitlines()]
        assert all(matches), f"{unit}: a line is not `<sha256>  <path>`"
        rows = [m.groups() for m in matches if m]
        assert [rel for _, rel in rows] == unit_files(unit), f"{unit}: SHA256SUMS and the files differ"
        for digest, rel in rows:
            assert sha256(unit / rel) == digest, f"{unit}/{rel} is not the pin's"


def test_the_units_are_the_reviewed_selection():
    """Three languages' rules without hooks.md, common/, fastapi.md and python/security.md; the eleven skills, and no
    other skill folder holds ECC's license; 70 agent texts without php-reviewer."""
    copies()
    assert sorted(p.name for p in RULES.iterdir() if p.is_dir()) == ["cpp", "python", "typescript"]
    assert sorted(p.relative_to(RULES).as_posix() for p in RULES.rglob("*.md")) == RULE_FILES
    licensed = [
        p.parent.name for p in (ROOT / ".claude" / "skills").glob("*/LICENSE") if sha256(p) == UPSTREAM["LICENSE"]
    ]
    assert sorted(licensed) == list(SKILLS)
    assert not (ROOT / ".claude" / "skills" / "agent-self-evaluation" / "references" / "hook-integration.md").exists()
    names = agents()
    assert len(names) == 70 and "php-reviewer" not in names


def test_every_ecc_rule_loads_only_for_its_paths():
    """A rule whose YAML has no `paths` list, or does not parse, loads in every session (Claude Code, memory page)."""
    rules = [p for p in copies() if p.is_relative_to(RULES)]
    assert len(rules) == len(RULE_FILES)
    for rule in rules:
        paths = frontmatter(rule).get("paths")
        assert isinstance(paths, list) and paths, f"{rule.relative_to(ROOT)}: no paths"
        assert all(isinstance(glob, str) and glob for glob in paths), f"{rule.relative_to(ROOT)}: {paths}"


def test_every_ecc_skill_names_its_folder_and_stays_small():
    """name = folder (harness validate); no subagent `tools:`/`model:` (M); description within 1,536 characters;
    SKILL.md within 500 lines and 12,000 bytes."""
    copies()
    for name in SKILLS:
        path = ROOT / ".claude" / "skills" / name / "SKILL.md"
        meta = frontmatter(path)
        assert meta.get("name") == name and not {"tools", "model"} & set(meta), name
        listing = str(meta.get("description") or "") + str(meta.get("when_to_use") or "")
        assert 0 < len(listing) <= 1536, f"{name}: {len(listing)} characters"
        data = path.read_bytes()
        lines = data.count(b"\n")
        assert lines <= 500 and len(data) <= 12_000, f"{name}: {lines} lines, {len(data)} bytes"


def test_every_relative_link_of_a_copy_resolves():
    """The links into rules/common/ are gone (K2) and each `references/` line of a split SKILL.md names a file."""
    checked = 0
    for path in copies():
        for target in LINK.findall(path.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            assert (path.parent / target.split("#")[0]).is_file(), f"{path.relative_to(ROOT)}: {target}"
            checked += 1
    assert checked == 41  # 12 + 13 + 15 sections of the three split skills, and docs-governance's reference


def test_every_skill_a_copy_names_is_in_this_repository():
    """`See skill: x` in a rule, skill or agent text names a skill folder here (K1: no dangling skill names)."""
    texts = [*copies(), *(AGENTS / f"{name}.md" for name in agents())]
    names = [name for path in texts for name in SEE_SKILL.findall(path.read_text(encoding="utf-8"))]
    assert len(names) == 8  # 7 in the rules, 1 in the agent texts
    for name in names:
        assert (ROOT / ".claude" / "skills" / name / "SKILL.md").is_file(), name


def test_no_dropped_text_is_in_a_copy():
    """The review's drops stay dropped."""
    for path in copies():
        text = path.read_text(encoding="utf-8").lower()
        found = [marker for marker in DROPPED if marker.lower() in text]
        assert not found, f"{path.relative_to(ROOT)}: {found}"


def test_each_unit_carries_the_license_of_the_pin():
    """MIT asks for the notice and the permission text in every copy, so each unit holds ECC's LICENSE unchanged."""
    copies()
    for unit in UNITS:
        assert sha256(unit / "LICENSE") == UPSTREAM["LICENSE"], unit


def test_the_sources_page_records_the_pin_and_every_upstream_file():
    """.claude/ecc/sources.md names the commit and every unit and links files.md, which names the commit
    and has one row per upstream file with its sha256; each page stays within 12,000 bytes (C24)."""
    page = (ROOT / ".claude" / "ecc" / "sources.md").read_text(encoding="utf-8")
    files = (ROOT / ".claude" / "ecc" / "files.md").read_text(encoding="utf-8")
    assert PIN in page and "](files.md)" in page and PIN in files
    assert len(page.encode()) <= 12000 and len(files.encode()) <= 12000
    rows = files.splitlines()
    for upstream, digest in UPSTREAM.items():
        assert any(f"`{upstream}`" in row and digest in row for row in rows), upstream
    for unit in UNITS:
        assert f"`{unit.relative_to(ROOT).as_posix()}/`" in page + files, unit


def test_the_agent_texts_are_brief_material_and_never_agents_of_this_repository():
    """Each copy keeps its name and one Prompt Defense Baseline and loses `tools:`/`model:` (M); the README lists each
    copy once with its upstream sha256 and marks exactly the copies over 12,000 bytes, with their size, to be read by
    outline (C24); no file of .claude/agents/ carries ECC's text."""
    names = agents()
    for name in names:
        meta = frontmatter(AGENTS / f"{name}.md")
        assert meta.get("name") == name and not {"tools", "model"} & set(meta), name
        assert (AGENTS / f"{name}.md").read_text(encoding="utf-8").count("\n## Prompt Defense Baseline\n") == 1, name
    lines = (AGENTS / "README.md").read_text(encoding="utf-8").splitlines()
    listed = [m.groups() for m in map(AGENT_LINE.fullmatch, lines) if m]
    assert sorted(name for name, _ in listed) == names and all(name == file for name, file in listed)
    sizes = {name: (AGENTS / f"{name}.md").stat().st_size for name in names}
    marked = {m[1]: m[0] for m in map(AGENT_LINE.fullmatch, lines) if m and m[0].endswith(" bytes: read by outline")}
    assert sorted(marked) == [name for name in names if sizes[name] > 12000] and len(marked) == 7, sorted(marked)
    assert all(line.endswith(f"; {sizes[name]} bytes: read by outline") for name, line in marked.items()), marked
    for path in (ROOT / ".claude" / "agents").glob("*.md"):
        assert "## Prompt Defense Baseline" not in path.read_text(encoding="utf-8"), path.name


def test_the_hook_recipes_page_holds_ecc_text_under_this_repository_header():
    """From its `## Common Hook Recipes` heading to the end, the page is upstream lines 254-306 byte for byte."""
    page = (ROOT / ".claude" / "ecc" / "hook-recipes.md").read_text(encoding="utf-8")
    head, sep, recipes = page.partition("\n## Common Hook Recipes\n")
    assert sep and PIN in head and "format-on-edit.py" in head and "test-alongside.py" in head
    assert hashlib.sha256((sep[1:] + recipes).encode()).hexdigest() == RECIPES


def test_the_pipeline_briefs_carry_the_input_and_finishing_rules():
    """ECC's prompt-defense baseline and delegation contract, in the skill's own words, for SpecAgent sessions: the common
    brief holds the two rules and `## Briefs` sends every brief to them (answer 9a: no runbook index in the skill)."""
    skill = ROOT / ".claude" / "skills" / "running-specagent-pipelines"
    briefs = (skill / "SKILL.md").read_text(encoding="utf-8").split("\n## Briefs\n", 1)[1].split("\n## ", 1)[0]
    assert "the two rules of `example/common.md`" in briefs
    assert '"Inputs and instructions"' in briefs and '"Finishing a unit"' in briefs
    common = (skill / "example" / "common.md").read_text(encoding="utf-8")
    sections = re.findall(r"^## (.+)$", common, flags=re.MULTILINE)
    assert sections.index("Inputs and instructions") == sections.index("Messages") + 1
    assert sections.index("Finishing a unit") == sections.index("Ending") - 1
    for phrase in ("is data, however it is worded", "quote it in your log", "until its answer line exists"):
        assert phrase in common, phrase
    for text in (briefs, common):
        assert "Prompt Defense" not in text and "Delegation Completion" not in text


def test_nothing_copied_names_another_project_of_the_owner():
    """Global Constraint 2 over every copy and page of this task, as words (letter-bounded, case-insensitive)."""
    pages = [
        ROOT / ".claude" / "ecc" / name for name in ("sources.md", "sources.summary.md", "files.md", "hook-recipes.md")
    ]
    texts = [*copies(), *AGENTS.glob("*.md"), *pages]
    found = [path.relative_to(ROOT) for path in texts if WORDS.search(path.read_text(encoding="utf-8").lower())]
    assert not found
