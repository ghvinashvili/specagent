"""The hooks under .claude/hooks are plain scripts: each test feeds one its JSON on stdin and reads what it prints."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[3] / ".claude" / "hooks"


def run_hook(name: str, payload: dict, env: dict | None = None) -> dict | None:
    res = subprocess.run(
        [sys.executable, str(HOOKS / name)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
        env={"PATH": "/usr/bin:/bin", **(env or {})},
    )
    return json.loads(res.stdout) if res.stdout.strip() else None


def wrapped(command: str) -> str | None:
    out = run_hook("compact-output.py", {"tool_name": "Bash", "tool_input": {"command": command}})
    return out["hookSpecificOutput"]["updatedInput"]["command"] if out else None


def test_only_a_plain_test_command_is_rewritten():
    assert wrapped("uv run pytest -q packages/harness")
    assert wrapped("pytest -q")
    assert wrapped("uv run ruff check .") is None
    assert wrapped("uv run pytest -q | tail -3") is None  # the session already chose what to see


def test_a_test_run_keeps_its_exit_code_and_leaves_the_full_output_where_a_role_session_can_read_it(tmp_path: Path):
    stage = tmp_path / "stage"
    (stage / "logs").mkdir(parents=True)
    script = wrapped("pytest -q").replace("( pytest -q\n)", "( echo one failure; echo FAILED test_x; exit 3\n)")
    res = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": "/usr/bin:/bin", "HARNESS_STAGE_DIR": str(stage)},
    )
    assert res.returncode == 3 and "FAILED test_x" in res.stdout
    logs = list((stage / "logs").iterdir())
    assert len(logs) == 1 and f"full output: {logs[0]} (exit 3)" in res.stdout
    assert logs[0].read_text() == "one failure\nFAILED test_x\n"


def test_a_long_output_is_cut_to_its_failures_and_its_tail(tmp_path: Path):
    lines = "for i in $(seq 1 200); do echo line $i; done; echo FAILED test_y; echo 1 failed; exit 1"
    script = wrapped("pytest -q").replace("( pytest -q\n)", f"( {lines}\n)")
    res = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": "/usr/bin:/bin", "TMPDIR": str(tmp_path)},
    )
    assert res.returncode == 1 and "FAILED test_y" in res.stdout and "line 50\n" not in res.stdout
    assert f"full output: {tmp_path}" in res.stdout  # no stage directory: a temporary file


def test_a_session_with_a_checkout_touches_the_repository_only_from_inside_it(tmp_path: Path):
    root, stage = tmp_path / "repo", tmp_path / "runs" / "r1" / "stages" / "verify"
    (root / "packages").mkdir(parents=True)
    stage.mkdir(parents=True)
    env = {"HARNESS_RUN_DIR": str(stage.parents[1]), "HARNESS_WORKTREE": "r1-verify", "CLAUDE_PROJECT_DIR": str(root)}

    def decision(tool: str, tool_input: dict, cwd: Path = root, env: dict = env) -> str | None:
        out = run_hook("guard-checkout.py", {"tool_name": tool, "tool_input": tool_input, "cwd": str(cwd)}, env)
        return out["hookSpecificOutput"]["permissionDecision"] if out else None

    assert decision("Bash", {"command": "uv run pytest -q"}) == "deny"  # the shared checkout is the base
    assert decision("Read", {"file_path": str(root / "packages" / "x.py")}) == "deny"
    assert decision("Grep", {"pattern": "count"}) == "deny"  # no path: the search would run in the shared checkout
    assert decision("Read", {"file_path": str(stage / "prompt.md")}) is None  # its own first message and inputs
    inside = root / ".claude" / "worktrees" / "r1-verify"
    assert decision("Bash", {"command": "uv run pytest -q"}, cwd=inside) is None
    assert decision("Read", {"file_path": str(inside / "packages" / "x.py")}, cwd=inside) is None
    no_checkout = {k: v for k, v in env.items() if k != "HARNESS_WORKTREE"}
    assert decision("Bash", {"command": "ls"}, env=no_checkout) is None  # a unit without a checkout is not held


def test_a_shell_that_left_its_checkout_can_come_back(tmp_path: Path):
    """Seen live: a planner ran `cd` into its stage directory; every later command was refused with "call
    EnterWorktree", EnterWorktree answered "already in a worktree session", and the session could only escalate."""
    root, stage = tmp_path / "repo", tmp_path / "runs" / "r1" / "stages" / "plan"
    inside = root / ".claude" / "worktrees" / "r1-plan"
    (root / "packages").mkdir(parents=True)
    stage.mkdir(parents=True)
    env = {"HARNESS_RUN_DIR": str(stage.parents[1]), "HARNESS_WORKTREE": "r1-plan", "CLAUDE_PROJECT_DIR": str(root)}

    def answer(tool: str, tool_input: dict, cwd: Path) -> dict | None:
        out = run_hook("guard-checkout.py", {"tool_name": tool, "tool_input": tool_input, "cwd": str(cwd)}, env)
        return out["hookSpecificOutput"] if out else None

    # before the checkout exists the only way in is EnterWorktree, also for a command that asks to go there
    refused = answer("Bash", {"command": f"cd {inside} && ls"}, stage)
    assert refused["permissionDecision"] == "deny" and "EnterWorktree" in refused["permissionDecisionReason"]
    (inside / "packages").mkdir(parents=True)
    # the shell stands in the stage directory: what it does there is its own business
    assert answer("Bash", {"command": "ls input/read/probes"}, stage) is None
    assert answer("Read", {"file_path": str(inside / "packages" / "x.py")}, stage) is None  # its own checkout
    assert answer("Bash", {"command": f"cd {inside} && uv run pytest -q"}, stage) is None  # the way back
    assert answer("Bash", {"command": f'cd "{inside}"'}, root) is None
    # the shared checkout stays closed from there, and the refusal says how to get back
    reach = answer("Bash", {"command": f"cat {root}/packages/x.py"}, stage)
    assert reach["permissionDecision"] == "deny" and f"cd {inside}" in reach["permissionDecisionReason"]
    assert answer("Read", {"file_path": str(root / "packages" / "x.py")}, stage)["permissionDecision"] == "deny"
    assert answer("Bash", {"command": "uv run pytest -q"}, root)["permissionDecision"] == "deny"
    # the project directory may already be the checkout: the repository root is still found
    moved = {**env, "CLAUDE_PROJECT_DIR": str(inside)}
    out = run_hook(
        "guard-checkout.py", {"tool_name": "Bash", "tool_input": {"command": "ls"}, "cwd": str(stage)}, moved
    )
    assert out is None


def _stop_case(tmp_path: Path, status: str, failing: list[dict]) -> tuple[Path, dict]:
    """A role session about to stop: its result, and a `harness` that answers `gate --preview` with `failing`."""
    root, stage = tmp_path / "repo", tmp_path / "runs" / "r1" / "stages" / "plan"
    (root / "schemas").mkdir(parents=True)
    schema = HOOKS.parents[1] / "schemas" / "stage-result.schema.json"
    (root / "schemas" / "stage-result.schema.json").write_text(schema.read_text(encoding="utf-8"), encoding="utf-8")
    fake = root / ".venv" / "bin" / "harness"
    fake.parent.mkdir(parents=True)
    fake.write_text('#!/bin/sh\necho "$@" >> "$0.calls"\ncat "$0.out"\n', encoding="utf-8")
    fake.chmod(0o755)
    (fake.parent / "harness.out").write_text(json.dumps({"ok": not failing, "failing": failing}), encoding="utf-8")
    stage.mkdir(parents=True)
    doc = {"schema_version": 1, "run_id": "r1", "stage": "plan", "role_type": "planner", "status": status}
    doc.update(outputs=[], summary="s", evidence=[], open_questions=[])
    (stage / "result.json").write_text(json.dumps(doc), encoding="utf-8")
    env = {"HARNESS_RUN_DIR": str(stage.parents[1]), "HARNESS_STAGE": "plan", "HARNESS_MODE": "bg"}
    return stage, {**env, "CLAUDE_PROJECT_DIR": str(root)}


def test_a_session_that_says_complete_is_held_to_its_own_gate(tmp_path: Path):
    untried = {"name": "the design was tried before the plan was written", "passed": False, "detail": "trial.patch"}
    stage, env = _stop_case(tmp_path, "complete", [untried])
    out = run_hook("stop-gate.py", {}, env)
    assert (
        out["decision"] == "block" and "the design was tried before the plan was written (trial.patch)" in out["reason"]
    )
    assert "the gate of stage plan would refuse this work" in out["reason"]
    calls = (Path(env["CLAUDE_PROJECT_DIR"]) / ".venv" / "bin" / "harness.calls").read_text(encoding="utf-8")
    assert calls == "gate --preview --run r1 --stage plan\n"
    # the count is kept where the session can neither read nor write: the run's logs (04/F10)
    assert (stage.parents[1] / "logs" / "stop-gate" / "plan.holds").read_text(encoding="utf-8") == "1"
    for _ in range(2):
        assert run_hook("stop-gate.py", {}, env)["decision"] == "block"
    assert run_hook("stop-gate.py", {}, env) is None  # held three times: the gate outside the session decides now


def test_a_session_whose_gate_would_pass_or_that_cannot_be_asked_may_stop(tmp_path: Path):
    stage, env = _stop_case(tmp_path / "a", "complete", [])
    assert run_hook("stop-gate.py", {}, env) is None and not (stage.parents[1] / "logs" / "stop-gate").exists()
    stage, env = _stop_case(tmp_path / "b", "escalated", [{"name": "x", "passed": False}])
    assert run_hook("stop-gate.py", {}, env) is None  # a question is not held to the gate
    assert not (Path(env["CLAUDE_PROJECT_DIR"]) / ".venv" / "bin" / "harness.calls").exists()
    stage, env = _stop_case(tmp_path / "c", "complete", [{"name": "x", "passed": False}])
    (Path(env["CLAUDE_PROJECT_DIR"]) / ".venv" / "bin" / "harness").unlink()
    assert run_hook("stop-gate.py", {}, env) is None  # no harness and no uv on this PATH: nobody to ask
    stage, env = _stop_case(tmp_path / "d", "partial", [])
    assert "partial is a checkpoint" in run_hook("stop-gate.py", {}, env)["reason"]


def handoff_env(tmp_path: Path, **extra: str) -> dict:
    """A session of the manager or a human: its own temporary directory, project and user settings."""
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    return {
        "TMPDIR": str(tmp_path),
        "CLAUDE_CONFIG_DIR": str(tmp_path / "config"),
        "CLAUDE_PROJECT_DIR": str(tmp_path / "project"),
        "HARNESS_STATUSLINE_BASE": str(tmp_path / "no-statusline"),
        **extra,
    }


def status_line(env: dict, used: int, window: int = 1_000_000) -> None:
    """The status line records the size of the conversation, as Claude Code reports it to the status line."""
    payload = {
        "session_id": "s1",
        "context_window": {"total_input_tokens": used, "context_window_size": window},
        "workspace": {"project_dir": env["CLAUDE_PROJECT_DIR"]},
    }
    subprocess.run(
        [sys.executable, str(HOOKS / "statusline.py")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
        env={"PATH": "/usr/bin:/bin", **env},
    )


def after_tool(env: dict) -> dict | None:
    return run_hook("handoff.py", {"session_id": "s1", "hook_event_name": "PostToolUse", "tool_name": "Bash"}, env)


def test_a_session_writes_a_handoff_before_claude_code_compacts_it_and_reads_it_after(tmp_path: Path):
    env = handoff_env(tmp_path)
    folder = tmp_path / "project" / "docs" / "handoff"
    assert after_tool(env) is None  # nothing is known of the conversation before the status line reports it
    status_line(env, 500_000)  # a 1M window compacts at about 967,000 tokens
    assert after_tool(env) is None
    status_line(env, 900_000)
    first = after_tool(env)
    assert "write a handoff to" in first["hookSpecificOutput"]["additionalContext"]
    assert str(folder) in first["hookSpecificOutput"]["additionalContext"] and "handoff" in first["systemMessage"]
    assert after_tool(env) is None  # once
    status_line(env, 950_000)
    second = after_tool(env)["hookSpecificOutput"]["additionalContext"]
    assert second.startswith("Context is at 98% of the compaction point") and "up to date" in second
    assert after_tool(env) is None
    assert run_hook("handoff.py", {"session_id": "s1", "hook_event_name": "PostCompact"}, env) is None
    back = run_hook("handoff.py", {"session_id": "s1", "hook_event_name": "SessionStart", "source": "compact"}, env)
    assert f"read the newest file in {folder}/" in back["hookSpecificOutput"]["additionalContext"]
    assert after_tool(env) is None  # the size before the compaction is gone with it
    status_line(env, 900_000)
    assert "write a handoff" in after_tool(env)["hookSpecificOutput"]["additionalContext"]  # and the notices start over


def test_the_notices_follow_the_point_where_claude_code_compacts(tmp_path: Path):
    late = handoff_env(tmp_path / "a", CLAUDE_AUTOCOMPACT_PCT_OVERRIDE="60")  # 60 % of 967,000 is 580,200
    status_line(late, 540_000)
    assert "write a handoff" in after_tool(late)["hookSpecificOutput"]["additionalContext"]
    small = handoff_env(tmp_path / "b")  # a 200,000-token window compacts at its end
    status_line(small, 180_000, window=200_000)
    assert after_tool(small) is None
    status_line(small, 195_000, window=200_000)  # past both notices at once: one asks for the handoff
    out = after_tool(small)["hookSpecificOutput"]["additionalContext"]
    assert "write a handoff" in out and "once more" not in out and after_tool(small) is None
    window = handoff_env(tmp_path / "c", CLAUDE_CODE_AUTO_COMPACT_WINDOW="400000")
    status_line(window, 380_000)
    assert after_tool(window) is not None


def test_a_role_session_and_a_user_with_a_handoff_hook_of_their_own_are_left_alone(tmp_path: Path):
    env = handoff_env(tmp_path)
    status_line(env, 950_000)
    assert after_tool({**env, "HARNESS_RUN_DIR": str(tmp_path / "runs" / "r1")}) is None  # its checkpoint is its own
    sub = {"session_id": "s1", "hook_event_name": "PostToolUse", "agent_id": "a1"}
    assert run_hook("handoff.py", sub, env) is None  # a subagent's tool call says nothing of the conversation
    own = {"hooks": {"PostToolUse": [{"hooks": [{"type": "command", "command": "~/.claude/hooks/ctx-handoff.sh"}]}]}}
    (tmp_path / "config" / "settings.json").write_text(json.dumps(own), encoding="utf-8")
    assert after_tool(env) is None  # the user's own hook asks; a session is not asked twice
    (tmp_path / "config" / "settings.json").write_text("{}", encoding="utf-8")
    assert after_tool(env) is not None


def test_a_handoff_keeps_the_main_points_of_the_conversation_and_no_copy_of_it(tmp_path: Path):
    """The handoff holds what the conversation needs to go on after the compaction: what the user wants, what was
    agreed, what is open, and the state of the work. No copy of the conversation is kept: a transcript is read again
    and crowds out the documents and sources the work needs."""
    env = handoff_env(tmp_path)
    transcript = tmp_path / "s1.jsonl"
    transcript.write_text('{"type": "user"}\n', encoding="utf-8")
    payload = {"session_id": "s1", "hook_event_name": "PreCompact", "transcript_path": str(transcript)}
    assert run_hook("handoff.py", payload, env) is None
    assert not (tmp_path / "project" / "docs").exists()
    status_line(env, 900_000)
    asked = after_tool(env)["hookSpecificOutput"]["additionalContext"]
    assert "main points of the conversation, not a copy of it" in asked and "can go on after the compaction" in asked
    assert "what the user wants" in asked and "still open" in asked and "next steps" in asked
    settings = json.loads((HOOKS.parent / "settings.json").read_text(encoding="utf-8"))
    assert not any("handoff" in str(group) for group in settings["hooks"].get("PreCompact", []))


def hook_answer(tmp_path: Path, path: str | None = None, line: str = "- Hooks: open\n", **env) -> str | None:
    """What permission-request.py answers a role session that edits a hook script of its own checkout (ADR-0015)."""
    root, run = tmp_path / "repo", tmp_path / "runs" / "20261004-000000-fix"
    own = root / ".claude/worktrees/20261004-000000-fix-write-01"
    (own / ".claude/hooks").mkdir(parents=True, exist_ok=True)
    (root / ".claude/hooks").mkdir(parents=True, exist_ok=True)
    run.mkdir(parents=True, exist_ok=True)
    (run / "brief.md").write_text("# Brief\n\n## Constraints\n- Do not touch: `x/`\n" + line, encoding="utf-8")
    base = {
        "HARNESS_RUN_DIR": str(run),
        "HARNESS_WORKTREE": own.name,
        "HARNESS_OWN_CHECKOUT": "1",
        "CLAUDE_PROJECT_DIR": str(root),
    }
    payload = {
        "tool_name": env.pop("tool", "Edit"),
        "cwd": str(own),
        "tool_input": {"file_path": path or str(own / ".claude/hooks/guard-bash.py")},
    }
    out = run_hook("permission-request.py", payload, {k: v for k, v in {**base, **env}.items() if v is not None})
    return out["hookSpecificOutput"]["decision"]["behavior"] if out else None


def test_a_fix_run_that_opens_the_hooks_may_edit_the_hook_scripts_of_its_own_checkout(tmp_path: Path):
    assert hook_answer(tmp_path) == "allow"
    assert hook_answer(tmp_path, ".claude/hooks/new.py", tool="Write") == "allow"  # relative to the checkout


def test_every_other_permission_prompt_of_a_role_session_is_denied(tmp_path: Path):
    root = tmp_path / "repo"
    own = root / ".claude/worktrees/20261004-000000-fix-write-01"
    other = root / ".claude/worktrees/20261004-000000-fix-write-02/.claude/hooks/guard-bash.py"
    assert hook_answer(tmp_path, line="") == "deny"  # the brief does not open the hooks
    assert hook_answer(tmp_path, line="- Flow files: open\n") == "deny"  # no other line opens them
    assert hook_answer(tmp_path, HARNESS_OWN_CHECKOUT=None) == "deny"  # a reviewer's checkout is work it reviews
    assert hook_answer(tmp_path, str(root / ".claude/hooks/guard-bash.py")) == "deny"  # the main checkout's
    assert hook_answer(tmp_path, str(other)) == "deny"  # another unit's checkout
    # what a session that enters the checkout would read: its settings, agents, skills, commands and rules
    for flow in ("settings.json", "settings.local.json", "agents/writer.md", "skills/x/SKILL.md", "commands/x.md"):
        assert hook_answer(tmp_path, str(own / ".claude" / flow)) == "deny", flow
    assert hook_answer(tmp_path, ".claude/hooks/../settings.json") == "deny"  # `..` is refused, link or not
    assert hook_answer(tmp_path, "src/app.py") == "deny"  # not a hook script
    assert hook_answer(tmp_path, tool="Bash") == "deny"
    assert hook_answer(tmp_path, HARNESS_RUN_DIR=None) is None  # outside a run the hook decides nothing
    assert hook_answer(tmp_path, CLAUDE_PROJECT_DIR=str(own)) == "deny"  # its hooks would be the ones it edits
    assert hook_answer(tmp_path, CLAUDE_PROJECT_DIR=None) == "deny"  # where its hooks come from is unknown


def test_a_hook_script_is_judged_without_links(tmp_path: Path):
    """A link in the session's own checkout could name the main checkout's hook, now or after the answer."""
    hook_answer(tmp_path)  # lays the two checkouts out
    root = tmp_path / "repo"
    hooks = root / ".claude/worktrees/20261004-000000-fix-write-01/.claude/hooks"
    (root / ".claude/hooks/guard-bash.py").write_text("x\n", encoding="utf-8")
    (hooks / "real.py").write_text("x\n", encoding="utf-8")
    (hooks / "out.py").symlink_to(root / ".claude/hooks/guard-bash.py")
    (hooks / "in.py").symlink_to(hooks / "real.py")
    (hooks / "linked").symlink_to(hooks, target_is_directory=True)
    (hooks / "hard.py").hardlink_to(root / ".claude/hooks/guard-bash.py")  # the same file under a second name
    assert hook_answer(tmp_path, str(hooks / "real.py")) == "allow"
    for link in ("out.py", "in.py", "linked/real.py", "hard.py"):
        assert hook_answer(tmp_path, str(hooks / link)) == "deny", link
    # server-19's case: `away/..` folds to the hooks folder as text, but the write follows the link out first
    (hooks / "away").symlink_to(root / ".claude/hooks", target_is_directory=True)
    assert hook_answer(tmp_path, str(hooks) + "/away/../real.py") == "deny"


def test_a_permission_prompt_the_hook_cannot_read_is_denied_in_a_role_session():
    res = subprocess.run(
        [sys.executable, str(HOOKS / "permission-request.py")],
        input="not json",
        capture_output=True,
        text=True,
        check=True,
        env={"PATH": "/usr/bin:/bin", "HARNESS_RUN_DIR": "/nonexistent"},
    )
    assert json.loads(res.stdout)["hookSpecificOutput"]["decision"]["behavior"] == "deny"


# --- wave 1 of the fixes of 2026-10-04 ---


def fake_pytest(tmp_path: Path, code: int = 3) -> dict:
    """A `pytest` on PATH that prints two lines and ends with `code`."""
    (tmp_path / "bin").mkdir(exist_ok=True)
    fake = tmp_path / "bin" / "pytest"
    fake.write_text(f"#!/bin/sh\necho one\necho FAILED test_x\nexit {code}\n", encoding="utf-8")
    fake.chmod(0o755)
    return {"PATH": f"{tmp_path / 'bin'}:/usr/bin:/bin", "TMPDIR": str(tmp_path)}


def test_a_pytest_command_with_a_comment_keeps_its_exit_code(tmp_path: Path):
    """04/F11: the comment swallowed the wrapper's closing parenthesis; bash answered a syntax error with exit 2."""
    command = "pytest -q  # the whole suite"
    script = wrapped(command)
    res = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=False, env=fake_pytest(tmp_path))
    assert res.returncode == 3 and "FAILED test_x" in res.stdout and "syntax error" not in res.stderr


@pytest.mark.parametrize(
    "command",
    ["uv run --directory /w --package ingest pytest -q", "python -m pytest -q", "python3 -m pytest -q",
     "uv run python -m pytest -q", "/home/x/.venv/bin/python -m pytest -q", "env NO_COLOR=1 pytest -q",
     "NO_COLOR=1 pytest -q", "cd packages/harness && uv run pytest -q", "uv run --no-sync pytest -q packages/harness"],
)  # fmt: skip
def test_every_pytest_form_the_repository_counts_is_rewritten(command: str):
    """04/F17: the forms packages/harness/tests/test_steps.py counts as pytest runs; their whole output reached the
    session. A command that is no pytest run, or one that already chose what to see, stays as it is."""
    assert wrapped(command) and f"( {command}\n)" in wrapped(command)
    assert wrapped("uv run ruff check .") is None and wrapped("uv run pytest -q | tail -3") is None
    assert wrapped("cd a && cd b && pytest -q") is None and wrapped("pytest -q; rm -rf x") is None


def stop_stage(tmp_path: Path, escalation: str | None = None) -> tuple[Path, dict]:
    """A role session about to stop without a result, with the schemas a stop hook validates against."""
    root, stage = tmp_path / "repo", tmp_path / "runs" / "r1" / "stages" / "plan"
    (root / "schemas").mkdir(parents=True)
    for name in ("stage-result", "escalation"):
        source = HOOKS.parents[1] / "schemas" / f"{name}.schema.json"
        (root / "schemas" / f"{name}.schema.json").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    stage.mkdir(parents=True)
    if escalation is not None:
        (stage / "escalation.json").write_text(escalation, encoding="utf-8")
    env = {"HARNESS_RUN_DIR": str(stage.parents[1]), "HARNESS_STAGE": "plan", "HARNESS_MODE": "bg"}
    return stage, {**env, "CLAUDE_PROJECT_DIR": str(root)}


ESCALATION = {"schema_version": 1, "id": "000", "run_id": "r1", "stage": "plan", "session_id": "s1",
              "created_at": "2026-10-04T00:00:00+00:00", "question": "Which design?", "context": "c", "options": [],
              "recommendation": None, "blocking": True, "status": "open", "answer": None}  # fmt: skip


@pytest.mark.parametrize(
    ("text", "stops"),
    [(json.dumps(ESCALATION), True), (json.dumps({**ESCALATION, "status": "withdrawn"}), False), ("", False),
     (json.dumps({**ESCALATION, "stage": "read"}), False), (json.dumps({**ESCALATION, "question": ""}), False)],
)  # fmt: skip
def test_only_an_open_escalation_of_its_stage_lets_a_session_stop(tmp_path: Path, text: str, stops: bool):
    """04/F9: any escalation.json let the session stop, a withdrawn or an empty one too (and the empty one then stopped
    every poll). It has to be an open escalation of the stage, valid against its schema."""
    _, env = stop_stage(tmp_path, text)
    out = run_hook("stop-gate.py", {}, env)
    assert (out is None) == stops


def test_a_hold_count_the_session_wrote_does_not_switch_its_gate_off(tmp_path: Path):
    """04/F10: the count was read from the session's own stage directory, so `3` written there let it stop unasked."""
    failing = {"name": "the design was tried before the plan was written", "passed": False}
    stage, env = _stop_case(tmp_path, "complete", [failing])
    (stage / "logs").mkdir()
    (stage / "logs" / "stop-gate.holds").write_text("3", encoding="utf-8")
    assert run_hook("stop-gate.py", {}, env)["decision"] == "block"
    assert (Path(env["CLAUDE_PROJECT_DIR"]) / ".venv" / "bin" / "harness.calls").is_file()  # the gate was asked


def test_the_stop_hook_asks_the_gate_of_the_main_checkout_when_the_project_directory_is_a_checkout(tmp_path: Path):
    """03/F30: with CLAUDE_PROJECT_DIR the session's checkout the hook asked the preview of a run that is not there
    and made a runs folder under .claude/worktrees/."""
    _, env = _stop_case(tmp_path, "complete", [])
    root = Path(env["CLAUDE_PROJECT_DIR"])
    checkout = root / ".claude" / "worktrees" / "r1-plan"
    checkout.mkdir(parents=True)
    assert run_hook("stop-gate.py", {}, {**env, "CLAUDE_PROJECT_DIR": str(checkout)}) is None
    assert (root / ".venv" / "bin" / "harness.calls").read_text(encoding="utf-8").startswith("gate --preview")
    assert not [p for p in (root / ".claude" / "worktrees").iterdir() if p.name.endswith("-runs")]


def test_a_result_json_that_is_a_link_is_not_read(tmp_path: Path):
    """Item 7d: the hook runs outside the sandbox; what it reads through a link would come back in its reason."""
    stage, env = stop_stage(tmp_path)
    secret = tmp_path / "secret.json"
    secret.write_text(json.dumps({"summary": 7, "note": "SECRET-TEXT"}), encoding="utf-8")
    (stage / "result.json").symlink_to(secret)
    out = run_hook("stop-gate.py", {}, env)
    assert out["decision"] == "block" and "is a link" in out["reason"] and "SECRET" not in out["reason"]


def test_validate_json_holds_a_run_s_json_files_only(tmp_path: Path):
    """04/F16: every `.json` a session wrote was held to JSON syntax, a tsconfig.json with a comment line too."""
    root = tmp_path / "repo"
    (root / "schemas").mkdir(parents=True)
    source = HOOKS.parents[1] / "schemas" / "stage-result.schema.json"
    (root / "schemas" / "stage-result.schema.json").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    env = {"CLAUDE_PROJECT_DIR": str(root)}

    def write(path: Path, content: str) -> dict | None:
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Write",
                   "tool_input": {"file_path": str(path), "content": content}}  # fmt: skip
        return run_hook("validate-json.py", payload, env)

    assert write(root / "web" / "tsconfig.json", '{\n  // the compiler options\n  "strict": true\n}\n') is None
    run_file = tmp_path / "runs" / "20261004-000000-x" / "stages" / "plan" / "result.json"
    assert write(run_file, "{not json")["hookSpecificOutput"]["permissionDecision"] == "deny"


def raw_hook(name: str, text: str, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOKS / name)], input=text, capture_output=True, text=True, check=False,
        env={"PATH": "/usr/bin:/bin", **env},
    )  # fmt: skip


@pytest.mark.parametrize("name", ["guard-inbox.py", "validate-json.py", "config-audit.py"])
def test_a_guard_that_cannot_read_its_input_refuses_the_call(tmp_path: Path, name: str):
    """Item 7a: exit 1 lets the call through (hooks.md:840 in the facts file); a PreToolUse guard and the ConfigChange
    hook exit 2 on any exception (guard-checkout and guard-bash: test_guards.py)."""
    env = {"HARNESS_RUN_DIR": str(tmp_path / "runs" / "r1"), "HARNESS_WORKTREE": "r1-plan",
           "CLAUDE_PROJECT_DIR": str(tmp_path / "repo")}  # fmt: skip
    res = raw_hook(name, "", env)
    assert res.returncode == 2 and name.split(".")[0] in res.stderr


def test_the_hooks_that_cannot_block_fail_in_the_way_their_event_allows(tmp_path: Path):
    """Item 7a: permission-request answers no, also on an input it cannot read (PermissionRequest ignores exit 2);
    stop-gate lets the stop through on its own crash and logs it (exit 2 would keep the session working);
    compact-output and skill-audit let the call through unchanged (exit 2 would block every Bash or Skill call)."""
    run_dir = tmp_path / "runs" / "r1"
    role = {"HARNESS_RUN_DIR": str(run_dir), "HARNESS_STAGE": "plan", "HARNESS_MODE": "bg",
            "CLAUDE_PROJECT_DIR": str(tmp_path / "repo")}  # fmt: skip
    denied = raw_hook("permission-request.py", "", role)
    assert denied.returncode == 0 and json.loads(denied.stdout)["hookSpecificOutput"]["decision"]["behavior"] == "deny"
    stopped = raw_hook("stop-gate.py", "", role)
    assert stopped.returncode == 0 and not stopped.stdout.strip()
    assert "crashed" in (run_dir / "stages" / "plan" / "logs" / "stop-gate.log").read_text(encoding="utf-8")
    for name in ("compact-output.py", "skill-audit.py"):
        res = raw_hook(name, "", role)
        assert res.returncode == 0 and not res.stdout.strip(), name
