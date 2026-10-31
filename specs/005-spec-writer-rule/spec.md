# Spec 005 — the spec-writer writes the skeleton, the planner the flesh

Owner's decision, 2026-10-31 01:5x UTC (vault `decisions/global/models-per-role.md`): the specification is short and
Fable writes it; the plan is Opus's; the spec-writer is never used as a planner: it writes the skeleton, the planner puts
the flesh on it. The template must say this itself.

## Requirements
1. The spec-writer role type (`.claude/agents/spec-writer.md`, `docs/roles/types/spec-writer.md`) produces one short
   document: intent, requirements, limits, what counts as done, out of scope. It names no data model, interfaces,
   signatures, file lists, line numbers, moves or tests: those belong to the planner's plan. A spec is about one page
   (under ~8,000 bytes); a longer one is a sign the brief asked for the plan.
2. The planner type puts the flesh on the skeleton: data, flows, interfaces, tasks with files, commands and tests,
   from the spec. The `software-factory` pipeline's spec stage feeds the plan stage; no stage asks the spec-writer for
   plan content, and no brief template for the spec-writer asks for lists.
3. The model map says: spec-writer on the owner's spec model (today Fable), planner, critic, verifier, judge on the
   judgment class, builder on the mechanical class, effort never lowered (economy R6 stays).
4. The pipeline skill (`SKILL.md`, `references/choosing-roles-and-skills.md`, the example briefs) and the manager's
   documents (`docs/roles/MANAGER.md`, `ROLE-MAP.md`, `catalogue.md`, `need-to-know.yaml`) agree with 1-3, in the
   neutral wording the consolidation run set (no owner's language or name).
5. A check enforces it: the role catalogue or `harness validate` refuses a spec-writer type whose output sections
   include data model, interfaces or tests, and a spec file over the size limit gets a warning in `docs-check`.

6. The lessons loop's third step is written into the template: a rule broken a second time becomes a check in code (hook, watcher/monitor script, check_formats or validate rule, test); SKILL.md "Briefs" and `example/lessons.md` say so (vault decision a-rule-broken-twice-becomes-code, 2026-10-31).

7. The cache is measured in money, not tokens (owner, 2026-10-31 12:0x UTC: the cache and the
   separate reads were the open economy question). (a) `usage_report.py` and `score_run.py` print cache reads, cache writes and output as dollars
   beside the token counts (one usage per message id, as `usage_report.py` counts now), and the economy row gets a
   "cache write $ per unit" column. (b) The pipeline skill states the rule "stable first, unique last": what is
   byte-identical across a role's sessions (the brief, the hand-over rule, lessons.md's "Read first" section, the facts
   pack) comes before what is unique to one session (the hand-over note, last in the launch prompt); `make_pack.py` gets
   an option that leaves the note out of the pack; the "packs are off" line stays until a run measures the pack in
   dollars. (c) The cache TTL per role: a role's settings `env` sets `CLAUDE_CODE_PROMPT_CACHE_TTL` (read by Claude Code
   2.1.314: "5m" or "1h"): `5m` for roles that do not wait on another role (builder, writer, planner), `1h` for roles
   that wait (verifier, critic, plan fixer, judge); the skill's example settings and `references/launch.md` carry it.
   This is the rule for the SpecAgent role sessions launched with the skill's settings; the harness's stage types keep
   the hour `docs/roles/need-to-know.yaml` sets (ADR-0016).
   (d) `docs/economy.md` gets the measurement of 2026-10-31 (the owner's vault page
   `context/measurements/2026-10-31-cache-ttl.md`, one usage per message id): the readme writer's $129.61 = cache reads
   31%, cache writes 29%, output 40%; a fresh session's first call reads at least the 20,452 tokens of the shared prefix
   and writes about 14k; at 5m instead of 1h a cache write costs 37.5% less, so the saving is at most 37.5% of a role's
   write dollars, less the rewrites after gaps of 5 to 60 minutes: readme writer +$13.49 (1 gap in 1,697 calls),
   consolidation builder +$3.07 (0 in 659), readme verifier +$2.79 (13 in 1,265), consolidation verifier +$2.99 (4 in
   633).
8. The version: `docs/template/VERSION` 1.7.0, a `docs/template/MIGRATIONS.md` entry for 1.7.0 (the paths this run
   changes, copied from the template; "Breaks active runs": whether a running run must refreeze), and `CHANGELOG.md`.

## Done
`uv run harness validate`, `docs-check`, the harness tests and the skill's `check_formats.py` pass; `git grep` finds
no spec-writer instruction asking for data model, interfaces, signatures or tests; `docs/roles/CHANGELOG.md` and
`CHANGELOG.md` carry the change; the decision page `wiki/decisions/spec-writer-writes-the-skeleton.md` exists.

## Out of scope
Lowering the owner's effort rule; renaming roles; changing the planner's or builder's method; the consolidation run's files beyond the wording fix.


## Run plan (owner's decisions, 2026-10-31)
- Launched now (owner, 13:1x UTC: launch it now), before grantsdaily-next is carried (the owner: the carry comes
  last, so it takes 1.6.0 and 1.7.0 at once), in parallel with the judge of the consolidation and readme runs.
- The size rule: the spec is precise enough to build from; no planner and no critic. Two roles: a builder (mechanical
  class, max) and a verifier (judgment class, max). Three units: Unit 1 = requirements 1-4 and 6 (wording in the role
  types, the skill, the manager's documents, the decision page); Unit 2 = requirement 5 (the check, test first);
  Unit 3 = requirements 7 and 8 (the scripts, the settings, docs/economy.md, the version). Estimate ~$12, 2-3 hours.
- Cache TTL in this run already: the builder's settings `env` `CLAUDE_CODE_PROMPT_CACHE_TTL=5m`, the verifier's `1h`.
- Branch `feat/spec-005` from `feat/readme` at 081968d (it holds main and the README the docs refer to); the judge's
  fixes on `feat/readme`, if any, are merged into it by the main session.
- Effort: every role at `--effort max` (owner, 12:3x UTC).
