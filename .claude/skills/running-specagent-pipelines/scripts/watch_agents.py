#!/usr/bin/env python3
"""Main-session watcher for a SpecAgent pipeline, version 3: one script for every pipeline, its behaviour read from the
config instead of the code. Version 2 was the union of three earlier runs' copies of 2026-10-26 and the milestones of
version 1's copy for one project; version 3 (2026-10-29) adds the registry, the orders and their ACK lines, the reload
of a changed brief, the hand-over at the end of a unit, the match of a session by its ids and the restart without
loss. Run it in the background from the orchestrating session:

  python3 watch_agents.py <config> [rounds]     (one round every `interval` seconds; default 240 rounds = 8 hours)
  python3 watch_agents.py --check <config>      (one round as a fresh start would see it: the decision per agent is
                                                 printed; only `claude agents --json --all` and the agents'
                                                 `work_check`s are run)
  python3 watch_agents.py --order <agent> <text> <config>
                                                (appends one order to orders.jsonl beside the registry and prints the
                                                 prompt to send; runs no claude command; rounds is ignored)

A round of version 3, in its order: the rows of `claude agents --json --all`; each agent's row, matched by the
session id recorded at its launch, then by the job id its `--bg` launch printed (`claude stop <id>`), then by name
(the newest row of its name in its cwd started since its last launch or, before the first launch, since the first
`Yes:` line of `_launch.md`: `adopted <agent> <id> by name`), so a renamed session stays the agent's and a namesake
with another id or in another folder is not; the briefs, a changed or new one reloaded with a `reload`
order to the sessions whose texts name it; the inbox `orders.jsonl` beside the registry (the manager's `--order`
lines); per agent its `ACK <msg_id>` lines, then its acts below; the registry last.

Each round, for every agent with a session whose STATUS line is not final (the role is the part of the name after the
slash):
- budget: a session past `budget` calls or output tokens (from its transcript, one call per message id, no
  '<synthetic>' line) gives the line
  `budget <agent> calls=<n> output=<n> session=<id>` and, at the end of the round, exit code 3; the session is never
  stopped for it. An agent's own `budget` overrides the common one: that is how the main session lets a session it was
  told about go on (a session already past it when the watcher starts is reported in the first round).
- hand-over: a new line 1 `HANDOFF …` in handoff-<role>.md stops the session and starts a fresh one with the same name
  and the role's `fresh` text, when the note's mtime lies between the session's first and last transcript timestamps
  plus five minutes; otherwise `note not from <agent>: <file>` is logged and nothing is launched. At start, a note
  outside that window is taken as handled (a newer session exists) and is not logged. An agent with a `work_check`
  (a command; `{run}` and `{skill}`, this script's folder, filled; run in the run folder, 60 s at most) is launched
  only when the check exits 0: exit 3 logs `idle <agent>: nothing to take (<last line>)`, stops the session (a live
  one would wake on a waiter or a message in its old context) and keeps the note as the role's `idle`, any other exit
  or a check that cannot run logs `work_check failed …` and launches, and a note that answers the watcher's own
  hand-over order (cap, unit end) launches unchecked. An idle role's turn is its check, once a round, with nothing else
  done for it (no revival, nudge or timeout launch): exit 0 launches `fresh <agent> after idle: work waits`, and a
  config reload and the registry keep the role idle.
- on demand: an agent with `on_demand` is launched by the watcher alone, never at the start. Each round its open ids
  (`open_ids.py` with its `demand`: kinds, cause, parity) are kept with the time each was first seen; not busy, it is
  launched when they reach `demand.queue` or the oldest is `demand.wait_minutes` old, a final session at its prompt
  with none open is stopped, a stopped one is never revived, a failed one is an exit event (never relaunched), and
  its note is never kept as `idle`. With none open and no live session it counts as final for the end exit (a fixer
  the run never needed has no record).
- milestones: a builder's `STATUS: milestone done after Task N` starts a fresh builder; a verifier whose `STATUS:
  verified through Task N` reaches a listed milestone gets a fresh session, once for every milestone it passed. Lines
  that already say so when the watcher starts count as handled.
- failed: an exit event. blocked: a waiting agent (busy, no waitingFor) is left alone; a block that lasts
  `permission_wait` seconds is a permission prompt nobody can answer (the session is stopped and resumed with the
  `unblock` text) or, waiting for anything else, an exit event. `permission_wait: null`: every block exits at once.
- context cap: a last call over `cap` tokens gives the session a `handoff` order (the `handoff_order` text); if no note
  appears within `handoff_wait` seconds, a fresh session starts anyway, from the files. An order already in the
  transcript (given by a watcher that ran before this one) counts as given, at its timestamp.
- revival: a session with no process, stopped or done, is resumed with the `nudge` text, at most `nudges` times.
- copies: two or more live rows of the agent (its name, its job id or one of its session ids) are an exit event, and
  nothing else is done for it; a row the watcher stopped in this round or the one before is not counted. A resume
  that started a copy (the session was still running) keeps the copy as the agent's session (`copy <agent> <id> kept`)
  and stops the original once more.
- unit end: a new line 1 in the agent's record while its last call is over `handoff_at` tokens gives a `unit-end`
  order (the `unit_end_order` text): hand over now, once the line is `unit_end_grace` seconds old; a note before then
  starts the fresh session as usual. In the middle of a unit nothing is ordered. A session that started without its lane's pack (an `extra_prompt` whose mark its transcript lacks) gets the same
  hand-over order at its next unit end at any context (`unit end <agent>: its session lacks the pack`), and a dead
  one (no process: its cache is cold anyway), revived or woken by an order, final or not, starts fresh with the pack
  and its open orders instead of a resume (owner, 2026-11-01: a resume never gets the pack; a run's shared extra prompt
  keeps the resume rule).
- orders: the watcher's (`handoff`, `unit-end`, `reload`) and the manager's (`--order`) reach a session by a stop
  (when it has a process) and a resume whose prompt is each order's text and its line `Order <msg_id>: append the line
  `ACK <msg_id>` to <record> before anything else.`; a line `ACK <msg_id>` at the start of a line of the record closes
  the order (`ack <agent> <msg_id>`). Without it the order is resent after `ack_wait` seconds, at most `ack_resends`
  times, then closed with the exit event `no ack <agent> <msg_id> after <n> resends`. A fresh session gets the open
  manager orders in its prompt, and the watcher's own are superseded. A manager order to an agent with no process or
  a final line 1 is delivered by the watcher at once, once (`woke <agent> with order <msg_id>`); while it is open the
  agent is not final.
- registry: `<run_dir>/<registry>` (default `_control/registry.json`), written whole with `os.replace` at the end of
  every round and when the watcher returns (never with --check, --order or on exit 2): per agent its lane and settings
  (from the first table of `_launch.md` with role, lane and settings columns), record, unit, state, session ids,
  context, calls, cost, revivals, pending hand-over, idle note and orders. It is read once at start
  (`registry: <agent> revivals=<n> orders=<open ids>`), so a restarted watcher keeps the orders, the revivals and the
  session ids.
Every log line starts with the UTC minute (`2026-10-29T20:41Z`), and `{time}` in the texts is UTC too.
Exit codes: 0 an event (a failed or blocked agent, `blocked` on line 1 of a `blocked_files` file, two live copies of
one agent, an order with no ACK line after its resends, every STATUS final); 1 after the last round; 2 a config error
at start (nothing is run); 3 a budget; 4 a settings file or an extra prompt file (a lane's pack) changed, or a brief was removed (a
changed brief is reloaded).
Safety: at start the SHA-256 of every control file is recorded: the config, the settings files, the extra prompt files
and the `_*` files of the run folder that its texts name (the briefs). At the start of each round a config whose
SHA-256 changed is read and checked again: a valid one replaces the old one and logs `config reloaded: <name>` (the
run state stays), an invalid one is kept out and logs `config invalid, kept the previous one: <error>`; neither
exits. A changed or new brief is re-hashed and reloaded each round (`control file reloaded: <name>`) and gives a
`reload` order to every role with a session whose texts name it. Before each stop and launch the settings files and
the extra prompt files are checked again and every brief must still exist, else the watcher logs
`control file changed: <name>` and exits with code 4.

Config v3: only `run_dir` and `agents` are required; every other field defaults to DEFAULTS below. A value whose JSON
type is not the one TYPES (AGENT_TYPES for an agent) gives its field is a config error: a number is never negative or
a bool, `permission_wait` may be null, `handoff_at` lies below `cap`.
  {"run_dir": "...", "common": [flags for every agent], "blocked_files": ["build-log.md", ...],
   "cap": 260000, "handoff_at": 250000, "handoff_wait": 1200, "nudges": 6, "permission_wait": 600, "interval": 120,
   "unit_end_grace": 600, "ack_wait": 900, "ack_resends": 2, "registry": "_control/registry.json",
   "budget": {"calls": 150, "output_tokens": 2000000},
   "fresh": {"<role>": "text with {run}"},  merged over FRESH; milestone-builder and milestone-verifier take {n}, {next}
   "lang": " Work in English only …",       appended to the fresh texts, the nudge and the watcher's orders
   "nudge": "…", "handoff_order": "… {run}/_handoff-rule.md …", "unblock": "…",
   "unit_end_order": "… {at} …", "reload_order": "… {file} … {time} …",
   "milestones": [7, 13],
   "extra_prompt": {"file": "_pack.md", "mark": "<its first line>"},  --append-system-prompt-file for every new
                                             session and for a resume of a session whose transcript carries the mark
   "agents": {"<name>": {"cwd", "add_dirs", "settings": "<file in run_dir>", "status": "<file in run_dir>",
                         "final": "STATUS: done", "budget": {…}, "work_check": ["python3", "{skill}/…", "{run}"],
                         "extra_prompt": {"file": "_pack-<role>.md", "mark": "<its first line>"},
                         "final_check": ["python3", "-I", "{skill}/open_ids.py", "{run}", "--kind", "V,R",
                                         "--cause", "code", "--tasks", "<the lane's tasks>"]}}}
An agent's `final_check` keeps it from counting as final while its exit is 0: a builder whose line 1 says done is
revived when the verifier files (code) findings for its lane (a project's run of 2026-11-01: they waited ten hours).
An agent's own `extra_prompt` replaces the run's for that agent: one frozen pack per lane in the system prompt, so it
survives a compaction and every session of the lane reads it from the cache (owner, 2026-11-01). The pack holds the
lane's standing orders (`_common.md`, the role's assignment, `_first-pass-rules.md`, `_handoff-rule.md` and the "Read
first" section of lessons.md, built by `scripts/make_pack.py --no-note` before the first launch, never the live
lessons.md); it is a control file like the settings: changed during the run, the watcher exits 4.
A launch is `claude [--resume <sessionId>] --name <name> --add-dir <dirs> <common> --settings <the settings file's
path> [--append-system-prompt-file <file>] --bg <prompt>`, run in the agent's cwd. The settings, status, extra_prompt
and registry files must lie inside run_dir (a config error otherwise), and the agents must not be able to write the
control files (the briefs' `_*` denies and the sandbox's denyWrite): the watcher hashes every control file at start
and again right before each launch, and exits 4 when a settings file or an extra prompt file changed or a brief is
gone. The old run-wide `pack: true` (packs read as a first message) is refused as a config error, and a resume of a
session that started with such a pack is an exit event; a lane's pack goes through its own `extra_prompt` instead.
"""

import argparse
import datetime
import glob
import hashlib
import json
import os
import pathlib
import re
import secrets
import shlex
import subprocess
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import open_ids
import usage_report as ur

LANG = (
    " Work in English only, from your first word (thinking, replies, tool descriptions, files, summaries): the "
    "owner decided this for the pipeline because a script outside the Latin blocks costs about twice the tokens; see _common.md, Language."
)
NUDGE = (
    "Your process was stopped while you were waiting and has now been restarted. Check your files for work that "
    "arrived meanwhile and do it, as your assignment says; if there is none, start your background waiter again."
)
HANDOFF_ORDER = (
    "Orders from the owner: your context has passed the size limit ({cap} tokens per call). Finish the step "
    "you are on at a point where nothing is half done (not the whole task), save and commit what you have, "
    "then write your hand-over note exactly as {run}/_handoff-rule.md says (handoff-<role>.md, line 1 "
    "`HANDOFF <role> after Task <N> — <date time>`) and end your turn. Start no waiter and no new work; a "
    "fresh session continues from your note and the files."
)
# Its first 50 characters equal HANDOFF_ORDER's on purpose: the transcript check of an order already given finds both.
UNIT_END_ORDER = (
    "Orders from the owner: your context has passed the hand-over mark ({at} tokens) and your unit of work has "
    "ended. Do not start the next unit: write your hand-over note now, as {run}/_handoff-rule.md says, and end your "
    "turn."
)
RELOAD_ORDER = (
    "Orders from the main session: {file} was changed at {time} UTC and you were restarted so that the change "
    "applies. If it is a brief, read it again before your next step; it wins over what you remembered. Then continue "
    "where you were."
)
ORDER_LINE = "Order {msg_id}: append the line `ACK {msg_id}` to {record} before anything else."
PACK_ORDER = (  # a session without its lane's pack hands over at a unit end, so the next one starts with it (2026-11-01)
    "Orders from the owner: this session started without your lane's pack in its system prompt, so it reads its "
    "standing orders at full price on every call. Your unit has ended: hand over now, writing the note as your "
    "hand-over rule says; the next session starts with the pack."
)
WAKE_LINE = (  # a manager order to an agent whose line 1 is final: the order wakes it (owner, 2026-11-01)
    "Your record {record} is final on line 1. After the ACK, set line 1 to `STATUS: working on order {msg_id}`; when "
    "this order's work is done, set it back to your final line."
)
UNBLOCK = (
    "Your last command waited more than 10 minutes for a permission approval that nobody could give, so the "
    "owner's watcher cancelled it and restarted you. Do not run that command again. Reach the same result another "
    "way that needs no approval (reading with sed -n or python3; writing your own files with python3); if there is "
    "none, record the step as open in your log and go on with your work. Work in English only."
)
FRESH = {  # pack-aware since 2026-11-01 (owner): a lane's pack in the system prompt holds the files they name
    "planner": (
        "You are a fresh planner session; the previous one handed over (a model change or a stuck session). Your "
        "standing orders are {run}/_planner-assignment.md, {run}/_first-pass-rules.md and {run}/_handoff-rule.md: when your system prompt holds them (this lane's pack), do not read them "
        "again; else read them. Read the lessons added to {run}/lessons.md since the run began and, last, "
        "{run}/handoff-planner.md. Answer open findings first, then write the next task the note names. Write the facts your next step needs into your record as you go; "
        "write a HANDOFF note only on the watcher's order."
    ),
    "critic": (
        "You are a fresh critic session; the previous one handed over (a model change or a stuck session). Your "
        "standing orders are {run}/_critic-assignment.md and {run}/_handoff-rule.md: when your system prompt holds them (this lane's pack), do not read them "
        "again; else read them. Read the lessons added to {run}/lessons.md since the run began and, last, "
        "{run}/handoff-critic.md. Continue with the next completed task of the plan and check waiting answers. Write the facts your next step needs into your record as you go; "
        "write a HANDOFF note only on the watcher's order."
    ),
    "builder": (
        "You are a fresh builder session; the previous one handed over (a model change or a stuck session). Your "
        "standing orders are {run}/_builder-assignment.md, {run}/_first-pass-rules.md and {run}/_handoff-rule.md: when your system prompt holds them (this lane's pack), do not read them "
        "again; else read them. Read the lessons added to {run}/lessons.md since the run began and, last, "
        "{run}/handoff-builder.md. Fix open verifier findings first, then build the task the note names. Write the facts your next step needs into your record as you go; "
        "write a HANDOFF note only on the watcher's order."
    ),
    "verifier": (
        "You are a fresh verifier session; the previous one handed over (a model change or a stuck session). Your "
        "standing orders are {run}/_verifier-assignment.md and {run}/_handoff-rule.md: when your system prompt holds them (this lane's pack), do not read them "
        "again; else read them. Read the lessons added to {run}/lessons.md since the run began and, last, "
        "{run}/handoff-verifier.md. Your checkout exists; rebuild its environment only at a milestone. Verify the next done task. Write the facts your next step needs into your record as you go; "
        "write a HANDOFF note only on the watcher's order."
    ),
    "judge": (
        "You are a fresh judge session; the previous one handed over (a model change or a stuck session). Your "
        "standing orders are {run}/_judge-assignment.md and {run}/_handoff-rule.md: when your system prompt holds them (this lane's pack), do not read them "
        "again; else read them. Read the lessons added to {run}/lessons.md since the run began and, last, "
        "{run}/handoff-judge.md. Do the next unit (Task 1-5). Write the facts your next step needs into your record as you go; "
        "write a HANDOFF note only on the watcher's order."
    ),
    "plan-fixer": (
        "You are a fresh plan-fixer session; the previous one handed over (a model change or a stuck session). Your "
        "standing orders are {run}/_plan-fixer-assignment.md, {run}/_first-pass-rules.md and {run}/_handoff-rule.md: when your system prompt holds them (this lane's pack), do not read them "
        "again; else read them. Read the lessons added to {run}/lessons.md since the run began and, last, "
        "{run}/handoff-plan-fixer.md. Answer the open points the note names and every new one, in the assignment's order. Write the facts your next step needs into your record as you go; "
        "write a HANDOFF note only on the watcher's order."
    ),
    "milestone-builder": (
        "You are a fresh builder session; the previous one ended at a milestone to keep the context "
        "small. Read {run}/_builder-assignment.md, {run}/_first-pass-rules.md and {run}/lessons.md, then "
        "{run}/build-log.md and {run}/verify.md to learn the state: Tasks 1–{n} are built and committed. "
        "Fix any open verifier findings first, then continue with Task {next}. Make the first line of "
        "build-log.md read your status again."
    ),
    "milestone-verifier": (
        "You are a fresh verifier session; the previous one ended at a milestone to keep the context "
        "small. Read {run}/_verifier-assignment.md, then {run}/verify.md and {run}/build-log.md to learn "
        "the state: Tasks 1–{n} are verified. Your checkout exists. Rebuild its environment from scratch "
        "now (this is a milestone), then verify the next done tasks in the log and go on as your "
        "assignment says."
    ),
}
DEFAULTS = {
    "common": [],
    "blocked_files": [],
    "cap": 260_000,  # a backstop: `--autocompact 235000` in `common` compacts near 197k first (owner, 2026-11-01)
    "handoff_at": 250_000,
    "handoff_wait": 20 * 60,
    "unit_end_grace": 600,
    "nudges": 6,
    "permission_wait": 600,
    "final_stop_minutes": 10,
    "interval": 120,
    "ack_wait": 15 * 60,
    "ack_resends": 2,
    "registry": "_control/registry.json",
    "budget": {"calls": 3000, "output_tokens": 40_000_000},  # a whole-run session: compactions and waiter calls
    "fresh": FRESH,
    "lang": LANG,
    "nudge": NUDGE,
    "handoff_order": HANDOFF_ORDER,
    "unit_end_order": UNIT_END_ORDER,
    "reload_order": RELOAD_ORDER,
    "unblock": UNBLOCK,
    "milestones": [],
}
OTHER_FIELDS = ("run_dir", "agents", "extra_prompt", "pack")
AGENT_FIELDS = ("cwd", "add_dirs", "settings", "status", "final")
PACK_MARK = "Your standing orders are in your system prompt"  # startup packs (`scripts/make_pack.py`)
MARK_HEAD = 300_000  # characters of a transcript searched for a system-prompt mark, as an earlier run does
NOTE_SLACK = 5 * 60
MILESTONE = re.compile(r"STATUS: milestone done after Task (\d+)")
VERIFIED = re.compile(r"STATUS: verified through Task (\d+)")
# What a reloaded config leaves as it was: the run so far, not the config's values (Watcher.reload).
RUN_STATE = (
    "seen",
    "pending",
    "idle",
    "revived",
    "not_revived",
    "blocked_since",
    "switched",
    "started",
    "failures",
    "said",
    "changed_file",
    "roles",
    "matched",
    "stopped",
    "left_busy",
    "waiting_final",
    "round_no",
    "started_at",
)
BRIEF = re.compile(r"(?<![\w.-])_[\w-]+(?:\.[\w-]+)+")
ACK = re.compile(r"(?m)^ACK ([0-9a-f]{8})\b")  # a role's answer to an order: a line of its own record
JOB = re.compile(r"claude stop ([0-9a-f]{8})\b")  # the job id a `--bg` launch prints
COPY = re.compile(r"a copy as ([0-9a-f]{8})\b")  # a resume of a session that still runs starts a copy
ORIGINAL = re.compile(r"claude attach ([0-9a-f]{8})\W+opens the original")
YES = re.compile(r"(?m)^Yes: (\d{4}-\d\d-\d\dT\d\d:\d\dZ) — ")  # the pre-flight's yes line in _launch.md (preflight.py)
ORDER_KEYS = ("msg_id", "kind", "text", "sent_at", "resends", "acked_at", "closed", "woken")  # an order in the registry
PRICED = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")  # PRICE's order


def number(value):
    """An int or a float the watcher can count, compare and sleep with: not a bool, finite, never negative."""
    return isinstance(value, int | float) and not isinstance(value, bool) and 0 <= value < float("inf")


# The JSON type of each config field and agent field: a value of another type is a ConfigError, so the watcher refuses
# it at start (exit 2) and a reload keeps it out, where a later round would raise on it or apply it (a "200k" cap).
STRING = ("a string", lambda v: isinstance(v, str))
NUMBER = ("a non-negative number", number)
STRINGS = ("a list of strings", lambda v: isinstance(v, list) and all(isinstance(x, str) for x in v))
NUMBERS_BY_NAME = ("an object of non-negative numbers", lambda v: isinstance(v, dict) and all(map(number, v.values())))
TYPES = {
    "run_dir": STRING,
    "common": STRINGS,
    "blocked_files": STRINGS,
    "cap": NUMBER,
    "handoff_at": NUMBER,
    "handoff_wait": NUMBER,
    "unit_end_grace": NUMBER,
    "nudges": NUMBER,
    "permission_wait": ("null or a non-negative number", lambda v: v is None or number(v)),
    "final_stop_minutes": ("null or a non-negative number", lambda v: v is None or number(v)),
    "interval": NUMBER,
    "ack_wait": NUMBER,
    "ack_resends": NUMBER,
    "registry": STRING,
    "budget": NUMBERS_BY_NAME,
    "fresh": ("an object of strings", lambda v: isinstance(v, dict) and all(isinstance(x, str) for x in v.values())),
    "lang": STRING,
    "nudge": STRING,
    "handoff_order": STRING,
    "unit_end_order": STRING,
    "reload_order": STRING,
    "unblock": STRING,
    "milestones": ("a list of non-negative numbers", lambda v: isinstance(v, list) and all(map(number, v))),
}
EXTRA_PROMPT = (
    "an object with file and mark, each a string",
    lambda v: isinstance(v, dict) and all(isinstance(v.get(k), str) for k in ("file", "mark")),
)
AGENT_TYPES = {
    "cwd": STRING,
    "add_dirs": STRINGS,
    "settings": STRING,
    "status": STRING,
    "final": STRING,
    "budget": NUMBERS_BY_NAME,
    "work_check": STRINGS,
    "final_check": STRINGS,
    "on_demand": ("a boolean", lambda v: isinstance(v, bool)),
    "demand": ("an object", lambda v: isinstance(v, dict)),
    "extra_prompt": EXTRA_PROMPT,
}
# An on-demand agent's `demand` (spec Decided 2: the fixer's queue and wait, per agent); a key left out takes its
# default.
DEMAND_DEFAULTS = {
    "kinds": ["C", "A", "B", "V", "R"],
    "cause": "plan",
    "parity": "all",
    "shared": True,
    "queue": 6,
    "wait_minutes": 45,
}
DEMAND_TYPES = {
    "kinds": (
        "a list of C, A, B, V or R",
        lambda v: isinstance(v, list) and bool(v) and all(x in DEMAND_DEFAULTS["kinds"] for x in v),
    ),
    "cause": ("plan or any", lambda v: v in ("plan", "any")),
    "parity": ("odd, even or all", lambda v: v in ("odd", "even", "all")),
    "shared": ("a boolean", lambda v: isinstance(v, bool)),
    "queue": ("a positive integer", lambda v: isinstance(v, int) and not isinstance(v, bool) and v > 0),
    "wait_minutes": NUMBER,
}


class ConfigError(Exception):
    pass


class Exit(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def check_types(values, types, prefix=""):
    """Raise a ConfigError for the first field of `values` whose value is not of the JSON type `types` gives it."""
    for key, (kind, test) in types.items():
        if key in values and not test(values[key]):
            raise ConfigError(f"{prefix}{key} is not {kind}")


def log(*parts):
    print(time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()), *parts, flush=True)


def utc(t):
    """Epoch seconds as the registry writes a time, `%Y-%m-%dT%H:%M:%SZ` in UTC; None stays None."""
    return None if t is None else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def first_line(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.readline().rstrip("\r\n")
    except OSError:
        return ""


def written(path):
    """When the file was last written, in epoch seconds and never later than now; now when it cannot be read."""
    try:
        return min(path.stat().st_mtime, time.time())
    except OSError:
        return time.time()


def sha256(path):
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def stamp(text):
    try:
        return datetime.datetime.fromisoformat(text).timestamp()
    except (AttributeError, TypeError, ValueError):
        return None


def transcript_path(session_id):
    paths = glob.glob(os.path.expanduser(f"~/.claude/projects/*/{session_id}.jsonl")) if session_id else []
    try:
        return max(paths, key=os.path.getmtime) if paths else None
    except OSError:
        return None


def read_config(path, given):
    """The config file's JSON with the checks that need no run folder: the fields, their types and the agents."""
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ConfigError(f"cannot read {given}: {e}")
    if not isinstance(config, dict) or "run_dir" not in config or not isinstance(config.get("agents"), dict):
        raise ConfigError("run_dir and agents are required")
    unknown = sorted(k for k in config if k not in DEFAULTS and k not in OTHER_FIELDS and not k.startswith("_"))
    if unknown:
        raise ConfigError(f"unknown fields {', '.join(unknown)}")
    check_types(config, TYPES)
    if config.get("pack"):
        raise ConfigError("pack: startup packs (`scripts/make_pack.py`) are not built by this watcher")
    for name, agent in config["agents"].items():
        if not isinstance(agent, dict):
            raise ConfigError(f"{name} is not an object")
        missing = [k for k in AGENT_FIELDS if k not in agent]
        if missing:
            raise ConfigError(f"{name} has no {', '.join(missing)}")
        check_types(agent, AGENT_TYPES, f"{name}: ")
        if "demand" in agent and agent.get("on_demand") is not True:
            raise ConfigError(f"{name}: demand needs on_demand")
        extra = sorted(set(agent.get("demand", {})) - set(DEMAND_DEFAULTS))
        if extra:
            raise ConfigError(f"{name}: unknown demand fields {', '.join(extra)}")
        check_types(agent.get("demand", {}), DEMAND_TYPES, f"{name}: demand.")
    cap = config.get("cap", DEFAULTS["cap"])
    if "handoff_at" not in config and DEFAULTS["handoff_at"] >= cap:  # an older run's own cap below the new default
        config["handoff_at"] = cap * 3 // 4  # the earlier defaults' ratio, 150000 for 200000
    handoff_at = config.get("handoff_at", DEFAULTS["handoff_at"])
    if handoff_at >= cap:
        raise ConfigError(f"handoff_at {handoff_at} is not below cap {cap}")
    return config


def blank():
    """An agent's registry fields before anything is known about it (the fields K1 restores at start)."""
    return {
        "job_id": None,
        "session_id": None,
        "session_ids": [],
        "launched_at": None,
        "unit": None,
        "unit_since": None,
        "orders": [],
        "first_seen": {},
    }


def restored(order):
    """A registry file's order in the form the watcher keeps (times in epoch seconds); None if it is none."""
    if not isinstance(order, dict) or not all(isinstance(order.get(key), str) for key in ("msg_id", "text")):
        return None
    return {
        "msg_id": order["msg_id"],
        "kind": order["kind"] if isinstance(order.get("kind"), str) else "manager",
        "text": order["text"],
        "sent_at": stamp(order.get("sent_at")),
        "resends": order["resends"] if number(order.get("resends")) else 0,
        "acked_at": stamp(order.get("acked_at")),
        "closed": order["closed"] if isinstance(order.get("closed"), str) else None,
        "woken": order.get("woken") is True,
    }


def bind(entry, row):
    """The row's session becomes the agent's current one and joins its sessions."""
    entry["session_id"] = row.get("sessionId")
    if entry["session_id"] and entry["session_id"] not in entry["session_ids"]:
        entry["session_ids"].append(entry["session_id"])


class Transcripts:
    """What the watcher reads from a session's transcript; a file is parsed again only when it has changed."""

    def __init__(self, order_mark):
        self.order_mark = order_mark
        self.cache = {}

    def stats(self, session_id):
        """First and last timestamp (epoch seconds), calls (distinct message ids: the transcript has one line per
        content block), output tokens, the last call's context, and the time of the last hand-over order (a user prompt
        that starts with it); None when there is no transcript."""
        path = transcript_path(session_id)
        if path is None:
            return None
        try:
            st = os.stat(path)
        except OSError:
            return None
        key = (st.st_size, st.st_mtime_ns)
        if self.cache.get(path, (None,))[0] != key:
            self.cache[path] = (key, self.parse(path))
        return self.cache[path][1]

    def parse(self, path):
        """stats() of one transcript file."""
        first = last = context = ordered = None
        outputs = {}
        with open(path, encoding="utf-8", errors="ignore") as f:
            for n, line in enumerate(f):
                if '"timestamp"' not in line:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                t = stamp(d.get("timestamp")) if isinstance(d, dict) else None
                if t is None:
                    continue
                first, last = t if first is None else min(first, t), t if last is None else max(last, t)
                message = d["message"] if isinstance(d.get("message"), dict) else {}
                if message.get("model") == "<synthetic>":
                    continue  # Claude Code's own line ("No response requested.", a usage-limit notice): no call
                usage = message.get("usage")
                if isinstance(usage, dict):
                    call = message.get("id") or d.get("requestId") or n
                    outputs[call] = max(outputs.get(call, 0), usage.get("output_tokens") or 0)
                    context = sum(
                        usage.get(k) or 0
                        for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
                    )
                elif (
                    d.get("type") == "user"
                    and isinstance(message.get("content"), str)
                    and message["content"].startswith(self.order_mark)
                ):
                    ordered = t if ordered is None else max(ordered, t)
        return {
            "first": first,
            "last": last,
            "calls": len(outputs),
            "output": sum(outputs.values()),
            "context": context,
            "ordered": ordered,
        }

    def head_has(self, session_id, mark):
        path = transcript_path(session_id)
        if path is None:
            return False
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                return mark in f.read(MARK_HEAD)
        except OSError:
            return False


class Watcher:
    def __init__(self, config_path, check=False):
        self.check = check
        self.config_path = pathlib.Path(config_path).resolve()
        self.configure(read_config(self.config_path, config_path))
        self.transcripts = Transcripts(self.order[:50])
        self.hashes = {path: sha256(path) for path in self.control_files()}
        self.table, self.unwatched = self.launch_table()
        self.seen, self.pending, self.idle, self.revived, self.blocked_since, self.switched = {}, {}, {}, {}, {}, set()
        self.not_revived = {}  # an on-demand agent's session id whose stop revive() logged, once per session
        self.unit_wait = {}  # an agent whose unit end waits out `unit_end_grace`: when its new line 1 was written
        self.started, self.failures, self.said, self.changed_file = False, 0, {}, None
        self.roles, self.matched, self.stopped = {name: blank() for name in self.agents}, {}, {}
        self.left_busy, self.waiting_final = [], None
        self.round_no, self.started_at, self.usage_cache = 0, time.time(), {}

    def configure(self, config):
        """The config's values, and the checks that need the run folder."""
        get = lambda key: config[key] if key in config else DEFAULTS[key]
        self.config = config
        self.run, self.agents = pathlib.Path(config["run_dir"]).resolve(), config["agents"]
        self.common, self.blocked_files = list(get("common")), list(get("blocked_files"))
        self.cap, self.handoff_wait, self.nudges = get("cap"), get("handoff_wait"), get("nudges")
        self.permission_wait, self.interval = get("permission_wait"), get("interval")
        self.final_stop_minutes = get("final_stop_minutes")
        self.handoff_at, self.ack_wait, self.ack_resends = get("handoff_at"), get("ack_wait"), get("ack_resends")
        self.unit_end_grace = get("unit_end_grace")
        self.budget = {**DEFAULTS["budget"], **get("budget")}
        self.milestones = sorted(get("milestones"))
        self.lang, self.fresh = get("lang"), {**FRESH, **get("fresh")}
        self.nudge = self.fill(get("nudge")) + self.lang
        self.order = self.fill(get("handoff_order"), cap=f"{self.cap // 1000}k") + self.lang
        self.unit_order = self.fill(get("unit_end_order"), at=f"{self.handoff_at:,}") + self.lang
        self.reload_order, self.unblock = get("reload_order"), self.fill(get("unblock"))
        self.extra = config.get("extra_prompt")
        if self.extra and not EXTRA_PROMPT[1](self.extra):
            raise ConfigError("extra_prompt needs file and mark, each a string")
        # A lane's own system-prompt file (its frozen pack) replaces the run's; an agent without one takes the run's.
        self.extras = {n: a.get("extra_prompt", self.extra) for n, a in self.agents.items()}
        inside = [(f"{n}: {k}", a[k]) for n, a in self.agents.items() for k in ("settings", "status")]
        inside += [("extra_prompt file", self.extra["file"])] if self.extra else []
        inside += [
            (f"{n}: extra_prompt file", a["extra_prompt"]["file"])
            for n, a in self.agents.items()
            if "extra_prompt" in a
        ]
        for what, name in [*inside, ("registry", get("registry"))]:
            if not (self.run / name).resolve().is_relative_to(self.run):
                raise ConfigError(f"{what} {name} leaves run_dir")
        self.registry = self.run / get("registry")
        roles = sorted({name.split("/")[-1] for name in self.agents} - set(self.fresh))
        if roles:
            raise ConfigError(f"no fresh text for role {', '.join(roles)}")

    def fill(self, text, **values):
        for key, value in {"run": self.run, **values}.items():
            text = text.replace("{" + key + "}", str(value))
        return text

    def fresh_text(self, key, **values):
        return self.fill(self.fresh[key], **values) + self.lang

    def fixed_files(self):
        """The control files that are no brief: the config, the settings files and the extra prompt files."""
        files = {self.config_path, *(self.run / a["settings"] for a in self.agents.values())}
        return files | {self.run / e["file"] for e in [self.extra, *self.extras.values()] if e}

    def control_files(self):
        texts = [self.nudge, self.order, self.unit_order, self.unblock]
        texts += [self.fresh_text(n.split("/")[-1]) for n in self.agents]
        if self.milestones:
            texts += [self.fresh_text(k) for k in ("milestone-builder", "milestone-verifier")]
        return sorted(self.fixed_files() | {self.run / name for text in texts for name in BRIEF.findall(text)})

    def named(self, name):
        """The briefs an agent's texts name: its fresh and milestone texts, the nudge and the watcher's orders."""
        role = name.split("/")[-1]
        texts = [self.fresh_text(role), self.nudge, self.order, self.unblock, self.unit_order]
        if self.milestones and role in ("builder", "verifier"):
            texts.append(self.fresh_text(f"milestone-{role}"))
        return {self.run / brief for text in texts for brief in BRIEF.findall(text)}

    def changed(self):
        """The name of the first control file whose change stops a launch: a settings file or the extra prompt file
        whose SHA-256 changed, or a brief that was there and is gone (a changed brief is briefs()'s, the config
        reload()'s)."""
        fixed = self.fixed_files()
        for path, digest in self.hashes.items():
            if path == self.config_path:
                continue
            now = sha256(path)
            if (now != digest) if path in fixed else (digest is not None and now is None):
                return path.name
        return None

    def reload(self):
        """Read a config whose SHA-256 changed: a valid one replaces the old one, an invalid one is kept out."""
        digest = sha256(self.config_path)
        if digest == self.hashes.get(self.config_path):
            return
        self.hashes[self.config_path] = digest  # an invalid file is reported once
        try:
            new = Watcher(self.config_path, self.check)  # the checks of __init__, nothing of self touched
        except ConfigError as e:
            log(f"config invalid, kept the previous one: {e}")
            return
        old = self.hashes
        keep = {*RUN_STATE, "hashes"} | ({"transcripts"} if new.order[:50] == self.order[:50] else set())
        for key, value in vars(new).items():
            if key not in keep:
                setattr(self, key, value)
        # the control files of the new config: a recorded one keeps its SHA-256, a new one is recorded now
        self.hashes = {path: old.get(path, digest) for path, digest in new.hashes.items()}
        for name in self.agents:  # an agent the new config adds starts with nothing known
            self.roles.setdefault(name, blank())
        log(f"config reloaded: {self.config_path.name}")

    def say(self, name, text):
        """A decision for --check (a run logs what it does instead)."""
        self.said.setdefault(name, []).append(text)

    def tell(self, name, text):
        if self.check:
            self.say(name, text)
        else:
            log(text)

    def all_rows(self):
        """Every row of `claude agents --json --all`; None when the call failed."""
        output, rows = "", None
        try:
            r = subprocess.run(["claude", "agents", "--json", "--all"], capture_output=True, text=True, check=False)
            output = r.stdout + r.stderr
            rows = json.loads(r.stdout or "[]")
        except (OSError, ValueError) as e:
            output = output or str(e)
        if not isinstance(rows, list):
            self.failures += 1
            log("claude agents --json --all failed:", output.strip()[-80:])
            return None
        self.failures = 0
        return [row for row in rows if isinstance(row, dict)]

    def match(self, name, rows):
        """The agent's row (6e): the one with its session id, else its job id, else the newest of its name in its cwd
        started since its launch (before the first launch: since the first `Yes:` line of _launch.md, J5); --check
        matches by name and cwd alone."""
        entry = self.roles[name]
        for key, field in () if self.check else (("session_id", "sessionId"), ("job_id", "id")):
            row = next((r for r in rows if entry[key] and r.get(field) == entry[key]), None)
            if row:
                live = None if row.get("pid") else self.live_namesake(name, rows, row)
                if live:  # a session launched beside a finished recorded one (by hand) is the agent's (2026-11-02)
                    entry["job_id"], entry["session_id"] = live.get("id"), None
                    bind(entry, live)
                    log(f"adopted {name} {live.get('id')} by name: live beside its recorded {row.get('id')}")
                    return live
                bind(entry, row)
                return row
        floor = self.yes_floor() if entry["launched_at"] is None else entry["launched_at"] - 5
        home = os.path.realpath(self.agents[name]["cwd"])
        found = None
        for r in rows:
            started, cwd = r.get("startedAt") or 0, r.get("cwd")
            here = isinstance(cwd, str) and cwd != "" and os.path.realpath(cwd) == home  # an earlier run's is elsewhere
            if r.get("name") != name or not here or (floor is not None and started / 1000 < floor):
                continue
            if found is None or started >= (found.get("startedAt") or 0):
                found = r
        if found and not self.check:
            entry["job_id"] = found.get("id")
            bind(entry, found)
            log(f"adopted {name} {found.get('id')} by name")
        return found

    def live_namesake(self, name, rows, recorded):
        """The newest row with a process, of the agent's name in its cwd, started after the recorded row: a session the
        manager launched by hand while the watcher still held a finished one (a project's run of 2026-11-02: two more sessions
        of an on-demand role were launched beside a busy hand-launched one)."""
        home = os.path.realpath(self.agents[name]["cwd"])
        since = recorded.get("startedAt") or 0
        live = [
            r
            for r in rows
            if r.get("name") == name
            and r.get("pid")
            and isinstance(r.get("cwd"), str)
            and r.get("cwd")
            and os.path.realpath(r["cwd"]) == home
            and (r.get("startedAt") or 0) > since
        ]
        return max(live, key=lambda r: r.get("startedAt") or 0, default=None)

    def yes_floor(self):
        """Rule 3's floor before the first launch (J5): the earliest `Yes:` line of _launch.md, minus 5 s. The
        pre-flight holds every launch until each role is named in a `Yes:` line, so the line precedes every launch and
        is written once (the run folder's ctime moves with every entry made in it); None without the file or such a
        line, and the cwd test decides alone."""
        try:
            text = (self.run / "_launch.md").read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None
        times = [t for t in map(stamp, YES.findall(text)) if t is not None]
        return min(times) - 5 if times else None

    def note_from(self, path, row):
        """The note was written while the agent's latest session was active (its transcript's time span, plus slack)."""
        stats = self.transcripts.stats(row.get("sessionId"))
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return False
        return bool(stats and stats["first"] and stats["first"] <= mtime <= stats["last"] + NOTE_SLACK)

    def seed(self, rows):
        """What the watcher finds at start: notes outside their session's window and milestone lines are handled."""
        for name, a in self.agents.items():
            role, row = name.split("/")[-1], rows.get(name)
            path = self.run / f"handoff-{role}.md"
            note = first_line(path)
            if note.startswith("HANDOFF") and not (row and self.note_from(path, row)):
                self.seen[name] = note
            status = first_line(self.run / a["status"])
            if role == "builder" and (m := MILESTONE.match(status)):
                self.switched.add(("builder", int(m.group(1))))
            if role == "verifier" and (m := VERIFIED.match(status)):
                self.switched.update(("verifier", t) for t in self.milestones if t <= int(m.group(1)))

    def round(self):
        """One round (6d): returns the exit events and the budget lines."""
        self.reload()
        self.round_no += 1
        self.said, events, budget, self.left_busy = {}, [], [], []
        self.final_checks = {}  # an agent's `final_check`, run at most once a round
        for name in self.blocked_files:
            line = first_line(self.run / name)
            if "blocked" in line.lower():
                events.append(f"{name}: {line}")
        rows = self.all_rows()
        if rows is None:
            if self.failures >= 3:
                events.append(f"claude agents --json --all failed {self.failures} times")
            return events, budget
        self.matched = {name: self.match(name, rows) for name in self.agents}
        if not self.started:
            self.seed(self.matched)
            self.started = True
        if not self.check:
            self.briefs()
            self.inbox()
        for name in self.agents:
            self.agent(name, rows, events, budget)
        if all(self.final(name) or self.dormant(name) for name in self.agents):
            if self.left_busy:  # the end exit waits for a busy final session until final_stop() stops it
                names = ", ".join(self.left_busy)
                if names != self.waiting_final:
                    self.waiting_final = names
                    self.tell(self.left_busy[0], f"every STATUS line is final; waiting for busy {names}")
            else:
                events.append("every STATUS line is final")
        if not self.check:
            self.write_registry()
        return events, budget

    def agent(self, name, rows, events, budget):
        """An agent's turn (6d): its ACK lines, an on-demand agent's demand, its acts on the matched row (6i), then its
        unit."""
        row, final = self.matched[name], self.final(name)
        if not self.check:
            self.acks(name)
            if final:
                for order in self.roles[name]["orders"]:
                    order["closed"] = order["closed"] or "final"
            elif self.line_final(name):  # woken by a manager order: the watcher's own orders end with line 1
                for order in self.roles[name]["orders"]:
                    if order["kind"] != "manager":
                        order["closed"] = order["closed"] or "final"
        if not self.check and row is not None and self.copies(name, rows, events):
            pass  # two live copies: the copies rule acts before any launch (2026-11-02)
        elif self.demand(name, row, events):
            pass  # an on-demand agent launched or stopped: nothing else this turn
        elif row is None:
            self.say(name, "no session")
        elif final:
            if not self.final_stop(name, row):
                self.say(name, f"no action (final: {first_line(self.run / self.agents[name]['status'])})")
        elif self.check:
            self.decide(name, row, events, budget)
        elif not self.decide(name, row, events, budget):
            self.unit_end(name, row)
            self.send_due(name, row, events)
        if not self.check:
            self.track_unit(name)

    def final(self, name):
        """K1: line 1 of the agent's record starts with its `final`; an on-demand agent's record was also written at or
        after its session's launch (C19: a relaunched fixer whose line 1 still says the last session's done is live).
        With no `launched_at` (a session this watcher did not launch) line 1 alone decides."""
        a, path = self.agents[name], self.run / self.agents[name]["status"]
        if not first_line(path).startswith(a["final"]):
            return False
        if self.open_manager_orders(name):
            return False  # a manager order wakes a final agent (owner, 2026-11-01): it is delivered, not closed
        if a.get("final_check") and self.lane_has_work(name):
            return False
        launched = self.roles[name]["launched_at"]
        if not a.get("on_demand") or launched is None:
            return True
        try:
            return path.stat().st_mtime >= launched
        except OSError:
            return False

    def final_stop(self, name, row):
        """A final agent's live session is stopped by the watcher, never by the manager (owner, 2026-10-30: sessions
        close without the owner; the auto-mode classifier refuses `claude stop` to the main session): at its prompt at
        once, busy (a waiter shell shows as busy) once its record is `final_stop_minutes` old, so a last commit is not
        cut; `null` leaves it live. True when it stopped, said it would, or left a busy one for round() to wait for."""
        if self.final_stop_minutes is None or not row.get("pid") or row.get("id") in self.stopped:
            return False
        path = self.run / self.agents[name]["status"]
        line = first_line(path)
        if row.get("status") == "busy":
            try:
                age = time.time() - path.stat().st_mtime
            except OSError:
                age = 0.0
            if age < self.final_stop_minutes * 60:
                self.left_busy.append(name)
                self.say(name, f"final ({line}): busy, stopped in {int(self.final_stop_minutes - age // 60)} min")
                return True
        self.stop_session(name, row)
        if not self.check:
            log(f"stopped {name} {row['id']}: final ({line})")
        return True

    def dormant(self, name):
        """R8: an on-demand agent with no open id and no live session counts as final for the end exit: a fixer the
        run never needed has no record, and one stopped before its first write has an old one (`final` is False)."""
        live = (self.matched[name] or {}).get("pid")
        return bool(self.agents[name].get("on_demand")) and not live and not self.roles[name]["first_seen"]

    def demand(self, name, row, events):
        """An on-demand agent's launch and stop (spec Decided 2): its open ids, each kept with the time it was first
        seen; neither busy nor failed (R9: a failed row goes on to decide()'s exit), it is launched when they reach
        `demand.queue` or the oldest is `demand.wait_minutes` old, and a final session at its prompt is stopped when
        none is open. True when it launched or stopped (the turn ends); an agent without `on_demand` only keeps an
        empty `first_seen`."""
        seen, a = self.roles[name]["first_seen"], self.agents[name]
        if not a.get("on_demand"):
            seen.clear()
            return False
        d = {**DEMAND_DEFAULTS, **a.get("demand", {})}
        parity, cause = (None if d["parity"] == "all" else d["parity"]), (None if d["cause"] == "any" else d["cause"])
        found = open_ids.open_ids(self.run, d["kinds"], parity, cause=cause, shared=d["shared"])
        now = time.time()
        for ident in [i for i in seen if i not in found]:
            del seen[ident]
        for ident in found:
            seen.setdefault(ident, now)
        live = row is not None and row.get("pid")
        if live and not self.final(name):
            return False  # busy: the cap, the note and the budget apply to it as to any role
        if row is not None and row.get("state") == "failed":
            return False  # R9: decide() exits with `<agent> failed`, as for any role; a relaunch would fail again
        if row is None and self.wake_orders(name, row):
            why = f"demand {name}: order {self.wake_orders(name, row)[0]['msg_id']}; launched"
            self.launch_fresh(name, row, self.fresh_text(name.split("/")[-1]), why, events)
            return True
        if found and (len(found) >= d["queue"] or now - min(seen.values()) >= d["wait_minutes"] * 60):
            oldest = int((now - min(seen.values())) // 60)
            why = f"demand {name}: {len(found)} open ids, oldest {oldest} min; launched"
            self.launch_fresh(name, row, self.fresh_text(name.split("/")[-1]), why, events)
            return True
        if not found and live and row.get("id"):
            self.stop_session(name, row)
            self.tell(name, f"demand {name}: queue empty, stopped")
            return True
        return False

    def acks(self, name):
        """The ACK lines of the agent's record close the open orders they name (6h); a quoted ACK is no answer."""
        orders = {o["msg_id"]: o for o in self.roles[name]["orders"] if o["closed"] is None}
        if not orders:
            return
        try:
            text = (self.run / self.agents[name]["status"]).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return
        for msg_id in ACK.findall(text):
            if msg_id in orders:
                order = orders.pop(msg_id)
                order["closed"], order["acked_at"] = "acked", time.time()
                log(f"ack {name} {msg_id}")

    def copies(self, name, rows, events):
        """Two or more live rows of the agent (6i.1: its name, its job id or one of its session ids) end the watch; a
        row stopped in this round or the one before is none (that stop may still be running). True when they did."""
        entry, ids = self.roles[name], []
        for r in rows:
            mine = r.get("name") == name or r.get("sessionId") in entry["session_ids"]
            mine = mine or (entry["job_id"] is not None and r.get("id") == entry["job_id"])
            if mine and r.get("pid") and self.stopped.get(r.get("id"), -1) < self.round_no - 1:
                ids.append(str(r.get("id")))
        if len(ids) < 2:
            return False
        self.event(name, f"copies {name}: {', '.join(sorted(ids))}", events)
        return True

    def decide(self, name, row, events, budget):
        """v2's decisions on the matched row, in v2's order; True when one launched or ended the agent's acts."""
        a, role = self.agents[name], name.split("/")[-1]
        status = first_line(self.run / a["status"])
        sid, state = row.get("sessionId", ""), row.get("state")
        stats = self.transcripts.stats(sid)
        limit = {**self.budget, **a.get("budget", {})}
        if stats and (stats["calls"] > limit["calls"] or stats["output"] > limit["output_tokens"]):
            budget.append(f"budget {name} calls={stats['calls']} output={stats['output']} session={row.get('id')}")
            self.say(name, f"would exit {budget[-1]}")
        if self.handoff_note(name, row, role, events) or self.milestone(name, row, role, status, events):
            return True
        if name in self.idle:  # an idle role's whole turn is its check: no revival, nudge or timeout launch
            if self.wake_orders(name, row):
                self.launch_fresh(name, row, self.fresh_text(role), f"fresh {name} after idle: an order waits", events)
            elif self.work_check(name)[0]:
                self.launch_fresh(name, row, self.fresh_text(role), f"fresh {name} after idle: work waits", events)
            return True
        if state == "failed":
            self.event(name, f"{name} failed", events)
            return True
        if state == "blocked":
            return self.blocked(name, row, sid, events)
        self.blocked_since.pop(name, None)
        ordered = self.cap_rule(name, row, sid, stats, events)
        if ordered is not None:
            return ordered  # False: the order waits for send_due() in this round, before waiting() may supersede it
        if name in self.pending:
            return self.waiting(name, row, role, events)
        if self.wake_orders(name, row) and self.packless(name, sid):  # never a resume without the pack (2026-11-02)
            self.launch_fresh(
                name, row, self.fresh_text(role), f"fresh {name}: woken by an order, with its pack", events
            )
            return True
        if not row.get("pid") and self.wake_orders(name, row):
            return False  # send_due() resumes the session with the order, an on-demand agent's too
        if not row.get("pid") and state in ("stopped", "done") and "blocked" not in status.lower():
            return self.revive(name, row, sid, events)
        detail = [state, row.get("status") or "no status", "pid" if row.get("pid") else "no process"]
        if stats:
            detail += [f"context {stats['context'] or 0:,}", f"calls {stats['calls']}", f"output {stats['output']:,}"]
        self.say(name, f"no action ({', '.join(map(str, detail))})")
        return False

    def handoff_note(self, name, row, role, events):
        """A new note from the agent's session starts a fresh session; True when it did, or when the agent's
        `work_check` found nothing to take (the session is stopped and the note kept as the role's `idle`, an on-demand
        agent's not; the round's other acts wait)."""
        path = self.run / f"handoff-{role}.md"
        note = first_line(path)
        if not note.startswith("HANDOFF") or note == self.seen.get(name):
            return False
        self.seen[name] = note
        if self.note_from(path, row):
            # a note that answers the watcher's own hand-over order launches unchecked: it may come mid-unit
            if name not in self.pending and self.agents[name].get("work_check"):
                waits, last = self.work_check(name)
                if not waits and not self.wake_orders(name, row):  # an order waiting for it is work to take now
                    self.tell(name, f"idle {name}: nothing to take ({last})")
                    if row.get("id"):  # R6: a session left live would wake on a waiter or a message, past any cap
                        self.stop_session(name, row)
                    if not self.agents[name].get("on_demand"):  # C20: only demand() launches an on-demand agent
                        self.idle[name] = note
                    return True
            self.launch_fresh(name, row, self.fresh_text(role), f"fresh {name} after note: {note[:60]}", events)
            return True
        self.tell(name, f"note not from {name}: {path.name}")
        return False

    def lane_has_work(self, name):
        """The agent's `final_check` (a command, {run} and {skill} filled, run in the run folder, 60 s at most), at most
        once a round: exit 0 means work of its lane waits although its line 1 is final (a verifier's (code) findings
        after a builder's `STATUS: done`), so it is not final and is revived like any stopped session; exit 3 means
        final; any other exit or a check that cannot run is told and keeps it final, as before the check."""
        checks = getattr(self, "final_checks", {})
        if name not in checks:
            skill = os.path.dirname(os.path.abspath(__file__))
            argv = [self.fill(x, skill=skill) for x in self.agents[name]["final_check"]]
            try:
                r = subprocess.run(argv, capture_output=True, text=True, timeout=60, cwd=self.run, check=False)
                lines = [x.strip() for x in f"{r.stdout}\n{r.stderr}".splitlines() if x.strip()]
                last = " ".join(lines[-3:]) if lines else "no output"
                if r.returncode not in (0, 3):
                    self.tell(name, f"final_check failed (exit {r.returncode}): {last}")
                elif r.returncode == 0:
                    self.tell(name, f"final, but its lane has work: {last}")
                checks[name] = r.returncode == 0
            except (OSError, ValueError, subprocess.SubprocessError) as e:
                self.tell(name, f"final_check failed to run: {e}")
                checks[name] = False
            self.final_checks = checks
        return checks[name]

    def work_check(self, name):
        """The agent's `work_check`, run in the run folder with {run} and {skill} (this script's folder) filled:
        (False, its last line) on exit 3, nothing to take, else (True, its last line). Any other exit, a check that
        cannot run and one past 60 s are told and count as work waiting: a broken check never silences a role."""
        check = self.agents[name].get("work_check")
        if not check:  # a reload removed or emptied it: the idle role launches as one without a check
            return True, ""
        skill = os.path.dirname(os.path.abspath(__file__))
        argv = [self.fill(x, skill=skill) for x in check]
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=60, cwd=self.run, check=False)
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            self.tell(name, f"work_check failed to run: {e}")
            return True, ""
        lines = [x.strip() for x in f"{r.stdout}\n{r.stderr}".splitlines() if x.strip()]
        last = lines[-1] if lines else "no output"
        if r.returncode not in (0, 3):
            self.tell(name, f"work_check failed (exit {r.returncode}): {last}")
        return r.returncode != 3, last

    def blocked(self, name, row, sid, events):
        """A waiting session is left alone; a permission prompt is cancelled after `permission_wait`, anything else
        that blocks is an exit event. True when it launched or added an event; a wait launches nothing (6i.2)."""
        waiting = row.get("waitingFor")
        if row.get("status") == "busy" and not waiting:
            self.blocked_since.pop(name, None)  # idle at its prompt with a waiter shell running: waiting, not stuck
            self.say(name, "no action (waiting: blocked, busy, no waitingFor)")
            return False
        if self.permission_wait is None:
            self.event(name, f"{name} is blocked ({waiting})", events)
            return True
        since = self.blocked_since.setdefault(name, time.time())
        if time.time() - since < self.permission_wait:
            self.say(name, f"no action (blocked on {waiting}, {time.time() - since:.0f} of {self.permission_wait} s)")
            return False
        self.blocked_since.pop(name, None)
        if waiting == "permission prompt" and row.get("pid"):
            self.act(name, row, self.unblock, f"unblock {name}", events, resume=sid)
        else:
            self.event(name, f"{name} is blocked ({waiting})", events)
        return True

    def cap_rule(self, name, row, sid, stats, events):
        """Past `cap` the session is ordered to hand over: a `handoff` order, which send_due() sends, and then False
        (--check shows v2's stop and resume instead, and then True); None when the rule gives no order."""
        if name in self.pending or not row.get("pid") or not stats or (stats["context"] or 0) <= self.cap:
            return None
        if stats["ordered"]:
            self.pending[name] = stats["ordered"]  # a watcher that ran before this one gave the order
            return None
        self.pending[name] = time.time()
        why = f"cap {name} {stats['context']:,} tokens; ordered to hand over"
        if self.check:
            self.act(name, row, self.order, why, events, resume=sid)
            return True
        self.add_order(name, "handoff", self.order, why)
        return False

    def waiting(self, name, row, role, events):
        """A pending hand-over: a fresh session once `handoff_wait` has passed without a note; True when launched."""
        waited = time.time() - self.pending[name]
        if waited > self.handoff_wait:
            self.launch_fresh(name, row, self.fresh_text(role), f"fresh {name} without a note (timeout)", events)
            return True
        self.say(name, f"no action (ordered to hand over {waited:.0f} s ago; the note may take {self.handoff_wait} s)")
        return False

    def revive(self, name, row, sid, events):
        """A session with no process is resumed with the nudge, at most `nudges` times; an on-demand agent's is not
        (only demand() launches it), which is logged once per session."""
        if self.agents[name].get("on_demand"):
            if self.not_revived.get(name) != sid:
                self.not_revived[name] = sid
                self.tell(name, f"demand {name}: done, not revived")
            return True
        if self.packless(name, sid):  # a dead session's cache is cold anyway: fresh with the pack, not a resume
            self.launch_fresh(
                name, row, self.fresh_text(name.split("/")[-1]), f"fresh {name}: revived with its pack", events
            )
            return True
        count = self.revived.get(name, 0) + 1
        if count > self.nudges:
            self.revived[name] = count
            self.event(name, f"{name} was revived {self.nudges} times; check it", events)
            return True
        output = self.act(name, row, self.nudge, f"continued {name} {row.get('id')}", events, resume=sid, stop=False)
        if output is not None or self.check:
            self.revived[name] = count  # counted once launched: an exit 4 before the launch leaves the count
        return True

    def milestone(self, name, row, role, status, events):
        if not self.milestones or role not in ("builder", "verifier"):
            return False
        if role == "builder":
            m = MILESTONE.match(status)
            if not m or ("builder", int(m.group(1))) in self.switched:
                return False
            n = int(m.group(1))
            self.switched.add(("builder", n))
            text = self.fresh_text("milestone-builder", n=n, next=n + 1)
            self.launch_fresh(name, row, text, f"fresh {name} after milestone Task {n}", events)
            return True
        m = VERIFIED.match(status)
        if not m or not row.get("id"):  # a waiting verifier shows as busy, so there is no idle check
            return False
        due = [t for t in self.milestones if t <= int(m.group(1)) and ("verifier", t) not in self.switched]
        if not due:
            return False
        self.switched.update(("verifier", t) for t in due)
        text = self.fresh_text("milestone-verifier", n=int(m.group(1)))
        self.launch_fresh(name, row, text, f"fresh {name} after milestone Task {max(due)}", events)
        return True

    def unit_end(self, name, row):
        """A new line 1 in the record while the last call is over `handoff_at` (6i.3): a `unit-end` order, once the line
        is `unit_end_grace` seconds old and the session is still over the mark. A note before then starts the fresh
        session, and launched() drops the wait."""
        entry, path = self.roles[name], self.run / self.agents[name]["status"]
        line = first_line(path) if path.exists() else None
        if name in self.pending or entry["unit"] is None or line is None:
            return
        stats = self.transcripts.stats(row.get("sessionId", ""))
        context = (stats or {}).get("context") or 0
        packless = self.packless(name, row.get("sessionId", ""))
        if line != entry["unit"]:
            self.unit_wait.pop(name, None)
            if context > self.handoff_at or packless:
                self.unit_wait[name] = written(path)
                left = self.unit_end_grace - (time.time() - self.unit_wait[name])
                if left > 0:
                    self.tell(
                        name,
                        f"grace {name}: new line 1 at {context:,} tokens; "
                        f"the unit-end order comes in {left:.0f} s unless the note does",
                    )
        since = self.unit_wait.get(name)
        if since is None or time.time() - since < self.unit_end_grace:
            return
        del self.unit_wait[name]
        if context > self.handoff_at:
            self.pending[name] = time.time()
            why = f"unit end {name} {context:,} tokens; ordered to hand over"
            self.add_order(name, "unit-end", self.unit_order, why)
        elif packless:
            self.pending[name] = time.time()
            why = f"unit end {name}: its session lacks the pack; ordered to hand over"
            self.add_order(name, "unit-end", PACK_ORDER + self.lang, why)

    def track_unit(self, name):
        """K1's unit: line 1 of the agent's record (None while there is none), and since when the watcher sees it."""
        entry, path = self.roles[name], self.run / self.agents[name]["status"]
        line = first_line(path) if path.exists() else None
        if line != entry["unit"]:
            entry["unit"], entry["unit_since"] = line, None if line is None else time.time()

    def add_order(self, name, kind, text, why):
        """A new order of the watcher's; send_due() sends it and logs `why`, which the registry leaves out."""
        order = {"msg_id": secrets.token_hex(4), "kind": kind, "text": text, "sent_at": None, "resends": 0}
        self.roles[name]["orders"].append({**order, "acked_at": None, "closed": None, "woken": False, "why": why})

    def open_manager_orders(self, name):
        """The manager's orders to the agent that no ACK, final line or resend limit has closed."""
        return [o for o in self.roles[name]["orders"] if o["closed"] is None and o["kind"] == "manager"]

    def wake_orders(self, name, row):
        """The open manager orders the watcher delivers at once (owner, 2026-11-01): the manager cannot reach an agent
        with no process or one whose line 1 is final, so each such order resumes it once (`woken`); a live working
        agent gets the manager's orders from the manager, and from the watcher only as resends after `ack_wait`."""
        if row is not None and row.get("pid") and not self.line_final(name):
            return []
        return [o for o in self.open_manager_orders(name) if not o.get("woken")]

    def packless(self, name, sid):
        """The agent has a pack of its own (`extra_prompt`) and its session `sid` started without its mark: a resume
        would go on without the pack for the rest of the session's life (owner, 2026-11-01)."""
        own = self.agents[name].get("extra_prompt")  # the lane's own pack; a run's shared one keeps the resume rule
        return bool(own and sid and not self.transcripts.head_has(sid, own["mark"]))

    def line_final(self, name):
        """Line 1 of the agent's record starts with its `final`, whatever the open orders say."""
        return first_line(self.run / self.agents[name]["status"]).startswith(self.agents[name]["final"])

    def order_text(self, name, o):
        """An order's prompt: its text, the wake line when line 1 is final and it is the manager's, its Order line."""
        wake = o["kind"] == "manager" and self.line_final(name)
        record = self.run / self.agents[name]["status"]
        middle = f"{self.fill(WAKE_LINE, msg_id=o['msg_id'], record=record)}\n\n" if wake else ""
        return f"{o['text']}\n\n{middle}{self.order_line(name, o['msg_id'])}"

    def order_line(self, name, msg_id):
        """K3's Order line: the ACK goes to the agent's record, named by its absolute path."""
        return self.fill(ORDER_LINE, msg_id=msg_id, record=self.run / self.agents[name]["status"])

    def send_due(self, name, row, events):
        """The agent's due orders in one launch (6j): the new ones, and a resend of one without ACK after `ack_wait`
        while `ack_resends` allows; after the last resend it is closed `no ack`, an exit event. Nothing moves while the
        row is blocked."""
        if not row.get("sessionId") or row.get("state") == "blocked":
            return
        now, due, lines, wake = time.time(), [], [], self.wake_orders(name, row)
        for o in self.roles[name]["orders"]:
            if o["closed"] or (name in self.pending and o["kind"] not in ("handoff", "unit-end")):
                continue  # while a hand-over is pending, only its own order moves
            if o["sent_at"] is None:
                due.append(o)
                lines.append(o.get("why") or f"{o['kind']} {name} {o['msg_id']}")
            elif o in wake:
                due.append(o)
                lines.append(f"woke {name} with order {o['msg_id']}")
            elif now - o["sent_at"] >= self.ack_wait and o["resends"] < self.ack_resends:
                due.append(o)
                lines.append(f"resent {o['msg_id']} to {name} ({o['resends'] + 1} of {self.ack_resends})")
            elif now - o["sent_at"] >= self.ack_wait:
                o["closed"] = "no ack"
                self.event(name, f"no ack {name} {o['msg_id']} after {o['resends']} resends", events)
        if not due:
            return
        prompt = "\n\n".join(self.order_text(name, o) for o in due)
        if self.act(name, row, prompt, lines[0], events, resume=row["sessionId"], stop=bool(row.get("pid"))) is None:
            return
        for o in due:
            o["resends"] += 0 if o["sent_at"] is None or o in wake else 1
            o["sent_at"], o["woken"] = time.time(), o["woken"] or o in wake
        for line in lines[1:]:
            log(line)

    def launch_fresh(self, name, row, text, why, events):
        """A fresh session (6k): its prompt carries the agent's open manager orders; the watcher's are superseded."""
        orders = [] if self.check else [o for o in self.roles[name]["orders"] if o["closed"] is None]
        manager = [o for o in orders if o["kind"] == "manager"]
        prompt = text + "".join(f"\n\n{o['text']}\n\n{self.order_line(name, o['msg_id'])}" for o in manager)
        if self.act(name, row, prompt, why, events) is None:
            return
        for o in orders:
            if o["kind"] == "manager":
                o["sent_at"], o["resends"], o["woken"] = time.time(), 0, True
            else:
                o["closed"] = "superseded"

    def event(self, name, text, events):
        events.append(text)
        self.say(name, f"would exit {text}")

    def act(self, name, row, prompt, why, events, resume=None, stop=True):
        """Stop the session (when it has an id and `stop`) and launch `prompt`; with --check, say what would be run.
        Returns what the launch printed, None when nothing was launched."""
        changed = self.changed()
        if changed:
            if not self.check:
                log(f"control file changed: {changed}")
                raise Exit(4)
            self.changed_file = changed
            self.say(name, f"{why}: would exit control file changed: {changed}")
            return None
        if resume and "pack" in self.config and self.transcripts.head_has(resume, PACK_MARK):
            self.event(name, f"{name} started with a startup pack, which this watcher does not build", events)
            return None
        argv = self.command(name, prompt, resume)
        if self.check:
            steps = [f"would stop {row['id']}"] if stop and row and row.get("id") else []
            steps.append(f"would {'nudge' if prompt == self.nudge else 'launch'} {self.shown(name, argv)}")
            self.say(name, f"{why}: {'; '.join(steps)}")
            return None
        if stop and row and row.get("id"):
            self.stop(row["id"])
        changed = self.changed()  # once more, right before claude reads the settings file: no window after the stop
        if changed:
            log(f"control file changed: {changed}")
            raise Exit(4)
        r = subprocess.run(["claude", *argv], cwd=self.agents[name]["cwd"], capture_output=True, text=True, check=False)
        output = r.stdout + r.stderr
        log(why, "|", output.strip()[-80:])
        self.launched(name, output, fresh=resume is None)
        return output

    def stop(self, job):
        """`claude stop <job>`, remembered with its round: the copies check skips that row this round and the next."""
        subprocess.run(["claude", "stop", job], capture_output=True, text=True, check=False)
        self.stopped[job] = self.round_no

    def stop_session(self, name, row):
        """Stop the row's session with no launch after it, as act() stops one; with --check, say it."""
        if self.check:
            self.say(name, f"would stop {row['id']}")
        else:
            self.stop(row["id"])

    def launched(self, name, output, fresh):
        """What a launch printed (6k): a fresh session's job id, a resume's new job id, or a copy, which is kept as the
        agent's session while the original, whose stop may still be running, is stopped once more."""
        entry, job = self.roles[name], JOB.search(output)
        if fresh:
            entry.update(job_id=job.group(1) if job else None, session_id=None, launched_at=time.time())
            self.pending.pop(name, None)
            self.unit_wait.pop(name, None)
            self.idle.pop(name, None)
        elif job:
            entry["job_id"] = job.group(1)
        copy = COPY.search(output)
        if copy:
            entry["job_id"], entry["session_id"] = copy.group(1), None
            log(f"copy {name} {copy.group(1)} kept")
            original = ORIGINAL.search(output)
            if original:
                self.stop(original.group(1))

    def command(self, name, prompt, resume=None):
        a, own = self.agents[name], self.extras.get(name)
        extra = []
        if own and (resume is None or self.transcripts.head_has(resume, own["mark"])):
            extra = ["--append-system-prompt-file", str(self.run / own["file"])]
        return [
            *(["--resume", resume] if resume else []),
            "--name",
            name,
            "--add-dir",
            *a["add_dirs"],
            *self.common,
            "--settings",
            str(
                self.run / a["settings"]
            ),  # the path, not the text: the model and the denies stay out of argv (owner, 2026-10-29)
            *extra,
            "--bg",
            prompt,
        ]

    def shown(self, name, argv):
        """The command as a shell line, the settings text shown as the file it is read from."""
        a = self.agents[name]
        words = [
            f'"$(cat {shlex.quote(str(self.run / a["settings"]))})"' if before == "--settings" else shlex.quote(arg)
            for before, arg in zip(["claude", *argv], argv)
        ]
        return f"(cd {shlex.quote(str(a['cwd']))} && claude {' '.join(words)})"

    def briefs(self):
        """A changed or new brief is reloaded (6f): its hash is stored, and every role with a session whose texts name
        it gets a `reload` order (a removed brief is changed()'s exit 4)."""
        fixed = self.fixed_files()
        for path in [path for path in self.hashes if path not in fixed]:
            digest = sha256(path)
            if digest is None or digest == self.hashes[path]:
                continue
            self.hashes[path] = digest
            log(f"control file reloaded: {path.name}")
            text = self.fill(self.reload_order, file=path, time=time.strftime("%Y-%m-%d %H:%M", time.gmtime()))
            for name, row in self.matched.items():
                if row and row.get("sessionId") and not self.final(name) and path in self.named(name):
                    self.add_order(name, "reload", text + self.lang, f"reload {name} {path.name}")

    def inbox(self):
        """The manager's orders (6g, K4): a line of `orders.jsonl` with a new msg_id for an agent of the config becomes
        its open order, sent at its `at`. The manager only appends to the file; the watcher never writes it."""
        try:
            lines = (self.registry.parent / "orders.jsonl").read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        known = {o["msg_id"] for entry in self.roles.values() for o in entry["orders"]}
        for line in lines:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if not isinstance(d, dict) or not all(isinstance(d.get(k), str) for k in ("msg_id", "agent", "text")):
                continue
            if d["agent"] in self.agents and d["msg_id"] not in known:
                known.add(d["msg_id"])
                order = {"msg_id": d["msg_id"], "kind": "manager", "text": d["text"], "sent_at": stamp(d.get("at"))}
                self.roles[d["agent"]]["orders"].append(
                    {**order, "resends": 0, "acked_at": None, "closed": None, "woken": False}
                )

    def state(self, name, row):
        """K1's state: done (final), blocked (the row or line 1 says so), running (a row with a pid) or stopped."""
        if self.final(name):
            return "done"
        line = first_line(self.run / self.agents[name]["status"])
        if (row and row.get("state") == "blocked") or "blocked" in line.lower():
            return "blocked"
        return "running" if row and row.get("pid") else "stopped"

    def usage(self, name):
        """Calls and cost (K6) over every session of the agent, each call once: one `seen` for all their transcripts (a
        resumed session's begins with the calls of the one it resumes). Kept while the files are unchanged."""
        files = []
        for path in (path for sid in self.roles[name]["session_ids"] for path in sorted(ur.transcripts(sid))):
            try:
                st = os.stat(path)
            except OSError:
                continue
            files.append((path, st.st_size, st.st_mtime_ns))
        if self.usage_cache.get(name, (None,))[0] != files:
            seen, calls, cost = set(), 0, 0.0
            for path, _, _ in files:
                try:
                    for d in ur.calls(path, seen):
                        usage, price = d["message"]["usage"], ur.PRICE[ur.family(d["message"].get("model"))]
                        cost += sum((usage.get(k) or 0) * p for k, p in zip(PRICED, price)) / 1_000_000
                        calls += 1
                except OSError:
                    continue
            self.usage_cache[name] = (files, (calls, round(cost, 6)))
        return self.usage_cache[name][1]

    def entry(self, name):
        """K1's object for one agent: the restored fields as they stand, the others computed now (6l)."""
        a, e, row = self.agents[name], self.roles[name], self.matched.get(name)
        stats = self.transcripts.stats(e["session_id"]) if e["session_id"] else None
        lane, settings = self.table.get(name, (None, a["settings"]))
        calls, cost = self.usage(name)
        orders = [
            {**{k: o[k] for k in ORDER_KEYS}, "sent_at": utc(o["sent_at"]), "acked_at": utc(o["acked_at"])}
            for o in e["orders"]
        ]
        return {
            "role": name.split("/")[-1],
            "lane": lane,
            "settings": settings,
            "record": str(self.run / a["status"]),
            "unit": e["unit"],
            "unit_since": utc(e["unit_since"]),
            "state": self.state(name, row),
            "row_state": row.get("state") if row else None,
            "waiting_for": row.get("waitingFor") if row else None,
            "job_id": e["job_id"],
            "session_id": e["session_id"],
            "session_ids": e["session_ids"],
            "launched_at": utc(e["launched_at"]),
            "context": stats["context"] if stats else None,
            "calls": calls,
            "cost_usd": cost,
            "revivals": self.revived.get(name, 0),
            "handoff_since": utc(self.pending.get(name)),
            "idle": self.idle.get(name),
            "first_seen": {ident: utc(t) for ident, t in e["first_seen"].items()},
            "orders": orders,
        }

    def write_registry(self):
        """K1's object, written whole: a temporary file in the registry's folder, moved over the old one (6l)."""
        data = {
            "version": 1,
            "run_dir": str(self.run),
            "written_at": utc(time.time()),
            "watcher": {
                "pid": os.getpid(),
                "started_at": utc(self.started_at),
                "round": self.round_no,
                "interval": self.interval,
            },
            "roles": {name: self.entry(name) for name in self.agents},
        }
        temporary = self.registry.with_name(f".{self.registry.name}.tmp")
        try:
            self.registry.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            os.replace(temporary, self.registry)
        except OSError as e:
            log(f"registry not written: {e}")

    def restore(self):
        """The fields K1 restores, from the registry an earlier watcher of this run wrote (6c); a missing file or one
        that is no version 1 object restores nothing."""
        try:
            data = json.loads(self.registry.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        roles = data.get("roles") if isinstance(data, dict) and data.get("version") == 1 else None
        if not isinstance(roles, dict):
            return
        for name in self.agents:
            saved, entry = roles.get(name), self.roles[name]
            if not isinstance(saved, dict):
                continue
            for key in ("job_id", "session_id", "unit"):
                entry[key] = saved[key] if isinstance(saved.get(key), str) else None
            ids, orders = saved.get("session_ids"), saved.get("orders")
            entry["session_ids"] = [x for x in ids if isinstance(x, str)] if isinstance(ids, list) else []
            entry["launched_at"], entry["unit_since"] = stamp(saved.get("launched_at")), stamp(saved.get("unit_since"))
            entry["orders"] = [o for o in map(restored, orders if isinstance(orders, list) else []) if o]
            self.revived[name] = saved["revivals"] if number(saved.get("revivals")) else 0
            if stamp(saved.get("handoff_since")) is not None:
                self.pending[name] = stamp(saved.get("handoff_since"))
            if isinstance(saved.get("idle"), str):  # re-checked, not taken as a new note
                self.idle[name] = self.seen[name] = saved["idle"]
            seen = saved["first_seen"] if isinstance(saved.get("first_seen"), dict) else {}  # none from older watchers
            entry["first_seen"] = {ident: t for ident, v in seen.items() if (t := stamp(v)) is not None}
            opened = ",".join(o["msg_id"] for o in entry["orders"] if o["closed"] is None) or "-"
            log(f"registry: {name} revivals={self.revived[name]} orders={opened}")

    def start(self):
        """A run's start (6c, K2): the launch table's rows that name no agent, then the registry read back."""
        for name in self.unwatched:
            log(f"launch table: {name} is not watched")
        self.restore()

    def launch_table(self):
        """K2: {agent: (lane, settings)} from the first table of `<run_dir>/_launch.md` whose header cells include role,
        lane and settings (spaces and backticks stripped), and the role cells that name no agent of the config."""
        try:
            lines = (self.run / "_launch.md").read_text(encoding="utf-8").splitlines()
        except OSError:
            return {}, []
        table, unwatched, header, inside = {}, [], None, False
        for line in lines:
            if not line.lstrip().startswith("|"):
                if header:
                    break  # the end of the launch table
                inside = False
                continue
            cells = [cell.replace("`", "").replace(" ", "") for cell in line.strip().strip("|").split("|")]
            if not inside:  # a table's first line is its header
                inside, header = True, cells if {"role", "lane", "settings"} <= set(cells) else None
            elif header and not all(set(cell) <= set("-:") for cell in cells):
                values = dict(zip(header, cells))
                role = values.get("role", "")
                if role in self.agents:
                    table[role] = (values.get("lane"), values.get("settings"))
                elif role:
                    unwatched.append(role)
        return table, unwatched

    def add_manager_order(self, agent, text):
        """--order (K4): the order goes to the inbox beside the registry, and the prompt to send is printed."""
        if agent not in self.agents:
            raise ConfigError(f"no agent {agent}")
        if not text.strip():
            raise ConfigError("empty order")
        msg_id = secrets.token_hex(4)
        self.registry.parent.mkdir(parents=True, exist_ok=True)
        line = {"msg_id": msg_id, "agent": agent, "text": text, "at": utc(time.time())}
        with open(self.registry.parent / "orders.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
        print(f"order {msg_id} {agent}\n{text}\n\n{self.order_line(agent, msg_id)}", flush=True)
        return 0


def report(watcher):
    """--check: one round, then the decision per agent and the exit a run would take."""
    events, budget = watcher.round()
    for name in watcher.agents:
        print(f"{name}: " + "; ".join(watcher.said.get(name, ["no decision"])))
    if watcher.changed_file:
        print(f"would exit 4: control file changed: {watcher.changed_file}")
    if budget:
        print("would exit 3: " + "; ".join(budget + events))
    elif events:
        print("would exit 0: " + "; ".join(events))
    elif not watcher.changed_file:
        print(f"would sleep {watcher.interval} s and go on")
    return 0


def watch(watcher, rounds):
    """The rounds of a run after its start; the registry is written once more when the watcher returns (6l)."""
    watcher.start()
    code = 1
    try:
        for _ in range(rounds):
            events, budget = watcher.round()
            for line in budget:
                log(line)
            if events:
                log("; ".join(events))
            if budget or events:
                code = 3 if budget else 0
                break
            time.sleep(watcher.interval)
    except Exit as e:
        code = e.code
    watcher.write_registry()
    if code == 1:
        print("watcher stopped after its last round", flush=True)
    return code


def main(argv=None):
    ap = argparse.ArgumentParser(description="Watch a SpecAgent pipeline; the module docstring has the details.")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="one round: print the decision per agent, launch nothing")
    mode.add_argument(
        "--order",
        nargs=2,
        metavar=("AGENT", "TEXT"),
        help="append an order for AGENT to the inbox and print its prompt; runs no session",
    )
    ap.add_argument("config")
    ap.add_argument("rounds", nargs="?", type=int, default=240)
    args = ap.parse_args(argv)
    try:
        watcher = Watcher(args.config, check=args.check)
        if args.order:
            return watcher.add_manager_order(*args.order)
    except ConfigError as e:
        print(f"config error: {e}", flush=True)
        return 2
    return report(watcher) if args.check else watch(watcher, args.rounds)


if __name__ == "__main__":
    sys.exit(main())
