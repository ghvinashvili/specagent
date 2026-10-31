# The checkout is a claude-obsidian vault (summary)

The checkout root is the plugin's vault and `wiki/` its pages, made with the plugin's own adopt. The plugin is
declared in the internal marketplace with a github source and installed from git at project scope; nothing at user
scope. Every session starts with `wiki/hot.md`; pages carry `created` and `tags`; summaries are excluded from the
plugin's lint; `python3 ops/adopt-obsidian.py lint` is clean before a commit. `ops/adopt-obsidian.py --apply` moves
another checkout the same way.
