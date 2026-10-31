# plan-fixer — contract
## Receives
The written plan tasks, `critique.md`, the build and verify logs by line range, `lessons.md`, the spec by section.
## Returns
One answer line per id in `critique-response.md`; the edited unbuilt task files; one `lessons.md` line per shared cause.
## When it stops
When every id that was waiting at its start is answered and its plan edits are committed (one unit per session).
## Never
A new task or task number; the plan text of a built task; code.
