"""The manager chat's first reading names the pipeline skill before the harness's stage runner.

On 2026-10-31 a project's manager chat read the map line that named the harness first and ran a day's work as
`harness launch` stages, the planner alone and the critic waiting, the form the owner had decided against (the
chat-agent pipeline stays, 2026-10-29). CLAUDE.md and docs/roles/manager-chat.md now say which pipeline a project's
work uses; this test keeps the sentences, in the template and in every project that copies the files.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ".claude/skills/running-specagent-pipelines/"


def test_claude_md_names_the_skill_before_the_harness_stage_runner():
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert SKILL in text, "CLAUDE.md names the pipeline skill"
    assert "docs/roles/manager-chat.md" in text, "CLAUDE.md names the manager chat's page"
    assert text.index(SKILL) < text.index("harness launch"), "the skill comes before the harness's launch command"
    assert "unless the owner names a harness run" in text


def test_manager_chat_page_rules_out_harness_stages_for_project_work():
    text = (ROOT / "docs" / "roles" / "manager-chat.md").read_text(encoding="utf-8")
    assert "never through the harness's stage runner" in text


def test_manager_chat_page_forbids_messages_on_routine_events():
    text = (ROOT / "docs" / "roles" / "manager-chat.md").read_text(encoding="utf-8")
    assert "No message on a routine event" in text
    assert "a background wake ends with no text at all" in text


def test_manager_chat_page_balances_roles_by_their_queues():
    text = (ROOT / "docs" / "roles" / "manager-chat.md").read_text(encoding="utf-8")
    assert (
        "starts one more\n  session of the role that is behind" in text
        or "one more session of the role that is behind" in text.replace("\n  ", " ")
    )
    assert "stops it when the queue drains" in text


def test_harness_manager_page_sends_project_work_to_the_skill():
    text = (ROOT / "docs" / "roles" / "MANAGER.md").read_text(encoding="utf-8")
    assert "never through these stages by default" in text
    assert "docs/roles/manager-chat.md" in text
