# `startup_report.py` — the start-up cost per session
```
python3 -I scripts/startup_report.py [--prefix demo/] [--since 2026-10-22] [--threshold 60000]
```
The start-up cost is the context size of a session's first write call (an Edit, a Write, or a Bash command with `git
commit`, `>>` or `tee -a`). Per agent: the fresh sessions measured, those that never wrote, the resumed ones (counted,
not measured), the median and the maximum, and how many are over the threshold; then each session over it, with the
Bash commands it ran and the files it read (Read paths, deduplicated, at most 12) before its first write. A session
that never wrote is over the threshold when its largest call passed it. It imports usage_report.py's parsing.
