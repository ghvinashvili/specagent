# `lessons_report.py` — whether a lesson lowers the error it was written for
```
python3 -I scripts/lessons_report.py <run-dir> [<run-dir> ...] [--transcript FILE]... [--json]
```
Reads the run's `lessons.md` items by section ("Read first", "Known error classes", the classes carried from earlier
runs and the vault, and "Lessons from this run"), each with the finding ids it names as its sources, and every finding
of `critique.md`, `verify.md`, `verify-kb.md` and `judge.md` that names a lessons.md line with `Lesson:` or cites one
as its `Checklist:` item. A citing finding that is not one of the lesson's sources is a recurrence; a lesson with one
was broken twice and is listed under `make code (broken twice)` (vault a-rule-broken-twice-becomes-code). Per run:
the units (`Task N: done` lines of the build logs), the cited lessons with their recurrences per 10 units, the carried
classes broken again per 10 units (the measured effect of what earlier runs and the vault carried in), and the lessons
no finding names, reported as unmeasured. Several runs add one row per lesson text across them. `--transcript` lists
the vault pages a session read. The numbers go onto the run's measurement page with this command (vault
measure-the-effect-of-every-improvement). Exit 2 when a folder has no `lessons.md`. Not yet split: whether the session
that made a recurring error held the lesson when it worked (a lesson reaches a session at its start or by an ACKed
order); until it is, a recurrence counts whatever the session's start.
