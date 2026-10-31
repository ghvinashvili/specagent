---
title: The default template exists to start any complex project right from the first day
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-10-31
audience: [main]
sources: []
decided: 2026-10-30
by: owner
review: 2027-10-31
why: the owner's own words on what the template is for; it decides what belongs in the template and what stays a project's add-on
decision_status: decided
would_change_if: the owner names a second purpose for the template
---
# The default template exists to start any complex project right from the first day

**Rule.** The default template exists so that any complex project starts right from its first day. Its default set is what every complex project needs on day one and is project-neutral; what one project needs is that project's add-on, never part of the default set.

**Why.** The owner stated the template's purpose on 2026-10-30, and it decides what belongs in the template and what stays a project's add-on. The first reading of the owner's lines that hour put one project's plugins into the default set; the final reading, which this rule states, keeps the default set neutral.

**How to apply.**
- The default set is the roles, the pipeline, the gates, the knowledge layer (a vault), the code-intelligence and conventions plugins and the bootstrap.
- What one project needs (for example an audit plugin and an article-writing plugin of one site) is declared in that project as an add-on, never in the template's default set.
- A new project starts from the template (`ops/new-project.py`), not by migrating an old checkout in place: the project's own content moves into the fresh tree and takes the template's rules.

Related: [[plugins-load-per-session]], [[sessions-close-by-the-watcher]].
