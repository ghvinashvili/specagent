Decision (owner, 2026-10-29): the skill's script docs are one page per script, the README an index.
Each script's usage, options and files live in scripts/docs/<stem>.md.
scripts/README.md holds the index lines, the config fields and the tests, at most 12,000 bytes.
A new script adds its page and its index line; test_docs.py keeps both.
