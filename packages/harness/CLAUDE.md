# harness — map for Claude

@AGENTS.md

- Purpose: launch, poll, resume and gate role sessions; write the run directory (`<runs root>/<run-id>/`, `state.runs_root`) through `state.py` only.
- Commands: `uv run pytest -q packages/harness`; `uv run harness --help`.
- Never call the `claude` binary from tests; tests use recorded `claude agents --json` fixtures under `tests/fixtures/`.
