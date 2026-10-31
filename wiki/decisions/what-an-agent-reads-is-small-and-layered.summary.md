Decision (owner, 2026-10-28): what an agent reads is small and layered.
Plans are folders of task files of at most 1,500 lines; an index has one line per page; a page stays under 12 KB.
A large file is read by its sections through ops/outline.py, never whole.
The record is ADR-0026.
