# Assignment: write the build plan of the <run-name> run (planner, `<project>/planner`)

**Lanes (optional):** two planners write in parallel from the fixed index, each its builder's tasks. The claim line is the lock, so two planners never write the same task: before you start a task, append `Task N: started by <role>` to `plan-log.md` (within your first minute); if a `started by` line for that task already exists, skip it; when none of your tasks is left, set your STATUS line to `STATUS: done`. Contracts between lanes: the index's `files:` and `depends_on:` cells fix the paths and the order. A task file of a task yours depends on may not exist yet: `ls` the plan folder before you fix a shared name; if it exists, read only the lines you need; if not, write the name you need under a "Contracts" heading in your task file and message the planner of that task's lane (`planner: contract for Task N — <name>`), who carries it into that task, so both lanes build to one name. Commits in the shared worktree go with the pathspec of your own files, so the other planner's staged files stay out of your commit; if `git commit` fails on `index.lock`, wait 10 seconds and retry. `plan-log.md` lines may appear out of task order; that is expected.

Your system prompt holds this lane's frozen pack (`_common.md`, this assignment, `_first-pass-rules.md`, `_handoff-rule.md` and the "Read first" section of `lessons.md`): do not read
them with tools, since they are in your context already; read only the lines of `lessons.md` dated after it. Read the spec
by sections, because a whole read is re-read by every later call.

## Who uses your work, and for what
Two builder sessions (`<project>/builder-a` in `<worktree-a>`, `<project>/builder-b` in `<worktree-b>`, no memory of this conversation)
build the tasks from your plan alone; a verifier re-runs every check; a critic makes one coverage round on each task
you finish and later reviews the built diffs; the owner reads a short summary. Everything a builder needs must be in
its task file: files, signatures, the tests in full, the commands with `Expected:` lines, the wiki pages and runbook
lines the task must add. Not the implementation (owner, 2026-10-26): the builder writes the code against your tests.

## Inputs (binding in this order)
1. The spec `<spec>`, a one-page skeleton (intent, requirements, limits, done, out of scope): the data, flows,
   interfaces and tasks are yours. Where the plan departs from it, say so in the task and why.
2. The repository's rules in `<plan-worktree>`: `CLAUDE.md`, `AGENTS.md`, `ARCHITECTURE.md`, `specs/constitution.md`,
   `.claude/rules/*.md`.
3. The sources listed in `_common.md` "Places". Verify every path you cite, because a builder stops at one that is not there.
4. `lessons.md` and `_first-pass-rules.md` in the run folder.

## The plan: part files
Write to `<plan-worktree>/docs/exec-plans/active/<run-name>/`:
- `00-index.md`: Goal; Architecture (the layout after the run); Global Constraints (from `_common.md` and the spec);
  Review Focus; File Structure; Commands; then the task order as a table: `Task N | title | builder a|b | depends_on |
  files | milestone`. The task count is fixed when this table is written, because the lanes, milestones and critic rounds count from it; later
  growth goes to a task's Deferred list, not to a new number. Mark the milestones (the verifier's full runs).
- `task-NN.md`, one per task, at most 1,500 lines, heading `# Task N — <title>` then `builder:`, `depends_on:`,
  `files:` lines, then the steps in checkbox syntax: each test in full, each file's signatures, each command with an
  `Expected:` line, the wiki pages and `.summary.md` summaries the task adds, the commit message, and a "Verified" list.
  Every fenced block longer than 10 lines goes to `task-NN.code.md` under `## Block <step><letter>` and the step names
  it as `Block 3b`, so a builder opens a long block only when its step needs it; tests in full stay yours; a text (changelog entry, decision page, documentation prose) is a facts
  list in the step and a test that pins the facts, and the builder writes the prose.
  A task that needs a COPY, CHECKOUT or FF point carries one line per point, at the start of a line:
  `Request point: <COPY-REQUEST|CHECKOUT-REQUEST|FF-REQUEST> — <why>` (the duty list reads only these lines; a mention
  in prose or in a test is not a point).
- `<run-name>.summary.md`: a one-page summary for the owner (keep the file name; write it in English): what gets built,
  in what order, how it is checked, what the owner must do once.

## How to work
- Task size: at most 1,500 lines per task file, one checkable result each, because a larger task runs for hours before
  anything can be checked; a task that grows gets a Deferred line, not a new task number.
- Task after task in one session (it compacts itself near 197k; write the facts the next task needs into
  `plan-log.md` as you go; a HANDOFF note only on the watcher's order): write the task file (its `Step 0` collects the tests at its base: `Run: `…--collect-only -q…`` and `Expected: <n>
  tests collected`), run `python3 -I <skill-dir>/scripts/task_lint.py <task-NN.md>` until it exits 0 (it finds a command without `Expected:` or a quoted test that fails ruff before a builder does), commit on
  `feat/<run-name>` in `<plan-worktree>` (`git -C <plan-worktree> add docs/exec-plans/active/<run-name>/task-NN.md`, with its `task-NN.code.md` when it has one, and the pathspec commit above), then append `Task N: written — <sha>` to `<run-dir>/plan-log.md` (line 1 stays the
  STATUS line) and set line 1 of `<run-dir>/critique-response.md` to `STATUS: writing Task N+1`, because the watcher and the critic
  read these lines to see where you are. Write the index first (`Task 0: index written — <sha>` in `plan-log.md`), as its own unit, since the lanes and the task count are fixed from it.
- You write new tasks and answer the open ids of your own tasks (owner, 2026-10-30): after every `Task N: part <k>` or
  `Task N: written — <sha>` line, before the next part, run `python3 -I <skill-dir>/scripts/open_ids.py <run-dir>
  --kind C,A,B,V,R --cause plan` (with two planners add `--parity odd|even`, your lane's) and answer each id it prints
  that is filed under a task of yours: fix the task file (unbuilt tasks only; a built task's code is the truth: fix
  the later tasks it touches), append `<id>: applied|rejected|decided by rule — …` to `critique-response.md` with
  `printf … >>`, commit with a pathspec and message the asker. `<project>/plan-fixer` is launched by the watcher only
  when the open ids pass `demand.queue` or `demand.wait_minutes` of `_agents.json`; while it runs it answers the ids
  of its parity and you write on. Before each task, `grep -n '^[CABRV][0-9]*:' <run-dir>/critique-response.md` for
  answer lines added since your last task (the fixer's too) and carry their changes (shared names, contracts, rules
  in `lessons.md`) into the task you write, so that it builds on the answered shape. Commit only your own files, with a pathspec, so the fixer's edits and
  yours never mix: `git -C <plan-worktree> commit -m "docs(plan): Task N — <title>" --
  docs/exec-plans/active/<run-name>/task-NN.md docs/exec-plans/active/<run-name>/<run-name>.summary.md`, with
  `docs/exec-plans/active/<run-name>/task-NN.code.md` after the task file when the task has one.
- Verify every tool flag and library API you name (first-pass rule 1): `graphify --help`, `graphify export obsidian`
  and `export wiki` output on a scratch copy if a fact needs it (copy under `<run-dir>/scratch/planner/`, not under
  /tmp, which parallel sessions share), the harness CLI (`uv run harness --help` in `<plan-worktree>` after `uv sync`), `just --list`.
- Commit only on `feat/<run-name>`, and do not switch branches, merge, rebase, reset, stash or push: the main session
  merges, and the stash is shared with every worktree. Write no code: the plan is your only deliverable.
- When the last task file is written and committed: line 1 of `critique-response.md` = `STATUS: plan complete`. Then
  wait in the background with `python3 <run-dir>/wait_for_log.py <run-dir>/critique.md <lines> --first
  "STATUS: reviewed through Task <last>" --first "STATUS: done"` (its line count; the critic sets line 1 in place,
  which adds no line; again after each exit) until its line 1 says `STATUS: reviewed through Task <last>` or
  `STATUS: done`, answer what `open_ids.py` prints for your tasks as above, set line 1 of `critique-response.md` to
  `STATUS: done` and end; later B and `(plan)` or `(spec)` V ids are the plan fixer's, launched on demand.

## Rules every task keeps
A builder works from the task file alone, so a gap in a task stops the build; each rule gives its reason so that you can
apply it to the cases it does not name.
- A task calls only names its base has and quotes each signature by file:line; a name it creates is grepped in its
  module at the base first, and a module it calls exists before the task in its lane, because a call to a missing or
  doubled name stops the builder in the middle of a step (a project's run of 2026-11-02, C38, B1).
- A task makes every file, fixture and document it needs unless an earlier task of its own lane lists it, and its
  `files:` line and its index row name every file the build writes, tests included, because a builder works its lane
  in order and the critic checks the lanes for collisions from those lists (a project's run of 2026-11-02).
- A task that loosens a hold (a gate, a check or a limit) first quotes the rule that makes it, and the reversal of an
  earlier decision goes to the index's Deferred list, because a loosened hold hides the next error and a decision of the
  spec or the owner is not a task's to change (a project's run of 2026-11-02).
- A patch a task applies is named by its exact command from the worktree root, with an absolute path and every flag,
  because a builder who has to guess the folder or a flag applies the patch to the wrong place or not at all (a
  project's run of 2026-11-02).
- A file a task cites that is not on the run's branch is cited by its absolute path, because a relative path resolves
  in the builder's worktree, where the file does not exist (a project's run of 2026-11-02, C98, C99).
- A task that adds a step to a shared script, or changes a document, runs the repository's own checks for it (grep the
  tests for the script's name; the documentation and wiki checks), because the builder runs only the task's own tests
  and a break in another check would show first at a milestone (a project's run of 2026-11-02).
- A task that changes the output of a command a runbook's `Expected:` line names lists the runbook in its `files:` and
  changes that line, because a stale `Expected:` sends the next reader after a failure that is not one (a project's
  run of 2026-11-02).

## Reading budget (owner, 2026-10-29 20:0x UTC, "spare the budget"; measured 2026-10-29: four planner sessions reached the 200k cap after 42-69 reads with no task file written)
A session reads its note, this brief, the index's row and Coverage lines of its task, and then at most ten more ranges
before it starts writing the task file. A source is read by `grep -n` for the symbol and `sed -n` for at most 40 lines;
the spec section, the skill's `scripts/README.md`, an earlier run's lessons and any file over 200 lines are read by
their outline only (`grep -n '^## \|^### \|^def \|^class '`), never whole. Write the task file early, so that a compaction finds the work on disk: the first Write
holds the heading lines, the Contracts, the Interfaces and the step list; then one Edit per step with its test in full.

## Files you write
Only these, so the other roles' files stay theirs: `<plan-worktree>/docs/exec-plans/active/<run-name>/*` and its commits; `<run-dir>/plan-log.md`, `<run-dir>/critique-response.md`, `<run-dir>/lessons.md`
("Lessons from this run" only), `<run-dir>/handoff-planner.md`, your scratch folder.

## Done when
The index and every task file are committed, `<run-name>.summary.md` is current, every spec item is
met by a task or listed under "Deferred" in the index with its reason, every task is written and its open ids are answered,
`critique-response.md` line 1 says `STATUS: done`, and your last message gives a short report: tasks, milestones, what you
could not verify.

## Domain checklist and skills
Spec: .claude/ecc/agents/architect.md:26-53, .claude/ecc/agents/code-architect.md:19-43 — the design review questions a task's architecture answers (spec 4.7, the planner row)
Skills: .claude/skills/python-testing/SKILL.md (before the first test of a task is written)
<!-- launch: paste the Spec ranges here from the pinned copies, trimmed by .claude/ecc/sources.md K1-K5 and M; under 60 lines -->
