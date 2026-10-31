# Hazards

The classes of input and timing that broke this repository's work (fix waves 1 and 2, runs of 2026-10-04). The
critic of a plan applies every class that fits a file the plan reads or an input it accepts, with a probe on the
trial; the verifier does the same on the work (`.claude/agents/critic.md`, step 11; `.claude/agents/verifier.md`). A
class the judge finds that a reviewer missed is added here with the run that showed it (`open_questions`:
`critic missed: ...`).

| Class | What to try | Seen |
| --- | --- | --- |
| Missing file | the file the code reads is absent | |
| Empty file | zero bytes; whitespace only | |
| Wrong JSON shape | `{}`, `[]`, `null`, a string, a field of the wrong type | w2: `_pause.json` holding `{}` was set for two commands and unset for four |
| Directory instead of file | a folder under the file's name | w2: `harness pause lift` raised on a folder |
| Deep or huge input | 100 000 nested brackets; a file of 100 MB | w2: RecursionError past the unreadable-run guards |
| Link | a symbolic link out of the root; a link loop; a link a session plants where the harness writes later | w1: a gate read through a link; 2026-10-08: pack.md and `logs/` of a stage were written through a planted link |
| Path out of the root | `..`, an absolute path, `~`, a name with a slash, a name that starts with a dash | w2: `approve` made a folder outside the runs root |
| Spelling of a name | a name git quotes (`-z` reads it as stored), another case on a file system that ignores case, a folder of the same name deeper down | 2026-10-08: `.claude/skills/é/` and `.CLAUDE/settings.json` passed the scope check |
| Two writers at once | another command writes between this one's read and write; the same command twice | w2: a poll undid an escalation answer; a wave split wrote into an aborted run |
| Stopped in the middle | abort, pause or a crash between two steps of one operation | w2: the wave split after an abort |
| Shell spelling | `#` inside a word, a variable, `cd -P`, braces, globs, `eval`, `sh -c`, `python3 -c`, a pipe into `sh` | w1: guards that read the command's text let 27 of 70 spellings through; protect at the boundary instead |
| Closed files | `.env`, `.env.*`, `secrets/**`, key files | w1: the read gate opened files the settings close |
| Code the work runs | a `conftest.py`, a pytest option or a hook the work adds, run by a check that trusts its report | 2026-10-08: a conftest could report a failing given test as passed |
| One job, two owners | the same rule in two places (a flag read, a path checked, a state written) | w2: 7 of 13 reasons |
| Document promise | every sentence a change adds to a document, against the code and a test | w1 and w2: 9 of 27 reasons |
