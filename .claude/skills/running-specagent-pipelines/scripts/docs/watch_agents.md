# `watch_agents.py` — the watcher, version 3
One watcher for every pipeline: the union of three earlier runs' copies of 2026-10-26 and the milestones of an
earlier project's copy, its behaviour read from the config (Config v2 in [the README](../README.md)) instead of the code. Run it in the background from the main session; it logs one line per action to stdout, the UTC minute first (`2026-10-29T20:41Z`).
```
python3 -I scripts/watch_agents.py <config> [rounds]    one round every `interval` s; default 240 rounds (8 hours)
python3 -I scripts/watch_agents.py --check <config>     one round as a fresh start sees it; prints, launches nothing
python3 -I scripts/watch_agents.py --order <agent> <text> <config>   appends an order to the inbox; runs nothing
```
Each round, for every agent whose STATUS line (line 1 of its `status` file) does not start with its `final`:
- budget: a session past `budget` calls or output tokens (one call per message id, no `<synthetic>` line) gives the
  line `budget <agent> calls=<n> output=<n> session=<id>` and exit code 3; the session is never stopped for it.
- hand-over: a new line 1 `HANDOFF …` in `handoff-<role>.md` stops the session and starts a fresh one with the same
  name and the role's `fresh` text, when the note's mtime lies between the session's first and last transcript
  timestamps plus five minutes; otherwise `note not from <agent>: <file>` is logged and nothing is launched.
  An agent with a `work_check` (a command as a list of strings, `{run}` and `{skill}`, the folder of
  `watch_agents.py`, filled in; run in the run folder, 60 s at most) gets the fresh session only when the check says
  work waits: exit 0 launches as above; exit 3, nothing to take, logs `idle <agent>: nothing to take (<last line>)`
  once per note, stops the session (one left live at its note would wake on a waiter or a message in its old
  context, past any cap), keeps the note as the role's `idle` (an on-demand agent's not) and does nothing else for
  the agent that round; any other exit, a check that cannot run and one past 60 s log `work_check failed (exit <n>):
  <last line>` or `work_check failed to run: <error>` and launch, so a broken check never silences a role. A note that
  answers the watcher's own hand-over order (the cap's or the unit end's, which may come in the middle of a unit)
  launches without the check. An idle role's whole turn is its check, once a round: exit 0 or a failed check launches
  `fresh <agent> after idle: work waits`, exit 3 does nothing and logs nothing (no revival, nudge or timeout launch);
  a newer note is read first. A fresh launch ends the idle state, a config reload keeps it, and the registry's `idle`
  (the note's line 1, else `null`) makes a restarted watcher re-check the role instead of taking its note as new.
- on demand: an agent with `on_demand` is launched by the watcher alone, never by the manager at the start (the
  watcher's start launches nothing). Each round, before its other acts, `open_ids.py`'s reading of the run folder
  gives its open ids (its `demand`: `kinds`, `cause`, `parity`, `shared`; a key left out takes `DEMAND_DEFAULTS`), and its
  registry entry's `first_seen` keeps each with the time it was first seen and drops each one answered. Busy (a live
  row, not final), it is left to the cap, the note and the budget as any role. Not busy, it is launched fresh with
  its `fresh` text when its open ids reach `demand.queue` or the oldest was first seen `demand.wait_minutes` ago or
  earlier (`demand <agent>: <n> open ids, oldest <m> min; launched`, whole minutes); with none open, a final session
  at its prompt is stopped (`demand <agent>: queue empty, stopped`). It is final when line 1 starts with its `final`
  and the record was written at or after its launch (with no launch by this watcher, line 1 alone decides), so a
  relaunched fixer whose line 1 still says the last session's `STATUS: done` is live until it writes. It is never
  revived (`demand <agent>: done, not revived`, once per session) and its note is never kept as `idle`, so the idle
  re-check never launches it below its queue. Under `--check` both stops are said, not done (`would stop <id>`). An
  agent without `on_demand` (also one a reload stripped of it) keeps an empty `first_seen`. A failed on-demand agent
  is never relaunched: its row goes on to the exit event `<agent> failed`, as any role's. With none open and no live
  row, an on-demand agent counts as final for the end exit (`every STATUS line is final`), so a fixer the run never
  launched (no record yet) or one stopped before its first write does not keep the watcher polling.
- final: a final agent's live session is stopped by the watcher, never by the manager (owner, 2026-10-30: sessions
  close without the owner; the auto-mode classifier refuses `claude stop` to the main session): at its prompt at
  once (`stopped <agent> <id>: final (<line 1>)`), busy (a waiter shell shows as busy) once its record is
  `final_stop_minutes` old (default 10), so a last commit is not cut; the end exit waits for such a session
  (`every STATUS line is final; waiting for busy <agents>`, once per change) and comes when it is stopped;
  `final_stop_minutes: null` leaves final sessions live and exits as before. Under `--check`: `would stop <id>`.
- milestones: a builder's `STATUS: milestone done after Task N` starts a fresh builder; a verifier whose `STATUS:
  verified through Task N` reaches a listed milestone gets a fresh session. Only the roles `builder` and `verifier`.
- context cap: a last call over `cap` tokens stops the session and resumes it once with the `handoff_order` text; with
  no note within `handoff_wait` seconds, a fresh session starts anyway, from the files.
- blocked: a block that lasts `permission_wait` seconds is a permission prompt nobody can answer (the session is
  stopped and resumed with the `unblock` text) or, waiting for anything else, an exit event.
- revival: a session with no process, stopped or done, is resumed with the `nudge` text, at most `nudges` times.
- the match: an agent's row is the one whose `sessionId` is the session id recorded at its launch, else the one whose
  `id` is the job id `--bg` printed (`claude stop <id>`), else the newest row with its name whose real `cwd` is the
  agent's, started at or after its launch or, before the watcher's first launch, after the first `Yes:` line of
  `_launch.md` minus 5 s (`adopted <agent> <id> by name`; J5); when the recorded row has no process and a row of the
  agent's name in its cwd, started after it, has one, that live row is the agent's (`adopted <agent> <id> by name:
  live beside its recorded <old>`): a session the manager launched by hand with the agent's `--name` in its cwd is
  taken, and no demand or wake launches beside it; the copies rule runs before any launch. A renamed session stays
  the agent's, a namesake with
  another id or in another folder (an earlier run's) is not. `copies` still counts live namesakes in any folder.
- copies: two or more live rows of one agent (its name, its job id or one of its session ids) give
  `copies <agent>: <ids>` and exit code 0; nothing else is done for that agent in that round. A row the watcher
  stopped in this round or the one before is not counted (its stop may still be running). A resume the CLI answers
  with `started a copy as <id>` keeps the copy as the agent's session (`copy <agent> <id> kept`; the next round
  matches it by that job id) and stops the original again when the output names it (`claude attach <id>`).
- a changed brief: its new SHA-256 is stored and logged as `control file reloaded: <name>`, and every agent with a
  session whose texts name the file is stopped and resumed with the `reload_order` text (`reload <agent> <name>`);
  the watcher goes on.
- unit end: when line 1 of the record changed (a unit ended) and the last call is over `handoff_at` tokens, the
  `unit_end_order` text orders the hand-over (`unit end <agent> <tokens> tokens; ordered to hand over`) once the line
  is `unit_end_grace` s old (600, from the record's mtime; `0`: at once; the round that sees it logs `grace <agent>: …`)
  and the session's own note has not come; a session in the middle of a unit gets no such order (the cap holds). A session that started without its lane's pack (an `extra_prompt` whose mark its transcript lacks) gets the same
  hand-over order at its next unit end at any context (`unit end <agent>: its session lacks the pack`), and a dead
  one (no process: its cache is cold anyway), revived or woken by an order, final or not, starts fresh with the pack
  and its open orders instead of a resume (owner, 2026-11-01: a resume never gets the pack; a run's shared extra prompt
  keeps the resume rule).
- orders: every order (the cap's hand-over, the unit end, a reload, the manager's `--order`) ends with the line
  ``Order <msg_id>: append the line `ACK <msg_id>` to <record> before anything else.`` and is sent by stop and resume.
  A line of the record that starts with `ACK <msg_id>` closes it (`ack <agent> <msg_id>`); without one after
  `ack_wait` seconds it is resent (`resent <msg_id> to <agent> (<n> of <ack_resends>)`), and after `ack_resends`
  resends it gives `no ack <agent> <msg_id> after <n> resends` and exit code 0. A fresh session gets the open
  `--order` orders in its prompt; it supersedes the cap's, the unit end's and the reload orders. A `--order` order to
  an agent the manager cannot reach (no process, or line 1 final: a finished builder, a done on-demand fixer) is
  delivered by the watcher in its next round, once (`woke <agent> with order <msg_id>`; the order's `woken` in the
  registry): a resume of its session, or a fresh launch when it has none or is idle. While the order is open the agent
  is not final; a final agent's prompt also gets the line "Your record <record> is final on line 1. After the ACK, set
  line 1 to `STATUS: working on order <msg_id>`; when this order's work is done, set it back to your final line."
  (owner, 2026-11-01: an order to a done on-demand fixer waited unanswered, and a hand resume made a second copy).
- the registry: the `registry` file (default `_control/registry.json`) is written whole at the end of every round and
  when the watcher returns: per agent its `state` (`running`, `stopped`, `blocked`, `done`), lane and settings (from
  `_launch.md` when the run folder has one), line 1 of its record, its session ids, context, calls, cost, idle note,
  orders and `first_seen` (an on-demand agent's open ids, each with the time it was first seen). A restarted watcher
  reads it once and keeps the orders, the revivals, the idle notes, the `first_seen` times and the session ids
  (`registry: <agent> revivals=<n> orders=<ids>`).

Safety: at start it records the SHA-256 of every control file (the config, the settings files, the `extra_prompt`
file, the `_*` files of the run folder its texts name: the briefs).
A brief whose hash changed, or one created after the start, is reloaded each round (above). Before each stop and launch
it checks the settings files and every `extra_prompt` file (the run's and each lane's pack) again, and that every brief still exists; on a change it logs
`control file changed: <name>` and exits with code 4 instead. The config is the exception: a
changed config is read and checked again at the start of the next round; a valid one replaces the old one (the run
state stays: the sessions seen, pending orders, revivals) and logs `config reloaded: <name>`, an invalid one
(unreadable, not JSON, a field missing or unknown, a value of the wrong JSON type, as the script's `TYPES` gives
them, or a negative number) is kept out and logs `config invalid, kept the previous one: <error>`, once per change,
and neither exits. At start the same checks give exit 2.
Code 4 is left for a settings file, an `extra_prompt` file (a lane's pack included) and a removed brief.

`--check` runs only `claude agents --json --all` (and, for a new note, the agent's `work_check`, so a check must only read)
and prints one line per agent with its decisions (`would stop <id>`,
`would launch <command>`, `would nudge`, `would exit <reason>`, `no action (…)`, `no session`), then `would exit
<code>: <events>` or `would sleep <interval> s and go on`, and exits 0. A launch is `claude [--resume <sessionId>]
--name <name> --add-dir <dirs> <common> --settings <the settings file's text> [--append-system-prompt-file <file>]
--bg <prompt>`, run in the agent's `cwd`. It reads no registry, merges no inbox, writes nothing and matches rows by
name only, so its output for the same rows is version 2's.

`--order <agent> <text>` is how the manager gives an order: it checks the config as a start does (a config error,
`config error: no agent <agent>` or `config error: empty order`: exit 2, nothing written), appends one line
`{"msg_id", "agent", "text", "at"}` to `orders.jsonl` beside the registry, prints `order <msg_id> <agent>` and the
prompt to send (the text, a blank line, its Order line), runs no `claude` command and exits 0. The manager sends that
prompt itself to a live working session; the running watcher merges the line in its next round as sent at `at`, waits
`ack_wait` seconds for the `ACK <msg_id>` line and resends by stop and resume. To an agent with no process or a final
line 1 the manager sends nothing and never resumes it by hand (a second copy): the watcher delivers it (orders above).

| code | the watcher returns because |
|---|---|
| 0 | an event: an agent failed or is blocked, `blocked` on line 1 of a `blocked_files` file, every STATUS is final (its live sessions stopped), two live copies of one agent (`copies …`), an order with no `ACK` line after its resends (`no ack …`) |
| 1 | the last round ended without an event |
| 2 | a config error at start; nothing is run (a config changed later is reloaded or kept out, above) |
| 3 | a budget line (above); decide whether the session may go on, then restart the watcher |
| 4 | a settings file or an `extra_prompt` file (the run's, or a lane's own pack) changed, or a brief was removed (a changed brief is reloaded, above); check the change, then restart the watcher: the registry keeps the orders, the revivals and the session ids |

An agent's `final_check` (a command like `work_check`, run at most once a round while its line 1 is final) keeps it
from counting as final while it exits 0: a builder whose lane got (code) findings after its `STATUS: done` is revived;
exit 3 keeps it final; any other exit is told and keeps it final (2026-11-01).
