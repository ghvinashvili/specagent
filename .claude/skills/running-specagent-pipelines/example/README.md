# Example run folder

The briefs, settings and configs of a run with a planner, a plan fixer, a critic, two builders, a verifier and a
judge, in the generic form a new run starts from (`../SKILL.md` says how the pipeline runs).

## Starting a run
1. Make the run folder outside the repository and copy each file into it with a leading `_` (`common.md` becomes
   `_common.md`, `launch.md` becomes `_launch.md`), except `lessons.md`, which keeps its name because the agents
   add to it, and the configs and settings files, which go to `<run-dir>/_control/` (`agents.json` becomes
   `_control/_agents.json`, `agents-judge.json` becomes `_control/_agents-judge.json`, `planner-settings.json`
   becomes `_control/planner-settings.json`), each agent's `settings` naming its file as
   `_control/<role>-settings.json`: the roles' `Read(/<run-dir>/_control/**)` deny keeps them out of reach, and the
   pre-flight reads them there. This README stays here.
2. Copy the waiters in: `<skill-dir>/scripts/wait_for_*.py` into `<run-dir>/`.
3. Fill in the placeholders below in every file, and the run's own text (what it builds, its sources, its lanes).
4. Fill `_launch.md`: the key lines and one table row per role. Start the request-line monitor in the background
   (`python3 -I <skill-dir>/scripts/monitor_records.py watch <run-dir>`), append the usage reading to
   `_control/usage.json` and run the pre-flight:
   `python3 -I <skill-dir>/scripts/manager/preflight.py check <run-dir> --checkout <checkout>`. Send the owner the
   table in one message, with the models; append the answer as a `Yes:` line and run the pre-flight again with
   `--yes` (`references/preflight-and-capacity.md`).
5. After one round of `--check`, start the watcher in the background from the main session:
   `python3 -I <skill-dir>/scripts/watch_agents.py <run-dir>/_control/_agents.json 2>&1 | tee -a
   <run-dir>/_watch.log` (`score_run.py` reads that log). The judge comes once, at the
   end, with the owner's approval: `bash <skill-dir>/scripts/judge_after_verify.sh
   <run-dir>/_control/_agents-judge.json <checkout> <record-file>...`.

A run with one builder deletes `builder-b-*` and renames `builder-a` to `builder` (in the file names, in
`agents.json`, `packs.json` and the briefs). `{run}` in the configs' texts is no placeholder: the watcher fills it in,
and `{skill}` too, with the folder of `watch_agents.py` (the critic's and the plan fixer's `work_check` in
`agents.json` run `wait_for_task.py --once` and `open_ids.py` from it; a role without one launches after every note).

The plan fixer's entry also has `"on_demand": true` and a `demand` object: the watcher launches it only when its open
ids reach `demand.queue` (default 6) or the oldest is `demand.wait_minutes` (default 45) old, and stops it when none
is open.

## Files
- `common.md`: the brief every role reads first (language, places, owner decisions, proof rule, messages, waiting,
  shell commands, context).
- `first-pass-rules.md`: facts from installed code and official pages, the check against the error classes, the
  lessons loop, read late and narrow.
- `handoff-rule.md`: one unit of work per session, the cap, and the hand-over note's shape.
- `lessons.md`: "Read first", the known error classes, and an empty "Lessons from this run" that the agents fill.
- `sim_bwrap.py`: builds a bwrap in the order Claude Code mounts a role's sandbox and runs a probe in it, so a settings
  file is checked before the rollout (`python3 example/sim_bwrap.py <run-dir>/_control/_agents.json <agent> '<probe>'`).
- `planner-assignment.md`: the planner, who writes new tasks and answers the open ids of its own tasks after each
  part (optional lanes).
- `plan-fixer-assignment.md`: the plan fixer, launched by the watcher on demand when the open ids pass a count or an
  age.
- `critic-assignment.md`: the critic: one coverage round per task (C and A ids); it reads no code.
- `builder-a-assignment.md`: builder A, the index rows with `builder: a`.
- `builder-b-assignment.md`: builder B, the index rows with `builder: b`.
- `verifier-assignment.md`: the verifier, who reads each built commit's diff by file and re-runs its checks in its own
  worktree (V ids with their cause).
- `judge-assignment.md`: the judge, once, after every task is verified.
- `planner-settings.json`: the planner's `--settings` (permissions, the sandbox, the empty compaction override).
- `plan-fixer-settings.json`: the plan fixer's `--settings`.
- `critic-settings.json`: the critic's `--settings` (read-only commands).
- `builder-a-settings.json`: builder A's `--settings` (its own worktree only).
- `builder-b-settings.json`: builder B's `--settings` (its own worktree only).
- `verifier-settings.json`: the verifier's `--settings` (no commit).
- `judge-settings.json`: the judge's `--settings` (no message, no commit).
- Every role but one that edits a checkout served by a local dev server or containers (`references/launch.md`) runs
  in the sandbox (`failIfUnavailable`, no unsandboxed retry). Its settings deny the transcripts, the
  run's `_control/`, the checkout's `docs/handoff/`, the credentials file `~/.claude/.credentials.json`, `/proc`, `ps`,
  `pgrep` and `claude agents|logs|attach`, and `filesystem.denyRead` hides the same paths, the credentials file
  included, from its shell, so no role learns which model another runs on or reads the owner's login. The
  sandbox mounts each `Edit` or `Write` deny read-only over the paths a role writes, so no deny names an ancestor of
  one: a role that commits or checks out denies `<checkout>` entry by entry and writes `<checkout>/.git` but its
  `hooks/` and `config`.
- Every role's settings run the checkout's guards under `hooks.PreToolUse` (D10): `guard-read.py` on `Read` refuses a
  whole read of a file over 20,000 bytes (`grep -n` first, then `offset` and `limit`), and `guard-records.py` on
  `Write|Edit` refuses a call that removes or rewrites a line of a run's record (`build-log*.md`, `verify.md`, …):
  line 1, the STATUS line, may change, and line 2 of `judge.md` (`VERDICT:`) and of `critique.md` (`Reviewed:`).
- Every role's settings carry `"includeCoAuthoredBy": false`: no commit ends with a `Co-Authored-By` trailer that names
  the model, and the pre-flight's `blind` check fails a file without it (`references/sandbox-and-blindness.md`).
- Every role's settings carry `CLAUDE_CODE_PROMPT_CACHE_TTL` under `env`: `5m` for the planner and the builders, which
  wait on no other role, `1h` for the plan fixer, critic, verifier and judge, which do (`references/launch.md`).
- `agents.json`: the watcher's config for the six roles (config v2; fields in `../scripts/README.md`).
- `agents-judge.json`: the judge's config, with its one agent, for `judge_after_verify.sh`.
- `packs.json`: the roles' startup packs for `make_pack.py` (packs are off since 2026-10-25; it builds them to
  measure again; `--no-note` leaves a hand-over note out, as it is unique to one session).
- `launch.md`: the launch table the manager fills before every launch, with the owner's `Yes:` lines
  (`_launch.md` in the run folder; `references/preflight-and-capacity.md`).
- `surface-phrases.en.json`: the English phrases of the owner's surface, `../scripts/manager/surface.py` (answer 11a):
  one string per key, each `{field}` filled from the control files. The owner's own file keeps every key and every
  field, lives outside the template and is passed with `--phrases`; `surface.py --check-phrases FILE` checks it.

## Placeholders
Each stands for an absolute path or a name; a path under the home folder that is no placeholder is written with `~`
(`~/.claude/jobs`, `~/.config/`).
- `<run-dir>`: the run folder.
- `<model>`: the model id the manager sets in a role's settings file (specification, judgment or mechanical class); no
  brief, flag or text of the skill names one.
- `<run-name>`: the run's short name (the `feat/<run-name>` branches, the plan's folder).
- `<project>`: the session-name prefix, as in `<project>/planner`.
- `<checkout>`: the main checkout, read-only.
- `<checkout-entry>`: each top-level folder of `<checkout>` but `.git` (`ls -A -p <checkout> | grep /`); a `/**` rule that
  holds it is written once per folder.
- `<checkout-file>`: each top-level file of `<checkout>` (`ls -A -p <checkout> | grep -v /`); a bare rule once per file, because
  a `/**` rule never matches the file itself (gitignore matching).
- `<plan-worktree>`: the worktree the plan is written in.
- `<worktree-a>`: builder A's worktree.
- `<worktree-b>`: builder B's worktree.
- `<verify-worktree>`: the verifier's detached worktree.
- `<judge-worktree>`: the judge's detached worktree (`judge_after_verify.sh` adds it).
- `<spec>`: the spec file, a one-page skeleton; the planner puts the flesh on it.
- `<sources>`: the read-only source folders.
- `<vault>`: the owner's notes, read-only.
- `<skill-dir>`: this skill in the checkout.
- `<role>`: stays as it is, where a session writes its own role.
