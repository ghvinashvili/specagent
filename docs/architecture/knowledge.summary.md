# Knowledge layer: summary for the owner

- Stores: `context/` (raw material), `wiki/` (the project's Obsidian vault: concepts, entities, sources, decisions and
  the plans link), the code graph (`graphify-out/` and `wiki/graph/`, generated), `docs/`, and the owner's vault, which
  a project only reads.
- The wiki has two writers: the librarian from `context/`, and the builder of a task in the task's own commit. A code
  change carries its pages, or the planner's `tasks.json` says `docs: none — <reason>` for its task.
- Only verified pages reach a knowledge pack; `harness integrate` marks them when every verdict of the run is accept.
- Retrieval: the wiki and the graph first, the repository's files second; the owner's vault only for the owner's rules
  and past decisions.
