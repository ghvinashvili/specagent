# The session cases of the regression suite, run on this machine (by hand or from the owner's cron), never in CI:
# `bash evals/nightly.sh`. The timeout is the suite's minutes plus 10; HARNESS_EVAL_MAX_USD caps the worst-case spend.
set -euo pipefail
cd "$(dirname "$0")/.."
cap="${HARNESS_EVAL_MAX_USD:-20}"
need="$(uv run python -c 'from pathlib import Path; from harness.evals import suite_minutes; print(suite_minutes(Path("."), "regression"))')"
minutes=$((need + 10))
echo "nightly: cap \$$cap, timeout $minutes min" >&2
HARNESS_EVAL_MAX_USD="$cap" timeout -k 10 "${minutes}m" uv run harness eval --suite regression --threshold 1.0
