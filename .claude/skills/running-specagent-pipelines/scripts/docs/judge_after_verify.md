# `judge_after_verify.sh` — the judge, once, after every task is verified
```
bash scripts/judge_after_verify.sh <agents-judge.json> <checkout> <record-file>...
```
Waits until line 1 of every record file (in the config's `run_dir`) is `STATUS: done`, polling every `JUDGE_POLL`
seconds (default 300), logs `HH:MM main: all <n> STATUS lines done; judge starts in <JUDGE_DELAY> s` to
`<run_dir>/_watch.log` and sleeps `JUDGE_DELAY` seconds (default 600; the pipeline's watcher exits by itself). Then it
adds a detached worktree at the checkout's HEAD in the agent's `cwd` (unless that folder exists), makes
`<run_dir>/scratch/judge`, launches the config's one agent there once (`claude --name <name> --add-dir <add_dirs>
<common> --settings <the settings file's text> --bg <prompt>`), logs `HH:MM main: <name> launched at <HEAD> in <cwd>
(exit <code>)`, and runs `watch_agents.py` on the config, its output on stdout and appended to `_watch.log`. It writes
only `_watch.log`, the worktree and the scratch folder; `example/agents-judge.json` is such a config. Exit 2: fewer
than three arguments, or a config that does not name exactly one agent (nothing is done); a failed launch: its code;
otherwise the watcher's code.
