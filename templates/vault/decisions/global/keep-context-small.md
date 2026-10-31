---
title: "Keep every session's context small: plugins off by default, filtered output, no schema-heavy skills for simple edits"
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-10-31
audience: [all]
sources: []
decided: 2026-10-09
by: owner
review: 2027-10-31
why: the owner watches token use; every turn re-reads the whole context from cache, so anything dumped in is paid for again on every later turn
decision_status: decided
would_change_if: never
---
# Keep context small

**Rule.** Every session keeps its context small. Plugins and optional tools stay off by default and are turned on only in the session whose task needs them; output is filtered to the fields needed; a simple settings edit does not load a schema-heavy skill; after a large unavoidable read the hand-over note is updated and `/clear` is suggested.

**Why.** The owner watches token use. Every turn re-reads the whole context from cache, so anything dumped in is paid for again on every later turn. A new session starts at about 27k tokens (the harness's prompt and tools, the instruction files, hooks), measured with a one-shot print-mode call (`claude -p`).

**How to apply.**
- Keep these off by default and turn them on only in the session whose task needs them: the designer-skills plugin (merge the design-plugins settings file into `--settings`), the IDE MCP server (`--mcp-config` with its own config file), Chrome tools (`/chrome` or `--chrome`), the Artifact tool (`enableArtifact`).
- The synced claude.ai skills and connectors stay off (`syncClaudeAiSkills: false`, `disableClaudeAiConnectors: true`, in force since 2026-10-15); turn them on only when a document skill (docx, pptx, pdf) or the Docs connector is needed.
- Print only the fields you need: no `ps aux` with full arguments, no whole JSON, no transcripts; read agent states with `claude agents --json --all` and print `state`, `status`, `pid`, `sessionId` (`context/skills/running-chat-agent-pipelines/SKILL.md`:86).
- For a simple `settings.json` edit, edit the file; the `update-config` skill injects about 85k tokens of schema.
- After a large unavoidable read, update the hand-over note and suggest `/clear`.
