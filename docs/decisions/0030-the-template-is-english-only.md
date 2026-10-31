---
status: accepted
date: 2026-10-29
decision-makers: the owner, in the order of 2026-10-29 that no text outside the Latin blocks appears anywhere in the template
consulted: the template-core run's planner, critic and plan fixers
informed: every project created from this template
---

# The template is English only

## Context and Problem Statement

A template copies its text into every project, and a script outside the Latin blocks costs about twice the tokens for every
agent that reads it. The attack stage of ADR-0024 asked for a translated summary, and summaries were named
`<name>.<language>.md` (ADR-0026, ADR-0027 and the summaries case of ADR-0028). How does the template keep every file it hands
on in English, and what holds that rule?

## Decision Drivers

* The owner's order: no text outside the Latin blocks anywhere in the template.
* A rule is held by a check that CI runs.
* A project whose product text is in another script can still use the template.

## Considered Options

* A letter check in `harness validate` over the git listing, narrowed by `english_only:`
* The check in `harness docs-check` only
* A rule without a check

## Decision Outcome

Chosen option: "A letter check in `harness validate` over the git listing, narrowed by `english_only:`", because CI
runs validate on every pull request over every listed file, and one key lets a project with product text in another script
narrow it.

* `harness validate` reports each listed file that holds a letter of a refused block (U+10A0-U+10FF), once, at its first such
  line. The listing is git's: tracked files and new ones, not ignored ones.
* `english_only:` in `docs/template/variables.yaml`, a list of path prefixes, narrows the check to those paths, and
  `[]` turns it off. Without the key every listed file is checked.
* A summary is in English, at most one page, and named `<name>.summary.md`. The attack stage writes
  `output/summary.md`, at most 6,000 characters, with no letter of a refused block.
* History keeps its names: the changelogs, the accepted ADRs, the run-loop plan (development records) and
  `specs/002-run-loop/`.
* The original design record is the owner's vault's; ADRs 0004, 0009 and 0018 point there.

### Consequences

* Good, because every file an agent reads costs the English rate, and a check holds it.
* Bad, because a project with product text in another script must set `english_only:`.
* Bad, because the two further blocks (U+1C90-U+1CBF, U+2D00-U+2D2F) are not checked.

### Confirmation

`packages/harness/tests/test_validate_listing.py` (the listing, one problem per file at its first such line,
`english_only:`, and no letter of a refused block in this repository) and the attack gate's test in
`packages/harness/tests/test_gates.py` (an English summary of at most one page).

## Pros and Cons of the Options

### A letter check in `harness validate` over the git listing, narrowed by `english_only:`

* Good, because CI runs it on every pull request, over code, tests, settings and pages alike.
* Good, because one key narrows it for a project with product text in another script.
* Bad, because validate reads every listed file once more on each run.

### The check in `harness docs-check` only

* Good, because docs-check already reads every document.
* Bad, because it reads the documents under `docs/` only, so code, tests, settings, skills and wiki pages could hold
  text outside the Latin blocks unseen.

### A rule without a check

* Good, because it costs no code.
* Bad, because nothing holds it: a page or a test copied from an older project brings text outside the Latin blocks back unseen.

## More Information

* Amends [ADR-0024](0024-a-run-loops-until-its-reviewers-pass.md), [ADR-0026](0026-plans-in-parts-and-layered-document-indexes.md), [ADR-0027](0027-pages-are-written-with-the-work.md) and [ADR-0028](0028-pipeline-evals.md).
* Revisit when a script outside the Latin blocks costs no more tokens than English for the models a pipeline runs.
