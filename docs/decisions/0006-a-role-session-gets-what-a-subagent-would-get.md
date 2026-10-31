---
status: accepted
date: 2026-10-02
decision-makers: platform team
consulted: harness maintainers
informed: all package owners
---

# A role session gets every demand a subagent would get for the same job

## Context and Problem Statement
A role session used to start on two texts: the instruction of its type, the same in every run, and the brief, the
same for every stage. What one stage owes in one run was written nowhere. A subagent is never started that way:
whoever sends one writes a prompt for this job, with the deliverables, how exact they have to be and what to check.
Measured on 2026-10-02 on one task (a command that writes a diagram source per stage table), with the same model on
both sides: the planner that ran as a role session wrote a plan of 156 lines; the planner that ran as a subagent,
told that the plan had to be exact enough for the writer to decide nothing, built the whole design in a scratch
copy, ran it, and wrote a plan of 678 lines with measured numbers and a byte-exact reference output. The reader
subagent, told to read whatever the goal needed, ran twelve probes against the tool; the reader session read the
listed paths. The subagents also ran at a higher effort level than the table gave the sessions, and the critic
subagent was allowed to run the work while the critic type was not. The sessions cost a twelfth of the subagents
and their product passed more hidden checks, but their documents were shallower: the comparison was not one of
sessions against subagents, it was one of thin demands against full ones.

## Decision Drivers
* A role session has to do what a subagent sent to do the same job would do, one to one, and may not do less.
* What a session adds must stay: an instruction, rules and a knowledge pack read from the prompt cache, access
  limited to what its type needs, a gate.
* The demand must not depend on the manager remembering it: the cause above was an omission, not a decision.
* Depth must not be bought with a stop, a poll and a resume for every repair.

## Considered Options
* Put every demand into the type's instruction
* An assignment per stage and run, written by the manager, required by the launcher
* Subagents for the deep stages

## Decision Outcome
Chosen option: an assignment per stage and run, with the depth every run needs written into the types and held by
the gates.

1. The manager writes the assignment of a stage the way it would write the prompt of a subagent it was about to
   send, and gives that text to the role session (`templates/stage-assignment.md`, `harness assign`). It follows the
   brief in the first message, so the cached system prompt of the type does not change. `harness launch` starts
   nothing without it; a text without `Deliver`, `Prove` and `Done when`, a copy of the brief and a copy of another
   stage's assignment are refused.
2. What a subagent did unasked is now the method of the type: a reader reads what the goal needs beyond the listed
   paths and probes where the material is silent; a planner builds and runs its design in a checkout of its own
   before it writes the plan, decides every question the reader left and carries the reference output of the trial;
   a writer shows a test failing on broken behaviour; a verifier writes checks of its own and tries the edges; a
   critic runs the work to reproduce a defect. "Prefer the smallest design" and "do not execute the work" are gone.
3. The gates ask for the traces of that work, and the stop hook asks the gate before a session may end with
   `complete` (`harness gate --preview`), so that a session repairs its work while its context is in the cache.
4. The tools of a type are the ones a subagent would use for the job. The reader has `WebFetch` for the URLs a brief
   names, within the domains the settings allow; the planner has `EnterWorktree`; the researcher has `Bash`.
5. A session knows about the project what a subagent would know. Claude Code gives every subagent the project's
   `CLAUDE.md` and `AGENTS.md`; role sessions had been started without them (ADR-0004). Both files are now in the
   pack of every type that works in the repository (`pack_files`), in the cached system prompt. Found on the
   second measured run: the reader session, with every other demand equal, never opened the wiki, the settings or
   the lint configuration, which the root map names and the reader subagent had read.
6. What a command showed is written down fact by fact. In that run the reader session ran twenty probes and wrote
   twenty lines; the reader subagent ran twelve and wrote 139 located facts out of their records, which is what
   the planner after it built on. A probe record is now a source of the notes with one located item per result,
   a contradiction shows the texts at their places, and the read gate checks both.
7. Work that is done is not done again. The planner subagent built the whole design in a scratch copy and threw
   it away; the writer subagent typed it again from the plan. A planner session, told that the writer would get
   the plan alone, pasted its whole module and test file into the plan instead (876 of 1,224 lines). Now the plan
   specifies and the gate refuses a plan that is mostly code; the trial goes to the writer as a patch among its
   inputs, to start from and to answer for; the plan wins where the two differ.
8. A reviewer is given the claims a reviewer would be given. The verifier subagent had the writer's report (the
   commits, a claim per task, the decisions the plan did not make, what was noticed) and wrote 75 entries; the
   verifier session had the task list alone and wrote 17. The writer now states its work in `report.md`, the
   verify stage receives it, and the gates ask a verifier for its own checks and a critic for a run of the work.
9. A session works from the cache, and gets only what its job needs. A role session exists to start with its
   material already in its prompt, read from the prompt cache on every request, where a subagent finds and opens it
   file by file. On a reader run its cached text held the rules and the two instruction files only, and the session
   opened the material one file at a time as the subagent did; given the brief's material it still had to search the
   rest of the repository. Cutting the material by hand cost the manager a turn per stage and still missed pieces.
   Now a script chooses it at launch (`harness/pieces.py`, `pack.material`): the files are cut at their natural
   seams, and the session gets, after its pack and while they fit, its inputs, the brief's material when it receives
   `context`, the pieces its assignment lists (optional, for what no text points to), every place its texts cite as
   `path:line` with the piece that holds it, the short files they name, and the pieces whose words match the brief.
   Nothing is rewritten: every line as the file has it, after its number, an empty line left out with its number. A
   file of the pack is not given again, and what the script adds has a budget of its own, because everything a
   session carries is read on every request. The same texts give the same bytes, so the shards of a stage share them
   in the cache.

### Consequences
* Good, because the demand that produced the deeper plan is now part of every launch and cannot be left out.
* Good, because the variable text stays in the first message: sessions of one type still share their system prompt
  in the cache.
* Good, because a session that would fail its gate learns it before it stops.
* Bad, because the manager spends a turn per stage on the assignment. It is the turn it would spend on the prompt of
  a subagent. The material costs it nothing: a script chooses it.
* Neutral: the pieces chosen for their words are a guess; they are the first to go when the section is full, and
  the session opens what it lacks.
* Bad, because a planner that builds its design costs more than one that only writes. The writer that follows
  decides nothing and the reviewers find less; the sum is measured in the experiment record of the template.
* Neutral: web access stays limited to the domains in `.claude/settings.json` for every session.

## More Information
`docs/roles/MANAGER.md` section 14; `packages/harness/src/harness/launch.py` (`assignment_problem`);
`packages/harness/src/harness/gates/plan.py` (`depth_checks`); `packages/harness/src/harness/gates/read.py`
(`unsectioned`, `unsupported`); `.claude/hooks/stop-gate.py`. A type that cannot write a file gets no pieces chosen
by script: [ADR-0012](0012-a-type-that-cannot-write-accounts-for-no-material.md).
- Amended on 2026-10-04 by `docs/decisions/0015-a-type-that-is-not-blind-reads-what-a-subagent-reads.md`: a type
  that is not blind reads what a subagent reads, and a fix run may change the hook scripts by a line of its brief.
