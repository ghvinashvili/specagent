---
paths:
  - "packages/**/*.py"
---
# Python rules
- Run tests with `uv run pytest -q packages/<pkg>`; never with the system interpreter and never with `--package`, which leaves pytest out of a fresh environment.
- Public functions carry type hints and a one-line docstring.
- No new top-level dependency without a line in the package's `pyproject.toml` and `uv lock`.
- Keep functions under 50 lines; extract before you nest a third level.
