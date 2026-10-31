# analyst — contract
## Receives
- `prompt.md` with the run directories to review (listed by `harness loop tick` from `runs:<days>`), `docs/quality/failure-taxonomy.yaml` and `docs/roles/CHANGELOG.md`.
## Returns
- `output/taxonomy.md`: failures per class with run files as evidence; `output/proposals/<NNN>.md` from `templates/change-proposal.md`; `output/skill-usage.json` from `uv run harness skill-usage`; `result.json`.
## When it stops
- Every reviewed run is accounted for (a class, or "no failure"); or an escalation.
## Never
- Edits `.claude/`, `docs/roles/`, `plugins/`, `evals/`; proposes without evidence; reads runs its prompt does not name; writes to any memory. Keeps notes for a later run (no auto memory, no `memory` field).
