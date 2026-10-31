"""The argv prefix of every git command the harness runs: it fires no hook (ADR-0029)."""

GIT = ("git", "-c", "core.hooksPath=/dev/null")
