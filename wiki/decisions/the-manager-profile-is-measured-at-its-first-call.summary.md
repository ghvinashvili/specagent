Decision (owner, 2026-10-29): both manager profiles, the terminal claude profile and just manager, are measured once at the first call; the one under 30,000 tokens is kept.
Answer to question 5 of the manager spec; 51,915 tokens were measured with the desktop app's 36 plugins.
measure_manager.py first-call prints each profile's first call against --limit 30000, pass or fail.
The record is .claude/skills/running-specagent-pipelines/references/measuring.md.
