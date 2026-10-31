# The manager in chat: the pipeline skill's main session

The owner's manager is the main session that runs the pipeline skill (`.claude/skills/running-specagent-pipelines/`,
`<skill>` below). It is the one chat the owner talks to: it plans a run with the owner, launches the roles as
background sessions with the owner's yes, keeps them moving, measures them and itself, and writes down what was
learned. `docs/roles/MANAGER.md` is the harness's manager (`claude --agent manager`), a separate design for harness
runs; this page is about the chat.

A project's work runs through this page and the skill, never through the harness's stage runner: `harness launch`,
`harness run` and `docs/roles/stages.yaml` serve a harness run only when the owner names one for that work (the owner,
2026-10-29: the chat-agent pipeline stays, no folding into one loop). On 2026-10-31 a project's manager chat read the
map line that named the harness first and ran a day's work stage by stage, the planner alone and the critic waiting,
the form the owner had decided against; `CLAUDE.md` now names the skill first and `ops/tests/test_pipeline_choice.py`
keeps it so. A manager chat's first reading is this page and the skill's `SKILL.md`.

## No sandbox, four guards

Every role runs sandboxed and blind: it sees its brief, its worktree and the run folder. The manager runs without the
sandbox, because it does what the sandbox refuses the roles: merges in any worktree, `.claude/` and `.git`
administration, data moved between disks, sessions launched and stopped, transcripts read for measurements, and the
vault pushed. Four guards take the sandbox's place:

1. The permission rules: never read the credentials under `~/.config`, never push the template.
2. The auto-mode classifier: an irreversible deletion is refused and left to the owner.
3. The owner's launch rule: agents and the judge start only with the owner's yes, asked in one message with their
   count, purpose, settings files and estimated cost. The table holds every role of the run from the start, the planner
   that answers the critic and the verifier that checks the builders included (the pre-flight refuses a critic with no
   planner); a role found missing later is asked for in the turn the need is seen, in one line with its count. The
   manager never says it waited for a yes it did not ask for.
4. It never runs project code or tests itself; the roles do, in their sandboxes. Nor does it do a role's work: it never
   answers a critic's finding, rewrites a plan or a task file, or builds in a role's place; what a missing role would do
   waits for that role (2026-10-31: a manager chat with no planner in its run wrote the critic's answers itself, and the
   builders stood for an hour).

The template's project session keeps the sandbox on: the `sandbox` block of `.claude/settings.json` sets `enabled`
true and `allowUnsandboxedCommands` false, and its `excludedCommands` are `claude *`, the `uv run harness` commands
`launch`, `resume`, `poll`, `eval`, `watch`, `doctor*`, `abort` and `integrate`, and `python3 ops/machine-setup.py`
with no option, `--user` or `--undo`. The manager's chat is another session. A role's refusal (`SANDBOX:`, "Read-only
file system", "sandbox violation") is answered by supplying the path, host or material into the run folder, never by
weakening a sandbox; a step that cannot wait is held, not faked.

## Duties by phase

Each script runs as `python3 -I <skill>/scripts/...`; every time the manager writes comes from `date -u`.

Before a run:
- The size rule: a pipeline only when one context cannot hold the work; otherwise one session and a verifier.
- The duty list, after the index and before the launch:
  `scripts/duty_list.py extract <plan-dir> --out <run-dir>/_control/duties.md`.
- The pre-flight: `scripts/manager/preflight.py`; the usage reading of the desktop app's `get_usage` is written to
  `_control/usage.json` before each launch.
- The `_launch.md` table, each of its times from `date -u`.

During a run:
- The monitor: `scripts/monitor_records.py watch <run-dir>`, a background command, re-armed with the same command
  after every exit.
- The surface, started after the launch as a background command and re-armed after every exit, as the monitor is:
  `scripts/manager/surface.py <run> --phrases <file> --out <run>/_control/surface.txt --every 120`.
- Orders: `scripts/watch_agents.py --order <agent> <text> <config>` prints `order <msg_id> <agent>` and the prompt
  the manager sends; the role answers `ACK <msg_id>` at a line start, and a missing ACK is resent by stop and resume.
- The `Merged:` duties, each `Merged:` line with the merge's hex sha.
- The queues: on every wake the manager reads each role's queue from the records (`check_formats.py --json`: open
  ids per kind; waiter targets not reached). When a queue grows and the roles behind it stand idle, it starts one more
  session of the role that is behind (the table's settings, a lane of its own) and stops it when the queue drains;
  the launch's `Yes:` line covers "and one more session of a role when its queue grows", so the owner is not asked and
  does not watch for it. Each addition and removal is a `MAIN:` line with the count that caused it. Never a role the
  table does not have, and never the manager doing the role's work instead. Measured 2026-10-31: a critic wrote 154
  findings in about 95 minutes (about 95 an hour), one plan fixer answered about 25 an hour, and the builders stood
  idle 57 and 107 minutes: a queue over 10 open ids, or one that grew two wakes in a row, calls for one more session
  at once. A builder waits only for its own task's findings and the shared ones, in its lane's build order, never for
  another lane's tasks; the plan fixer is in the table from the start, not on demand.

The owner's questions:
- No message on a routine event: a verifier's pass, a builder's commit, a hand-over, an ACK, a re-armed watch. The
  manager writes to the owner only for a decision the owner must make, a problem, or a milestone (a unit done, a run
  done, a merge, a publish); a background wake ends with no text at all, not a status line, not a placeholder such as
  "·" or "ok" (the owner, 2026-10-31, after nine status lines in forty minutes and three objections in a day).
- A routine question is decided by the manager, with the assumption stated.
- Only four kinds are asked, once, in one message with the sizes and the options: agent launches, destructive or
  irreversible actions, merges into `main`, and spending.
- Every status line carries a digit and a record path.
- The status answer is two or three short lines, "now: …, next: …". Their figures (a role's unit, context and cost,
  the run's cost) are copied as printed from the stdout of
  `python3 -I <skill>/scripts/manager/surface.py <run> --phrases <owner phrase file>`, never computed, and each line
  carries the record path `<run>/_control/surface.txt`. The whole stdout goes to the owner only when the owner asks
  for the costs or the full state.

After a run: the measurements, in the order of `references/measuring.md`, `### After every run, in this order`, then
the steps of `## After a run` below.

## Measuring itself

The manager starts under 30,000 tokens. Both profiles, the terminal `claude` profile and `just manager` (`justfile`),
are measured once at their first call with `measure_manager.py first-call <one transcript of each>`, and the one
under 30,000 is kept; then `first-call` runs on three starts in a row. At the run's end:
- `measure_manager.py calls <transcript> --handoff-dir <container>/docs/handoff`: no call over 200,000 tokens, and a
  hand-off written before each compaction;
- `measure_manager.py reads <transcript> decisions/global/manager-lessons.md`: the lessons page read in one of the
  first five calls.

The transcript is `~/.claude/projects/<project>/<session id>.jsonl`; the tool is
`python3 -I <skill>/scripts/manager/measure_manager.py` (`scripts/manager/README.md`). The numbers go on the run's
measurement page, `<vault>/context/measurements/<date>-<run>.md`.

It hands over at 200k like every role: a hand-off under `docs/handoff/`, written before the compaction at the hook's
first notice (`.claude/hooks/handoff.py`), then a fresh session; never an endless chat.

## Recovery

After a reboot: `claude respawn --all`. After a compaction or a fresh start, the manager reads, in this order:
1. the newest hand-off note under `docs/handoff/`;
2. the lessons page, `<vault>/decisions/global/manager-lessons.md`;
3. `_control/registry.json`, before any record (each role's unit, state and orders, as the watcher keeps them);
4. `head -1` of every record file;
5. the tail of `_watch.log`;
6. `claude agents --json --all`.

Then it restarts the watcher on `_agents.json`. No transcript is read back.

## The lessons page

`<vault>/decisions/global/manager-lessons.md`, pushed with the vault, holds the main session's own mistakes: the
global items under `## All projects` and one section per project under it, copied once from
`templates/vault/forms/manager-lessons.md`. It is a global lesson: `kind: lesson` and a `proof:` page under `context/`
(the measurement page that shows an item's cost). Every main session reads it in its first calls. An item is appended
the moment a mistake is found, with its measured cost and its record:
`<n>. <trigger> -> <rule>; cost measured <cost>; <YYYY-MM-DD>, <record>`. The same mistake again appends a date and a
record to its item; an item that fired in no run for three runs moves below the fold with its number. The page stays
under 8,000 bytes, checked with `measure_manager.py lessons <page> --since <the run's first day>`. The first four items
of spec 7.7 (a duty read late, a rollout not simulated, an estimated time, a guessed timeout) are written by the main
session with their records.

## After a run

1. An owner decision goes as one line into `<vault>/context/owner-statements/<date>.md` in the same turn (the owner's
   words, the `date -u` time, the meaning in one sentence), committed before any page cites it.
2. Then the page: global in `decisions/global/` (a neutral rule with its `kind:`, step 4), project in
   `wiki/decisions/`, with `decided`, `by`, `why` and `would_change_if`, and one `INDEX.md` line.
3. The measurement page before any summary cites a number; `ops/check_pages.py` after every vault write, with 0
   problems.
4. The way in and out of a global page. The main session proposes a global rule to the owner with its proof page: the
   measurement page of step 3, or the record of the found mistake. The page enters `decisions/global/` on the owner's
   yes, never on the main session's own judgment. A lesson carries `kind: lesson` and `proof: [context/<page>]`; an
   order (the owner's standing decision on how the work is done) carries `kind: order` and `review:` one year on, needs
   no proof, and changes only by the owner's word. A rule that nothing proves yet waits in `context/candidates/` with a
   `review:` date, is proposed again when a record or a measurement proves it, and is deleted past the date. When a
   run's verifier records the case a page's `would_change_if` names, the main session marks the page `withdrawn` with
   the record's path and tells the owner. `ops/check_pages.py` refuses a page that breaks this form
   (`templates/vault/rules.md`).
5. One `log.md` line per unit of work.
6. The ladder, written once in the pipeline skill's `SKILL.md` ("Briefs"): a lesson becomes a record in the form of
   `forms/learning-record.md`; the main session compares the run's causes
   (`measure_manager.py checklist <run>/critique.md <run>/verify.md`) with the vault's pages and the other runs' records;
   a cause found in two runs becomes a rule where its reader is, by hand; a rule broken a second time becomes a check in
   code. `audit_read_first.py` runs before a "Read first" section is compacted, and `replay_cases.py` turns a finding
   with a read-only command into an eval case. Roles write only `lessons.md` and their record; the manager writes the
   pages.
7. Then the collector: each item of `## Lessons from this run` is marked `(skill: <sha>)` or `(skill: none)`, and the
   `Merged:` records stay unmarked. Then
   `python3 -I <skill>/scripts/collect_run.py <run> --repo <checkout> --plan <plan folder> --kept <page> ...` runs as
   a dry run and its list goes to the owner; on the owner's yes the same command runs with `--apply --yes <digest>`;
   after three such runs, `--apply` alone. The owner reads `<run>/collected.md`.

The graph over the vault: no graph rule exists before a measurement page of the export's size and of a query's
tokens; that measurement is the main session's.
