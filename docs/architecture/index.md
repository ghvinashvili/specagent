# Architecture: index

`ARCHITECTURE.md` at the root is the one-page map. The pages here go one level deeper.

- [Harness](harness.md): the manager, role types, runs, gates, the two caches
- [Memory map](memory.md): working, episodic, semantic and procedural stores
- [Memory policy](memory-policy.md): what each store may remember and what never
- [Knowledge layer](knowledge.md): context, wiki, graph and docs; the knowledge pack; retrieval order
- [Connections between chats](connections.md): every mechanism by which sessions exchange work
- [Harness module map](harness-modules.md): one row per module of the harness package and what it owns
- [What settings and hooks enforce](harness-enforcement.md): the rules no instruction to a session lifts

Where a decision was made and why: `docs/decisions/`. What a role type may see: `docs/roles/need-to-know.yaml`.
What comes from outside the repository: `docs/roles/EXTENSIONS.md`.
