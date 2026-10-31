---
status: accepted
date: 2026-10-03
decision-makers: the human, who approves the plan of run 20261003-200017-chat-depth-fix
consulted: harness maintainers
informed: all package owners
---

# A type that cannot write a file accounts for no material and gets no pieces chosen by script

## Context and Problem Statement
[ADR-0008](0008-a-role-session-works-to-a-subagents-depth.md) has every role session account for every file of its
material, whatever its type, and [ADR-0006](0006-a-role-session-gets-what-a-subagent-would-get.md) has a script choose
pieces of the repository for every session: the places its texts cite, the short files they name and the pieces that
match its brief. Some types return their result as structured output only and write no file: today the judge, the
comparator, the quarantine reader and the classifier. Such a type has no document to account in; seen on 2026-10-03,
a judge failed its gate on the 39 files of its material. And the script gave it pieces it can do nothing with: it
cannot account for them, and the judge's method forbids it to open the work, the spec or the sources.

## Decision Drivers
* A check that a session can pass by no means is no check.
* A session gets only what its job needs (ADR-0006, point 9); everything it carries is read on every request.
* Whether a type can write follows from the tools its agent file names; a list kept beside them goes stale.

## Considered Options
* A fixed list of the four types
* The tools of the agent file, read as the gate reads them
* Keep the pieces and drop only the check

## Decision Outcome
Chosen option: "The tools of the agent file, read as the gate reads them", because the agent file is where the tools
of a type are decided, and the gate and the launcher then cannot disagree. A type that cannot write a file is
a type whose agent file lists tools, none of them Write or Bash (`access.writes_files`). A type without an agent file,
and one whose agent file lists no tools (its session gets every tool), count as writing. A type that cannot write a
file:
* is not asked to account for its material (`gates.common_checks`);
* gets no piece chosen by script, neither cited, nor named, nor related (`launch.stage_material`): its material is its
  inputs, the pieces its assignment lists and, for a stage that receives `context`, the pieces its brief lists.

The sentence added to ADR-0008 on 2026-10-03 said the first of the two; this decision takes its place.

### Consequences
* Good, because a judge, a comparator, a quarantine reader and a classifier are no longer failed for material they
  have no way to account for.
* Good, because their prompt holds what they work from and nothing their method forbids them to open.
* Bad, because a type with Bash and without Write keeps the check: it can write a file through Bash.
* Neutral: a new type with neither tool falls under this decision by its agent file alone.

### Confirmation
`packages/harness/tests/test_gates.py`: the material check of a judge and of a planner, and the fallbacks that keep
it. `packages/harness/tests/test_access.py`: `access.writes_files`, and the pieces a judge gets against a planner.

## Pros and Cons of the Options

### A fixed list of the four types
* Good, because it is short and can be read at a glance.
* Bad, because a type that changes its tools, and every new type, is outside it until someone edits the list.

### The tools of the agent file, read as the gate reads them
* Good, because one predicate serves the gate and the launcher.
* Bad, because a type whose agent file cannot be read counts as writing and keeps the check.

### Keep the pieces and drop only the check
* Good, because nothing changes at launch.
* Bad, because the judge gets sources its method forbids it to open, and every request reads pieces nobody uses.

## More Information
[ADR-0006](0006-a-role-session-gets-what-a-subagent-would-get.md),
[ADR-0008](0008-a-role-session-works-to-a-subagents-depth.md); `docs/roles/MANAGER.md` section 14;
`packages/harness/src/harness/access.py` (`writes_files`).
