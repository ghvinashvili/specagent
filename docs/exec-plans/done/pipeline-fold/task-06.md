# Task 6 — The measurement: Task 10 rebuilt with the folded pipeline

builder: a
depends_on: 1, 2, 3, 4, 5, 7
milestone: M3
status: cancelled (owner, 2026-10-30 15:4x UTC)

## Cancelled
The owner cancelled the measurement run on 2026-10-30 at 15:4x UTC: no four to six hours of measuring and no tokens
thrown into tests.
- Step 0, the score rules of `score_run.py` (V5, R4, C31), is on `main`: ecf5bbe, dc1a11b, 7c643de.
- Steps 1-7 are not run: no measure run folder, no rebuilt Task 10, no plain session, no score of either.
- The measure worktrees and branches (`measure/task-10`, `measure/task-10-plan`) are deleted by the main session.
- The comparison table is not written; the design document's Measurement section stays as the recipe for a later run.

## Goal
The fold is kept only if the numbers say so. Golden Task 10 of the manager-build run (the scripts README split into
pages and the price table of `usage_report.py`; 995 lines; 1 plan finding, 1 diff finding, no V) is planned and built
again from the spec with the folded pipeline, on a scratch branch from the commit before its original build, with
`lessons.md` and the vault on. `score_run.py` scores both; the design document's status follows the comparison.
Then, once, a plain session on the same task.

**Files:**
- Create (outside the repository): `/home/tite/Desktop/aftpro/runs/fold-measure-<date>/` from the skill's
  `example/` (briefs, settings, `agents.json`, waiters) with the placeholders filled as `example/README.md` lists them
- Create (repository, scratch branches `measure/task-10-plan` and `measure/task-10` from `fa475a4`, the original
  Task 10's base, C27): nothing kept; both are deleted after the score
- Modify: `docs/design-docs/pipeline-fold.md` (a "Measured" section and the status line), the owner's vault page
  `context/measurements/2026-10-29-manager-build.md` (the comparison table; outside the repository)
- Modify (Step 0, V5 and R4; in `.claude/skills/running-specagent-pipelines/`): `scripts/manager/score_run.py`,
  `scripts/tests/test_score_run.py`, and the page that states the script's rules, `scripts/manager/README.md`
  (`## score_run.py`, `:103-147` at a879526; V4's fix kept the rules there, so no `scripts/docs/score_run.md`)

**Interfaces:**
- Consumes: Task 1's `score_run.score`; the skill's `preflight.py check`, `catalogue.py` (the prefix bounds),
  `watch_agents.py --check`, `usage_report.py --prefix`.
- Changes (Step 0): the cost rule of `score_run.score`; each `attribution[<session id>]` gains `by`: `lines` (its own
  unit lines), `next` (the tasks of its role's next session) or `none`; each `tasks[<task>]` row gains `rejected`
  (R4), shown as a task-table column and as `rejected <k>` in the first line.
- Produces: the comparison table (original Task 10 slice against the measured run, one row per item of the spec's
  score list, `pipeline-fold.md:67-73`: findings by kind, how many were rejected (R4) and how many the critic missed;
  sessions, cap hand-overs, idle restarts and first-call tokens; cost; requests and their minutes; repeated lesson
  classes; and the cache ratio), and one row per R of the original Task 10 (R502; spec `:146`, "anything the
  verifier found that the original run's critic had found as R", C30): the measured V that names the same defect,
  `absent` (the built commit does not have it) or `missed`; the status of the design document (`accepted` when cost
  fell and quality held: no V the original run did not have, no rebuild, Step 4's three checks pass on the built
  commit, as the judge is not launched (spec `:145`, C33); else `superseded` by a note on which pair is unfolded,
  and a Deferred line in the index: unfold that pair, one at a time, and measure again on Task 10, spec `:148`).

- [ ] **Step 0: Every session of a task in its cost row (V5)**

Task 1's rule (`task-01.md:31-34`, `:112-113`; at a879526, Task 1 with V1-V4 and R1-R3 fixed: `score_run.py:52`,
`:100-117` keep an Edit's or Write's `file_path` only, `:184-185` take `Task N` from record writes) misses a
`Task N: done` written with Edit, the
verifier's sections, the fixer's answer lines and every hand-over that wrote no unit line: in the baseline 55.2% of
the cost stays in `none` ($372.08 of $674.50) and Task 10's row holds 11 sessions (`verify.md` V5). The design
attributes a session by "the unit lines they wrote" (`pipeline-fold.md:71`), and a role's unit lines include "an open
id of its parity" (`:120-121`). Task 1's plan text stays, as it is built; this step changes the code, one rule for the
baseline and the measured run alike (`:161-162`):
1. A call writes a record file when it is an Edit or a Write whose `file_path` matches `RECORD`, or a Bash command
   that names one and writes it (the write test as V2's fix leaves it). Its text is the command (Bash), the lines of
   `new_string` that `old_string` does not have (Edit), or `content` (Write).
2. That text names a task by `Task N:` or `## Task N` at a line start (`TASK`, `score_run.py:45`, which also takes
   one after a quote, as a Bash command writes it), or by an id there (`#### <id>` or `<id>:`; C, A, R, V or B and a
   number): the task the id is filed under in the run's records, C, A and R by `fr.task_ids` of `critique.md`, V by
   `fr.task_ids` of `verify.md` (as `task_counts` reads them, `:71-77`), B by the build-log rule of `:86-96` in the
   log the line is written to; a B line written to `critique-response.md` names the task of the B whose first line
   in its log is `B<n>: sent to …`, as rule 5 reads it (A17: B ids are numbered per build log). An id filed under
   no task names none.
3. A session that names no task takes the tasks of its role's next session (in `ur.started` order) that names one: a
   hand-over continues its unit (`_handoff-rule.md:20-21`), and an idle restart is that unit's cost. A role's
   sessions after its last naming session keep `none`.
4. `attribution[<session id>]["by"]` is `lines`, `next` or `none`; a session with two or more tasks still splits its
   cost equally.
5. Rejected (R4; `pipeline-fold.md:67-68`, "which were rejected"): each task row gains `rejected`, the number of ids
   filed under the task (C, A, R and V as rule 2 files them, a B as `task_counts` files it, `:86-96`) that have an
   answer line `<id>: rejected` (`(?:- )?` before it, as a B line may have) in `critique-response.md` or a build log
   (`cf.build_logs`), each id once whatever lines follow it; an id filed under no task counts in `none`. B ids are
   numbered per build log (the baseline's `build-log-b.md` and `build-log-c.md` both hold B1-B3), so a B counts by a
   line in its own log, or by one in `critique-response.md` when its first line in its log is `B<n>: sent to …`. The
   row literals `:69`, `:247`, `:250` gain `"rejected": 0`, the task table a `rejected` column after `B` (`:346`
   header, `:348` cells), the first line `, rejected <k>` after `missed <k>)` (`found` `:323`, the line `:325-329`).
6. Idle (C31): a session is idle when none of its record writes holds a unit line, it ran no `git commit` and no
   call reached the cap. A unit line is a `Task N` or an id line as rule 2 finds them (an id filed under no task
   too) or a request line (`cf.REQUEST`, `check_formats.py:68`: `SANDBOX:`, `COPY-REQUEST:`, `CHECKOUT-REQUEST:`,
   `FF-REQUEST:`, found where rule 2 finds an id); spec `:69-70` counts "a fresh session that wrote no unit line
   before its own hand-off" and `:120` names the unit lines. Today any record write makes a session working
   (`session_entry`, `score_run.py:184`, `:191`), so a session whose only write is `ACK <msg_id>` (the answer to an
   order, `_common.md`, Messages) is not idle, and only folded runs write ACK lines (`grep -c '^ACK'`: 23 in this
   run's records at 08:49 UTC, 0 in the baseline's).

The rules page states the six rules in place of the old cost and idle sentences (`:118-123`), with one example
line each; its header row `:143` gains `rejected` after `B` (`test_score_run.py:255-263` pins the table's headers
to the page), and its example line `:137` gains `, rejected 0` after `missed 3)` (the baseline has no rejected
answer line: Verified). The tests, added to `scripts/tests/test_score_run.py` (its `run` and `home` fixtures; import
`tool` from `transcript_home` beside `bash`, `read`, `write`), V5's three:

```python
FIXER = "12121212-3434-5656-7878-909090909090"
EARLY = "13131313-2424-3535-4646-575757575757"
LATE = "14141414-2525-3636-4747-585858585858"


def test_a_line_written_with_edit_or_write_names_the_task(run, home):
    write_call = tool("Write", file_path=f"{run}/critique.md", content="## Task 2\n#### C2 — x\n")
    home.session("t/critic", CRITIC, [(30_000, 10, [write_call])], start="2026-10-30T19:20:00")
    old = "#### V1 — (plan) major, w"
    edit_call = tool("Edit", file_path=f"{run}/verify.md", old_string=old, new_string=f"{old}\n\n## Task 2 — def5678")
    home.session("t/verifier", VERIFIER, [(30_000, 10, [edit_call])], start="2026-10-30T19:30:00")
    d = score_run.score(run, "t/", None)
    assert (d["attribution"][CRITIC]["tasks"], d["attribution"][CRITIC]["by"]) == (["2"], "lines")
    assert d["attribution"][VERIFIER]["tasks"] == ["2"]  # V1's line is in old_string: not written by this call


def test_an_answer_or_fix_line_names_the_task_its_id_is_filed_under(run, home):
    answer = bash(f"printf '%s\\n' 'V1: applied — t' >> {run}/critique-response.md")
    home.session("t/plan-fixer", FIXER, [(30_000, 10, [answer])], start="2026-10-30T19:40:00")
    fix = bash(f"printf 'R1: fixed — def5678\\n' >> {run}/build-log-a.md")
    home.session("t/builder-a", LATE, [(30_000, 10, [fix])], start="2026-10-30T19:50:00")
    d = score_run.score(run, "t/", None)
    assert d["attribution"][FIXER]["tasks"] == ["1"]  # V1 is filed under ## Task 1 in verify.md
    assert d["attribution"][LATE]["tasks"] == ["2"]  # R1 under ## Task 2 (diff) in critique.md


def test_a_session_that_names_no_task_takes_the_tasks_of_its_roles_next_session(run, home):
    home.session("t/builder-a", EARLY, [(30_000, 10, [bash("git commit -m 'wip'")])], start="2026-10-30T19:05:00")
    note = write(f"{run}/handoff-builder-a.md")
    home.session("t/builder-a", LATE, [(30_000, 10, [note])], start="2026-10-30T19:55:00")
    d = score_run.score(run, "t/", None)
    early, late = d["attribution"][EARLY], d["attribution"][LATE]
    assert (early["tasks"], early["by"]) == (["1"], "next")  # the 19:10 builder-a session wrote Task 1: done
    assert (late["tasks"], late["by"]) == ([], "none")
    assert abs(sum(t["cost"] for t in d["tasks"].values()) - d["cost"]) < 1e-9
```

R4's test, beside `test_a_b_id_counts_once_for_the_task_its_text_names_or_the_next_done_line_below` (`:122-128` at
a879526), and `test_the_line_names_the_run_and_the_totals` (`:176-180`) in full, as the line gains `rejected 0`:

```python
def test_rejected_counts_each_id_once_under_its_task_from_the_response_and_the_build_logs(tmp_path):
    critique = "STATUS: x\n\n## Task 1\n#### C1 — x\n#### A1 — y\n\n## Task 2 (diff)\n#### R1 — (code) z\n"
    (tmp_path / "critique.md").write_text(critique, encoding="utf-8")
    (tmp_path / "verify.md").write_text("## Task 2 — def5678\n#### V1 — (code) minor, u\n", encoding="utf-8")
    response = "STATUS: x\nC1: rejected — a\nC1: rejected — b\nA1: added to Task 1 — t\nB1: rejected — c\n"
    (tmp_path / "critique-response.md").write_text(response, encoding="utf-8")
    log = "Task 1: done — a\nB1: sent to plan-fixer — x\nTask 2: done — b\nR1: rejected — p\nV1: rejected — q\n"
    (tmp_path / "build-log.md").write_text(log, encoding="utf-8")
    (tmp_path / "build-log-b.md").write_text("B1: fixed in code — Task 1 Step 2, y\n", encoding="utf-8")
    assert {t: r["rejected"] for t, r in score_run.task_counts(tmp_path).items()} == {"1": 1, "2": 3}


def test_the_line_names_the_run_and_the_totals(run):
    line = score_run.score(run, "t/", None)["line"]
    assert line.startswith(
        "score run: tasks 2, findings C 1 A 1 R 1 V 2 (plan 1, missed 1), rejected 0, sessions 2 (cap 1, idle 0)"
    )
```

A16's and A17's tests (rules 6 and 2), beside V5's:

```python
BUILDER_B = "15151515-2626-3737-4848-595959595959"


@pytest.mark.parametrize(
    ("line", "idle", "tasks", "by"),
    [
        ("ACK 1234abcd", True, [], "none"),
        ("R1: fixed — def5678", False, ["2"], "lines"),
    ],
)
def test_a_session_whose_record_writes_hold_no_unit_line_is_idle(run, home, line, idle, tasks, by):
    write_line = bash(f"printf '{line}\\n' >> {run}/build-log-a.md")
    home.session("t/builder-a", LATE, [(30_000, 10, [write_line])], start="2026-10-30T19:55:00")
    late = score_run.score(run, "t/", None)["attribution"][LATE]
    assert (late["idle"], late["tasks"], late["by"]) == (idle, tasks, by)


def test_a_b_line_names_the_task_of_its_own_log_and_an_answer_the_task_of_the_b_sent_to_a_fixer(run, home):
    (run / "build-log-b.md").write_text("B1: fixed in code — x\nTask 2: done — def5678\n", encoding="utf-8")
    fix = bash(f"printf 'B1: fixed in code — x\\n' >> {run}/build-log-b.md")
    home.session("t/builder-b", BUILDER_B, [(30_000, 10, [fix])], start="2026-10-30T19:45:00")
    answer = bash(f"printf '%s\\n' 'B1: applied — t' >> {run}/critique-response.md")
    home.session("t/plan-fixer", FIXER, [(30_000, 10, [answer])], start="2026-10-30T19:40:00")
    d = score_run.score(run, "t/", None)
    assert d["attribution"][BUILDER_B]["tasks"] == ["2"]  # B1 above Task 2: done in build-log-b.md
    assert d["attribution"][FIXER]["tasks"] == ["1"]  # build-log-a.md's B1 is the one sent to the planner
```

Run: `(cd .claude/skills/running-specagent-pipelines/scripts && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_score_run.py)`
before the change and after it; then `uv run ruff check .`; `uv run ruff format --check .`
Expected: before, 8 failed, 25 passed (measured on a scratch copy of 0d2445f's scripts, where `score_run.py` and
its tests are as at a879526, with these tests): V5's three (no `by` key; the fixer's `tasks` empty), R4's (no
`rejected` key), the rewritten line test (no `rejected 0`), A16's two (no `by` key) and A17's (the builder-b
session's `tasks` empty); after, 33 passed (a879526's 26 with the line test rewritten, and these 7); ruff clean.

```bash
git add .claude/skills/running-specagent-pipelines/scripts
git commit -m "feat(skill): score_run.py — every session of a task in its row, rejected ids, idle by unit lines (V5, R4, C31)"
```

- [ ] **Step 1: The baseline slice**

Run: `mkdir -p /home/tite/Desktop/aftpro/runs/pipeline-fold-2026-10-30/scratch/main` (the run's scratch rule:
never under /tmp, `lessons.md` "Read first" item 6), then
`python3 -I scripts/manager/score_run.py /home/tite/Desktop/aftpro/runs/manager-build-2026-10-29 --prefix manager/ --json > /home/tite/Desktop/aftpro/runs/pipeline-fold-2026-10-30/scratch/main/baseline.json`
Expected: the `tasks["10"]` row and the roles' rows, under Step 0's rule; copy the Task 10 row (`rejected` too, R4)
and the per-role rows
of the sessions attributed to Task 10 (`attribution`, any `by`) into the vault page's new table as the "original"
column (`main-duties.md` gets the D4 line), with the cost left in `none`, its share of `cost`, and the cost moved by
`next`. Every session left in `none` comes after its role's last naming session; any other is a Step 0 bug, sent
back before the slice is copied. This score replaces the vault's baseline line of M1 (scored with Task 1's rule),
with one sentence on the change (V5; and idle by rule 6, C31, where M1 counted the 3 sessions that wrote no record
line at all, the vault page `:74`).

- [ ] **Step 2: The run folder**

Place `example/`'s files as its README's "Starting a run" items 1-2 say (C32; at 0d2445f `example/README.md:7-14`):
each brief as `_<name>` in the run folder (the `_` prefix is what the settings deny), `lessons.md` as it is, the
configs and settings under `<run-dir>/_control/` (`_control/_agents.json`, `_control/<role>-settings.json`), the
waiters `scripts/wait_for_*.py` in the run folder; one builder, so `builder-b-*` deleted and `builder-a` renamed
`builder` (`:27-28`). Fill every placeholder of the README's list (`<run-dir>`, `<plan-worktree>`, `<checkout>`,
`<worktree-a>`, `<verify-worktree>`, `<skill-dir>`, `<vault>`, `<spec>`, `<run-name>`, `<project>` =
`fold-measure`: the agents are named `<project>/<role>`, `example/agents.json:45`, and `fold/` names this run's
own sessions, which `--prefix fold/` would score with the measured ones, C29). The spec is the manager-build
spec's items for Task 10, as `docs/exec-plans/done/manager-build/task-10.md:38-46` carries them (C28): items 9
(the `scripts/README.md` half) and 14 of section 8.3 and item 18 of section 10
(`/home/tite/Desktop/aftpro/runs/manager-spec-2026-10-29/spec.md:1029-1030`, `:1037`, `:1131`), and the
tracker row TD-008 (line 12 of `git show fa475a4:docs/exec-plans/tech-debt-tracker.md`), copied into the
run folder as `_spec.md` with one line at its top naming the sources and `fa475a4`. `agents.json`: one planner,
one critic, one builder (`builder`), one verifier, the plan fixer on demand (Task 4's fields); no judge.
Worktrees from `fa475a4` (C27: the original Task 10's base, its "review range fa475a4..129a9d5",
`manager-build-2026-10-29/build-log-b.md:15`; `129a9d5~1` is its WIP commit 5900551, which holds the task's 21
files): `measure-plan` on `measure/task-10-plan` and `measure-a` on `measure/task-10` (git refuses a branch that
another worktree has checked out, C32), `measure-verify` detached; the main session merges the plan branch into
`measure/task-10` before the builder's task, as this run does (c124ad8).

Run: `git -C <worktree-a> rev-parse --short HEAD` and
`git -C <worktree-a> cat-file -s HEAD:.claude/skills/running-specagent-pipelines/scripts/README.md`; for each of
Tasks 1, 2 and 4 (`build-log.md`) and Tasks 3, 5 and 7 (`build-log-b.md`, both in
`/home/tite/Desktop/aftpro/runs/pipeline-fold-2026-10-30/`), `grep -n '^Task <N>: done' <log>` (its `<sha>`),
then `git -C <skill-dir> merge-base --is-ancestor <sha> HEAD; echo $?`;
`python3 -I scripts/usage_report.py --prefix fold-measure/`;
`python3 -I scripts/manager/preflight.py check <run-dir> --checkout <checkout>` and
`python3 -I scripts/watch_agents.py --check <run-dir>/_control/_agents.json`
Expected: `fa475a4` and `29492` (the README before the split); one done line and `0` per task (the skill the run
uses holds every task this one depends on, as Task 5 Step 0 checks Task 4; on `1`, the merge comes first); the
prices line, the header and `total` with no agent row between them (no `fold-measure/` session yet); every check
ok; one decision line per agent, nothing launched.

- [ ] **Step 3: The owner's yes**

One message to the owner: the five sessions (planner, critic, builder, verifier, fixer on demand), the branch, the
expected cost from the baseline slice, the question. Nothing before the yes. `_control/usage.json` and the D0 line
before the launches, as the manager's duties say.

- [ ] **Step 4: The run**

Launch the planner, the critic, the builder and the verifier with the watcher's command builder; the watcher in the
background; the Monitor on the records; the request lines answered within minutes. The planner writes `task-01.md`
and `task-01.code.md` (Task 3's form) from `_spec.md`; the critic's coverage round; the builder; the verifier with the
diff reading (Task 5); the plan fixer only if the watcher launches it (Task 4). The run ends at `STATUS: done` in
`verify.md` with the verifier's full checks on the built commit.

Run, on the built commit `<sha>` (the `Task 1: done` line of the run's build log):
`git -C <worktree-a> cat-file -s <sha>:.claude/skills/running-specagent-pipelines/scripts/README.md`;
`(cd <worktree-a>/.claude/skills/running-specagent-pipelines && python3 -I scripts/usage_report.py --prefix fold-measure/ | head -1)`;
`git -C <worktree-a> diff fa475a4 <sha> -- .claude/skills/running-specagent-pipelines/scripts/tests/test_usage_report.py`
Expected: one built commit on `measure/task-10`; at most `12000` (the original's `files:` line, "an index, at most
12,000 bytes", `manager-build/task-10.md:6`); `prices of <date> from <page>` (8.3.14); an added assert on the
`total` row's form and value (10.18, the original's `acceptance:` line, `:7`; the original's test is
`test_the_total_row_is_the_last_line_and_sums_the_unrounded_costs`, 5900551 `test_usage_report.py:193`). These
three checks are the task's acceptance and, as the judge is not launched (spec `:145`), the quality check of Step
5's decision rule (C33).

- [ ] **Step 5: The score and the comparison**

Run: `python3 -I scripts/manager/score_run.py <run-dir> --prefix fold-measure/ --json > /home/tite/Desktop/aftpro/runs/pipeline-fold-2026-10-30/scratch/main/measured.json`;
`git -C <worktree-a> grep -n -F '(above)' <sha> -- .claude/skills/running-specagent-pipelines/scripts/README.md`
Expected: the measured column (`tasks["1"]`, the run's one task, `rejected` too, under Step 0's rule, with its
`none` and `next` as
in Step 1) beside the original one in the vault page's table and in the design document's "Measured" section; one
sentence per row on what changed. The R row (C30): R502, the original Task 10's one diff finding
(`manager-build-2026-10-29/critique.md:1820`: the README's Config v2 `milestones` row still said "(above)" after
the text it pointed at moved to `docs/watch_agents.md`; fixed at 5b8d3b1), gets the measured V that names the same
defect, or `absent` when no `(above)` line of the built README points at text that left it (the grep), or `missed`;
one sentence in "Measured". The decision rule of the design (Measurement 3): kept when cost fell and quality held
(no V the original run did not have, no rebuild, Step 4's three checks pass); else the losing pair is named, the
design's status set to `superseded` with the note, and the index's Deferred list gains "unfold <the pair>, one at
a time, and measure again on Task 10" (spec `:148`, C33).

- [ ] **Step 6: The plain session, once**

With the owner's yes: one session, `claude --bg --name fold-plain/plain` (a session with no name matches no
`--prefix`, C29; `claude --help`: `--bg`, `-n, --name`), the builder's settings, cwd a fresh worktree
`measure-plain` on a branch `measure/task-10-plain` from `fa475a4` (C27), the prompt the planner's brief material
and `_spec.md` in one message (no critic, no verifier); before the launch,
`python3 -I scripts/usage_report.py --prefix fold-plain/` prints no agent row; the verifier's checks and Step 4's
three run by the main session on its commit; scored with `--prefix fold-plain/`. One row more in the comparison
table.

- [ ] **Step 7: Close**

Delete the scratch worktrees and branches (`git worktree remove` `measure-plan`, `measure-a`, `measure-verify`,
`measure-plain`; `git branch -D` `measure/task-10-plan`, `measure/task-10`, `measure/task-10-plain`); the run
folder stays for the collector; the design document's status committed on `main`; the vault page pushed; the D4
line.

```bash
git add docs/design-docs/pipeline-fold.md
git commit -m "docs(design): pipeline fold — measured on Task 10, status set"
```

## Verified (Step 0, V5 and R4; plan fixer, 2026-10-30)
- `score_run.py` at a879526 (lane a: Task 1 with V1-V4 and R1-R3 fixed; unchanged at a877ad6, Task 2's WIP): `:42`
  `RECORD`, `:45` `TASK`, `:52` `TEXT_KEY` and `:100-117` `tool_texts` (`command` or `file_path` of a tool call),
  `:178` `ur.started`, `:184-185` (record writes, then `TASK` over them), `:69`, `:247`, `:250` (the row literals),
  `:71-77` `fr.task_ids`, `:86-96` (B ids by build log), `:245-252` `attribute`, `:323` `found` and `:325-329` (the
  first line), `:346`, `:348` (the task table's header and cells)
- `scripts/tests/test_score_run.py`: 26 tests collected at a879526 (`python3 -m pytest --co -q -p no:cacheprovider`);
  fixtures `home`, `run` (`:57-82`); sessions `CRITIC`, `VERIFIER` (`:22-23`); `CRITIQUE` files R1 under
  `## Task 2 (diff)`, `VERIFY` files V1 under `## Task 1 — abc1234` (`:25-34`); `RESPONSE` and `BUILD_LOG` hold no
  `rejected` line (`:29`, `:35-38`); `:122-128`, `:176-180`, `:255-263` (the headers pinned to the README section);
  `transcript_home.tool` (`:30`); `Home.rows` is a list (`transcript_home.py:62`), so one name holds several sessions
- Step 0's five tests on a scratch copy of a879526's scripts (`git archive a879526`): 5 failed, 25 passed, for the
  reasons Expected names; `ruff format --check` and `ruff check` clean with the repository's `pyproject.toml`
- `scripts/manager/README.md` at a879526: `## score_run.py` `:103-147`, the rules `:118-132`, the example line `:137`,
  the header rows `:143-145`; no `scripts/docs/score_run.md`; `check_formats.py:83-86` (`build_logs`: every
  `build-log*.md`)
- the baseline `manager-build-2026-10-29`: `grep -cE '^(- )?[CABRV][0-9]+: rejected'` gives 0 for its
  `critique-response.md` and `build-log-a.md` to `build-log-d.md`; B ids per build log (`build-log-b.md` B1-B3,
  `build-log-c.md` B1-B7, its B6 and B7 `sent to`)
- `pipeline-fold.md:67-73` (the score list), `:71`, `:120-121`, `:145-146`, `:161-162`; `verify.md` `#### V5`;
  `critique.md` `#### R4`; `_handoff-rule.md:20-21`
- C27-C33, A16, A17 (plan fixer, 2026-10-30 08:56 UTC): `git show --stat 129a9d5` lists no file; `git rev-parse
  --short 129a9d5~1`: 5900551, "21 files changed, 499 insertions(+), 316 deletions(-)"; `git log -1 5900551~1`:
  fa475a4 "merge: lane c (Tasks 6 and 8, baf3590) into lane b before Task 10"; `git cat-file -s` of the skill's
  `scripts/README.md`: 29492 at fa475a4, 7416 at 5900551; `manager-build-2026-10-29/build-log-b.md:15` (review range
  fa475a4..129a9d5); `git help worktree`: add refuses a branch "already checked out by another worktree"
- `docs/exec-plans/done/manager-build/task-10.md:6-7` (`files:` README "at most 12,000 bytes"; `acceptance:` 10.18),
  `:38-46` (Spec carried); its `00-index.md:113`, `:125` (3.1-3.8 are Task 1's), `:152` (TD-008 is Task 10's);
  `manager-spec-2026-10-29/spec.md:1029-1030` (8.3 item 9), `:1037` (item 14), `:1131` (10 item 18); line 12 of
  `git show fa475a4:docs/exec-plans/tech-debt-tracker.md`: TD-008; 5900551 `test_usage_report.py:193` (the total row)
- at 0d2445f (lane a; `score_run.py`, `test_score_run.py` and `manager/README.md` as at a879526: `git diff --stat`
  empty): `example/agents.json:45` (`<project>/planner`; the other agents `:58`, `:96`, `:122`, `:136`, `:150`);
  `example/README.md:7-14` (the run folder, `_control/`, the waiters), `:19` (`preflight.py check <run-dir> --checkout
  <checkout>`), `:23` (the watcher on `_control/_agents.json`), `:27-28` (one builder); `preflight.py:583-585`
  (`--checkout` required, `--config` default `<run-dir>/_control/_agents.json`); `usage_report.py:41-51` (rows by name
  prefix only), `:138-149` (prices line, header, `total`); `score_run.py:171-178` (`--since`, by day), `:181-191`
  (`session_entry`: `writes` `:184`, `idle` `:191`); `check_formats.py:62-68` (`REQUEST_KINDS`, `REQUEST`);
  `manager/README.md:123` (the idle sentence); `python3 -I scripts/usage_report.py --prefix fold-measure/`: no agent
  row, `total 0.00`; `claude --help`: `--bg, --background`, `-n, --name <name>`; `catalogue.py` validates no name
- `grep -c '^ACK'` at 08:49 UTC: `critique.md` 8, `verify.md` 7, `build-log.md` 6, `build-log-b.md` 2 in this run, 0 in
  the baseline's eight records; the vault's `context/measurements/2026-10-29-manager-build.md:74` (idle 3: "no record
  line at all"); `_common.md:77-79` (the ACK rule); `pipeline-fold.md:69-70`, `:120`, `:145-148`;
  `manager-build-2026-10-29/critique.md:1814-1922` (Task 10's diff sections; R502 at `:1820` the only R)
- Step 0's tests with A16's and A17's on a scratch copy of 0d2445f's scripts (`git archive`): 8 failed, 25 passed,
  for the reasons Expected names (`KeyError: 'by'` twice, `assert [] == ['2']`); `ruff check` and `ruff format
  --check` clean with the repository's `pyproject.toml`

## Deferred
- A second measurement on a task with many plan findings (a new project, thin lessons), where the on-demand fixer
  is expected to launch; this run will probably not launch it.
