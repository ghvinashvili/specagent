# Why it is built this way: summary for the owner

- Roles are full chats: on one task (2026-10-02) they cost a twelfth of subagents and passed more hidden checks
  (ADR-0006). Roles run sandboxed and blind to models and authors; the manager stays outside to launch and supply them.
- One unit per session and a hand-over at 200k: a read costs its size times the calls that follow; no cap costs twice
  as much, a 300k cap 15-25% more per task
  (`.claude/skills/running-specagent-pipelines/references/context-and-cost.md`,
  `.claude/skills/running-specagent-pipelines/example/handoff-rule.md`).
- Proof for every finding, three rounds, then a rule; nothing waits for the owner after the one yes before the run.
- English only (about twice the tokens otherwise); no sample project and no development records in the template.
- A private vault per user, one public commons by pull request, private material refused in code with no flag to skip;
  a one-project decision is not a global rule; contradictions go by evidence and scope; the collector lists before it
  deletes and a run's leftovers wait for the owner's check (TD-010).
