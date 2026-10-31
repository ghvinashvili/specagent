# Role map: every role named in the sources, and what it is here

A role type exists only where the tool set or the contract differs. A role that differs only by its brief is a
stage of an existing type; a role that is a rule, a budget or a schedule is code, not a chat. `harness select`
needs one best match per request, so two types never share a "Use when:" situation.

| Role in the sources | Here | Kind |
| --- | --- | --- |
| orchestrator, lead agent, supervisor, router, coordinator, CEO | `manager` | type |
| codebase researcher, documentation researcher, data analyst, parallel searcher of a research run | `researcher` | type |
| reader of source material, extractor | `reader` | type |
| story writer, product owner writing acceptance criteria | `story-writer` | type |
| spec writer | `spec-writer`: the skeleton, one page (intent, requirements, limits, done, out of scope) | type |
| planner, initializer, task decomposer, CTO setting the next slice | `planner`: the flesh on the spec (data, flows, interfaces, tasks); the initializer session is `harness run` | type and code |
| architect who rules on disagreements and freezes contracts | `planner` (specification) and `judge` (rulings); frozen contracts are `specs/<NNN-feature>/contracts/` and `schemas/` | stage pattern |
| builder, backend builder, frontend builder, coder, implementer, generator, worker, lane agent, writer, copywriter, content strategist, designer | `writer`; a lane is a shard, folder ownership comes from the task's `category` and the brief's "Do not touch" | type |
| test verifier, API tester, database query validator | `test-verifier` (writes tests); `verifier` (runs existing checks) | type |
| implementation validator | `validator` | type |
| verifier, evaluator, QA reviewer, citation agent, meta-verifier | `verifier`; the meta-verifier is a second `verifier` stage over the first report | type |
| grader | `evals/graders/` (code) and `evals/rubrics/` (LLM grader) | evals, not a role type |
| reviewer, code reviewer, critic, skeptic, devil's advocate, refuter, security checker, architecture reviewer, UX reviewer | `critic` with the rubric named in the brief | type |
| judge, arbiter, reviewer who answers APPROVE or a defect list, chairman deciding acceptance | `judge` | type |
| council advisors (contrarian, first principles, expansionist, outsider, executor), research perspectives (practitioner, academic, skeptic, economist, historian), personas | `advisor`; the perspective is the shard's task | type |
| council peer reviewer, pairwise or tournament judge, filter of generate-and-filter, comparison agent of a lightweight eval | `comparator` | type |
| council chairman writing the verdict, synthesizer, weekly synthesis | `synthesizer` | type |
| quarantine reader, safe researcher (reading side) | `quarantine-reader` | type |
| classifier, triager, model router | `classifier` plus the `routes` table of a pipeline | type and table |
| trace analyst, diagnosing agent of a self-healing harness, skill-performance reviewer, instruction distiller, analytics reviewer | `analyst` | type |
| wiki maintainer (ingest, lint), nightly compiler | `librarian` | type |
| plan fixer, findings responder, plan reviser | `plan-fixer` | type |
| translator, localiser | `translator` | type |
| doc gardener | skill `doc-gardening` and `.github/workflows/doc-gardening.yml` | skill and CI |
| debugger | `verifier` reproduces and reports; `writer` fixes | stage pattern |
| daily briefing writer, morning or weekly report writer | `synthesizer`, if a loop for it is added to `docs/loops/` | not configured |
| pull request babysitter, issue triager, chat feedback collector, deploy watcher | none: this repository has no connection to those services | not included |
| browser tester | none: needs a browser tool that is not enabled | not included |
| finance or budget agent | none: budgets are `max_minutes`, `--max-budget-usd` and loop `stops` | code |
| human board, human in the loop | `docs/roles/HUMAN.md` | humans |
| subagents (Explore, Plan, general-purpose), agent team teammates | none: the `Agent` tool is denied; teams are not used | not included |
| advisor tool (a second model consulted inside a session) | none: experimental and not enabled | not included |
