# A run that does not move: summary for the owner

- Signs: `harness poll` prints the same actions again, `state.json` is old, or a unit stays working or blocked.
- A table gives, for each action of the poll (attention, timeout, resume, max_attempts, escalation, the limits, a
  paused run), its cause and what to do.
- The status answers `locked`, `config_changed` and `already_launched` are explained. After the fix, rewrite the handoff
  and write a harness cause down for the weekly review.
