---
title: "Pipeline economy: a measured estimate, three model classes, and the open items closed"
type: decision
status: draft
updated: 2026-10-30
created: 2026-10-30
audience: [all]
decided: 2026-10-30
by: owner
why: the obsidian-ingest run of 2026-10-30 was launched on an estimate of $15-25 made by feel and cost $43.01; a duplicate manager chat (20:50-22:00) launched a second grantsdaily run unseen; a fresh builder read about 150k tokens before its first edit and hit the cap 14 minutes in; four small open items of the run's tools stayed open
would_change_if: the economy row of the first run after the merge shows escaped above 0 for a shape that ran in the mechanical class; that shape goes back to the judgment class and the rule that failed is revised against the row
decision_status: decided
scope: global
tags:
  - decision
---
# Pipeline economy: a measured estimate, three model classes, and the open items closed

Six rules of the SpecAgent pipeline, R5 to R10 of the pipeline-economy spec, follow the four of
[Unit 1](pipeline-economy-hand-over-units-checks-facts-pack.md): a launch's price comes from a measurement and from a look
at the live sessions, the model class follows the work, and the four open items of the ingest run are closed. One more
order of the owner, which came after the spec, is the last item: no commit of a role names a model.

- **A launch's estimate comes from a measurement.** The `Estimate:` line of a launch file names the last run's
  measurement page (`measurements/<date>-<run>.md`), its dollars per session and its start-up read
  (`start-up read <t>k tokens`, the median of `startup_report.py`). `preflight.py` `ESTIMATE` (`:48-56`) fails a line
  without any of the three, for example `Estimate: names no start-up read`, and `example/launch.md:15` and
  `references/preflight-and-capacity.md:38` ask for all three. The spec named the first two; the third comes from the
  run's `lessons.md`: a fresh builder that read its whole note, its brief and the spec's sections was near 150k before its
  first edit. The ingest run's guess was $15-25 for a run that cost $43.01.
- **A live check runs before the launch.** `preflight.py check` lists `claude agents --json --all` (`check_live`,
  `:391-417`). A busy session with a pid that is outside the run's agent names and `<project>/` prefix and works in the
  checkout or a worktree of `.git/worktrees/*/gitdir` fails the check, unless a `Live:` line of the launch file names it
  (`Live: <name>, <name> — <what each is>`, written by the manager after it reads the list: `example/launch.md:5`). A
  listing that fails, or is no JSON list, is a FAIL, not an empty list. The duplicate manager chat of 20:50-22:00 had
  launched a second grantsdaily run unseen.
- **The model class follows the work; the effort is never lowered.** The class text names three classes, by the owner's
  order of 2026-10-30: specification (the spec writer; a spec's mistake is the most expensive in a run), judgment
  (planner, plan fixer, critic, verifier, judge, writer for readers) and mechanical (a builder checked by a verifier,
  extraction, conversion, data collection). The spec writer's model, a dated exception on 2026-10-29
  ([the page](the-spec-writers-model-is-a-dated-exception.md)), is now this class. The builder is no longer a fixed
  judgment role (`SKILL.md:19`; `references/launch.md:9-14` and `example/README.md:89` say the same),
  `references/choosing-roles-and-skills.md:24-26` stands as it was (in doubt, the judgment class), and every role keeps
  the effort max, because the cost is context re-reads, not effort. No file of the skill names a model
  (`scripts/tests/test_skill_md.py:68-73`): the launch table's message alone names them, and the classes' prices stay the
  manager's, in no file, so the saving is read as cost per unit in the economy row.
- **The night tick commits the renewal.** `ops/night-tick.sh:19-39` (`commit_renewal`): after `--refresh` exits 0, on
  `main`, when `git status --porcelain -- wiki/meta/ledgers wiki/log.md wiki/hot.md` lists a change, it runs
  `git commit -m "chore(wiki): renew the due sources (night tick)" -- <those paths>`, so a file staged for something else
  stays staged and out of it. On another branch, in no git repository or when git refuses, it logs
  `renewal not committed: <reason>` and the fire goes on (`docs/loops/README.md:95`). No manual step is left, and no
  dirty checkout blocks a merge that touches `wiki/log.md`. `packages/harness/tests/test_night_tick.py -k renewal`: 5
  tests, red first, with a mutation check.
- **A finding's cause may be `(brief)`.** In a run without a planner the fix of a finding can sit in a brief or a rule,
  not in the code. `scripts/check_formats.py:61` (`CAUSE`) accepts it and its message names four causes (`:229-231`),
  `scripts/findings_report.py:34` counts a `brief` row, and `example/verifier-assignment.md:27-28,49-52` and
  `scripts/docs/check_formats.md:8-9` add it as a clause beside the pinned `(code)|(plan)|(spec)` pattern. `SKILL.md`
  stays as it is, because its pipeline has a planner.
- **A lint answer without its counts is an error.** `ops/obsidian-ingest.py:647-658` (`lint`): an answer without
  `summary.category_counts` stops with a message naming the key; the default `{}` let such an answer pass as a clean
  vault. `{"summary": {"category_counts": {}}}` and plugin 3.0.1's answers pass as before
  (`ops/tests/test_obsidian_ingest.py -k lint_answer`: 6 tests, the core replaced, no plugin needed).
- **The supersede loop is recorded, not fixed.** `docs/architecture/knowledge.md:34-35` keeps it as "To check (plugin)":
  after a revert and `--supersede` two sources name each other in `supersedes`; the plugin checks only the id's form, so a
  tool that walks the chain must stop at an id it has seen.
- **No commit of a role names a model.** The owner's order of 2026-10-30 (the run's `lessons.md`): a commit on
  `feat/readme` (83bf336) ended with Claude Code's default `Co-Authored-By: <model name> <noreply@anthropic.com>`, and a
  role is blind to models. Every role's settings carry `"includeCoAuthoredBy": false` (the seven
  `example/*-settings.json`, `references/launch.md:9-16`, `references/sandbox-and-blindness.md` "The commit trailer"),
  and `preflight.py:205-228` (`check_blind`) fails a file where the key is absent, `true` or no boolean, for every role,
  sandboxed or not (`scripts/tests/test_preflight.py -k include_co_authored_by`: one test, five wrong files, red first).
  Checked in Claude Code 2.1.314: a valid `attribution` object (one with a `commit` or a `pr`) wins, else the key at
  `false` blanks the commit and PR text. The key is marked deprecated for `attribution` and still works, so the
  examples carry no `attribution` object, and the check reads the file, not the runtime. The verifier's V1 found the
  check held only the key: `{"pr": ""}` brings the default trailer back with the key at `false`, so `check_blind` also
  fails a file with an `attribution` key, whatever it holds (`-k attribution_key`: one test, six values, red first).
  The run generator's templates (`_control/make_run.py`) are the main session's to change.

Quality is guarded, not traded: the estimate line's other checks stay, a shape that lets one finding escape in the
mechanical class goes back to the judgment class (escaped, the last cell of the economy row, is the number that must stay
0), the night tick's commit holds only its three paths, the other causes of a finding read as before, and plugin 3.0.1's
answers pass as they did. Only the model class can lower a cost, and its prices are in no file; the first run after the
merge (grantsdaily) is read by the economy row.

## Record and source
- [The spec, R5-R10](../../specs/003-pipeline-economy/spec.md)
- The skill's files, `.claude/skills/running-specagent-pipelines/`: `scripts/manager/preflight.py:48-56,61-63,391-417`,
  `example/launch.md:5,15`, `references/preflight-and-capacity.md:29-38`, `SKILL.md:19`, `references/launch.md:9-14`,
  `example/README.md:89`, `scripts/tests/test_skill_md.py:68-107`, `scripts/check_formats.py:61,229-231`,
  `scripts/findings_report.py:34`, `example/verifier-assignment.md:27-28,49-52`, `scripts/docs/check_formats.md:8-9`
- The checkout's files: `ops/night-tick.sh:19-39`, `docs/loops/README.md:95`, `ops/obsidian-ingest.py:647-658`,
  `docs/architecture/knowledge.md:34-35`
- Unit 2 of the pipeline-economy run: commits 7ab12f6 (R5, the live check), 0685f1b (R7), d9458f4 (R8), 3db745f (R9,
  R10), e11e83a (R6's three classes) and the unit's docs commit
- Task 3 of the run (the owner's order on the commit trailer): `scripts/manager/preflight.py:205-228`,
  `example/*-settings.json`, `references/sandbox-and-blindness.md`, `scripts/tests/test_preflight.py:1103,1119`,
  `scripts/tests/test_skill_example.py:266`, `scripts/tests/test_skill_md.py:110`; its own commit and the V1 fix
