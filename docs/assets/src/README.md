# The diagrams as text

The README shows these four flows as pictures drawn by the archify skill from the specs in this folder
(`<name>.<type>.json`); here they stay text you can edit
([decision](../../../wiki/decisions/diagrams-are-mermaid-text.md)).

## The run loop

```mermaid
flowchart LR
  you(["you"]) -->|a task, one yes| manager["manager chat"]
  manager -->|launch| roles["role sessions"]
  manager -->|when no spec exists| spec["spec-writer"] -->|the spec| roles
  roles --> records[("run folder")] --> gate{"gates"}
  gate -->|pass| manager
  gate -.->|findings| roles
  roles -->|pages| vault[("vault")]
  vault -.->|read first| roles
  manager -->|one branch| you
```

## The roles and their records

```mermaid
flowchart TD
  spec["spec-writer"] -->|the spec| planner
  planner --> critic
  critic -.->|C, A| planner
  critic -.->|open ids| fixer["plan fixer, on demand: edits unbuilt tasks"]
  builders["builders a, b: two sessions, disjoint files"]
  critic -->|reviewed| builders
  builders --> verifier
  verifier -.->|V| builders
  builders -.->|"B ids (wrong steps)"| fixer
  verifier -.->|"(plan), (spec) V ids"| fixer
  fixer -.->|"fixed task files (unbuilt tasks)"| builders
  fixer -.->|"answer line in critique-response.md: the id's owner re-checks"| critic
  fixer -.->|"answer line in critique-response.md: the id's owner re-checks"| verifier
  verifier -.->|plan findings| planner
  verifier -->|all verified| judge
  judge -.->|"(code) blockers"| builders
  judge -.->|"(plan), (spec) blockers"| fixer
  judge -->|verdict| manager["manager chat: gate, merge"]
```

## The knowledge layer

```mermaid
flowchart TD
  lessons["lessons.md"] -->|decisions| wiki["wiki/: index, decision pages"]
  context["context/: raw sources"] -->|compiled| wiki
  wiki -->|ingest| hot["ledgers, hot.md"] -->|at start| session["every session: hot.md, index, graph, files"]
  wiki -->|each commit| graph["code graph: graphify, wiki/graph/"] -->|ask first| session
  wiki -->|every project| vault["your vault, read on need"]
  records["a run's records: logs, transcripts"] -->|measurements| vault
  vault -->|your yes| gate{"contribute.py"}
  gate -->|passes| commons["public commons, not built yet"]
  commons -.->|a source| session
```

## A session's life

```mermaid
flowchart TD
  fresh["fresh session"] --> reads["brief, lessons.md Read first, facts pack, hand-over note last"] --> wait["waiter"]
  wait -->|input| unit["one unit"] --> files["records"] --> check{"unit done (by itself), or 200k (the watcher)?"}
  check -->|no| unit
  check -->|yes| commit["commit, then the note"] --> handover["hand-over note"] --> watcher --> fresh
```
