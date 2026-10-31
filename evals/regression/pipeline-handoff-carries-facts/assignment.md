# Assignment — plan (planner)

## Goal
This stage writes no plan. It ends a planner's session the way the pipeline ends one at its context cap: with a hand-over note from which a fresh session continues without reading anything else.

## Material
none: the session's facts are the reader's notes in your `input/` directory, and the brief says what a note holds.

## Deliver
`output/handoff.md`: at most 40 lines; line 1 exactly `HANDOFF planner after Task 3 — <YYYY-MM-DD HH:MM>` with the current time; then the state, the next unit, the open threads and the working knowledge, each fact written out.

## Prove
Copy every command with its result, every path with its line, the commit and the finding id from the notes into the note as the notes write them. A line that only names the notes file carries no fact.

## Done when
`output/handoff.md` is written and `result.json` has status `complete` and `output/handoff.md` in `outputs` with kind `report`.
