# Cache and compaction measurements, 2026-11-01 (main session 49b26b)

Re-run: `python3 -I cache_gaps.py` (this folder; reads the seo-quality and one-agent transcripts read-only); its output
at 04:15 UTC is `cache_gaps.out`.

## Cold restarts after a wait past the 5-min TTL
10,603 calls; 30,475,758 cache-write tokens; 29 calls after a gap > 300 s that wrote > 20k tokens: 2,630,529 tokens,
8.6% of all writes (at 03:58 UTC: 27 calls, 2,350,988, 8%). Upper bound in dollars at the strongest class's write
price (usage_report.py's table, $8.0/M): ~$21; the builders run the cheaper class. Cause: `wait_for_log.py` and
`wait_for_ready.py` sleep in 60-s steps for up to 8 h inside one tool call (`timeout after 8 hours`), and a full
`pytest -q packages/seo` run takes 140-300 s (one ran 5 min 2 s at 02:44-02:49 and the next call was cold).

## Auto-compaction (one-agent, session e53f78a7, `--autocompact 190000`)
Seven compactions 02:51-04:04 UTC, about every 12 min: pre 157-167k, post 21.7-29.4k, 90-234 s each. The first call
after the first one: cache read 22,023, write 39,274 (files re-read after the summary are written anew; the cache
matches an exact prefix only). Cost estimates (usage_report.py prices): a compaction ~$0.45 (read 160k warm $0.03,
summary ~5k out $0.10, ~39k rewritten $0.31); a hand-over ~$0.70-1.00 (note calls at ~200k, then a fresh start of
50-80k written).

## Fresh-start prefix shared with the previous session
Not measured today: the 27k first call with 10k from the shared cache, 81k after ten calls, is the template's
2026-10-22 measurement on six fresh planner and critic sessions, in
`.claude/skills/running-specagent-pipelines/references/context-and-cost.md:4-6` of the main checkout.

## token-optimizer (before its removal at 03:22 UTC)
78 sessions started before 00:54 UTC vs 51 after: mean tool result 1,725 vs 1,876 characters, mean context per call
122.8k vs 119.0k, 4 `measure.py expand` calls; a real `pytest -v` output (6,567 chars) compressed to 6,532 (0.5%,
below its 10% floor); 12,866 tool results, the largest 24,348 chars, 1.4% over 10k chars.

## The numbers behind the cache rules (recomputed 2026-11-01 ~12:55 UTC; `cache_numbers.py`, output `cache_numbers.out`)
Prices: `usage_report.py:29-33`, $ per 1M tokens (input, output, cache read, 1-hour write): the large class 4.0, 20.0, 0.20, 8.0;
a 5-minute write is 1.25x input, a 1-hour write 2x input. Corrections: three numbers the main session gave earlier in
chat were estimates and are replaced here by these measurements: the 1-hour TTL "+$76 against ~$15" is +$59.51 against
$26.91; c0 "61k" is 64.9k (61.3k was the first compaction alone); the touch "$0.035" is $0.040.
- **1-hour TTL, seo-quality.** The critic, plan-fixer, verifier, verifier-b and judge sessions (worktrees
  seo-quality-critic, -verify, -v) ran `CLAUDE_CODE_PROMPT_CACHE_TTL=1h` until 11:59 UTC: 19,859,570 write tokens; at
  (2.0 - 1.25) x input that cost **$59.51 more** than 5-minute writes. What 1 h saved: 49 calls came after a gap of
  5-60 min and read from the cache what a 5-minute TTL would have written again: their cache reads x (1.25 x input -
  read) = **$26.91**. Net: the 1-hour TTL cost $32.60 more. Rule: 5m for every role.
- **Touch and rewrite.** A touch keeps a 150k context warm: 150,000 x $0.20/M read = $0.030 plus about 500 output
  tokens x $20/M = $0.010, **$0.040**. A rewrite of 150k after the cache expired: 150,000 x 1.25 x $4.0/M = **$0.75**.
  Break-even: 0.75 / 0.040 = 19 touches = **1.1 h** at one touch per 3.5 min. Rule: a working session's waiter returns
  within 3.5 min; a wait known to last over about 1 h stops the session instead.
- **Compaction against hand-over.** As above: a compaction about **$0.45** (the 160k read warm $0.03, a summary of about
  5k output $0.10, about 39k rewritten after it $0.31); a hand-over about **$0.70-1.00** (the note calls at about 200k,
  then a fresh start of 50-80k written). The seven compactions of session e53f78a7: pre 157,004-167,232, post
  21,736-29,416 tokens, 89.6-233.6 s (`cache_gaps.out`).
- **Balance.** One call costs the mean context read plus its share of the compaction: cost(C) = r (c0 + C)/2 + K g/(C - c0),
  with C the context at which the session compacts. d cost/dC = 0 gives **C\* = c0 + sqrt(2 K g / r)**. Inputs from
  e53f78a7: c0 = 64,888 tokens (the mean context of the first call after each of the seven compactions, 59,549-73,683:
  the summary of about 22-24k read plus 35-49k of files written again), g = 2,250 tokens per call (the mean growth per
  call over the six spans between compactions, 1,671-2,634), K = $0.45, r = $0.20/M. **C\* = 165,505 tokens**, at
  $0.0331 per call; 150k costs +0.9%, 175k +0.2%, 197k (`--autocompact 235000`, which compacts at about 84% of its
  window) +2.3%, 200k +2.7%. The curve is flat within 3% from 150k to 200k, so 235000 (near 197k) keeps the fewest
  compactions inside that band.
