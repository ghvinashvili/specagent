# Common mistakes
| Mistake | Fix |
|---|---|
| the 60% override in agents, or a hand-over as the default | `--autocompact 235000` in `common` and the empty env override; a HANDOFF note only on the watcher's order |
| the briefs read with tools at every start, or a pack rebuilt mid-run | one frozen pack per lane in the system prompt (`extra_prompt` per agent) |
| a waiter that blocks past 5 minutes, or the 1-hour TTL | waiters return within 3.5 minutes; 5m for every role |
| two models in one lane | one model per lane for the whole run |
| effort high or xhigh to save cost | max |
| critic only after the whole plan; builder waits for a frozen plan | the per-task flow (SKILL.md, Pipeline) |
| owner questions mid-run; the owner decides after round 3 | decided by rule; the owner reads summaries |
| a message from the main session never arrives | `lessons.md` for rules; stop and resume for new orders |
| changing global settings or plugins while agents run | running agents reload them mid-task; change them between runs |
| the verifier rebuilds from scratch for every task | milestones only |
| dumping `ps aux` or whole transcripts into the context | print the fields you need |
| a hand-over note that points at files ("read plan 56461–56572, critique.md after A117") | the note copies the facts in; pointers only to what the next session will write or edit |
| a fresh session that reads the plan, critique.md and the logs before its first step | brief, rule, "Read first" and, last, the note; a source only when a step needs it, by ranges |
| a session blocked on a permission prompt (a heredoc or `cp` writing under /tmp asked for an approval nobody gives; the planner lost 40 minutes, 2026-10-23) | `watch_agents.py` cancels it after `permission_wait` (10 minutes) and resumes the session; give every role a scratch folder `<run-dir>/scratch/<role>/` in its brief or lessons.md, written with Write and Edit |
| a lower cap, or a terse style, to save tokens | neither saves (measured 2026-10-22); shrink the startup reads instead |
| a mutation runner that leaves a mutated file in the worktree when it is killed, or a background mutation job that outlives its session (a project's run of 2026-11-02) | the runner restores the file when it is killed and runs the cheap tests first; after any restart compare the mutated files (sha256) with the runner's copies before editing anything, because a mutant left in the tree is committed or edited over without anyone noticing |
