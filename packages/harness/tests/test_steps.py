"""The step rules of specs/001-chat-depth, part 2 (harness/gates/steps.py): the language, the runner of a command, the
outcome of a test run, the order of runs and edits, the conditions, `harness validate` and the insertion script.
Run: `uv run pytest -q packages/harness/tests/test_steps.py`."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest
import yaml
from harness.gates import steps

REPO = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file() and (p / "specs").is_dir())
METHODS = (REPO / "specs" / "001-chat-depth" / "methods.md").read_text(encoding="utf-8")
COMMANDS = {"test": ["uv", "run", "pytest", "-q"], "lint": ["uv", "run", "ruff", "check", "."], "types": None}


def methods() -> dict[str, str]:
    """methods.md cut at its `## <type>` headings: the Working method of every type as it stands."""
    parts = re.split(r"(?m)^## (\S+)\s*$", METHODS)
    return {parts[i]: f"## {parts[i]}\n{parts[i + 1]}" for i in range(1, len(parts), 2)}


def rules() -> dict[str, dict[str, str]]:
    """The rule of every step of every type, read when a test asks: a missing file fails that test, not the module."""
    out = json.loads((REPO / "specs" / "001-chat-depth" / "step-rules.json").read_text(encoding="utf-8"))
    # Spec 005: the spec stage's gate checks `spec.md` (five sections), and its Constitution and Files to change checks
    # are gone (the plan's Phase -1 gates and file lists are the planner's), so the three rules of the old technical
    # brief name checks that no gate has; spec 001's file stays as it was, the record of the first rule set.
    out["spec-writer"].update(
        {
            "4": "output: spec.md has the required sections",
            "6": "trust: the constitution is checked by the plan's Phase -1 gates since spec 005",
            "7": "trust: a spec lists no files since spec 005",
        }
    )
    return out


def every_step(rule: str) -> dict[str, dict[str, str]]:
    """One rule on every step of every type of methods.md: a rule set that holds whatever the real rules are."""
    return {name: {str(s["n"]): rule for s in steps.method_steps(text)} for name, text in methods().items()}


def bash(seq: int, command: str, exit_code: int | None = 0, output: str = "", denied: bool = False) -> dict:
    return {"seq": seq, "tool": "Bash", "command": command, "exit_code": exit_code, "output": output,
            "denied": denied, "background": False, "cwd": "/repo"}  # fmt: skip


def edit(seq: int, file: str, tool: str = "Edit", ok: bool = True) -> dict:
    return {"seq": seq, "tool": tool, "file": file, "ok": ok, "cwd": "/repo"}


def read(seq: int, file: str, ok: bool = True) -> dict:
    return {"seq": seq, "tool": "Read", "file": file, "ok": ok, "offset": None, "limit": None, "start": None,
            "lines": None, "cwd": "/repo"}  # fmt: skip


def ctx(tmp_path: Path, events: list[dict] | None, **extra) -> dict:
    out = {
        "events": events,
        "stage_dir": tmp_path / "stage",
        "stage_id": "write",
        "run_id": "20261003-000000-demo",
        "prompt_files": ["prompt.md", "input/brief.md", "input/assignment.md", "input/plan/plan.md"],
        "roots": ["/repo"],
        "commands": COMMANDS,
        "code_changed": False,
        "gate": {},
    }
    return {**out, **extra}


def result(rule: str, c: dict) -> str:
    return steps.evaluate(rule, c)[0]


@pytest.mark.parametrize(
    "rule",
    [
        "read: tasks.json",
        "ran: {test}",
        "ran: {test} failed",
        "ran: {lint} passed",
        "ran: {test} before: edit: code",
        "ran: git diff; wrote: output/trial/trial.patch",
        "wrote: output/notes.md",
        "output: every finding has a source",
        "output: * has the five sections",
        "when: code_changed; ran: {test}",
        "when: input: changes.patch; read: changes.patch",
        "when: stage: plan,frame; read: code",
        "trust: a judgement no script can check; even with a ; inside",
    ],
)
def test_every_form_of_the_language_parses(rule: str):
    assert steps.parse(rule)


@pytest.mark.parametrize(
    ("rule", "why"),
    [
        ("seen: x", "not a rule of the language"),
        ("trust:", "trust: needs a reason"),
        ("read: tasks.json; trust: why", "trust: stands alone"),
        ("when: code_changed", "when: needs a rule after it"),
        ("read: a; when: code_changed", "when: comes first, once"),
        ("ran: {build}", "unknown placeholder"),
        ("ran: {test} before: run: x", "before: takes edit:"),
        ("when: someday; ran: x", "not a condition"),
        ("read: two words", "not a rule of the language"),
        ("ran: {test};", "an empty clause"),
    ],
)
def test_a_rule_outside_the_language_is_named(rule: str, why: str):
    with pytest.raises(ValueError, match=re.escape(why)):
        steps.parse(rule)


@pytest.mark.parametrize(
    ("command", "runner"),
    [
        ("pytest -q", "pytest"),
        ("uv run pytest -q packages/harness", "pytest"),
        ("uv run --package ingest pytest -q", "pytest"),
        ("uv run --directory /w --package ingest pytest -q", "pytest"),
        ("uv run --frozen --offline ruff check .", "ruff"),
        ("uvx --from ruff ruff check", "ruff"),
        ("python -m pytest -q", "pytest"),
        ("python3 -m pytest -q", "pytest"),
        ("uv run python -m pytest -q", "pytest"),
        ("/home/x/.venv/bin/python -m pytest -q", "pytest"),
        ("npx jest --ci", "jest"),
        ("env NO_COLOR=1 pytest -q", "pytest"),
        ("NO_COLOR=1 pytest -q", "pytest"),
        ("cd packages/harness && uv run pytest -q", "pytest"),
        ("python3 -c 'import pytest; pytest.main()'", "python3"),
    ],
)
def test_the_runner_is_the_first_program_after_the_wrappers(command: str, runner: str):
    assert [Path(w[0]).name for w in steps.runners(command)][-1] == runner


def test_a_runner_is_found_in_a_chain_after_cd_and_alone_but_not_in_a_refused_call(tmp_path: Path):
    chain = "uv run ruff format packages && uv run ruff check packages && uv run pytest -q x 2>&1 | tail -15"
    for command in (chain, "cd packages/harness && uv run pytest -q", "uv run pytest -q"):
        assert result("ran: {test}", ctx(tmp_path, [bash(1, command)])) == "pass", command
    assert result("ran: {test}", ctx(tmp_path, [bash(1, "uv run ruff check .")])) == "fail"  # ruff is not {test}
    assert result("ran: {test}", ctx(tmp_path, [bash(1, "uv run pytest -q", None, denied=True)])) == "fail"
    heredoc = "cat > x.py <<'EOF'\npytest -q\nEOF"
    assert result("ran: {test}", ctx(tmp_path, [bash(1, heredoc)])) == "fail"  # a here-document's body is no command
    assert result("ran: python *probes/*.py", ctx(tmp_path, [bash(1, "python3 output/probes/count.py a")])) == "pass"


@pytest.mark.parametrize(
    "command",
    [
        "cat > x.py <<'EOF'\nprint(1)\nEOF\nuv run pytest -q",  # on the line after the terminator
        "cat > x.py <<'EOF'\nprint(1)\nEOF\n\nuv run pytest -q",  # after a blank line
        "cat > x.py <<'EOF' &&\nprint(1)\nEOF\nuv run pytest -q",  # `&&` ends the opening line
        "cat > x.py <<'EOF'\nprint(1)\nEOF\necho done;\nuv run pytest -q",  # `;` ends the line before it
        'cat > x.py <<"EOF"\nprint(1)\nEOF\nuv run pytest -q',
        "cat > x.py <<EOF\nprint(1)\nEOF\nuv run pytest -q",
        "cat > x.py <<-EOF\n\tprint(1)\n\tEOF\nuv run pytest -q",  # <<- takes the tabs off the terminator
        "cat > a <<A\n1\nA\ncat > b <<B\n2\nB\nuv run pytest -q",  # two here-documents, one after the other
        "cat <<A <<B\n1\nA\n2\nB\nuv run pytest -q",  # two on one line: their bodies follow in order
        "grep x <<< 'abc'\nuv run pytest -q",  # a here-string has no body
        "echo 'a << b'\nuv run pytest -q",  # `<<` inside quotes opens nothing
    ],
)
def test_a_command_after_a_here_document_is_seen(tmp_path: Path, command: str):
    assert result("ran: {test}", ctx(tmp_path, [bash(1, command)])) == "pass"


def test_a_line_end_beside_another_operator_ends_a_command():
    """shlex joins operator characters that stand together (`;\\n`, `&&\\n`, the `\\n\\n` of a blank line); a line end
    among them still ends a command, and a line end inside quotes stays in its word."""
    for command in ("echo a\n\nuv run pytest -q", "echo a;\nuv run pytest -q", "echo a &&\nuv run pytest -q"):
        assert [w[0] for w in steps.runners(command)] == ["echo", "pytest"], command
    assert steps.segments("git commit -m 'one\n\ntwo' && uv run pytest -q")[0] == ["git", "commit", "-m", "one\n\ntwo"]


def test_the_body_of_a_here_document_is_no_command(tmp_path: Path):
    for body in ("cat > x.py <<'EOF'\npytest -q\nEOF", "cat > x.py <<EOF\npytest -q", "cat <<-EOF\n\tpytest -q\n\tEOF"):
        assert result("ran: {test}", ctx(tmp_path, [bash(1, body)])) == "fail", body
    recorded = "mkdir -p $TMPDIR && cat > $TMPDIR/chk.py <<'EOF'\nimport json\nprint(1)\nEOF\npython3 $TMPDIR/chk.py"
    assert [w[0] for w in steps.runners(recorded)] == ["mkdir", "cat", "python3"]  # the shape of a recorded call


def test_failed_and_passed_come_from_the_runner_s_summary_not_from_the_chain(tmp_path: Path):
    ruff_failed = "\x1b[1m\x1b[96mhelp\x1b[0m: Add explicit `check=False`\nFound 1 error."  # actions file, line 338
    tail_hid = "packages/harness/tests/test_poll.py::test_x\n4 failed, 61 passed, 3 skipped, 10 errors in 1.43s"
    coloured = "\x1b[31m\x1b[31m\x1b[1m3 failed\x1b[0m\x1b[31m in 0.01s\x1b[0m\x1b[0m\nfull output: /tmp/x (exit 1)"
    framed = "============================== \x1b[32m\x1b[1m3 passed\x1b[0m\x1b[32m in 0.01s\x1b[0m ==="
    chain = "uv run ruff check . && uv run pytest -q x 2>&1 | tail -15"
    cases = [
        (bash(1, chain, 1, ruff_failed), None),  # ruff failed, pytest never ran: neither
        (bash(1, "uv run pytest -q 2>&1 | tail -3", 0, tail_hid), "failed"),  # the pipe hid the code, not the line
        (bash(1, "uv run pytest -q x", 1, coloured), "failed"),
        (bash(1, "uv run pytest -q x -v", 0, framed), "passed"),
        (bash(1, "uv run pytest -q x", 2, "\x1b[31m1 error\x1b[0m in 0.05s"), "failed"),
        (bash(1, "uv run pytest -q x", 4, "no tests ran in 0.00s"), None),
    ]
    for call, outcome in cases:
        for wanted in ("failed", "passed"):
            got = result(f"ran: {{test}} {wanted}", ctx(tmp_path, [call]))
            assert got == ("pass" if wanted == outcome else "fail"), (call["output"], wanted)


def test_without_a_summary_line_one_program_counts_with_its_exit_code(tmp_path: Path):
    assert result("ran: {lint} failed", ctx(tmp_path, [bash(1, "uv run ruff check .", 1)])) == "pass"
    assert result("ran: {lint} passed", ctx(tmp_path, [bash(1, "uv run ruff check .", 0)])) == "pass"
    assert (
        result("ran: {lint} failed", ctx(tmp_path, [bash(1, "uv run ruff check . && uv run ruff format", 1)])) == "fail"
    )


def test_before_edit_code_leaves_out_test_files_and_files_of_the_run(tmp_path: Path):
    rule = "ran: {test} before: edit: code"
    first_test = [
        edit(1, "/repo/.claude/worktrees/r-write-01/packages/a/tests/test_a.py", "Write"),
        edit(2, "/runs/20261003-000000-demo/stages/write/01/progress.md", "Write"),
        bash(3, "uv run pytest -q packages/a"),
        edit(4, "/repo/.claude/worktrees/r-write-01/packages/a/src/a.py"),
    ]
    assert result(rule, ctx(tmp_path, first_test)) == "pass"
    code_first = [edit(1, "/repo/packages/a/src/a.py"), bash(2, "uv run pytest -q packages/a")]
    assert steps.evaluate(rule, ctx(tmp_path, code_first)) == (
        "fail",
        "no `pytest` run before the first edit of code (#1)",
    )
    refused = [edit(1, "/repo/packages/a/src/a.py", ok=False), bash(2, "uv run pytest -q")]
    assert result(rule, ctx(tmp_path, refused)) == "pass"  # a refused edit changed nothing


def test_when_applies_the_rule_only_under_its_condition(tmp_path: Path):
    (tmp_path / "stage" / "input" / "work").mkdir(parents=True)
    rule = "when: code_changed; ran: {test}"
    assert result(rule, ctx(tmp_path, [])) == "n/a"
    assert result(rule, ctx(tmp_path, [], code_changed=True)) == "fail"
    assert result("when: input: changes.patch; read: changes.patch", ctx(tmp_path, [])) == "n/a"
    (tmp_path / "stage" / "input" / "work" / "changes.patch").write_text("x", encoding="utf-8")
    assert result("when: input: changes.patch; read: changes.patch", ctx(tmp_path, [])) == "fail"
    assert result("when: stage: plan; read: code", ctx(tmp_path, [])) == "n/a"
    assert result("when: stage: write,plan; read: code", ctx(tmp_path, [])) == "fail"


def test_trust_passes_with_its_reason_and_a_rule_without_one_fails_the_step(tmp_path: Path):
    assert steps.evaluate("trust: thinking", ctx(tmp_path, [])) == ("trust", "thinking")
    assert result("trust:", ctx(tmp_path, [])) == "fail"
    assert steps.evaluate("", ctx(tmp_path, [])) == ("fail", "the rule is not in the language: an empty clause")
    assert steps.runners("") == [] and steps.runners("echo 'unbalanced") == [["echo", "'unbalanced"]]
    (check,) = steps.step_checks([{"n": 2, "rules": ["trust: thinking"]}], ctx(tmp_path, []))
    assert check == {"name": "step 2: trust: thinking", "passed": True, "detail": "trust: thinking"}


def test_read_wrote_and_output_pass_once_and_fail_once(tmp_path: Path):
    events = [read(1, "/runs/r/stages/write/01/tasks.json"), read(2, "/repo/missing.md", ok=False)]
    assert result("read: tasks.json", ctx(tmp_path, events)) == "pass"
    assert result("read: missing.md", ctx(tmp_path, events)) == "fail"  # the Read was refused
    assert result("read: plan.md", ctx(tmp_path, [])) == "pass"  # it was in the prompt
    assert result("read: code", ctx(tmp_path, [read(1, "/repo/packages/a/src/a.py")])) == "pass"
    assert result("read: code", ctx(tmp_path, [read(1, "/repo/packages/a/tests/test_a.py")])) == "fail"
    assert result("read: tasks.json", ctx(tmp_path, None)) == "n/a"  # no transcript
    (tmp_path / "stage" / "output").mkdir(parents=True)
    assert result("wrote: output/notes.md", ctx(tmp_path, [])) == "fail"
    (tmp_path / "stage" / "output" / "notes.md").write_text("n", encoding="utf-8")
    assert result("wrote: output/notes.md", ctx(tmp_path, [])) == "pass"
    gate = {"verdict.md has the five sections": True, "every finding has a source": False}
    assert result("output: * has the five sections", ctx(tmp_path, [], gate=gate)) == "pass"
    assert result("output: every finding has a source", ctx(tmp_path, [], gate=gate)) == "fail"
    assert result("output: a check this gate lacks", ctx(tmp_path, [], gate=gate)) == "n/a"
    assert result("ran: {types}", ctx(tmp_path, [])) == "n/a"  # the project names no type-check command


def test_a_background_run_is_a_run_whose_outcome_is_unknown(tmp_path: Path):
    started = {**bash(1, "uv run pytest -q", None), "background": True}
    assert result("ran: {test}", ctx(tmp_path, [started])) == "pass"
    assert result("ran: {test} passed", ctx(tmp_path, [started])) == "fail"


def test_steps_are_numbered_lines_with_their_indented_continuation_and_get_their_rule_at_the_end():
    reader = methods()["reader"]
    found = steps.method_steps(reader)
    assert [s["n"] for s in found] == list(range(1, 12)) and found[0]["last"] - found[0]["line"] == 6
    text = steps.insert_rules(
        reader, {1: "wrote: progress.md", 11: "output: every quote stands at its stated location"}
    )
    again = steps.method_steps(text)
    assert again[0]["rules"] == ["wrote: progress.md"] and again[1]["rules"] == []
    assert text.splitlines()[again[0]["last"] - 1].endswith("`progress.md`. <!-- check: wrote: progress.md -->")
    assert steps.insert_rules(text, {1: "trust: other"}) == text  # a step keeps the rule it has
    with pytest.raises(ValueError, match="no step 12"):
        steps.insert_rules(reader, {12: "trust: x"})


def fixture_root(tmp_path: Path, rules: dict[str, dict[str, str]], mode: str | None = "warn") -> Path:
    """A repository with the eighteen Working methods of methods.md as agent files, the rules inserted, a policy
    that gives every type a row, and one stage table with the stages of every table (docs/roles/stages.yaml and
    docs/roles/pipelines/*.yaml)."""
    root = tmp_path / "repo"
    (root / ".claude" / "agents").mkdir(parents=True)
    (root / "docs" / "roles" / "pipelines").mkdir(parents=True)
    for name, text in methods().items():
        own = {int(k): v for k, v in rules.get(name, {}).items()}
        (root / ".claude" / "agents" / f"{name}.md").write_text(steps.insert_rules(text, own), encoding="utf-8")
    defaults = {"steps": mode} if mode else {}
    policy = {"schema_version": 1, "defaults": defaults, "types": {name: {} for name in methods()}}
    (root / "docs" / "roles" / "need-to-know.yaml").write_text(yaml.safe_dump(policy), encoding="utf-8")
    rows, roles = [], REPO / "docs" / "roles"
    for path in [roles / "stages.yaml", *sorted((roles / "pipelines").glob("*.yaml"))]:
        rows += [{"id": s["id"], "role_type": s["role_type"]} for s in yaml.safe_load(path.read_text())["stages"]]
    (root / "docs" / "roles" / "stages.yaml").write_text(yaml.safe_dump({"stages": rows}), encoding="utf-8")
    return root


def test_the_rules_of_all_eighteen_types_pass_harness_validate(tmp_path: Path):
    real = rules()
    assert len(real) == 18 and sum(len(v) for v in real.values()) == 139
    assert steps.problems(fixture_root(tmp_path, real)) == []


def test_validate_names_a_step_without_rule_an_unknown_rule_and_a_check_no_gate_has(tmp_path: Path):
    given = every_step("trust: no check")
    del given["writer"]["3"]
    given["critic"]["4"] = "seen: critique.md"
    given["advisor"]["4"] = "output: answer.md is short"
    given["planner"]["4"] = "when: stage: write; read: code"
    found = steps.problems(fixture_root(tmp_path, given))
    assert found == [
        "advisor: step 4: output: names a check no gate of advisor has: 'answer.md is short'",
        "critic: step 4: not a rule of the language: 'seen: critique.md'",
        "planner: step 4: no table gives stage write to planner",
        "writer: step 3 has no rule `<!-- check: ... -->`",
    ]
    twice = fixture_root(tmp_path / "twice", every_step("trust: no check"))
    agent = twice / ".claude" / "agents" / "writer.md"
    agent.write_text(agent.read_text().replace("-->", "--> <!-- check: trust: again -->", 1), encoding="utf-8")
    assert steps.problems(twice) == ["writer: step 1 has 2 rules; one comment holds them all"]


def test_a_step_without_a_rule_is_a_problem_only_once_the_policy_sets_a_mode(tmp_path: Path):
    assert steps.problems(fixture_root(tmp_path, {}, mode=None)) == []
    assert len(steps.problems(fixture_root(tmp_path / "on", {}, mode="warn"))) == 139


def test_the_insertion_script_writes_all_files_or_none(tmp_path: Path):
    spec = importlib.util.spec_from_file_location("insert_step_rules", REPO / "ops" / "insert-step-rules.py")
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    agents = fixture_root(tmp_path, {}, mode=None) / ".claude" / "agents"
    before = {p.name: p.read_text(encoding="utf-8") for p in agents.glob("*.md")}
    wrong = rules()
    wrong["writer"]["9"] = "trust: a step the method does not have"
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(wrong), encoding="utf-8")
    assert script.main([str(path), str(agents)]) == 1
    assert {p.name: p.read_text(encoding="utf-8") for p in agents.glob("*.md")} == before  # nothing written
    path.write_text(json.dumps(rules()), encoding="utf-8")
    assert script.main([str(path), str(agents)]) == 0
    assert all(len(s["rules"]) == 1 for p in agents.glob("*.md") for s in steps.method_steps(p.read_text()))
    after = {p.name: p.read_text(encoding="utf-8") for p in agents.glob("*.md")}
    assert script.main([str(path), str(agents)]) == 0  # a second run changes nothing
    assert {p.name: p.read_text(encoding="utf-8") for p in agents.glob("*.md")} == after
