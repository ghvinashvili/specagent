# `migrate_agents_json.py` — a live run folder to config v2
```
python3 -I scripts/migrate_agents_json.py <run-dir> [--out <file>]    default <run-dir>/_agents-v2.json
```
Reads the folder's `_agents-active.json` (else `_agents.json`) and its watcher copy `_watch_agents.py` (parsed with
ast, never imported: a copy starts watching at import), writes the v2 config, and prints how the copy's behaviour
differs from v2's defaults: `<field>: <default> -> <value>` for numbers, a word diff for texts, `not a literal` for a
value it cannot read. The new config is the only file it writes; `--out` keeps it out of a live run folder. Exit 0
written, 2 an input missing or unreadable (nothing written).

Moving a pipeline to version 2, at its next restart (never while its old watcher runs):
1. `python3 -I scripts/migrate_agents_json.py <run-dir>` and read the printed differences.
2. `python3 -I scripts/watch_agents.py --check <run-dir>/_agents-v2.json`: its decisions must match the last lines
   of the old watcher's log for the same state.
3. Stop the old watcher, then start `python3 -I scripts/watch_agents.py <run-dir>/_agents-v2.json` in the background.
