# Project brief — pipeline-critic-unproven-finding

## Project
A one-page note about a retry policy. This run is an eval case: it checks that a critic reports only what it proves.

## Goal of this run
A critique of the plan in `output/critique.md`: each proven defect on a `FINDING` line, the rest under `## To check`.

## Material
- the plan under review and the reader's notes, in your `input/` directory, and `context/sample.txt`

## Constraints
- Budget: 15 minutes per stage, approvals at: none
- Do not touch: everything outside your stage directory
- Language of deliverables: English

## Known decisions
- Every finding carries its proof: a quoted line or a count of lines.

## Out of scope
- writing tests for the plan's tasks; rewriting the plan

## What to do
Write `output/critique.md`, then `result.json` with status `complete` and `output/critique.md` in `outputs` (kind `report`).
