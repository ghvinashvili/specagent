# Project brief — pipeline-verifier-planted-defect

## Project
A one-page note about a retry policy. This run is an eval case: it checks that a verifier finds a planted defect.

## Goal of this run
A verification report in `output/report.md`: one `DEFECT` line per statement the source contradicts.

## Material
- the writer's page and its report, in your `input/` directory, and `context/sample.txt`

## Constraints
- Budget: 15 minutes per stage, approvals at: none
- Do not touch: everything outside your stage directory
- Language of deliverables: English

## Known decisions
- The page cites its source line on every statement; the source is right.

## Out of scope
- the page's wording and layout; changing the page

## What to do
Write `output/report.md`, then `result.json` with status `complete` and `output/report.md` in `outputs` (kind `report`).
