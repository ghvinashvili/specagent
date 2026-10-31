# `clean_jobs_tmp.py` — the tmp folders of finished background jobs
```
python3 -I scripts/clean_jobs_tmp.py [--jobs DIR] [--hours N] [--apply]
```
A background job keeps its `tmp` folder under `~/.claude/jobs/<id>/` after it ends (an earlier run's jobs filled about
90 GB). From `claude agents --json --all` it takes the finished jobs (an 8-hex-digit `id`, no `pid`, state `done`,
`failed` or `stopped`, and no row with a `pid` shares its `sessionId`) and prints `would remove <path> (<state>,
<name>, <MB> MB)` per `tmp` folder, in id order, then `total: <n> folders, <MB> MB; nothing removed without --apply`.
`--apply` removes those folders and nothing else (`removed <path> (…)`; `state.json` and `timeline.jsonl` stay).
`--jobs` is the jobs folder (default `~/.claude/jobs`); `--hours` leaves a job whose `state.json` changed less than N
hours ago (default 24); a `tmp` that is a symlink is reported (`skipped <path>: a symlink`) and never followed. Exit 0;
2 for a missing jobs folder or a failed listing (one stderr line); 1 when a removal failed.
