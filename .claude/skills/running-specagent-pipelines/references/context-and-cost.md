# Context and cost
Without early compaction a session's context keeps growing, and every step re-reads all of it: a read costs its size
times the calls that follow it. Without the 200k cap sessions grew to 500–740k tokens per call (measured 2026-10-15:
every call re-reads it all; three times the cost of a fresh session). Measured 2026-10-22 on six fresh planner and
critic sessions: 27k at the first call (system prompt, tools, CLAUDE.md, the launch prompt; 10k of it from the shared
cache), 81k after ten calls (20k the briefs, 35k state rebuilt from critique.md, the plan and the logs because the note
only pointed there), 180–200k at hand-over after 30–70 calls. Of the growth 84% is tool results, 15% what the agent
writes into files and commands, 1% prose; of the output tokens three quarters are thinking. What follows from it:
- The cap stays at 200k. In a replay of the same work, hand-over at 140–180k moves the cost by under 7% (noise), 120k
  costs more, 100k a third more, no cap twice as much. Do not tune the cap.
- The lever is the startup. The note carries the facts the next session needs (shape in `example/handoff-rule.md`);
  the fresh session reads its brief, the rule, lessons.md's "Read first" section and, last, the note, and opens a source
  only when its step needs it, by line ranges, as late as the step allows. Startup 81k → 50k saves about 15% of a run.
- Stable first, unique last. The cache holds a prefix only as far as it is byte-identical from one session to the next,
  and writing to it costs more than reading it (`docs/economy.md`). What is the same for every session of a role comes
  first: the brief, the hand-over rule, lessons.md's "Read first" section, the facts pack. What is unique to one
  session comes last: the hand-over note, the last item of the launch prompt. The `fresh` texts of `example/agents.json`
  name the files in that order, and `scripts/make_pack.py --no-note` leaves a note out of a pack, which then stays the
  same from one session of the role to the next. The cache's cost is in dollars in `scripts/usage_report.py` and
  `scripts/manager/score_run.py`; the "packs are off" line below stays until a run measures a pack in dollars.
- A facts pack replaces reading a tool's documentation. The manager writes `_inputs/<topic>.md` before the launch (a few
  KB: each tool fact the run needs, with its source line) and the briefs name it. In the ingest run the builder read
  the plugin's documents many times, printed JSON answers whole and re-read a 660-line driver in each session, about
  13k tokens of context per page; each pack fact keeps its source (rule 1 of `example/first-pass-rules.md` holds). The
  pack and a hand-over note are sized so a fresh session starts under about 60k tokens: in the pipeline-economy run a
  builder that read its whole note, its brief and the spec's sections was near 150k before its first edit.
- A repeat's unit ends under `handoff_at`. The unit-size rule: k = floor((handoff_at - start) / per-item), from the last
  measured run of the shape; start = a unit's end context minus its items x per-item. Ingest run, 13k per page, 197k
  (its highest unit-end reading) taken as the end of a 9-page unit: start = 197k - 9 x 13k = 80k, k = floor((150k -
  80k) / 13k) = 5 pages, not 9 (4 if that unit had 8 pages). The builder was ordered to hand over 7 times there, 3 at
  a unit's end (181k-197k) and 4 mid-unit at the cap (205k-219k: a stop, a copy and a restarted unit). An order that
  still reaches a unit makes the builder write `Unit size: <k> -> <k-1>` (`example/common.md`), which corrects a k that
  is too big. Smaller units are more units (40 pages: 8, not 5), each checked as before
  (`example/verifier-assignment.md`).
- Terse-style prompts ("caveman") save nothing here: prose is 1% of the tokens, and an agent's prose is read by other
  agents, which pay for every ambiguity.
- Startup packs (a role's standing orders in one file, passed with `--append-system-prompt-file` and built by
  `scripts/make_pack.py`) are off since 2026-10-25. In an earlier run's trial, sessions without a pack (94) started
  at 30.7k tokens, reached 45.5k at call 10 and made 195 calls each, start-up 11% of the cost; with a pack (13) they
  started at 42.4k, reached 59.4k and made 125 calls each, start-up 15%. `watch_agents.py` refuses `pack: true`;
  `make_pack.py` stays, to measure again.
Give the builder and the verifier a fresh session per milestone (the planner marks milestones in its task order); the
new session reads its brief, lessons.md's first section and its note, not the old conversation. This is not
compaction, so the owner's rule holds; count these sessions in the launch approval. The verifier rebuilds from scratch at the same milestones. To switch without
anyone stepping in, a line in `lessons.md` tells the builder to end itself after a milestone task with
`STATUS: milestone done after Task N`, and the watcher then launches the fresh session; it replaces the verifier
once its STATUS passes the milestone (the config's `milestones`).
