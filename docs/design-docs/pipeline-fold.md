# Pipeline fold: fewer hand-overs in the SpecAgent pipeline

Status: adopted on main without the measurement run (owner, 2026-10-30 15:4x UTC); the Measurement section is the recipe for a later run.
Owner: the template owner. Written 2026-10-30 from the owner's decisions of 2026-10-30 04:0x-04:5x UTC
(vault `context/owner-statements/2026-10-29.md`) after reading claude.com's "Building agents: when to fold subagents
into your main agent loop". Scope: the skill `running-specagent-pipelines` (its example briefs, waiters, watcher,
format checks, manager scripts) and the plan form of `docs/exec-plans/active/`.

## Intent

Each role runs as its own `claude --bg` session, with files as the record. That stays: the owner keeps SpecAgent sessions
over subagents and over one loop, because the article's three conditions for separate agents are measured here (the
200k cap, parallel lanes, the critic and the verifier as independent eyes). What costs more than it returns is the
number of hand-overs: each spends a hand-off note on one side and a start-up (32-33k tokens) plus the re-reading of
the same files on the other. Measured in the manager-build run of 2026-10-29:

- the plan fixer restarted at 01:51, 02:28, 03:05, 03:28, 03:31 with one finding to answer in that span;
- every built commit was read by two sessions, the critic (R findings, 8 over Tasks 1-10) and the verifier (V findings,
  7, two of which the critic had missed);
- task files are 53-118 KB (13-30k tokens) and 61% of their lines sit in code fences (tests in full, texts in full,
  pasted blocks); a critic session once made 85 reads and reached the cap with no section written;
- plan findings per task fell from 3-5 (Tasks 1-9) to 1 (Tasks 10, 11) as `lessons.md` filled: the queue the fixer
  was made for no longer forms in a mature run.

The article's order is kept: measure first, fold one pair at a time, compare, keep what wins.

## Goals

1. Fewer sessions per task with the same checks: no file is read by two sessions when one already holds it.
2. Cost per task down, measured by the same script before and after; quality not down: the verifier and the judge find
   no more than now, and no task is rebuilt.
3. Every role receives exactly what its unit needs and nothing more (owner, 04:5x: delivered exactly, with nothing
   extra), with the choice written in the brief and checked by a script.

## Non-goals

- Moving to subagents, to a single agent loop, or to subagents called as tools (owner, 04:0x).
- Removing the critic, the verifier or the judge. The independent eye on the plan and on the code stays.
- Planner and builder in one session: a task file plus its build exceeds the cap.
- Any change to the sandbox, the blindness rules or the owner rules of the skill.
- A literal empty start-up: the harness prompt and the two CLAUDE.md files load before any brief, with no switch.

## Anti-goals (a failure even if it works)

- A lesson class returns because a role no longer received the rule that guarded it.
- The critic's attack tests (A) disappear with its diff review.
- The planner stalls answering findings while builders wait, which is what the fixer was made to prevent.
- The verifier's independence is weakened (it keeps its own clean worktree and runs every command itself).

## Constraints

- The owner's rules of the skill hold: ask before any launch; Opus max for judgment roles; the 200k cap and one unit
  per session; hand-off notes carry facts; nothing waits for the owner; proof for every finding; at most three rounds.
- English only in the template (`harness validate` refuses letters of the refused blocks since 1.5.0).
- The main session makes these changes on `main` directly after D9 (the merge of `feat/manager-build`) and D10 (cost
  regulation and surface pruning); no new template run is launched for building them (owner, 01:4x).
- Every change is measured before and after with the same script on the same records. The one run launched for this
  work is a measurement: golden Task 10 rebuilt with the folded pipeline (see Measurement).
- DrakenWar is not the measurement run (owner, 04:3x).

## Decided

### 1. One score per run, by script

`scripts/manager/score_run.py <run-dir>` prints one line and one table from the run folder's records and
`usage_report.py --prefix <run>/`:

- findings per task by letter: C, A (plan), V (code, by `(code)`/`(plan)`), B (builder's plan findings); which were
  rejected; how many the critic missed (a `(plan)` V on a reviewed task);
- per role: sessions started, cap hand-overs, idle restarts (a hand-off note followed by a fresh session that wrote no
  unit line before its own hand-off), first-call tokens;
- cost per task (sessions attributed to the task by the unit lines they wrote) and total;
- request lines (`CHECKOUT-REQUEST`, `COPY-REQUEST`, `FF-REQUEST`, `SANDBOX:`) with minutes to their answer;
- lesson classes repeated (a finding whose `Checklist:` item already had a lesson).

It reuses `usage_report.py`, `measure_manager.py` and `findings_report.py`. Its first run, on
`manager-build-2026-10-29`, is the baseline every later run is compared with; the vault's measurement page quotes it.

### 2. The planner answers its own findings; the fixer is launched on demand

The planner's brief gains a second phase: after every `Task N: part <k>` or `Task N: written — <sha>` line, before
the next part, it answers every open C, A, B and `(plan)` V id of its own tasks in `critique-response.md` and edits the
unbuilt task file, under the same rules the fixer had (the code of a built task is the truth). A part is the
checkpoint because a task is written in parts over hours (Task 11: twelve parts, 01:5x-03:1x); answering only at a
task's end would leave findings open for hours and defeat the fold (my call). The lanes stay.

The fixer role stays defined (`example/plan-fixer-assignment.md`) but is not launched at the start. The watcher gets two
config fields, `fixer_queue` (default 6 open ids across the lanes of one parity) and `fixer_wait_minutes` (default 45,
the oldest open id's age; longer than one part takes to write, so a planner between parts is not pre-empted); when
either is passed it launches the fixer with the same brief and stops it when the queue is empty. A new project, whose `lessons.md` is thin, will see the fixer early; a mature one will not see it at all.

### 3. The critic reviews the plan only; the verifier reads the code

The critic's brief keeps the coverage round (C and A ids, one per task, before the build) and loses the diff review.
The verifier's brief gains what the diff review did that the verifier did not: reading the diff by file against the
task's steps and the spec, and the `(plan)` tag that sends a finding to the planner when a later task would repeat the
mistake or a contract changes. One id series, V, with its `(code)`, `(plan)` or `(spec)` cause; R ids are retired
(`check_formats.py` stops expecting them; old runs still parse). The critic never opens a checkout's code. One critic
by default (my call, same date): its work halves, and the second one of 2026-10-29 was added for the diff reviews;
`agents.json` keeps the odd/even parity as an option for a run whose planner lanes outpace one critic.

### 4. The plan file is split: steps in one file, blocks in another

`task-NN.md` keeps the goal, departures, contracts, interfaces, the steps with their `Expected:` lines, the deferred
list and the verified list. `task-NN.code.md` holds every fenced block longer than 10 lines under a heading
`## Block <id>` (`1a`, `3b`, …), and a step names its block (`Block 3b`) instead of pasting it. Tests stay written in
full by the planner (the owner's rule: the builder cannot bend a test to its code, and the critic attacks the test
before any code exists). Texts (changelog entries, decision pages, documentation prose) change hands: the planner
gives the list of facts the text must state and the test that pins them; the builder writes the prose (my call, the
owner left it to me 2026-10-30 05:0x: the test, not the author, holds the quality, and 600 lines stop being read
twice).

Reading rules follow: the critic reads `task-NN.md` whole and, from the code file, every test block in full and other
blocks only when a finding needs them; the builder and the verifier open a block when the step names it.
`harness plan-lint` learns the second file (it belongs to the task, counts against no line limit of its own, and a
block a step names must exist). The expected size: the steps file about 40% of today's task file.

### 5. No fresh session after a finished role's hand-off

The watcher starts a fresh session on a hand-off note only when the role has a unit to take: its STATUS line is not
`done`, or a new unit line (a `Task N:` line it waits for, an open id of its parity, a request line) appeared after the
note. Otherwise it logs `idle: <role> handed over with nothing to take` and waits. What counts as a unit line for a role
is a per-role pattern in `agents.json` (`unit_lines`), next to the waiter the role runs, so the watcher reads the same
signal the role does. This removes the idle restarts of item 1's measurement at no cost to throughput.

### 6. A role loads what its brief names, nothing else

Prerequisite in D10, stated here because items 2-4 depend on it: the project `CLAUDE.md` holds rules only (a map, a
few lines), agent and skill descriptions are at most 150 bytes, and the brief's `Spec:` and `Skills:` lines (Task 1 of
the manager-build run) are the only place a role's start-up is chosen; `catalogue.py` checks the prefix against the
10k and 13k bounds before every launch. One measurement belongs to D10, not here: whether a role started with the run
folder as its cwd and the checkout under `--add-dir` still loads the checkout's `CLAUDE.md`.

The prompt cache is part of the same rule. A role's start-up prefix (harness prompt, brief, the files the brief names,
in that order) is byte-identical across its sessions and is read before anything that varies, so every call after the
first reads it from the cache (cache read costs a tenth of input); a hand-off note or a record file is read after it,
never before. `score_run.py` reports cache-read against input tokens per role from `usage_report.py`'s columns, so a
brief that breaks the prefix (a date, a session id, a changing path at its top) shows up as a fall in that ratio.

## Measurement

1. `score_run.py` on `manager-build-2026-10-29`: the baseline line.
2. Golden Task 10 of that run (the smallest: the scripts README split and the price table; 1 plan finding, 1 diff
   finding, 995 lines) is rebuilt with the folded pipeline on a scratch branch from its base commit, with `lessons.md`
   and the vault on as in the original run, one planner, one critic, one builder, one verifier; the judge is not
   launched. The run is launched with the owner's yes, as every launch is. `score_run.py` on that run, compared with Task 10's slice of the baseline: cost, sessions, findings,
   anything the verifier found that the original run's critic had found as R.
3. If quality held (no new V the original run did not have, no rebuild), the fold is kept and the next real run uses
   it. If not, the pair that lost is unfolded, one at a time, and measured again.
4. Cancelled (owner, 2026-11-01): no plain one-agent session. A project measured one agent playing every role in turn
   against the multi-role pipeline on 2026-11-01: a quarter cheaper per task, 2.5 times slower, and its own critique
   found 2.3 plan defects per task against 5-8 by a separate critic. The template offers no one-agent mode.

## Order

After D9 and D10. Within this work: item 1 first (it measures everything else), then 5 (cheapest, no brief changes),
then 4, then 2 and 3 together (they change the same briefs and waiters), then Measurement 2-3.

## Left to the builder

- Exact wording of the brief changes; the names of the two watcher fields and their place in `agents.json`'s schema;
  the block heading form in `task-NN.code.md` and how `plan-lint` reports a missing block.
- How `score_run.py` attributes a session's cost when it wrote unit lines for two tasks (one documented rule, applied
  to the baseline and the measured run alike).
- Test names; the pages under `scripts/docs/`; one decision page per item under `wiki/decisions/`; whether the
  fixer's on-demand launch reuses the watcher's fresh-session path.
