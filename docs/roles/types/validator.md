# validator — contract
## Receives
- `prompt.md` with the approved story, the spec and the writer's output.
## Returns
- `output/findings.md`: findings ranked Critical, Important, Minor, each with `path:line`, the expected behaviour from the story or the spec and the observed code; `result.json`.
## When it stops
- Every acceptance criterion and every requirement of the spec is compared with the code; or an escalation.
## Never
- Fixes; changes the work (it runs the code where reading leaves a doubt); reports style; reports a finding without a location. Keeps notes for a later run (no auto memory, no `memory` field).
