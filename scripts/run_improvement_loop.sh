#!/usr/bin/env bash
# Long-running agent improvement loop (baseline test → plan → build → test → deploy → commit → push).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MAX="${1:-1000}"
START="${2:-}"
LOG="$ROOT/data/loop_logs/agent_loop_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$ROOT/data/loop_logs"

export PYTHONPATH="${ROOT}/scripts:${ROOT}/src:${ROOT}/autopilot-local/backend"
export LOOP_ITERATION_SLEEP_SEC="${LOOP_ITERATION_SLEEP_SEC:-60}"
export LOOP_DEPLOY_EVERY="${LOOP_DEPLOY_EVERY:-0}"
export LOOP_PYTEST_TIMEOUT_SEC="${LOOP_PYTEST_TIMEOUT_SEC:-900}"

# Optional remote smoke: export DEPLOY_BACKEND_URL=https://your-host
if [[ -z "${DEPLOY_BACKEND_URL:-}" && -n "${CLOUD_RUN_URL:-}" ]]; then
  export DEPLOY_BACKEND_URL="${CLOUD_RUN_URL}"
fi

echo "Starting improvement loop max=$MAX start=${START:-auto} log=$LOG"
echo "Cloud URL=${CLOUD_RUN_URL:-unset} deploy_every=$LOOP_DEPLOY_EVERY"

ARGS=(--max-iterations "$MAX")
if [[ -n "$START" ]]; then
  ARGS+=(--start "$START")
fi

exec python "$ROOT/scripts/autonomous_loop.py" "${ARGS[@]}" 2>&1 | tee -a "$LOG"
