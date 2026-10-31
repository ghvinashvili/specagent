---
title: The template's standing requirements - any model and harness, a project brain with separate parts, a checkout that sets itself up
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-10-31
audience: [all]
sources: []
decided: 2026-10-01
by: owner
review: 2027-10-31
why: the template is every project's default structure; the owner wants it locked to no vendor and installed by no hand
decision_status: decided
would_change_if: the owner drops a requirement or a harness cannot meet the neutral contracts
---
# Template standing requirements

**Rule.** The agentic flow template meets three standing requirements: it fits any model and any harness, with no new coupling to one vendor; it keeps a project brain whose big parts stay apart as small projects; and a checkout sets itself up, so the owner types no terminal command.

**Why.** A language-server plugin of the template had silently never worked, before 2026-10-02, because its server was not installed. The owner does not want one vendor: other vendors' models may be in use as well.

**How to apply.**
- Any model, any harness (2026-10-03): contracts stay neutral (specs, briefs, plans, tasks, result schemas, gates' file checks, `need-to-know.yaml` as a statement of needs); each harness's specifics (launch and resume, access enforcement, instruction and role files, transcript reading, costs) sit behind an adapter, the first harness first and the second harness second; no new single-vendor coupling without such a boundary.
- The order of the work: a run's chats on any harness, then the manager. No second orchestrator is installed; the ideas of two tools of that kind are borrowed.
- A project brain (2026-10-01): a brain uniting the parts of one big project is filled at the end of every project (an Obsidian-compatible vault); a big brain as the product itself is a later project built with the template, not part of it.
- The big parts of one product (a website, a server engine, a browser extension) are each a small project with its own specs, never in one file with the others; their connections make the big project.
- A checkout sets itself up (2026-10-02, sharpened 2026-10-03): downloaded from GitHub or created as a new project, it installs everything itself; programming and web are covered by default; Linux, macOS and Windows via WSL2; with or without CLion or VS Code.
- Anything new it relies on installs the same way or `harness doctor` names it with its fix; an administrator step is never silently skipped, and the template does the step itself.

Related: [[template-carries-what-user-relies-on]], [[extensions-no-path-closed]], [[retry-loops-max-3]].
