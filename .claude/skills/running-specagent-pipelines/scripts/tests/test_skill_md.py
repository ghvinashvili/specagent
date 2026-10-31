"""Tests of SKILL.md and its reference files (moved from test_docs.py in manager-build Task 1): SKILL.md stays under
12,000 bytes with six sections of the source and a list of the reference files that hold the rest, names only files
the skill has, names no model (the model is each role's setting, which no role reads), and points to the selection
rules, whose page holds the bounds and the two domain lines.

  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests/test_skill_md.py
"""

import re

from transcript_home import SCRIPTS

SKILL = SCRIPTS.parent
REFERENCES = SKILL / "references"
MODEL = re.compile(r"\b(opus|sonnet|haiku)\b|--model")  # the regex of test_skill_example.py:157, on lower-cased text
# The paths a text names under the skill: the regex of test_docs.py:159 with (?<![\w/]) for \b, so that a path inside
# a longer path (docs/references/README.md) is a checkout file, not one of the skill's (C13).
NAMED = re.compile(r"(?<![\w/])(?:scripts|example|references)/[\w./-]*\w")
KEPT = (
    "Overview",
    "Owner rules (binding; they override defaults you may know)",
    "Pipeline",
    "Briefs",
    "Waiting, parking, watching",
    "Changing orders",
)
MOVED = {
    "launch.md": "Launch",
    "context-and-cost.md": "Context and cost",
    "measuring.md": "Measuring the pipeline",
    "common-mistakes.md": "Common mistakes",
    "sandbox-and-blindness.md": "Blind to models and authors, inside the sandbox",
    "preflight-and-capacity.md": "Pre-flight and capacity",
    "choosing-roles-and-skills.md": "Choosing roles and skills",
    "watching.md": "Watcher, monitor and collector",
}


def test_skill_md_keeps_six_sections_and_each_moved_section_is_one_reference_file():
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert len(skill.encode()) <= 12_000
    assert re.search(r"(?m)^name: (\S+)$", skill).group(1) == SKILL.name
    assert re.findall(r"(?m)^## (.*)$", skill) == [*KEPT, "References"]
    assert {p.name: p.read_text(encoding="utf-8").splitlines()[0] for p in REFERENCES.glob("*.md")} == {
        name: f"# {title}" for name, title in MOVED.items()
    }
    assert [
        h
        for p in REFERENCES.glob("*.md")
        for h in re.findall(r"(?m)^#{1,2} .*", p.read_text(encoding="utf-8"))
        if h.lstrip("# ") not in MOVED.values()
    ] == []


def test_skill_md_and_its_references_name_only_files_the_skill_has_and_the_current_rules():
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    texts = [skill, *(p.read_text(encoding="utf-8") for p in sorted(REFERENCES.glob("*.md")))]
    named = {x for text in texts for x in NAMED.findall(text)}
    assert sorted(p for p in named if not (SKILL / p).exists()) == []
    linked = set(re.findall(r"\]\((references/[\w.-]+\.md)\)", skill))
    assert linked == {f"references/{name}" for name in MOVED}
    gone = ("watch_agents_cap.py", "watch_agents_project.py", "SKILL.md.proposed")
    assert [x for x in gone if any(x in text for text in texts)] == []
    assert "200k" in skill and "300k" not in skill  # B6: the owner's cap since 2026-10-29 (C11)
    assert "`B<n>: sent to plan-fixer`" in skill and "plan fixer" in skill  # lessons.md: the plan-fixer role


def test_skill_md_and_its_references_name_no_model_and_the_settings_file_carries_it():
    # Blind to models (10.15; vault decisions/global/blind-to-models-and-authors.md): the manager sets each role's model
    # in its settings file under `_control/`, which no role can read; no brief, flag or text of the skill names one.
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    texts = {"SKILL.md": skill, **{p.name: p.read_text(encoding="utf-8") for p in sorted(REFERENCES.glob("*.md"))}}
    assert sorted(name for name, text in texts.items() if MODEL.search(text.lower())) == []
    rows = [line.lower() for line in skill.splitlines() if "the role's settings file" in line]
    assert len(rows) == 1
    needed = ("never in a brief, a flag or this skill", "judgment", "mechanical", "`_control/`")
    assert [x for x in needed if x not in rows[0]] == []


def test_the_fixed_judgment_list_drops_the_builder_the_effort_stays_max_and_the_criteria_page_is_unchanged():
    # R6 (spec 003): the class follows the work, so the builder is no longer a fixed judgment role (the owner,
    # 2026-10-30); the effort is never lowered, and the selection rule (criterion 1 of the page) stands as it was.
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert skill.count("fixer, critic, builder") == 0
    assert skill.count("fixer, critic, verifier, judge") == 1
    assert skill.count("Effort max for every role") == 1
    page = " ".join((REFERENCES / "choosing-roles-and-skills.md").read_text(encoding="utf-8").split())
    assert "in doubt, the judgment class; the effort is never lowered." in page


def test_the_model_class_text_names_three_classes_in_the_rule_row_the_launch_page_and_the_example_readme():
    # R6, the owner's order of 2026-10-30 (lessons.md): the class text names three classes by the work, not two; the
    # model names stay the manager's (the launch table's message), so no skill file spells one (the test above).
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    row = next(line for line in skill.splitlines() if "the role's settings file" in line)
    classes = (
        "specification (spec writer)",
        "judgment (planner, plan fixer, critic, verifier, judge, writer for readers)",
        "mechanical (builder checked by a verifier, extraction, conversion, data collection)",
    )
    assert [x for x in classes if x not in row] == []
    assert "any role whose mistake is expensive" not in row
    launch = " ".join((REFERENCES / "launch.md").read_text(encoding="utf-8").split())
    readme = " ".join((SKILL / "example" / "README.md").read_text(encoding="utf-8").split())
    for text in (launch, readme):
        assert "specification, judgment or mechanical" in text
    assert 'set `"model"` by the role\'s class' in launch


def test_the_launch_blindness_and_preflight_pages_and_the_example_readme_name_the_trailer_key():
    # The owner's order of 2026-10-30 (lessons.md:31): every role's settings carry `"includeCoAuthoredBy": false`, so a
    # commit never names the model in a `Co-Authored-By` trailer, and the pre-flight's `blind` check fails a file without
    # it. The key's name is no model name (the test above); SKILL.md stays at its byte limit and says nothing of it.
    key = '`"includeCoAuthoredBy": false`'
    pages = [REFERENCES / name for name in ("launch.md", "sandbox-and-blindness.md", "preflight-and-capacity.md")]
    pages.append(SKILL / "example" / "README.md")
    text = {page.name: " ".join(page.read_text(encoding="utf-8").split()) for page in pages}
    assert [name for name, page in text.items() if key not in page] == []
    page = text["preflight-and-capacity.md"]
    bullet = page[page.index("- `blind`:") : page.index("- `ancestor`:")]
    assert key in bullet and "`attribution` key" in bullet  # V1: the check holds the rule's second half as well


def test_skill_md_names_the_domain_lines_and_the_selection_page_holds_the_bounds_and_both_none_forms():
    # Spec 3.1, 3.8, 4.6 and 4.7 with answer 9a: the runbook sentence is gone; the page names the script and the figures.
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "`Spec:`" in skill and "`Skills:`" in skill
    assert "docs/runbooks/README.md" not in skill
    page = (REFERENCES / "choosing-roles-and-skills.md").read_text(encoding="utf-8")
    needed = ("scripts/manager/catalogue.py", "10,000", "13,000", "2,500", "Spec: none — ", "Skills: none — ")
    assert [x for x in needed if x not in page] == []


def test_a_path_inside_a_checkout_path_is_not_a_skill_path():
    # C13: the page of 5a names docs/references/README.md, a checkout file; with \b the regex read
    # references/README.md in it, a skill file that does not exist.
    found = NAMED.findall("see docs/references/README.md, (references/launch.md) and `scripts/x.py`")
    assert found == ["references/launch.md", "scripts/x.py"]


def test_skill_md_names_the_manager_tools_and_the_third_watcher_and_its_page_holds_the_rest():
    # Task 11 (K9, K10): the duty list, the monitor and the collector by command; the watcher's third version (the
    # hand-over at a unit's end past handoff_at, orders acknowledged by a line, the registry, exit 4 without a changed
    # brief); the manager's own measures. The v2 rule that a changed brief exits 4 is gone; the page keeps the rest.
    skill = " ".join((SKILL / "SKILL.md").read_text(encoding="utf-8").split())
    needed = (
        "`python3 -I scripts/duty_list.py extract <plan-dir> --out <run-dir>/_control/duties.md`",
        "`python3 -I scripts/monitor_records.py watch <run-dir>`",
        "`scripts/collect_run.py` (a dry run, then `--apply --yes <digest>`",
        "`handoff_at` (150000)",
        "`_control/registry.json`",
        "`ACK <msg_id>`",
        "`python3 -I scripts/watch_agents.py --order <agent> <text> <agents.json>`",
        "exits 4 only when a settings file or the extra prompt file changed or a brief was removed",
        "a changed brief is reloaded",
        "`scripts/manager/measure_manager.py`",
    )
    assert [x for x in needed if x not in skill] == []
    assert "(a settings file, a brief) changed" not in skill and "Pause the watcher" not in skill
    page = " ".join((REFERENCES / "watching.md").read_text(encoding="utf-8").split())
    kept = ("exit 3 when", "exit 4 when", "`ack_resends`", "`--apply --yes <digest>`", "three runs applied with a yes")
    assert [x for x in kept if x not in page] == []


def test_skill_md_gives_the_critic_the_plan_and_the_verifier_the_diff():
    # Spec Decided 3: one reader per commit; R ids retired; a V id has one of three causes.
    skill = " ".join((SKILL / "SKILL.md").read_text(encoding="utf-8").split())
    assert "own clean worktree; reads the diff by file; findings V<n> (code)|(plan)|(spec) with a repro;" in skill
    assert "tags each finding `(code)`, `(plan)` or `(spec)`" in skill and "R ids" not in skill
    assert "- The critic makes one coverage round per task (C and A ids) and reads no code; the verifier" in skill


def test_skill_md_sends_the_main_session_to_its_page_and_the_lessons_page():
    """J10 (judge.md of manager-build-2026-10-29, #### J10): nothing a fresh main session loads pointed it to its own
    page or to the lessons page."""
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "The main session is the manager: it first reads `docs/roles/manager-chat.md` and" in text
    assert "`<vault>/decisions/global/manager-lessons.md`." in text


def test_the_watcher_start_lines_tee_to_the_run_folders_watch_log():
    # Judge J5 of the pipeline-fold run: score_run.py reads <run>/_watch.log, so the start line must write it.
    skill = " ".join((SKILL / "SKILL.md").read_text(encoding="utf-8").split())
    readme = " ".join((SKILL / "example" / "README.md").read_text(encoding="utf-8").split())
    assert "`python3 -I scripts/watch_agents.py <agents.json> 2>&1 | tee -a <run-dir>/_watch.log`" in skill
    assert (
        "`python3 -I <skill-dir>/scripts/watch_agents.py <run-dir>/_control/_agents.json 2>&1 | tee -a "
        "<run-dir>/_watch.log`" in readme
    )
