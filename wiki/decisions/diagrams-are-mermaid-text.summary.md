Decision (owner, 2026-10-29): diagrams are Mermaid text; the template carries no diagram renderer.
harness map writes one Mermaid flowchart per stage table to docs/generated/maps/<name>.md; GitHub and Obsidian draw it.
A box per stage with its role type and tags, a diamond where a human approves, a dashed `revise` arrow, a box per route.
harness map --check and docs-check report a stale map; harness map removes the old *.workflow.json files.
