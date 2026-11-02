# `lessons_report.py` — whether a lesson lowers the error it was written for
```
python3 -I scripts/lessons_report.py <run-dir> [<run-dir> ...] [--repo DIR] [--projects DIR] [--transcript FILE]... [--json]
```
Reads the run's `lessons.md` items by section ("Read first", "Known error classes", the classes carried from earlier
runs and the vault, and "Lessons from this run"), each with the finding ids it names as its sources, and every finding
of `critique.md`, `verify.md`, `verify-kb.md` and `judge.md` that names a lessons.md line with `Lesson:` or cites one
as its `Checklist:` item. A citing finding that is not one of the lesson's own sources is a recurrence; a lesson with one
was broken twice (its first break is its source, or an earlier run for a carried class; then a recurrence) and is
listed under `make code (broken twice: …)` (vault a-rule-broken-twice-becomes-code). Finding ids restart in every run, so
only an item of "Lessons from this run" has sources among this run's findings: an id that an item of "Read first" or
"Known error classes" names (`J6 of an earlier judge`) is an earlier run's finding, shown in the sources column and no
exception, and this run's J6 that cites the item is a recurrence. Per run:
the units (`Task N: done` lines of the build logs), the cited lessons with their recurrences per 10 units, the carried
classes broken again per 10 units (the measured effect of what earlier runs and the vault carried in), and the lessons
no finding names, reported as unmeasured. Several runs add one row per lesson text across them. `--transcript` lists
the vault pages a session read. The numbers go onto the run's measurement page with this command (vault
measure-the-effect-of-every-improvement). Exit 2 when a folder has no `lessons.md`.

The held split (`--repo`, the checkout of the run's commits): a recurrence counts only when the session that made the
error held the lesson. The error is the commit of the finding's `## Task N — <sha>` heading; its session is the
commit's `Role-Session: <id>` trailer (the builder briefs ask for it), else the session of the role whose build log
names the commit (`Task N: done|committed — <sha>`, `V<n>: fixed — <sha>`) whose transcript under `--projects`
(default `~/.claude/projects`; first to last timestamp) spans the commit's time; copies of one session, which share
their start, count as one. A lesson of "Read first" or "Known error classes" was held by every session (the pack, the
start-up read); a lesson dated `added <ISO>` was held by a session that started after it, not by one that started
before (it reaches a session at its start; an ACKed order is not read yet). A recurrence whose session or lesson date
is unknown still counts and is listed under `held unknown`; one not held is listed under `not held` and is no
recurrence.
