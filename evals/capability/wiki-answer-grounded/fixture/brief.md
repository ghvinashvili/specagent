# Project brief — wiki-answer-grounded

## Project
The `ingest` package of this repository. This run is an eval case of the harness.

## Goal of this run
An answer to one question, with every statement tied to its source: how does `ingest` decide to skip a file?

## Material
- `wiki/` — compiled pages; start from `wiki/index.md`
- `context/ingest-samples/` — the raw material the pages cite

## Constraints
- Budget: 15 minutes per stage, approvals at: none
- Do not touch: `context/`, `wiki/`
- Language of deliverables: English

## Known decisions
- none

## Out of scope
- changing the package

## Escalation policy
- Blocking questions: write an escalation and stop. Non-blocking: list them in result.json open_questions.
