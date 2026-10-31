Decision (owner, 2026-10-31): the spec writer writes a one-page skeleton (intent, requirements, limits, done, out of scope; under 8,000 bytes; no data model, interfaces, signatures, file lists or tests), and the planner puts the flesh on it.
The model map follows the work: the spec writer on the owner's spec model, the planner, critic, verifier and judge in the judgment class, the builder in the mechanical class, the effort never lowered.
A check keeps it so: the role catalogue and `harness validate` refuse a spec-writer type that returns a data model, interfaces or tests, and `harness docs-check` warns about a spec that is not under 8,000 bytes.
The lessons loop gets a third step: a rule broken a second time becomes a check in code.
The record is spec 005, requirements 1-6.
