# `replay_cases.py` — replay cases from findings
```
python3 -I scripts/replay_cases.py <run-dir> --repo <checkout> --out <dir> [--try]
```
For every `#### V<n>` of verify.md and `#### J<n>` of judge.md that records a shell command, its output and a commit,
it writes `<out>/<id>/task.yaml` (the checkout's eval fields) and `<out>/<id>/grader.sh`: `sh grader.sh before`
passes when the recorded output appears at the commit before the fix, `sh grader.sh fix` when it does not appear at
the fix (a second argument names another sha). `<out>/index.md` lists the cases and every other section with its
reasons (no command, a placeholder, not a read-only tool, no recorded output, no sha, …). Only read-only tools on
paths inside the checkout are replayed; `--try` runs each grader once and records the result, and a case replays only
when every grader passes. It writes under `<out>` only. The graders are `type: "shell"`, run by hand. A finding can
be replayed only when its record holds a read-only command and that command's literal output. Exit 2 when the run
folder, the checkout or `<out>` is refused.
