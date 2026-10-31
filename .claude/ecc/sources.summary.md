# ECC sources: summary

- **What:** 11 ECC rules for Python, C++ and TypeScript, which load only when Claude works on a file of that language;
  11 ECC skills (Python patterns and testing, C++ coding standards and testing, PostgreSQL patterns, documentation
  governance, commit message review, agent security hardening, eval harness, agent comparison, agent self-evaluation);
  the text of 70 ECC agent definitions as material for chat-role briefs; ECC's hook recipes as reference. All from ECC
  commit `25278e7` (2026-10-26), with ECC's MIT license beside each unit.
- **Not taken:** ECC's hooks, commands and agents as mechanism; its shared rules, which would load into every session;
  the FastAPI rule, the Python security rule and the PHP reviewer.
- **Dropped from the copies** (whole lines, each with its reason in `files.md`): links to the shared rules,
  mentions of ECC agents, commands, hooks, scripts and skills not copied, the agents' `tools:` and `model:` lines,
  Python tools this repository does not use (black, isort, mypy, bandit, pip, bare `pytest`, `pytest --cov`,
  `pytest.ini`), tests on SQLite instead of the production database, one Supabase-only call.
- **Layered:** the three long skills keep a short `SKILL.md` and one file per section under `references/`; the seven
  agent texts over 12 KB are read through their outline; the table of copied files is a page of its own.
- **Checked by:** `uv run pytest -q ops/tests/test_ecc_pins.py` and the `SHA256SUMS` in each folder.
- **To update:** the "Re-pin" steps of `sources.md`; changed copies under `.claude/` need a new
  `docs/roles/VERSION`.
