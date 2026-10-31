# Assignment — verify (verifier)

## Goal
Check the writer's page in your `input/` directory against its source, statement by statement, and report each statement the source contradicts, so that only real defects go back to the writer.

## Material
none: the plan, the critique and the writer's page with its report are copied into your `input/` directory.

## Deliver
`output/report.md`: one line per defect, `DEFECT <file>:<line> — <what> — proof: <the source's line>`, then the line `Checked: <n> statements`.

## Prove
Open `context/sample.txt` and compare every statement of the page with the line it cites. A statement the source supports is no defect, however it is worded.

## Done when
`output/report.md` is written and `result.json` has status `complete` and `output/report.md` in `outputs` with kind `report`.
