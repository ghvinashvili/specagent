# `usage_report.py` — tokens and cost per agent
```
python3 -I scripts/usage_report.py [--prefix demo/] [--since 2026-10-15] [--by-day]
```
Reads `claude agents --json --all` and the transcripts `~/.claude/projects/*/<sessionId>.jsonl`: per agent the
calls, the context per call, the output and an API-equivalent cost (list prices of 2026-10-29; check them before
quoting a figure). A call is one message id; a `<synthetic>` line is no call; a resumed session's transcript begins
with a copy of the session it resumes, and those calls count once, under the session that started first. Figures
printed before 2026-10-26 (commit 031bb98) counted them twice.

Its first line names the date and the page of its prices (`PRICES_AS_OF` and `PRICES_URL` in the script): the API
list prices per million tokens with the 1-hour cache write, and Haiku 5.5 at its price for prompts up to 100,000
tokens.

The cache is measured in money, not tokens (spec 005): right of the cache reads, the cache writes and the output, a row
shows their dollars (`rd $`, `wr $`, `out $`), one usage per message id at the prices of the call's model family;
`$ equiv` is the row's whole cost, input included. The total row holds only that total: `surface.py` quotes its last
field. `usage_report.dollars(message)` gives one call's (input, output, cache read, cache write) dollars and is the
split `score_run.py` prints per role.
