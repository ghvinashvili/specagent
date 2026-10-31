# `collect_run.py` — a finished run's leftovers, removed only after its record is checked as saved
```
python3 -I scripts/collect_run.py RUN_DIR --repo DIR --plan PATH --kept PATH [--kept PATH ...] [--main BRANCH]
    [--final SHA ...] [--worktree DIR ...] [--branch NAME ...] [--also PATH ...] [--agents FILE] [--jobs DIR]
    [--history FILE] [--apply] [--yes DIGEST]
```
The manager runs it after the run, never a role: it reads the run's agents file first (`--agents`, default
`RUN_DIR/_control/_agents.json`), which every role's settings deny. It lists what the run owns, in this order, with
what each deletion loses: the worktrees of `--repo` whose path is an agent's `cwd` or a `--worktree`
(`would remove worktree <path> (branch <name>, HEAD <sha7>): loses …`), their branches and each `--branch`
(`would delete branch <name> at <sha7>: loses …`), `RUN_DIR/scratch`, the `<id>` folder under `--jobs` (default
`~/.claude/jobs`) of each finished session whose `claude agents --json --all` row has an agent's `name` and `cwd`, and
each `--also` path (eval result copies, preview copies); then `keep <path>` for the record files, `lessons.md` and each
`--kept`. The save check refuses (`refused: <reason>`, then `nothing removed: <n> refusals`, exit 3) when a record's
line 1 is not `STATUS: done`; `check_formats.py --repo` fails; an item of `## Lessons from this run` has no
`(skill: <sha>)` or `(skill: none)` mark, or its commit is not in `--main` (default `main`); a `--kept` item is missing
or lies inside a deletion; an `--also` path lies in the run folder outside `scratch/`;
a build log's `Task N: done — <sha>` or a `--final` is not an ancestor of `--main`, or none
is named; an item under a `Deferred` heading of the `--plan` files on `--main`, outside fenced code, is not in the
tracker (it names a `TD-` row there, or a row quotes its key); a run worktree has uncommitted paths (an empty
untracked path, such as the sandbox's 0-byte mount points, is not one: it is listed apart and removed right before
its worktree); a run branch or
detached HEAD has commits not in `--main`; or a session of the run is still running. Otherwise it prints
`total: …; digest <12 hex>; nothing removed without --apply`. `--apply --yes <digest>` removes the list the owner said
yes to (a list that changed needs a new yes); once `--history` (default `RUN_DIR/../collect-history.jsonl`) holds three
runs applied with a yes, `--apply` alone runs by the standing rule. Each apply appends to `RUN_DIR/collected.md` and
adds a history line. A `scratch` or job folder that is a symlink is reported (`skipped <path>: a symlink`) and never
followed. Exit 0 listed or removed; 1 a removal failed (the rest continues); 2 a usage error, a missing run folder, an
unreadable agents file, an unknown `--main` or a failed listing (one stderr line); 3 refused.
