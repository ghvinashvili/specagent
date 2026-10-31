# Assignment — <stage> (<role type>)

<!-- Written by the manager before the stage is launched for the first time, then stored with
     `uv run harness assign --run <run-id> --stage <stage>`. Delete this comment.
     Write it exactly as you would write the prompt of a subagent you were about to send to do this job. The session
     knows its type's instruction and the brief, and nothing of what you know about this run. Leave nothing out
     because the type's instruction covers it: say what THIS run needs. `Deliver`, `Prove` and `Done when` are
     required, `Material` is optional; a text that repeats the brief or another stage's assignment is refused, and so
     is a listed piece that does not exist or that the stage's type may not read. -->

## Goal
<What this stage is for in this run, who uses its output next, and what they must be able to do with it without asking anyone.>

## Known
<What earlier stages and the human have settled, and what was tried and ruled out, so that it is not found again. For a reviewing type: nothing its row hides (who made the work, what another reviewer found, the budget, a model).>

## Material
<Optional. The harness chooses the material by script and gives it in the session's cached system prompt: the
stage's inputs, the brief's material, every place the stage's texts cite as `path:line` with the piece that holds it,
the short files they name, and what matches the brief (a type whose agent file lists tools, none of them Write or Bash, gets its inputs, the brief's pieces when its stage receives `context`, and the pieces its assignment lists, and nothing chosen by script). Write the places you know as `path:line` in the sections
where they matter; they come with their pieces. List a piece here only when no text of the stage points to it: a
file, a directory or a range of lines, one per item: `- `path:120-260` — what it is for`. Delete the section when
there is nothing to add.>

## Deliver
<Every deliverable by name, and how exact it has to be: the level of detail at which the next session decides nothing itself. For a plan: the shape of the data, every rule with its numbers, the names, where each thing is wired in, what each test asserts.>

## Prove
<What is shown by running it or by opening the source, not asserted: the trial, the probes, the commands, the inputs at the edges, the check that is run before finishing.>

## Hard parts
<Where a quick answer would look right and be wrong in this run, and what to do there.>

## Done when
<The conditions that make this stage finished, and what does not count as finished.>
