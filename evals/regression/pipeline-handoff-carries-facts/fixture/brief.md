# Project brief — pipeline-handoff-carries-facts

## Project
A small date-parsing library. This run is an eval case: it checks the hand-over note a planner writes at its cap.

## Goal of this run
A hand-over note in `output/handoff.md` from which a fresh planner session continues Task 4 without opening a file.

## Material
- the reader's notes of this session, in your `input/` directory

## Constraints
- Budget: 10 minutes per stage, approvals at: none
- Do not touch: everything outside your stage directory
- Language of deliverables: English

## Known decisions
- The note follows the pipeline's hand-over rule: line 1 `HANDOFF <role> after Task <N> — <YYYY-MM-DD HH:MM>`, at most 40 lines, the facts copied in, never a pointer to a file in their place.

## Out of scope
- planning Task 4; reading the repository's code

## What to do
Write `output/handoff.md`, then `result.json` with status `complete` and `output/handoff.md` in `outputs` (kind `report`).
