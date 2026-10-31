# Role catalogue: summary

- **What:** every agent file, contract, example brief, skill (whole and by its description line) and pinned ECC text
  in bytes and tokens, with the bounds the manager chooses by: a prefix within 10,000 tokens, near up to 13,000; 2,500
  for an item half the sessions use.
- **Checked by:** `uv run pytest -q .claude/skills/running-specagent-pipelines/scripts/tests/test_catalogue.py`.
- **To update:** run `catalogue.py table` and paste its output over the tables; the page is a snapshot that no check
  regenerates.
