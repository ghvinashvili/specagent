# harness

Build: part of the uv workspace (`uv sync` at the root). Test: `uv run pytest -q packages/harness`.
Style: root `pyproject.toml` ruff rules. A gate reads files and runs fixed commands; it never calls a model.
Run state is written only through `state.save`, which validates against `schemas/`.
