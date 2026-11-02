# Watcher, monitor and collector
The main session's long-running and end-of-run tools besides the waiters. Each script's usage, options and files are
on its page under `scripts/docs/`, indexed in `scripts/README.md`.

### The watcher, `scripts/watch_agents.py` (version 3)
- Each round: a fresh session when a hand-over note appears, if the note's mtime lies within its session's transcript
  plus five minutes; builder and verifier switched at the config's `milestones`; a permission prompt cancelled after
  `permission_wait`; a stopped agent continued with a nudge, at most `nudges` times (6).
- Hand-over: at a unit's end (a new line 1 in the agent's record) once its last call passes `handoff_at` (250000),
  never in the middle of a unit; past the `cap` (260000) at once. Both are a backstop: a session compacts itself first
  (`--autocompact 235000` in `common`, `references/launch.md`).
- Orders: the watcher's (`handoff`, `unit-end`, `reload`) and the manager's (`--order <agent> <text>`) reach a session
  by a stop and a resume whose prompt ends with ``Order <msg_id>: append the line `ACK <msg_id>` to <record> before
  anything else.``; without that line the order is resent after `ack_wait` seconds, at most `ack_resends` times, and
  then the watcher returns.
- Registry: `_control/registry.json`, written whole at the end of every round: per agent its lane, settings, record,
  unit, state, session ids, context, calls, cost, revivals and open orders. A restarted watcher reads it and keeps the
  orders, the revivals and the session ids.
- Returns: exit 0 on an event (an agent failed or blocked, two live copies of one agent, an order with no ACK line
  after its resends, every STATUS final); exit 3 when a session passes its `budget` (the session is not stopped:
  decide, then restart the watcher); exit 4 when a settings file or the extra prompt file changed or a brief was
  removed. A changed brief is reloaded with a `reload` order, a changed config at the next round (an invalid one is
  kept out, with a log line).
- Give the planner the builder's final status, so it stays revivable while the builder may still report wrong steps.
  A pipeline that runs an older copy of the watcher moves at its next restart: `scripts/migrate_agents_json.py
  <run-dir>` writes its `_agents-v2.json`.

### Adding a role mid-run
The watcher launches a fresh session only for an agent it already has a session for, so a role added after the launch
gets its first session from `--launch` (a project's run of 2026-11-02 added a visual auditor at 04:28 UTC, launched it
by hand, and the watcher adopted it by name afterwards). In this order, each step because the next one reads it:
1. Its entry in `agents.json` (`cwd`, `add_dirs`, `settings`, `status`, `final`, its own `extra_prompt` pack, which the
   launch requires because the first prompt points at it) and a `fresh.<role>` text for its later hand-overs (the config
   refuses a role without one). A first session does not get that text, because it says a previous session handed over.
   The running watcher reloads the config at its next round (`config reloaded`) and keeps the run's state.
2. Its settings file and its pack, built by `scripts/make_pack.py --no-note <run-dir>/_packs.json <role>`: the launch
   refuses a missing file, so a session never starts without its pack.
3. Its row in the table of `_launch.md` and, once the owner has said yes to that role, its `Yes:` line (the pre-flight,
   `--launch` and the watcher's by-name match read them; `--launch` refuses an agent no `Yes:` line names, since the
   owner is asked before every launch); `preflight.py check <run-dir> --checkout <checkout> --roles <agent> --yes` passes
   (without `--yes` the pre-flight skips the `Yes:` check).
4. `python3 -I scripts/watch_agents.py --launch <agent> --dry-run <config>` shows the command; the same without
   `--dry-run` launches it with the argv of a fresh session and the first prompt of `launch.md`, and records the job id
   in the registry: a watcher started afterwards finds the session by that id, the running one adopts it by name at its
   next round. It refuses an agent that already has a session, since a second one is a copy.

### The duty list and the record monitor
- `scripts/duty_list.py extract <plan-dir> --out <run-dir>/_control/duties.md`, after the index and before the launch:
  every merge the task table implies, every marker the prose names, every `Request point:` line of a task file and
  the judge's approval, each with the task it blocks; `tick` marks one duty done with its time and evidence.
- `scripts/monitor_records.py watch <run-dir>`, the manager's background command: it exits 0 with one `WAKE` line
  per new event (a `SANDBOX:`, `COPY-REQUEST:`, `CHECKOUT-REQUEST:` or `FF-REQUEST:` line, a request open past the
  bound, a second or stalled claim, a due duty, a `VERDICT:` line, a failed merge check) and exits 1 after `--hours`.
  It answers no request: `answer` writes the answer line into the requester's file; re-arm it with the same command.

### The collector
- `scripts/collect_run.py RUN_DIR --repo DIR --plan PATH --kept PATH`, after the run, never by a role: a dry run lists
  what goes and what each deletion loses, and refuses while the record is not saved (final record lines, each lesson
  marked, the done commits in the main branch, every Deferred item of the plan a tracker row). `--apply --yes
  <digest>` removes on the owner's yes for that list; after three runs applied with a yes, `--apply` alone.
