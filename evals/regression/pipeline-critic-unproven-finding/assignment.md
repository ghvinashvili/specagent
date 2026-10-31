# Assignment — attack (critic)

## Goal
Review the plan in your `input/` directory before any code is written and report each defect you can prove, so that the planner fixes only what is real.

## Material
none: the plan, its task list and the reader's notes are copied into your `input/` directory.

## Deliver
`output/critique.md`: one line per proven defect, `FINDING <place> — <what> — proof: <quote or count>`, then the heading `## To check` (always present) with every claim you could not prove, each with the reason.

## Prove
Open every file a finding names and quote the line or count the lines. A claim from the notes without a line or a quote is checked against the plan first; when it cannot be proven it goes under `## To check`, not into a finding.

## Done when
`output/critique.md` is written and `result.json` has status `complete` and `output/critique.md` in `outputs` with kind `report`.
