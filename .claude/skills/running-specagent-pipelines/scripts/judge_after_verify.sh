#!/bin/bash
# The judge, once, after every task is verified: when line 1 of every record file named says STATUS: done, put a
# detached worktree at the checkout's HEAD, launch the one agent of the judge's agents config there and watch it.
#   bash judge_after_verify.sh <agents-judge.json> <checkout> <record-file>...
# Record files are read in the config's run_dir. JUDGE_POLL (seconds between polls, default 300) and JUDGE_DELAY
# (seconds from the last STATUS line to the launch, default 600). Exit 2 for a usage or config error, the launch's
# code when it fails, else the watcher's.
if [ "$#" -lt 3 ]; then
  echo "usage: judge_after_verify.sh <agents-judge.json> <checkout> <record-file>..." >&2
  exit 2
fi
CONFIG=$1
CHECKOUT=$2
shift 2
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd) || exit 1
VARS=$(python3 -I -c '
import json, os, shlex, sys
path = sys.argv[1]
def fail(why):
    print(f"judge_after_verify.sh: {path}: {why}", file=sys.stderr)
    sys.exit(2)
try:
    with open(path, encoding="utf-8") as f:
        config = json.load(f)
except (OSError, ValueError) as e:
    fail(f"cannot read it: {e}")
agents = config.get("agents") if isinstance(config, dict) else None
if not isinstance(agents, dict) or len(agents) != 1:
    fail("must name exactly one agent in `agents`")
(name, agent), = agents.items()
try:
    run, cwd, settings = config["run_dir"], agent["cwd"], os.path.join(config["run_dir"], agent["settings"])
    dirs, common = list(agent.get("add_dirs", [])), list(config.get("common", []))
except (AttributeError, KeyError, TypeError) as e:
    fail(f"needs `run_dir`, and `cwd` and `settings` in the agent: {e}")
if not os.path.isfile(settings):
    fail(f"no settings file {settings}")
def array(values):
    return "(" + " ".join(shlex.quote(str(v)) for v in values) + ")"
words = {"D": run, "N": name, "W": cwd, "SETTINGS": settings}
print("; ".join(f"{k}={shlex.quote(str(v))}" for k, v in words.items()))
print(f"DIRS={array(dirs)}; COMMON={array(common)}")
' "$CONFIG") || exit 2
eval "$VARS"

done_all() {
  local f p
  for f in "$@"; do
    case $f in /*) p=$f ;; *) p=$D/$f ;; esac
    [ "$(head -1 "$p" 2>/dev/null)" = "STATUS: done" ] || return 1
  done
}
until done_all "$@"; do sleep "${JUDGE_POLL:-300}"; done
echo "$(date +%H:%M) main: all $# STATUS lines done; judge starts in ${JUDGE_DELAY:-600} s" >> "$D/_watch.log"
sleep "${JUDGE_DELAY:-600}"
HEAD=$(git -C "$CHECKOUT" rev-parse HEAD) || exit 1
[ -d "$W" ] || git -C "$CHECKOUT" worktree add --detach "$W" "$HEAD" >> "$D/_watch.log" 2>&1 || exit 1
mkdir -p "$D/scratch/judge"
ADD=()
[ "${#DIRS[@]}" -gt 0 ] && ADD=(--add-dir "${DIRS[@]}")
PACK=()  # the judge lane's frozen pack in its system prompt (owner, 2026-11-01), when the run built one
TASK="Read and follow the assignment in $D/_judge-assignment.md."
[ -f "$D/_pack-judge.md" ] && PACK=(--append-system-prompt-file "$D/_pack-judge.md") &&
  TASK="Your system prompt holds this lane's pack, your assignment included: follow it."
(cd "$W" && claude --name "$N" "${ADD[@]}" "${COMMON[@]}" --settings "$(cat "$SETTINGS")" "${PACK[@]}" \
  --bg "$TASK Start now. Work in English only (thinking, replies, tool descriptions, files).") \
  >> "$D/_watch.log" 2>&1
code=$?
echo "$(date +%H:%M) main: $N launched at $HEAD in $W (exit $code)" >> "$D/_watch.log"
[ "$code" -ne 0 ] && exit "$code"
python3 -I "$S/watch_agents.py" "$CONFIG" 2>&1 | tee -a "$D/_watch.log"
exit "${PIPESTATUS[0]}"
