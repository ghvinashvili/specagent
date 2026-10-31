"""Tests of the documentation (Task 7; manager-build Task 10): every script has its page under scripts/docs/ with its
usage line and every option it parses, the watcher's page its exit codes; scripts/README.md is an index of at most
12,000 bytes, one line per page, with every field of a v2 config and its default; example/agents.json is a v2 config
that `watch_agents.py --check` accepts, every role of it having a fresh text; the SKILL.md tests are in
test_skill_md.py (manager-build Task 1).

  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests
"""

import ast
import json
import re
import subprocess
import sys

from transcript_home import SCRIPTS, Home

SKILL = SCRIPTS.parent
README = SCRIPTS / "README.md"
DOCS = SCRIPTS / "docs"
EXAMPLE = SKILL / "example" / "agents.json"
REFERENCES = SKILL / "references"


def watcher_names() -> dict:
    """watch_agents.py's defaults, other fields, agent fields and fresh roles, read in a child process."""
    code = (
        "import json, sys; sys.dont_write_bytecode = True; sys.path.insert(0, sys.argv[1]); import watch_agents as w; "
        "print(json.dumps({'defaults': w.DEFAULTS, 'other': w.OTHER_FIELDS, 'agent': w.AGENT_FIELDS, "
        "'roles': list(w.FRESH)}))"
    )
    return json.loads(
        subprocess.run(
            [sys.executable, "-I", "-c", code, str(SCRIPTS)], capture_output=True, text=True, check=True
        ).stdout
    )


def sections(text: str, depth: int) -> dict[str, str]:
    """Each heading line of at most `depth` #s, to its text up to the next such heading."""
    parts = re.split(rf"(?m)^(?=#{{1,{depth}}} )", text)
    return {part.splitlines()[0]: part for part in parts if part.startswith("#")}


def scripts() -> list[str]:
    """The scripts' names: scripts/*.py and scripts/*.sh (scripts/manager/ has a README of its own)."""
    return sorted(p.name for pattern in ("*.py", "*.sh") for p in SCRIPTS.glob(pattern))


def stem(name: str) -> str:
    return name.rsplit(".", 1)[0]


def script_pages() -> dict[str, str]:
    """Each scripts/docs/<stem>.md whose first line is ``# `<stem>.py` — …`` (or .sh), by script name."""
    found = {}
    for page in sorted(DOCS.glob("*.md")):
        text = page.read_text(encoding="utf-8")
        m = re.match(r"# `([\w.]+\.(?:py|sh))` — ", text)
        if m and stem(m.group(1)) == page.stem:
            found[m.group(1)] = text
    return found


def config_section() -> str:
    return next(
        (
            text
            for head, text in sections(README.read_text(encoding="utf-8"), 2).items()
            if head.startswith("## Config v2")
        ),
        "",
    )


def options(script) -> list[str]:
    """The `--x` strings of the script's add_argument calls, read with ast (the waiters poll from import on)."""
    tree = ast.parse(script.read_text(encoding="utf-8"))
    return sorted(
        {
            str(a.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument"
            for a in node.args
            if isinstance(a, ast.Constant) and str(a.value).startswith("--")
        }
    )


def test_every_script_has_a_page_named_after_it_with_its_usage_line():
    pages = script_pages()
    assert sorted(pages) == scripts()
    assert sorted(p.name for p in DOCS.glob("*.md")) == sorted(f"{stem(n)}.md" for n in scripts())
    usage = [n for n in pages if n.endswith(".py") and not re.search(rf"(?m)^ *python3 -I scripts/{n}\b", pages[n])]
    assert usage == []


def test_every_option_a_script_parses_is_on_its_page():
    pages = script_pages()
    missing = {
        p.name: [o for o in options(p) if not re.search(rf"(?<![\w-]){o}(?![\w-])", pages.get(p.name, ""))]
        for p in sorted(SCRIPTS.glob("*.py"))
    }
    assert {name: opts for name, opts in missing.items() if opts} == {}


def test_the_watcher_s_page_lists_its_exit_codes():
    text = script_pages().get("watch_agents.py", "")
    assert [code for code in range(5) if not re.search(rf"(?m)^\| {code} \|", text)] == []


def test_the_readme_documents_every_field_of_a_v2_config_and_the_short_defaults():
    text, names = config_section(), watcher_names()
    fields = [*names["defaults"], *names["other"], *names["agent"]]
    assert [f for f in fields if f"`{f}`" not in text] == []
    short = {k: json.dumps(v) for k, v in names["defaults"].items() if len(json.dumps(v)) <= 60}
    assert [k for k, v in short.items() if not re.search(rf"(?m)^\| `{k}` \| `{re.escape(v)}` \|", text)] == []


def test_the_example_config_is_v2_and_check_accepts_it(tmp_path):
    config, names = json.loads(EXAMPLE.read_text(encoding="utf-8")), watcher_names()
    assert {"cap", "handoff_wait", "nudges", "permission_wait", "budget", "milestones"} <= set(config)
    roles = {name.split("/")[-1] for name in config["agents"]}
    assert roles <= set(names["roles"]) | set(config.get("fresh", {}))
    assert not config["milestones"] or {"builder", "verifier"} <= roles  # the switch acts on these two roles only
    run = tmp_path / "run"
    (run / "_control").mkdir(parents=True)  # K4: each settings value is `_control/<role>-settings.json`
    for agent in config["agents"].values():
        (run / agent["settings"]).write_text("{}\n", encoding="utf-8")
        (run / agent["status"]).write_text("STATUS: building Task 1\n", encoding="utf-8")
    copy = run / "_agents.json"
    copy.write_text(json.dumps({**config, "run_dir": str(run)}), encoding="utf-8")
    home = Home(tmp_path)
    r = home.run("watch_agents.py", "--check", str(copy))
    assert r.returncode == 0, r.stdout + r.stderr
    assert home.claude_calls() == ["agents --json --all"]
    lines = r.stdout.splitlines()
    assert [f"{name}: no session" for name in config["agents"]] == [x for x in lines if ": no session" in x]
    assert lines[-1] == f"would sleep {config.get('interval', 120)} s and go on"


def test_the_judge_launcher_s_page_has_its_usage_line():
    text = script_pages().get("judge_after_verify.sh", "")
    usage = r"(?m)^ *(?:bash )?scripts/judge_after_verify\.sh <agents-judge\.json> <checkout> <record-file>\.\.\."
    assert re.search(usage, text) and "JUDGE_POLL" in text and "JUDGE_DELAY" in text


def test_the_main_session_runs_no_hook_of_a_role_s_unmerged_commit():
    text = (REFERENCES / "launch.md").read_text(encoding="utf-8")
    assert "`git -c core.hooksPath=/dev/null worktree add --detach <dir> <sha>`" in text
    assert "git worktree add" not in text
    rule = "Every git command the main session runs on a role's commit before that commit is merged into the trunk"
    assert rule in text and "`scripts/judge_after_verify.sh`" in text


def test_the_readme_is_an_index_of_at_most_12000_bytes_with_one_line_per_page():
    text = README.read_text(encoding="utf-8")
    assert len(text.encode()) <= 12_000
    assert re.findall(r"(?m)^### .*", text) == []
    lines = re.findall(r"(?m)^- \[`([\w.]+)`\]\(docs/([\w.-]+)\): \S", text)
    assert sorted(name for name, _ in lines) == scripts()
    assert [(n, page) for n, page in lines if page != f"{stem(n)}.md" or not (DOCS / page).is_file()] == []
