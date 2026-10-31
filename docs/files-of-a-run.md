# The files of a run

The record files of one run of the pipeline skill, written by the roles into the run folder (`<run>`, outside the
repository); [how it works, step by step](how-it-works.md) says when each is written.

Line 1 of each record is its `STATUS:` line, so `head -1 <run>/*.md` shows where the run stands.

| File | Written by | What a human reads there |
| --- | --- | --- |
| `_common.md`, `_<role>-assignment.md`, `_launch.md` | the manager, before the launch | the briefs, the launch table and your `Yes:` |
| `_control/usage.json` | the manager, before each launch | one usage reading per launch: `taken_at`, `source`, `extra_usage` and, per limit, `name`, `used_pct`, `resets_at`; an old reading is never edited |
| `spec-log.md` | the spec-writer, only when no spec exists | `Spec: written — <sha>`, line 1 `STATUS: done` |
| `plan-log.md` | the planner | each task written, and with lanes, who took it |
| `critique.md`, `critique-response.md` | the critic; the planner or the plan fixer | C and A findings, each answered below it |
| `build-log.md` (`-a`, `-b`) | each builder | `Task N: done — <sha>`, test counts, `B<n>` lines, `V<n>: fixed` |
| `build-summary-a.md`, `build-summary-b.md` | each builder, after its last task | what was built, what was deferred, what you must do once |
| `verify.md` | the verifier | V findings with their repro and checklist line |
| `verify-summary.md` | the verifier, when every task is verified and the last milestone passed | what passed, what was found, what remains |
| `handoff-<role>.md` | each session at its unit's end | the facts the next session starts from |
| `lessons.md` | the manager and the roles | rules from shared causes, the merge lines |
| `judge.md` | the judge | the verdict on line 2 |
| `_watch.log` | the watcher | launches, hand-overs and revivals |
| `_control/monitor.log` | the records monitor | a line per event with its UTC time: `armed`, `WAKE <event>`, `woke: <n>`, `answered <id>`, `written Task N`, `done Task N`, `ticked D<n>`, `expired` |

Outside the run folder: each role writes a short English summary for you, a `<name>.summary.md` beside each page you
read ([the skill](../.claude/skills/running-specagent-pipelines/SKILL.md),
[documentation](architecture/documentation.md)). Before Claude Code compacts the manager's conversation, or yours, a
hook asks for a note in `docs/handoff/` beside the checkout (the container's) and reads it back after
([ADR-0007](decisions/0007-a-conversation-hands-itself-off-before-compaction.md)); no role session reads that folder.
