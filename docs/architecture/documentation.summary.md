# Documentation layers: summary for the owner

- Four layers, each with its place: the user guide (`docs/user-guide/`, once a project has users), the design wiki
  (`wiki/`, the Obsidian vault, with decisions and balance tables), the technical docs and runbooks (`docs/`), and the
  decisions (`docs/decisions/` and `wiki/decisions/`).
- Indexes come in layers: `docs/llms.txt` links a document or the folder `README.md` that links it; one line per item,
  at most 12,000 bytes each. The decision records moved to `docs/decisions/README.md`.
- A plan is a folder: `00-index.md` with the task order, then `task-NN.md` files of at most 1,500 lines each, whose
  long blocks may sit in a `task-NN.code.md` beside them; `harness plan-lint` (also inside `harness docs-check`)
  checks them.
- Every page you read gets a short `.summary.md` summary beside it, in English; docs-check warns when a decision page or a
  runbook has none.
