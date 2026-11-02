"""The example run folder and the skill's words (spec B1, B4-B8, B13, B14, B16). example/ holds the briefs, settings
and configs of a run with a planner, a plan fixer, a critic, two builders, a verifier and a judge, in the generic form
a new run copies into its run folder (each file with a leading `_`, lessons.md as it is). No file of the skill names
a project of the owner or a home folder, and each rule the spec moves into a brief is in that brief.

  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests/test_skill_example.py
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from transcript_home import SCRIPTS

SKILL = SCRIPTS.parent
EXAMPLE = SKILL / "example"
ROLES = ("planner", "plan-fixer", "critic", "builder-a", "builder-b", "verifier", "judge")
FILES = {
    "README.md",
    "common.md",
    "first-pass-rules.md",
    "handoff-rule.md",
    "lessons.md",
    "agents.json",
    "agents-judge.json",
    "packs.json",
    "sim_bwrap.py",
    *(f"{r}-assignment.md" for r in ROLES),
    *(f"{r}-settings.json" for r in ROLES),
    "launch.md",
    "surface-phrases.en.json",
}
# Joined from parts that are no word of the lists, so that a grep of the template for these words does not find this
# file. HARD words count anywhere, inside a file name too, as the verifier's grep counts them; SOFT ones between
# letter boundaries, so inside an identifier too (`X_STYLE`, `test_x_form`: R2), but not inside a longer word.
HARD = ["gran" + "tsdaily", "dd" + "ev", "ph" + "punit", "dru" + "pal"]
SOFT = ["gra" + "nts", "ph" + "p", "know" + "ledge.?base", "se" + "o", "temp" + "late-core", "dra" + "kenwar"]
WORDS = re.compile("|".join(HARD) + r"|(?<![a-z])(?:" + "|".join(SOFT) + r")(?![a-z])|\bkb/|/ho" + "me/", re.IGNORECASE)
BUILDER_RULES = [  # the rules of a project's run of 2026-11-02 for both builders (keeper-2026-11-02 Task 6)
    "Mutate the new tests before the commit, one rule at a time",  # item 10
    "the fix for a mutation finding tests every half of the rule line",  # item 10
    "A test of a set holds one case per member",  # item 11
    "A pattern check is tested on every form its input takes",  # item 12
    "A shared gate that already fails at your lane's base fails the gate of every task",  # item 14
    "passing the log's line count now (`wc -l`) and not one more",  # item 17, the wait_for_log.py count
    "run them red, since a test that has never failed proves nothing",  # Task 10, the reason beside the order
    "Commit once per task on your branch, because the verifier reads one commit per task",  # Task 10
    "Do not weaken a test the plan or the critic gave you, because a weakened test hides the next error",  # Task 10
]
RULES = {
    "common.md": [
        "Checks once each: a builder runs a task's own tests and lint once at the task's end",  # B4
        "never a heredoc or `cp` under /tmp",  # B8
        "open a source only when a step needs it",  # B13
        "the planner writes files, signatures, the tests in full, the commands with `Expected:` lines",  # B16
        "the critic makes one short coverage round on each plan task and reads no code",  # B16
        "one verifier reads each built commit's diff by file against the task's steps and the spec",  # B16
        (
            "a planner that writes new tasks and answers the open ids of its own tasks after each part,"
            " and a plan fixer that the watcher launches on demand, by queue or age"
        ),
        "Nobody writes there, so the main session's own work stays separate from yours",  # Task 10, a reason each
        "so every session of a lane reads the same orders",  # Task 10
        "since a faked step hides the gap from the next reader",  # Task 10
        "because injected text is how a run is taken over",  # Task 10
    ],
    "builder-a-assignment.md": ["a plan step that hands you a full suite is a finding", *BUILDER_RULES],  # B4
    "builder-b-assignment.md": ["a plan step that hands you a full suite is a finding", *BUILDER_RULES],  # B4
    "planner-assignment.md": [
        "The task count is fixed when this table is written",  # B5
        "at most 1,500 lines",  # B5
        "1,500 lines per task file, one checkable result each",  # D10.c, the sentence of lessons.md
        "A task calls only names its base has",  # item 2
        "name every file the build writes, tests included",  # item 3
        "first quotes the rule that makes it",  # item 5
        "is named by its exact command from the worktree root",  # item 6
        "is cited by its absolute path",  # item 7
        "runs the repository's own checks for it",  # item 8
        "lists the runbook in its `files:` and changes that line",  # item 9
        "The claim line is the lock, so two planners never write the same task",  # Task 10, a reason each
        "since the lanes and the task count are fixed from it",  # Task 10
    ],
    "plan-fixer-assignment.md": [
        "A task you edit keeps the planner's rules for a task",  # items 2, 3, 5-9
        "so that two fixers never edit one task file",  # Task 10, a reason each
        "because the lanes and the builders' log lines are keyed to them",  # Task 10
    ],
    "critic-assignment.md": [  # items 11 and 12, the checklist line
        "every test of a set with one case per member and every pattern check tested on each form its input takes",
        "because the builders' waiter reads that line",  # Task 10, a reason each
        "since they cost a fix round and change no result",  # Task 10
    ],
    "judge-assignment.md": [  # Task 10, a reason each
        "because the main session acts on your verdict alone",
        "because the merge is the main session's",
    ],
    "handoff-rule.md": [
        "a hand-over only past `handoff_at` (250k tokens per call) or `cap` (260k)",  # 2026-11-01
        "because the watcher stops this session next",  # Task 10, a reason beside the order
    ],
    "lessons.md": [
        (
            "Where a vault page and your brief differ, the brief wins, because it records the owner's decisions"
            " for this run; log the difference in your log file"
        ),  # B7, and its reason (Task 10)
        "never list the same file, because two branches that edit one file conflict at the merge",  # Task 10
        "1,500 lines per task file, one checkable result each",  # D10.c
    ],
    "first-pass-rules.md": [
        "Read late and narrow.",  # B13
        "because a remembered flag or version may be wrong and everything built on it is redone",  # Task 10
        "so the critic can re-check each fact",  # Task 10
    ],
    "verifier-assignment.md": [
        "at 1024, 1200 and 1440 px",  # B14
        "because a pair would hide which commit broke a check",  # Task 10, a reason beside the order
        "since a page can pass every test and still look broken",  # Task 10
    ],
}
REFERENCE_RULES = {  # the pages of references/ that carry a rule of the same run (keeper-2026-11-02 Task 6)
    "common-mistakes.md": ["compare the mutated files (sha256) with the runner's copies before editing anything"],  # 13
    "sandbox-and-blindness.md": ["Chromium cannot start inside a role's sandbox"],  # item 16
    "choosing-roles-and-skills.md": [  # item 15, the web layout checklist
        "### Web layout checklist",
        "is a committed test whose first run is red on the decision's own examples",
        "selects each kind of element by its role in the markup, never from a list of classes",
        "counts box edges as lines",
        "### Writing an order",  # Task 10, the owner's order of 2026-11-02
        "states its reason beside it, the failure it prevents or the goal it serves, in one clause",
        (
            "no capitalised alarm word (`MUST`, `NEVER`, `ALWAYS`, `CRITICAL`, `IMPORTANT`),"
            " no exclamation mark and no stacked emphasis"
        ),
        "outside a code span, a fenced block or a `>` quote, and names the file and line",
        "A running pack is not rewritten, so the check holds from the next launch",
    ],
    "preflight-and-capacity.md": [
        "A critic files about 95 ids an hour and one plan fixer answers about 25",  # item 20
        "- `wording`: no pack file of a checked role",  # Task 10, the check of the order
        "It skips when the run has no `_packs.json`, and a running pack is not rewritten",  # Task 10
    ],
    "watching.md": [  # Task 9, a role added in the middle of a run
        "### Adding a role mid-run",
        "gets its first session from `--launch`",
        "`fresh.<role>` text for its later hand-overs",  # V19: the first session gets the first prompt of launch.md
        "A first session does not get that text, because it says a previous session handed over",
        "launches it with the argv of a fresh session and the first prompt of `launch.md`",
        "`--launch` refuses an agent no `Yes:` line names, since the owner is asked before every launch",  # V18
        "--roles <agent> --yes` passes (without `--yes` the pre-flight skips the `Yes:` check)",
        "It refuses an agent that already has a session, since a second one is a copy.",
    ],
}


def load(name: str) -> dict:
    return json.loads((EXAMPLE / name).read_text(encoding="utf-8"))


def read(rel: str) -> str:
    # A file of the skill with its whitespace folded, as the rule test folds a brief: a phrase may wrap at any space
    return " ".join((SKILL / rel).read_text(encoding="utf-8").split())


BRIEFS = [f"example/{r}-assignment.md" for r in ROLES] + ["example/common.md"]


def test_no_file_of_the_skill_names_a_project_of_the_owner_or_a_home_folder():
    files = sorted(p for p in SKILL.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    hits = [
        f"{p.relative_to(SKILL)}: {m.group(0)}"
        for p in files
        for m in WORDS.finditer(p.read_text(encoding="utf-8", errors="replace"))
    ]
    assert hits == []


def test_each_rule_the_spec_moves_into_a_brief_is_in_that_brief():
    def fold(text: str) -> str:
        return " ".join(text.split())

    missing = {
        name: [r for r in rules if fold(r) not in fold((EXAMPLE / name).read_text(encoding="utf-8"))]
        for name, rules in RULES.items()
    }
    assert {name: rules for name, rules in missing.items() if rules} == {}


def test_each_rule_a_project_run_moves_into_a_reference_page_is_on_that_page():
    # The same pin as the test above, for the pages of references/: a later edit cannot drop a rule unnoticed.
    missing = {
        name: [r for r in rules if " ".join(r.split()) not in read(f"references/{name}")]
        for name, rules in REFERENCE_RULES.items()
    }
    assert {name: rules for name, rules in missing.items() if rules} == {}


def test_the_configs_name_every_role_and_only_files_the_example_has():
    agents, judge, packs = load("agents.json"), load("agents-judge.json"), load("packs.json")
    roles = [name.split("/")[-1] for name in agents["agents"]]
    assert agents["cap"] == judge["cap"] == 260_000 and set(ROLES) - {"judge"} <= set(roles)
    assert [name.split("/")[-1] for name in judge["agents"]] == ["judge"]
    assert set(packs["roles"]) == {*roles, "judge"}
    every = {**agents["agents"], **judge["agents"]}
    assert [name for name, agent in every.items() if "<run-dir>" not in agent["add_dirs"]] == []
    named = {agent["settings"] for agent in every.values()} | {f for fs in packs["roles"].values() for f in fs}
    named |= set(re.findall(r"\{run\}/(_[\w.-]+)", json.dumps([agents, judge])))
    assert {name: agent["settings"] for name, agent in every.items()} == {
        name: f"_control/{name.split('/')[-1]}-settings.json" for name in every
    }  # K4: each settings file sits under `_control/`, out of every role's reach
    shipped = {f: re.sub(r"^_(?:control/)?", "", f) for f in named}  # `_control/<x>` and `_<x>` ship as example/<x>
    assert sorted(f for f, s in shipped.items() if f == s or not (EXAMPLE / s).is_file()) == []


def test_every_settings_file_denies_subagents_questions_and_edits_of_the_control_files():
    # An absolute path in a permission rule is `//` and the path without its leading slash; a placeholder stands for
    # an absolute path, so `Edit(/<run-dir>/_*)` is the documented form and `(///` or `(//<` is not.
    must = {
        "Agent",
        "AskUserQuestion",
        "Edit(/<run-dir>/_*)",
        "Write(/<run-dir>/_*)",
        "Edit(/<vault>/**)",
        "Write(/<vault>/**)",
        "Edit(/<sources>/**)",
        "Write(/<sources>/**)",
    }
    rules = {role: load(f"{role}-settings.json")["permissions"] for role in ROLES}
    lacking = {role: sorted(must - set(perms["deny"])) for role, perms in rules.items()}
    assert {role: deny for role, deny in lacking.items() if deny} == {}
    wrong = [r for perms in rules.values() for rs in perms.values() for r in rs if "(///" in r or "(//<" in r]
    assert wrong == []


def test_the_example_readme_lists_every_file_and_every_placeholder_of_the_configs():
    assert {p.name for p in EXAMPLE.iterdir()} == FILES
    readme = (EXAMPLE / "README.md").read_text(encoding="utf-8")
    assert sorted(f for f in FILES - {"README.md"} if f"`{f}`" not in readme) == []
    used = {m for p in EXAMPLE.glob("*.json") for m in re.findall(r"<[a-z][a-z0-9-]*>", p.read_text(encoding="utf-8"))}
    assert sorted(x for x in used if f"`{x}`" not in readme) == []


EXAMPLE_DIR = Path(__file__).resolve().parents[2] / "example"
BLIND = ("Read(~/.claude/projects/**)", "Read(/<run-dir>/_control/**)", "Read(/<checkout>/docs/handoff/**)",
         "Read(//proc/**)", "Bash(claude agents:*)", "Bash(claude logs:*)", "Bash(claude attach:*)", "Bash(ps:*)",
         "Bash(pgrep:*)", "Read(~/.claude/.credentials.json)")  # fmt: skip
SANDBOXED = ("~/.claude/projects", "<run-dir>/_control", "<checkout>/docs/handoff", "~/.claude/.credentials.json")


def test_every_role_is_blind_to_transcripts_control_files_hand_overs_and_processes():
    for role in ROLES:
        settings = json.loads((EXAMPLE_DIR / f"{role}-settings.json").read_text(encoding="utf-8"))
        assert [rule for rule in BLIND if rule not in settings["permissions"]["deny"]] == [], role


def test_every_role_runs_sandboxed_and_no_deny_rule_covers_a_path_it_writes():
    # The sandbox mounts each Edit or Write deny read-only after the paths a role may write, so a deny on an ancestor
    # of one (the checkout over its .git) fails the role's commits.
    for role in ROLES:
        settings = load(f"{role}-settings.json")
        sandbox = settings["sandbox"]
        flags = (sandbox.get("enabled"), sandbox.get("failIfUnavailable"), sandbox.get("allowUnsandboxedCommands"))
        assert flags == (True, True, False), role
        assert [path for path in SANDBOXED if path not in sandbox["filesystem"]["denyRead"]] == [], role
        rules = [r[r.index("(") + 1 : -1] for r in settings["permissions"]["deny"] if r.startswith(("Edit(", "Write("))]
        denied = [r.removeprefix("/").removesuffix("/**") for r in rules]
        writes = sandbox["filesystem"]["allowWrite"]
        assert [(d, w) for d in denied for w in writes if w == d or w.startswith(d + "/")] == [], role


def test_no_brief_names_a_model_and_common_carries_the_sandbox_rule():
    # Owner, 2026-10-29: no role knows which model any session runs on (the model is the manager's setting), and a
    # refused sandbox step is one `SANDBOX:` line that the manager answers, never a workaround.
    for path in sorted(EXAMPLE_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8").lower()
        assert not re.search(r"\b(opus|sonnet|haiku)\b|--model", text), path.name
    common = (EXAMPLE_DIR / "common.md").read_text(encoding="utf-8")
    assert "`SANDBOX: <what was refused> — <why the step needs it>`" in common
    assert "COPY-REQUEST: <stage> -> <worktree>" in common
    assert "Models are the manager's business" in common


def test_the_checkout_is_closed_to_the_edit_tools_by_folder_and_by_file():
    # A `/**` rule never matches the top-level file itself (gitignore matching), so a role that keeps `<checkout>/.git`
    # writable denies the checkout's folders with `/**` and its files with a bare rule; the others deny it whole.
    for role in ROLES:
        deny = load(f"{role}-settings.json")["permissions"]["deny"]
        if "Edit(/<checkout>/<checkout-entry>/**)" in deny:
            for tool in ("Edit", "Write"):
                assert f"{tool}(/<checkout>/<checkout-entry>/**)" in deny, role
                assert f"{tool}(/<checkout>/<checkout-file>)" in deny, role
        else:
            assert "Edit(/<checkout>/**)" in deny and "Write(/<checkout>/**)" in deny, role


CHECKOUT = SKILL.parents[2]
# role: (the pinned ECC copies its `Spec:` line names, the skills its `Skills:` line names); spec 4.6 and the 4.7 table
DOMAIN = {
    "planner": (["architect.md", "code-architect.md"], ["python-testing"]),
    "plan-fixer": ([], ["python-testing"]),
    "critic": (["code-reviewer.md", "silent-failure-hunter.md"], []),
    "builder-a": (["tdd-guide.md"], ["python-patterns", "python-testing"]),
    "builder-b": (["tdd-guide.md"], ["python-patterns", "python-testing"]),
    "verifier": (["pr-test-analyzer.md", "security-reviewer.md", "silent-failure-hunter.md"], []),
    "judge": ([], []),
}


def load_catalogue():
    # The recipe of test_catalogue.py, inside the tests, so this file's other tests run before catalogue.py exists.
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("catalogue", SCRIPTS / "manager" / "catalogue.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look string annotations up in sys.modules
    spec.loader.exec_module(module)
    return module


def section(name: str, heading: str) -> str:
    lines = (EXAMPLE / name).read_text(encoding="utf-8").splitlines()
    start = lines.index(heading)
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


def test_every_brief_ends_with_one_domain_section_naming_the_ecc_texts_and_skills_of_its_work():
    # Spec 4.6, 4.7 and 10.17 with answer 9a: `catalogue.py briefs` finds no problem in the example, and each brief's
    # last section names the pinned copies and the skills of its row (a critic with code-reviewer only, a verifier
    # without security-reviewer, a builder without python-patterns, or the section placed before `## Rules` each fail
    # here).
    catalogue = load_catalogue()
    assert catalogue.check_briefs(EXAMPLE, CHECKOUT) == []
    found = {}
    for role in ROLES:
        name = f"{role}-assignment.md"
        text = section(name, catalogue.SECTION)
        assert (EXAMPLE / name).read_text(encoding="utf-8").rstrip().endswith(text.rstrip()), f"{name}: not last"
        lines = text.splitlines()
        spec = catalogue.parse_spec(next(x for x in lines if x.startswith("Spec: ")))
        skills = catalogue.parse_skills(next(x for x in lines if x.startswith("Skills: ")))
        found[role] = (
            sorted({Path(path).name for path, _, _ in spec["ranges"]}),
            sorted(Path(path).parent.name for path, _ in skills["skills"]),
        )
    assert found == DOMAIN


def test_the_model_sits_in_each_settings_file_and_the_briefs_ask_for_checklist_items_and_request_points():
    # 10.15: the model is the role's setting (which no role reads), never a brief's text or a flag; 10.17: every critic
    # and verifier finding cites its checklist item, under the proof rule; Task 3's contract: a COPY, CHECKOUT or FF
    # point is a `Request point:` line of a task file (the model under "env", or a sentence in another section, fail).
    assert {role: load(f"{role}-settings.json").get("model") for role in ROLES} == dict.fromkeys(ROLES, "<model>")
    assert "`Checklist: <file>:<line>`" in section("common.md", "## Proof rule (binding)")
    point = "`Request point: <COPY-REQUEST|CHECKOUT-REQUEST|FF-REQUEST> — <why>`"
    assert point in section("planner-assignment.md", "## The plan: part files")


def test_every_settings_file_blanks_the_commit_trailer_and_carries_no_attribution():
    # The owner's order of 2026-10-30 (lessons.md:31): Claude Code's default `Co-Authored-By: <model>` trailer names the
    # model that no role may know (83bf336 on feat/readme leaked one). In 2.1.314 `"includeCoAuthoredBy": false` blanks
    # it unless a valid `attribution` object is set (that wins), so the examples carry the key and no such object.
    settings = {role: load(f"{role}-settings.json") for role in ROLES}
    assert [role for role, s in settings.items() if s.get("includeCoAuthoredBy") is not False] == []
    assert [role for role, s in settings.items() if "attribution" in s] == []


# Spec 005, requirement 7c: the cache TTL per role sits in the role's settings `env` (Claude Code 2.1.316 reads
# CLAUDE_CODE_PROMPT_CACHE_TTL, "5m" or "1h"): 5m for every role since 2026-11-01 (owner), the waiters returning within
# 3.5 minutes; the 1-hour TTL is rejected.
TTL_KEY = "CLAUDE_CODE_PROMPT_CACHE_TTL"
TTL = {
    "planner": "5m",
    "builder-a": "5m",
    "builder-b": "5m",
    "verifier": "5m",
    "critic": "5m",
    "plan-fixer": "5m",
    "judge": "5m",
}


def test_every_settings_file_sets_the_cache_ttl_of_its_role_beside_the_compaction_override():
    envs = {role: load(f"{role}-settings.json").get("env", {}) for role in ROLES}
    assert {role: env.get(TTL_KEY) for role, env in envs.items()} == TTL
    assert [role for role, env in envs.items() if env.get("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE") != ""] == []


def test_launch_md_has_a_row_per_cache_ttl_that_names_the_roles_of_each():
    text = (SKILL / "references" / "launch.md").read_text(encoding="utf-8")
    rows = dict(re.findall(r"(?m)^\| `(5m|1h)` \| ([^|]+) \|", text))
    assert TTL_KEY in text and sorted(rows) == ["1h", "5m"]

    def names(role: str, ttl: str) -> bool:
        return re.search(rf"(?<![\w-]){role}(?![\w-])", rows[ttl]) is not None

    # each role is in the row of its own TTL and not in the other
    assert [role for role, ttl in TTL.items() if not names(role, ttl)] == []
    assert [role for role, ttl in TTL.items() if names(role, "1h" if ttl == "5m" else "5m")] == []


SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")  # a code span, read as evals/graders/pipeline_plan.py reads one
READY = "python3 /r/wait_for_ready.py --critique /r/critique.md --response /r/critique-response.md"
INDEX = "--index /p/docs/exec-plans/active/demo/00-index.md"  # the lane waits by its own build order (2026-11-02)
WAITERS = {  # V7, spec 10.19: every waiter of a brief as its agent runs it (<run-dir> /r, <lines> 13, <N> 3)
    "planner-assignment.md": [  # C18, C42: the critic sets line 1 in place; the launched fixer waits on none
        'python3 /r/wait_for_log.py /r/critique.md 13 --first "STATUS: reviewed through Task 3" --first "STATUS: done"',
    ],
    "critic-assignment.md": ["python3 /r/wait_for_log.py /r/plan-log.md 13"],
    "builder-a-assignment.md": [f"{READY} {INDEX} --lane a 3", "python3 /r/wait_for_log.py /r/build-log-b.md 13"],
    "builder-b-assignment.md": [f"{READY} {INDEX} --lane b 3", "python3 /r/wait_for_log.py /r/build-log-a.md 13"],
    "verifier-assignment.md": [f"python3 /r/wait_for_log.py /r/build-log-{lane}.md 13" for lane in "ab"],
}


def test_every_waiter_a_brief_names_is_given_in_full_with_a_placeholder_for_each_word_the_agent_fills_in():
    # 10.19: the pipeline check passes a waiter only as a brief gives it, each <placeholder> standing for one word
    def forms(name: str) -> list[re.Pattern[str]]:
        text = " ".join((EXAMPLE / name).read_text(encoding="utf-8").split())
        spans = [m.group(2) for m in SPAN.finditer(text) if re.search(r"wait[\w-]*\.(?:py|sh)", m.group(2))]
        return [re.compile(re.sub(r"<[^<>]*>", r"\\S+", re.escape(span))) for span in spans]

    missing = {
        name: [c for c in commands if not any(f.fullmatch(c) for f in forms(name))]
        for name, commands in WAITERS.items()
    }
    assert {name: commands for name, commands in missing.items() if commands} == {}


def test_the_critic_reviews_no_diff_and_the_verifier_reads_it():
    # Spec Decided 3: the critic keeps its coverage round and opens no code; the verifier reads each commit's diff.
    critic = read("example/critic-assignment.md")
    for gone in ("diff review", "diff round", "git show", "build-log", "plan-fixer"):
        assert gone not in critic.lower(), gone
    assert "never open a checkout's code" in critic and "message `<project>/planner`" in critic
    assert "`STATUS: plan complete` or `STATUS: done` and every id is answered" in critic
    assert "diff review" not in read("example/handoff-rule.md")
    assert "then reviews each built commit's diff" not in read("example/common.md")
    verifier = read("example/verifier-assignment.md")
    assert "read the diff by file (`git show <sha> --stat`" in verifier and "plan-fixer" not in verifier
    assert "`#### V<n> — (code)|(plan)|(spec) <title>`" in verifier
    assert "`(spec)` when the step is built as the plan says and the spec says otherwise" in verifier
    assert "`<project>/planner` while line 1 of `critique-response.md` is not `STATUS: done`" in verifier


def test_the_example_verifier_adds_the_brief_cause_for_a_run_without_a_planner_and_skill_md_does_not():
    """R8 (specs/003-pipeline-economy): `(brief)` joins the heading pattern for a run without a planner; the pipeline
    SKILL.md describes has a planner, so its pattern stays."""
    verifier = read("example/verifier-assignment.md")
    assert "`#### V<n> — (code)|(plan)|(spec) <title>` (`(brief)` too in a run without a planner)" in verifier
    assert "in a run without a planner also `(brief)` when the fix is in a brief or a rule, not in the code" in verifier
    assert "(brief)" not in read("SKILL.md")


def test_no_brief_names_an_r_id_and_each_finding_on_a_commit_is_a_v_id():
    # R ids are retired (spec Decided 3): no brief files, waits for or answers one; old runs still parse.
    for name in BRIEFS:
        assert not re.search(r"R<n>|#### R|\(diff\)", read(name)), name
    for lane in "ab":
        assert "log `V<n>: fixed — <sha>`" in read(f"example/builder-{lane}-assignment.md"), lane
        assert "Fix open V findings first" in load("agents.json")["fresh"][f"builder-{lane}"], lane  # its launch prompt
    assert "`#### V<n> — (spec)` in `verify.md`" in read("example/plan-fixer-assignment.md")
    assert "(C, A, V, B)" in read("example/handoff-rule.md")  # a note's open threads carry no R id


def test_every_brief_has_a_reading_budget_and_the_builders_and_the_verifier_state_their_unit():
    # D10.a (owner, 2026-10-30 01:45 UTC): a role reads by ranges, one unit at a time, with its lines per unit
    budgets = {}
    for path in sorted(EXAMPLE.glob("*-assignment.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        heading = next((line for line in lines if line.startswith("## Reading budget")), None)
        budgets[path.name] = " ".join(section(path.name, heading).split()) if heading else ""
    assert sorted(budgets) == sorted(f"{r}-assignment.md" for r in ROLES)
    assert [name for name, text in budgets.items() if not text] == []
    for role, unit in [("builder-a", "step"), ("builder-b", "step"), ("verifier", "finding")]:
        text = budgets[f"{role}-assignment.md"]
        assert f"one {unit} at a time" in text and f"at most 200 more lines per {unit}" in text, role
        assert "never a file over 200 lines whole" in text, role


def test_sim_bwrap_masks_a_file_in_deny_read_with_dev_null_and_a_folder_with_a_tmpfs(tmp_path):
    """J6 (judge.md of manager-build-2026-10-29, #### J6) and Step 1: Claude Code 2.1.314 binds /dev/null over a file
    in denyRead and mounts a tmpfs over a folder; the sim put a tmpfs on both, which bwrap refuses for a file."""
    secret, folder, cwd, control = tmp_path / "secret.json", tmp_path / "hidden", tmp_path / "wt", tmp_path / "_control"
    for d in (folder, cwd, control, tmp_path / "bin"):
        d.mkdir()
    secret.write_text("{}\n", encoding="utf-8")
    settings = {"permissions": {"deny": []}, "sandbox": {"filesystem": {"denyRead": [str(secret), str(folder)]}}}
    (control / "s.json").write_text(json.dumps(settings), encoding="utf-8")
    agents = {"agents": {"t/a": {"cwd": str(cwd), "add_dirs": [], "settings": "_control/s.json"}}}
    (control / "_agents.json").write_text(json.dumps(agents), encoding="utf-8")
    fake = tmp_path / "bin" / "bwrap"  # a nested bwrap cannot make namespaces here: the fake prints the argv it gets
    fake.write_text(f"#!{sys.executable}\nimport sys\nprint(' '.join(sys.argv[1:]))\n", encoding="utf-8")
    fake.chmod(0o755)
    env = {**os.environ, "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}"}
    argv = [sys.executable, "-I", str(EXAMPLE / "sim_bwrap.py"), str(control / "_agents.json"), "t/a", "true"]
    out = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=30, check=False).stdout
    assert f"--ro-bind /dev/null {secret} " in out and f"--tmpfs {folder} " in out
    assert f"--tmpfs {secret} " not in out


def test_both_example_configs_give_every_lane_its_pack_and_the_cache_flags():
    """The cache and context rules of 2026-11-01 (owner), in the configs a run copies: every agent's own pack is the
    file make_pack.py writes for its role and holds its mark; `common` carries the three flags; `handoff_at` and `cap`
    lie above the compaction point; every fresh text names its assignment as held in the system prompt."""
    import json as _json
    import sys as _sys

    _sys.path.insert(0, str(SKILL / "scripts"))
    import make_pack

    packs = _json.loads((SKILL / "example" / "packs.json").read_text(encoding="utf-8"))
    for name in ("agents.json", "agents-judge.json"):
        config = _json.loads((SKILL / "example" / name).read_text(encoding="utf-8"))
        common = config["common"]
        assert common[common.index("--autocompact") + 1] == "235000", name
        assert "--exclude-dynamic-system-prompt-sections" in common, name
        assert common[common.index("--system-prompt-snapshot") + 1] == "on", name
        assert 197_000 < config["handoff_at"] < config["cap"], name
        for agent, entry in config["agents"].items():
            role = agent.split("/")[-1]
            assert role in packs["roles"], agent
            head = make_pack.HEAD.splitlines()[0].format(name=packs["name"], role=role)
            assert entry["extra_prompt"] == {"file": f"_pack-{role}.md", "mark": head.lstrip("# ")}, agent
        for role, text in config["fresh"].items():
            assert f"{{run}}/_{role}-assignment.md" in text and "do not read them again" in text, role
