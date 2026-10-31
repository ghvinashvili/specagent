# `make_pack.py` — a role's startup pack
```
python3 -I scripts/make_pack.py [--no-note] <run-dir>/_packs.json [<role> ...]
```
Packs are off since 2026-10-25 (an earlier run's trial; the numbers are in `references/context-and-cost.md`) and
`watch_agents.py` refuses `pack: true`; this builds them to measure again. It writes `<run-dir>/_pack-<role>.md` for
each role named (every role of the config, in its order, when none is): the role's files of the run folder in full
and the `sections` of the `lessons` file, with no time stamp, and only when the text changed; it prints
`_pack-<role>.md: <n> KB` per role. The config (`example/packs.json` is one): `roles` (role → file names in the run
folder), `name` (default: the run folder's name), `lessons` (default `lessons.md`), `sections` (default "Read first"
and "Known error classes"); keys that start with `_` are comments. Exit 0; 2 for a missing role, file, lessons file or
section (one stderr line; no pack is written).

`--no-note` leaves every file named `handoff-*.md` out of the packs: the rule "stable first, unique last"
(`references/context-and-cost.md`). A hand-over note is unique to one session, so a pack that held it would differ
at every start, and a cached prefix is only as long as what is byte-identical; the pack stays the same from one
session of the role to the next, and the note is read after it, as the last item of the launch prompt. The pack's
first paragraph then says so. The hand-over rule (`_handoff-rule.md`) is the same for every session and stays. With the
option a note need not exist when the pack is built; a role left with no file is exit 2.
