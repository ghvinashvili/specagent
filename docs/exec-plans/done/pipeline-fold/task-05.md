# Task 5 — The critic on the plan, the verifier on the code

builder: b
depends_on: 3, 4
milestone: M2

## Goal
One reader per commit. The critic keeps its coverage round (C and A ids, before the build) and loses the diff review;
the verifier, which already holds the commit in its clean worktree, reads the diff by file against the task's steps and
the spec and files what the diff review filed, as V ids with their `(code)`, `(plan)` or `(spec)` cause. R ids are
retired for new runs; old runs still parse. One critic by default; the odd/even parity stays a config option. The
planner's last wait also reads line 1 of `critique.md`, which the critic sets in place (C42: `wait_for_log.py --first`).

**Files (under `.claude/skills/running-specagent-pipelines/`):**
- Modify: `example/critic-assignment.md`, `example/verifier-assignment.md`, `example/plan-fixer-assignment.md`,
  `example/builder-a-assignment.md`, `example/builder-b-assignment.md` (items 3 and 4), `example/judge-assignment.md`
  (`:20`), `example/handoff-rule.md` (the critic's bullet), `example/common.md` (the pipeline-shape bullet,
  "Messages"), `example/README.md` (the critic's and the verifier's lines), `SKILL.md` (the pipeline block's verifier
  line, `:40`, the bullet on the critic), `example/planner-assignment.md` (C42: the last-task bullet, `:63-67` at
  3c80656; B3: the lanes' contract message, `:3`)
- Modify: `scripts/wait_for_log.py` (C42: `--first`), `scripts/docs/wait_for_log.md` (its paragraph),
  `scripts/tests/test_open_ids.py` (two asserts after `:35`), `scripts/tests/test_skill_example.py` (`read`, `BRIEFS`,
  two tests, the B16 pin at `:47`, `WAITERS["critic-assignment.md"]` at `:253-255`, `WAITERS["planner-assignment.md"]`
  at `:252` at 3c80656), `scripts/tests/test_skill_md.py` (one test)
- Create (repository): `wiki/decisions/critic-on-the-plan-verifier-on-the-code.md`,
  `wiki/decisions/critic-on-the-plan-verifier-on-the-code.summary.md`
- Modify (repository): `README.md` (B3: the pipeline diagram, `:56-70` at 3c80656), `wiki/index.md` (one line at the
  end of `## Decisions`), `wiki/log.md` (one section at the end)

**Interfaces** (lines are lane a's at 9bf3542, whose skill folder holds lane b's Task 3, unless marked "at 3c80656",
Task 4's commit. Task 4 rewords `example/common.md:34-35`, `example/plan-fixer-assignment.md:6-9`, `:15-17` and
`:35-37`, `SKILL.md:44-46` and the pin at `test_skill_example.py:48`, and puts the planner's waiter in place of
`WAITERS["plan-fixer-assignment.md"]` (`:249-252`): match the words below, not the line numbers):
- Consumes: `check_formats.CAUSE` (`check_formats.py:60`: code, plan or spec) and its error for a V section with none
  of the three (`:227-230`); `check_formats.HEADING`, `ANSWER`, `LOG_LINE` (generic over `[A-Z]{1,2}`: no code change
  for the retired R); `findings_report.KINDS` (keeps "R" so old runs report) and `CAUSES` (`findings_report.py:34`);
  Task 2's `open_ids.open_ids(..., cause="plan")`, which drops only a `(code)` V or R (`open_ids.py:56`), so a
  `(spec)` V goes to the planner and the fixer as a `(plan)` one does; in `test_skill_example.py`: `SKILL` (`:17`),
  `ROLES` (`:19`), `RULES` (`:41-59`), `load` (`:62-63`), `DOMAIN` (`:187-195`), `WAITERS` (`:248-259`) and the
  waiter test (`:262-273`); in `scripts/wait_for_log.py` at 3c80656 the arguments (`:13-18`) and `check` (`:21-25`);
  in `scripts/tests/test_open_ids.py` `run_script` (`:10-18`), `write` (`:21-24`) and the `--once` test (`:32-35`).
- Produces: the texts of Step 3; `wait_for_log.py --first TEXT` (repeatable: exit 0 also when line 1 equals one of
  the texts; with `--once` 0 then, else 3); `read(rel)` (a skill file, whitespace folded) and `BRIEFS` (the seven role
  briefs and `example/common.md`) in `test_skill_example.py`; the decision page
  `wiki/decisions/critic-on-the-plan-verifier-on-the-code.md` (type decision, status draft, decided 2026-10-30, by
  owner, scope global) for spec Decided 3 only (Tasks 2, 3 and 4 commit the pages of Decided 5, 4 and 2), with its
  summary, index line and log section.

- [ ] **Step 0: The base holds Task 4 (C37)**

Task 4 (lane a) edits `SKILL.md`, `example/common.md`, `example/plan-fixer-assignment.md` and
`scripts/tests/test_skill_example.py` before this task (`lessons.md`, "Read first" item 3: the other builder depends on
that task), and lane b receives lane a's commits only through the main session's merge, not with the done line.

Run: `grep -n '^Task 4: done' /home/tite/Desktop/agent-system-run/pipeline-fold-2026-10-30/build-log.md` (its `<sha>`),
then `git -C /home/tite/Desktop/agentic-flow-template/pipeline-fold-b merge-base --is-ancestor <sha> HEAD; echo $?`
Expected: one done line, then `0`. On `1`, wait in the background with `python3
/home/tite/Desktop/agent-system-run/pipeline-fold-2026-10-30/wait_for_log.py
/home/tite/Desktop/agent-system-run/pipeline-fold-2026-10-30/lessons.md <its line count>` until the main session's
`Merged: a->b` or `Merged: a+b` line is there, then run the check again. Merge nothing yourself.

- [ ] **Step 1: Write the failing tests on the briefs and SKILL.md**

In `scripts/tests/test_skill_example.py`, after `load` (`:62-63`):

```python
def read(rel: str) -> str:
    # A file of the skill with its whitespace folded, as the rule test folds a brief: a phrase may wrap at any space
    return " ".join((SKILL / rel).read_text(encoding="utf-8").split())


BRIEFS = [f"example/{r}-assignment.md" for r in ROLES] + ["example/common.md"]
```

In `RULES["common.md"]`, the pin `"then reviews each built commit's diff",  # B16` (`:47`) becomes two (C24, A15):

```python
        "the critic makes one short coverage round on each plan task and reads no code",  # B16
        "one verifier reads each built commit's diff by file against the task's steps and the spec",  # B16
```

`WAITERS["critic-assignment.md"]` (`:253-255`: the waiters on `plan-log.md`, `build-log-a.md` and `build-log-b.md`)
becomes the `plan-log.md` waiter alone (C24, A14): `"critic-assignment.md": ["python3 /r/wait_for_log.py /r/plan-log.md
13"],` on one line. `WAITERS["planner-assignment.md"]` (`:252` at 3c80656, the planner's `critique.md` waiter)
becomes (C42; the line fits 120 characters, as `ruff format` leaves it):

```python
    "planner-assignment.md": [  # C18, C42: the critic sets line 1 in place; the launched fixer waits on none
        'python3 /r/wait_for_log.py /r/critique.md 13 --first "STATUS: reviewed through Task 3" --first "STATUS: done"',
    ],
```

In `scripts/tests/test_open_ids.py`, `test_once_exits_0_when_the_condition_holds_and_3_when_not`, after `:35` (C42: one
assert per outcome of `--first`):

```python
    first = ("--first", "STATUS: reviewed through Task 1", "--first", "STATUS: done")  # line 1 set in place
    line_one = write(tmp_path, "line-one.md", "STATUS: reviewed through Task 1\n## Task 1\n")
    assert run_script("wait_for_log.py", line_one, "2", *first, "--once").returncode == 0
    assert run_script("wait_for_log.py", log, "2", *first, "--once").returncode == 3
```

At the end of `test_skill_example.py` (C22, C23, C25, C26, A14, A15):

```python
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


def test_no_brief_names_an_r_id_and_each_finding_on_a_commit_is_a_v_id():
    # R ids are retired (spec Decided 3): no brief files, waits for or answers one; old runs still parse.
    for name in BRIEFS:
        assert not re.search(r"R<n>|#### R|\(diff\)", read(name)), name
    for lane in "ab":
        assert "log `V<n>: fixed — <sha>`" in read(f"example/builder-{lane}-assignment.md"), lane
    assert "`#### V<n> — (spec)` in `verify.md`" in read("example/plan-fixer-assignment.md")
```

At the end of `scripts/tests/test_skill_md.py` (C23, C26):

```python
def test_skill_md_gives_the_critic_the_plan_and_the_verifier_the_diff():
    # Spec Decided 3: one reader per commit; R ids retired; a V id has one of three causes.
    skill = " ".join((SKILL / "SKILL.md").read_text(encoding="utf-8").split())
    assert "own clean worktree; reads the diff by file; findings V<n> (code)|(plan)|(spec) with a repro;" in skill
    assert "tags each finding `(code)`, `(plan)` or `(spec)`" in skill and "R ids" not in skill
    assert "- The critic makes one coverage round per task (C and A ids) and reads no code; the verifier" in skill
```

- [ ] **Step 2: Run them to verify they fail**

Run: `(cd .claude/skills/running-specagent-pipelines/scripts && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_skill_example.py tests/test_skill_md.py tests/test_open_ids.py tests/test_docs.py)`
Expected: `6 failed, 27 passed`. The six: `test_each_rule_the_spec_moves_into_a_brief_is_in_that_brief` (`common.md`
holds neither new B16 clause),
`test_every_waiter_a_brief_names_is_given_in_full_with_a_placeholder_for_each_word_the_agent_fills_in`
(`planner-assignment.md`: the `--first` waiter), `test_the_critic_reviews_no_diff_and_the_verifier_reads_it`
(`AssertionError: diff review`: item 2's heading), `test_no_brief_names_an_r_id_and_each_finding_on_a_commit_is_a_v_id`
(`AssertionError: example/plan-fixer-assignment.md`: the `(diff)` of `:12`),
`test_skill_md_gives_the_critic_the_plan_and_the_verifier_the_diff` (the pipeline block's verifier line),
`test_once_exits_0_when_the_condition_holds_and_3_when_not` (`assert 2 == 0`: argparse rejects `--first`). Measured on
a copy of lane a's skill folder at 3c80656 with Step 1 applied (`scratch/plan-fixer/t5b` in the run folder).

- [ ] **Step 3: Rewrite the texts**

Each change quotes the text at 9bf3542 (or as Task 4 leaves it) and gives its replacement; wrap at 120 characters.

`example/critic-assignment.md`:
1. `:3`, after "then the spec by sections.": "One critic by default; a second (`critic-b`, even tasks, ids from 500) only when
   `_agents.json` names it."
2. `:6-7` (C25): "1. The planner (`<project>/planner`) fixes the plan from your coverage findings at once (the plan fixer,
   when the watcher launches it, finds them itself). Each finding must be actionable without guessing."
3. `:23-24` (C25): "message `<project>/plan-fixer` (`Critic: …`); the planner only writes new tasks." becomes "message
   `<project>/planner` (`Critic: C3–C5, A2 for Task 2 in critique.md. Answer now.`)."; `:25`: "check the plan fixer's
   answers" becomes "check the answers".
4. Item 2 (`:27-34`, the diff review) goes. Item 3 (`:35-36`) becomes "2. One coverage round per session, then hand
   over. When `critique-response.md` says `STATUS: plan complete` or `STATUS: done` and every id is answered, write
   `critique-summary.md`" and its sentence goes on as it is (Task 4's planner sets `STATUS: done` once it has answered
   the last coverage round, `task-04.md:295-302`).
5. Proof rule `:41`: "(or the diff hunk) " goes. `:47-48`: "`git show`, `git diff`, " goes from the read-only commands.
6. `:52` (C25): "sections `## Index`, `## Task N`; one" (no `## Task N (diff)`).
7. Rules `:57-58` (C25): after "Run no git command that writes." the sentence "You never open a checkout's code: the
   verifier reads the diff."; "the task file by line ranges, the diff by file" becomes "the task file by line ranges".
8. `:62`: "the checklists of a coverage round and a diff round" becomes "the checklists of a coverage round"; the line's
   ranges and the `Skills:` line stay (`DOMAIN` pins them).

`example/verifier-assignment.md`:
1. `:6` (C25): "the plan fixer (`<project>/plan-fixer`) fixes `(plan)` findings" becomes "the planner
   (`<project>/planner`) fixes `(plan)` and `(spec)` findings (the plan fixer when the watcher has launched it)".
2. Item 1, `:13`: between "(`uv sync` once per worktree; again when `uv.lock` changed)," and "run, from the task file":
   "then read the diff by file (`git show <sha> --stat`, then `git show <sha> -- <path>`) against the task's steps and
   the spec: a step not built as written, a contract or shared name changed, a file outside the task's `files:` list,
   a test weakened, are findings. Then".
3. `:21` (C26): "`#### V<n> — (code)|(plan) <title>`" becomes "`#### V<n> — (code)|(plan)|(spec) <title>`".
4. `:23-24`: "`(plan)` ones also `<project>/plan-fixer`." becomes "`(plan)` and `(spec)` ones also `<project>/planner`
   while line 1 of `critique-response.md` is not `STATUS: done` (after that the watcher launches the plan fixer on
   demand, which finds them itself)."; "`R<n>/V<n>: fixed — <sha>`" becomes "`V<n>: fixed — <sha>`" (C22).
5. Proof rule `:36-37` (C26): after "`(plan)` when a later task would repeat it or a contract changes" add "; `(spec)`
   when the step is built as the plan says and the spec says otherwise". Item 3 keeps one commit per session.

`example/builder-a-assignment.md` and `example/builder-b-assignment.md`, the same lines in both (C22):
1. Item 3, `:27`: "the verifier and critic wait on this file's line count" becomes "the verifier waits on this file's
   line count"; `:29`: "and a message to `<project>/plan-fixer`" becomes "and a message to `<project>/planner` while
   line 1 of `critique-response.md` is not `STATUS: done` (after that the watcher launches the plan fixer on demand)";
   the line form `B<n>: sent to plan-fixer — <proof>` stays (`open_ids.py` and `check_formats.py` read it).
2. Item 4 (`:31-34`): "4. Findings on your commits arrive as `V<n>` (verifier, in `verify.md`), each `(code)`, `(plan)`
   or `(spec)`. Fix `(code)` ones first, test first, one commit `fix(template): V<n>, V<m> — <what>`, and log `V<n>:
   fixed — <sha>` (or `rejected — <proof>`); `(plan)` and `(spec)` ones are answered in `critique-response.md`: build
   what the plan says once it is fixed. Check `verify.md` for new ids before each task (`grep -n '^#### '`)."

`example/judge-assignment.md` `:20` (C22): "(`#### C<n>`, `#### A<n>`, `#### R<n>`)" becomes "(`#### C<n>`, `#### A<n>`)".
`example/handoff-rule.md` `:13-15`: "- Critic: when you have finished one unit, the coverage round of one plan task (its
findings are in `critique.md`, the STATUS line is updated), and you have checked the answers that were waiting."

`example/plan-fixer-assignment.md`, as Task 4 leaves it (its step 1 keeps the list of where ids are filed):
1. `:12`: " (also their `(diff)` sections)" goes; "the `(plan)` V ids on those tasks" becomes "the `(plan)` and `(spec)`
   V ids on those tasks".
2. Step 1's list, `:19-20`: "`#### R<n> — (plan)` there (diff findings that touch the plan), " goes; "`#### V<n> —
   (plan)` in `verify.md`" becomes "`#### V<n> — (plan)` and `#### V<n> — (spec)` in `verify.md`".
3. Step 2, `:27-28`: "`B<n>`, `R<n>`, `V<n>` the same way" becomes "`B<n>` and `V<n>` the same way".

`example/common.md`:
1. The pipeline-shape bullet of "Owner decisions that bind every role" (`:34-40`, as Task 4 leaves it; C24): "the critic
   makes one short coverage round on each plan task and then reviews each built commit's diff" becomes "the critic makes
   one short coverage round on each plan task and reads no code"; "one verifier re-runs every task's checks in its own
   worktree and the full suites at milestones" becomes "one verifier reads each built commit's diff by file against the
   task's steps and the spec, re-runs every task's checks in its own worktree and the full suites at milestones".
2. "Messages" (`:58-62`), after "a message only wakes it sooner.": "Who messages whom on a finding: the critic the
   planner; the verifier the builder, and the planner for a `(plan)` or `(spec)` V; a builder the planner for a `B<n>`;
   the last two only while line 1 of `critique-response.md` is not `STATUS: done`, since then the watcher launches the
   plan fixer on demand and it finds the open ids itself."

`example/README.md` (C25), `:43`: "- `critic-assignment.md`: the critic: one coverage round per task (C and A ids); it
reads no code."; `:46`: "- `verifier-assignment.md`: the verifier, who reads each built commit's diff by file and re-runs
its checks in its own worktree (V ids with their cause)."

`SKILL.md` (C26): the pipeline block's verifier line (`:35`): "verifier ⇄ builder   own clean worktree; reads the diff by
file; findings V<n> (code)|(plan)|(spec) with a repro;" and a second line at the block's text column (21 spaces, as
`:31`): "the builder fixes at once"; `:40`: "the verifier tags each finding `(code)`, `(plan)` or `(spec)` and sends
`(plan)` and `(spec)` ones to the planner too."; `:47`: "- The critic makes one coverage round per task (C and A ids)
and reads no code; the verifier reads each built commit's diff." SKILL.md stays at most 12,000 bytes
(`test_skill_md.py:41`): 11,913 measured with Task 4's `:44-46`.

`scripts/wait_for_log.py` at 3c80656 (C42): the docstring's usage line (`:4`) becomes "Usage: python3 _wait_for_log.py
FILE LINES [--first TEXT]... [--once]   Polls once a minute; gives up after 8 hours." with a line after it: "  --first
TEXT, repeatable: exit also when line 1 equals one of the texts (a line set in place adds no line)."; after
`ap.add_argument("--once", action="store_true")` (`:16`) one line, and in `check` (`:21-25`) two before its last
`return`:

```python
ap.add_argument("--first", action="append", default=[], metavar="TEXT")
```

```python
    if lines and lines[0].strip() in args.first:
        return f"first line is now: {lines[0]}", True
```

`scripts/docs/wait_for_log.md`: the usage line (`:3`) becomes `python3 -I scripts/wait_for_log.py FILE LINES [--first
TEXT]... [--once]`; at the end, after a blank line: "`--first TEXT`, repeatable: it also exits when line 1 of FILE
equals one of the texts. The planner waits so on `critique.md`, whose line 1 the critic sets in place, which adds no
line."

`example/planner-assignment.md` as Task 4 leaves it (3c80656):
1. The last-task bullet (`:63-67`, C42): "`python3 <run-dir>/wait_for_log.py <run-dir>/critique.md <lines>` (its line
   count; again after each exit)" becomes "`python3 <run-dir>/wait_for_log.py <run-dir>/critique.md <lines> --first
   "STATUS: reviewed through Task <last>" --first "STATUS: done"` (its line count; the critic sets line 1 in place,
   which adds no line; again after each exit)"; "later B, `(plan)` V and R ids are the plan fixer's" becomes "later B
   and `(plan)` or `(spec)` V ids are the plan fixer's". No shell loop: the pipeline check flags `sleep` in a command
   (`evals/graders/pipeline_plan.py:44`, `:459-475`).
2. Lanes (`:3`, B3): "and message `<project>/plan-fixer` (`planner: contract for Task N — <name>`), which carries it
   into the other task;" becomes "and message the planner of that task's lane (`planner: contract for Task N —
   <name>`), who carries it into that task;" (the fixer, launched on demand, reads open ids, not messages).

`README.md` at the repository root, the pipeline diagram at 3c80656 (B3): `:56` becomes `planner["planner<br/>writes
each task, answers its findings"]`; `:58` becomes `fixer["plan fixer<br/>on demand: open ids by count or age"]`; `:61`
(`review["critic<br/>each commit: R findings"]`) and `:68` (`review -.->|R findings| ba & bb`) go; `:62` becomes
`verifier["verifier<br/>reads each diff, re-runs the checks: V findings"]`; `:65` becomes `critic -.->|findings|
planner -.->|revised task| critic`, followed by a new line `critic -.->|open ids past a count or age| fixer`; `:67`
becomes `ba & bb --> verifier`; `:70` becomes `verifier -.->|plan findings| planner`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: the command of Step 2.
Expected: `33 passed`: `test_skill_example.py` 14 (the 12 at 9bf3542, the waiter and the domain-section tests among
them, and Step 1's two), `test_skill_md.py` 7 (its 6 and Step 1's one), `test_open_ids.py` 4, `test_docs.py` 8.

- [ ] **Step 5: The decision page**

One page for spec Decided 3 (`docs/design-docs/pipeline-fold.md:91-99`; one decision per page, in the commit with its
code, `_common.md`, "Documentation with the code"; Decided 5, 4 and 2 have their pages in Tasks 2, 3 and 4):
`wiki/decisions/critic-on-the-plan-verifier-on-the-code.md`, titled "The critic reviews the plan only; the verifier
reads the code", front matter with the keys of Task 3's page `wiki/decisions/plan-steps-and-blocks-in-two-files.md:1-13`
(`title`, `type: decision`, `status: draft`, `updated: 2026-10-30`, `audience: [all]`, `decided: 2026-10-30`, `by:
owner`, `why`, `would_change_if`, `decision_status: decided`, `scope: global`); the decision: the critic keeps its
coverage round (C and A ids) and never opens a checkout's code, the verifier reads each built commit's diff by file
and files V ids with their `(code)`, `(plan)` or `(spec)` cause, R ids are retired for new runs (old runs still parse),
one critic by default with the odd/even parity as an option; `why` from the spec's Intent (`:8-25`);
`would_change_if` from Measurement 3 (`:147-148`: the measurement run loses quality and this pair is unfolded); under
12,000 bytes. Its `.summary.md`: four lines, the first `Decision (owner, 2026-10-30): ...`. `wiki/index.md`: one line
at the end of `## Decisions`, after Task 4's (Task 3's is `:43` at 9bf3542), in its form. `wiki/log.md`: a section at
the end in the form of `wiki/log.md:73-76`: `## 2026-10-30 pages written with Task 5 of the pipeline-fold run`, `-
commit: Task 5 of the pipeline-fold run`, `- created: decisions/critic-on-the-plan-verifier-on-the-code.md`, `-
updated: index.md`. Both files are index-like: a task appends its own lines at the end and never reorders another
task's (the rule of the manager-build run, `lessons.md`, 22:45 UTC).

Run (at the repository root): `wc -c wiki/decisions/critic-on-the-plan-verifier-on-the-code*.md`;
`grep -c 'decisions/critic-on-the-plan-verifier-on-the-code.md' wiki/index.md wiki/log.md`
Expected: each page under 12,000 bytes; `wiki/index.md:1`, `wiki/log.md:1`.

- [ ] **Step 6: Ruff, once, and commit**

Run: `uv run ruff check .`; `uv run ruff format --check .`
Expected: clean.
Checks once each (`_common.md`, "Checks once each"): the full suites (`uv run pytest -q`, `just validate`, `uv run harness
docs-check`, `uv run harness wiki-lint`) and `uv run harness validate` are the verifier's at M2, not this task's; for
this task this replaces the index's Global Constraints line on them (`00-index.md:28-30`).

```bash
git add .claude/skills/running-specagent-pipelines README.md wiki/decisions/critic-on-the-plan-verifier-on-the-code.md \
  wiki/decisions/critic-on-the-plan-verifier-on-the-code.summary.md wiki/index.md wiki/log.md
git commit -m "feat(template): Task 5 — The critic on the plan, the verifier on the code"
```

## Deferred
- `findings_report.py` columns: R stays for old runs; a later cleanup may hide an all-zero R column.
- The critic's `add_dirs` in `example/agents.json` (its entry at `:82`) still name `<worktree-a>` and `<worktree-b>`,
  which it no longer reads; dropping them touches the settings tests and is left to a later task.
- `scripts/docs/open_ids.md:8` keeps `## Task 2 (diff)` as an example of a heading `open_ids.py` reads: old runs parse.
- B3, Task 4's leftovers that this task does not take: `wiki/decisions/no-fresh-session-after-a-finished-hand-off.md:18-20`
  describes exit 3 without R6's stop (Task 4's decision page states it); `example/agents.json:36`, the fixer's fresh
  text "then hand over", which the brief's Step 4 overrides when nothing is open (the watcher handles both).

## Verified
- `R<n>`, `#### R`, `(diff)`, "diff review", "diff round" at 9bf3542 (`grep -rn` on `example/*.md` and `SKILL.md`):
  critic `:30-33`, `:35`, `:52`, `:62`; plan fixer `:12`, `:19`, `:27`; both builders `:31-33`; judge `:20`;
  verifier `:24`; handoff-rule `:13`; README `:43`; common `:37`; SKILL `:47`; `scripts/docs/open_ids.md:8` (Deferred).
- `test_skill_example.py` at 9bf3542: `SKILL` `:17`, `ROLES` `:19`, `RULES` `:41-59` (B16 pin `:47`, Task 4's `:48`),
  `load` `:62`, `DOMAIN` `:187-195`, `WAITERS` `:248-259` (fixer `:249-252`, critic `:253-255`), 12 tests, no `read`
  or `BRIEFS`; `test_skill_md.py`: 6 tests, the 12,000-byte cap `:41`.
- Task 4 is built at 3c80656: `WAITERS` holds the planner's `critique.md` waiter at `:252` (plan b3bd3d9) in place of
  the fixer's four; `planner-assignment.md:63-67` is the last-task bullet, `:3` the lanes' contract message; root
  `README.md:56-70` the diagram (each old line of Step 3 found once there, scratch copy).
- C42: `wait_for_log.py` (3c80656) exits only on `len(lines) > seen` (`:21-25`), 480 polls of 60 s (`:28-34`); the
  critic sets line 1 in place (`critic-assignment.md:19-20`, `STATUS: done` `:37-38`); `test_open_ids.py:32-35` holds
  the `--once` asserts; the pipeline check flags `sleep` at a command position (`evals/graders/pipeline_plan.py:44`,
  `:459-475`), so no shell loop.
- `check_formats.py:60` (`CAUSE`: code|plan|spec), `:227-230`; `findings_report.py:34`; `open_ids.py:56`.
- SKILL.md bytes: 11,696 at 9bf3542, 11,806 after Task 4's `:44-46`, 11,913 after Step 3 (`wc -c`, scratch copy).
- Red and green measured on lane a's skill folder at 3c80656 (`scratch/plan-fixer/t5b`: `t5edit.py t5tests|t5text`,
  `t5c42.py tests|text`): 6 failed, 27 passed, then 33 passed; the skill's whole `scripts/tests` on that copy after
  Step 3: 450 passed, 2 deselected
  (`test_catalogue.py::test_the_table_command_on_the_checkout_lists_every_agent_file_as_a_type`,
  `test_measure_manager.py::test_the_readme_and_the_forms_carry_the_tool_s_contract`, which fail on a pristine copy
  too: the copy lacks the rest of the repository). Without C42's edits, on lane a's working tree at 4b517dd: 4 failed,
  17 passed, then 21 passed on the two skill test files.
- `ruff check` and `ruff format --check` with `pyproject.toml` (line-length 120, `:18`) pass on the added code.
- The second critic's form: `manager-build-2026-10-29/_critic-b-assignment.md:7-8` (even tasks, ids from 500).
- `git merge-base --is-ancestor`: "exit with status 0 if true, or with status 1 if not" (`man git-merge-base`); lane b
  at 92dcaae holds d0bd2e6 (0) and lacks Task 2's b797afc (1).
- Spec Decided 3 `pipeline-fold.md:91-99`; wiki at 9bf3542: index `:43` (Task 3's line), log `:73-76`, Task 3's
  decision page keys `:1-13`; commit form `feat(template): Task N — <title>` (`_builder-b-assignment.md:22`).
