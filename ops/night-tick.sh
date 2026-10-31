#!/usr/bin/env bash
# One unattended fire of a declared loop. A deterministic check decides first, without a model and without a tick
# (`harness loop due`, docs/decisions/0022-a-prompt-loop-is-judged-by-code.md): the pause switch, the loop's
# readiness and exit check, and for the poll loop whether `harness poll --all-active` left the manager anything to
# do. Only then a new headless session of the role type the human talks to (manager) starts, with the message the
# check printed: a prompt loop's file, which ticks by itself, or the loop-tick skill, so that one fire ticks once.
# Nobody answers prompts, so anything that would prompt is denied. Everything the session needs is on disk.
set -euo pipefail
loop="${1:?usage: ops/night-tick.sh <loop-name>}"
repo="$(cd "$(dirname "$0")/.." && pwd)"
runs="$(dirname "$repo")/runs"  # the runs root, as harness state.runs_root finds it
[ -f "$runs/.harness-runs" ] || runs="$(dirname "$repo")/$(basename "$repo")-runs"
mkdir -p "$runs/_audit/night-tick"
cd "$repo"
log="$runs/_audit/night-tick-$(date +%F).jsonl"
# The wiki's sources are renewed first, by code and without a session: the plugin's gate refuses every operation of a vault
# that has one source past its date, so `--refresh` renews the pages due within 30 days and prints "nothing to renew" when
# none is. The pause switch does not hold it (a long pause must not age the vault); a failure is logged and the fire goes on.
# What it renewed is committed here too, so that no dirty checkout blocks a merge that touches `wiki/log.md`: on `main`
# only, and only the paths `--refresh` rewrites (`git commit -- <paths>` leaves any other staged file out of it). On
# another branch, or when git refuses, the reason is logged, the renewal stays in the checkout and the fire goes on.
not_committed() { printf 'renewal not committed: %s\n' "$(printf '%s' "$*" | tr '\n' ' ' | cut -c1-300)" >>"$log"; }
commit_renewal() {
  local paths=(wiki/meta/ledgers wiki/log.md wiki/hot.md) changed branch out
  changed="$(git status --porcelain -- "${paths[@]}" 2>/dev/null)" ||
    { not_committed "git status failed (exit $?)"; return 0; }
  [ -n "$changed" ] || return 0  # nothing was renewed
  branch="$(git symbolic-ref --short -q HEAD 2>/dev/null)" || branch=
  [ "$branch" = main ] || { not_committed "on ${branch:-a detached HEAD}, not main"; return 0; }
  out="$(git commit -q -m 'chore(wiki): renew the due sources (night tick)' -- "${paths[@]}" 2>&1)" ||
    not_committed "git commit failed: $out"
}
if [ "$loop" = wiki-ingest ] && [ -f ops/obsidian-ingest.py ]; then
  if python3 ops/obsidian-ingest.py --refresh >>"$log" 2>&1; then
    commit_renewal
  else
    printf 'ops/obsidian-ingest.py --refresh failed (exit %s)\n' "$?" >>"$log"
  fi
fi
if ! message="$(uv run harness loop due --name "$loop" --plain 2>>"$log")"; then
  printf '%s\n' "$message" >>"$log"  # why this fire had nothing to do: no session started
  exit 0
fi
out="$(mktemp "$runs/_audit/night-tick/.$loop.XXXXXX")"
status=0
claude -p --agent manager \
  --add-dir "$runs" \
  --permission-mode dontAsk --permission-prompts none \
  --max-turns 40 --max-budget-usd 5 \
  --output-format json \
  "$message" >"$out" 2>>"$log" || status=$?
# one file per fire, named by the loop and the UTC time its session ended: `harness loop tick` counts its cost
mv "$out" "$runs/_audit/night-tick/$loop-$(date -u +%Y%m%dT%H%M%SZ).json"
exit "$status"
