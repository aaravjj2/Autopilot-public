#!/usr/bin/env bash
# Long-running agent improvement loop (test → plan → build → test → commit → push).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MAX="${1:-1000}"
START="${2:-}"
LOG="$ROOT/data/loop_logs/agent_loop_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$ROOT/data/loop_logs"

echo "Starting improvement loop max=$MAX start=${START:-auto} log=$LOG"

ARGS=(--max-iterations "$MAX")
if [[ -n "$START" ]]; then
  ARGS+=(--start "$START")
fi

exec python "$ROOT/scripts/autonomous_loop.py" "${ARGS[@]}" 2>&1 | tee -a "$LOG"
