#!/usr/bin/env bash
# Start full APEX stack: engine + health + Streamlit ops + copy-trading API + Next.js UI.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  echo "Run: python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'"
  exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate
# Keys loaded via Python bootstrap (avoids CRLF issues in keys.env when sourcing in bash)
export PYTHONPATH="$ROOT/src:${PYTHONPATH:-}"
.venv/bin/python -c "from apex.core.env_bootstrap import bootstrap_environment; bootstrap_environment(force=True)"

export PYTHONPATH="$ROOT/src:${PYTHONPATH:-}"
export COPY_TRADING_ENABLED="${COPY_TRADING_ENABLED:-true}"
export COPY_TRADING_API_URL="${COPY_TRADING_API_URL:-http://127.0.0.1:8001}"
export NEXT_PUBLIC_APEX_API_URL="${NEXT_PUBLIC_APEX_API_URL:-http://127.0.0.1:8000}"
export NEXT_PUBLIC_MARKETPLACE_API_URL="${NEXT_PUBLIC_MARKETPLACE_API_URL:-http://127.0.0.1:8001}"
export COPY_TRADING_WEB_URL="${COPY_TRADING_WEB_URL:-http://127.0.0.1:3000}"
export AUTOPILOT_LOCAL_PATH="${AUTOPILOT_LOCAL_PATH:-$ROOT/autopilot-local}"

bash "$ROOT/scripts/sync-copy-trading-env.sh"

mkdir -p "$ROOT/logs"

stop_all() {
  pkill -f 'apex-autopilot' 2>/dev/null || true
  pkill -f 'apex-healthz' 2>/dev/null || true
  pkill -f 'uvicorn main:app.*8001' 2>/dev/null || true
  pkill -f 'uvicorn backend_api:app.*8000' 2>/dev/null || true
  pkill -f 'next dev.*3000' 2>/dev/null || true
  sleep 1
}

if [[ "${1:-}" == "--restart" ]]; then
  stop_all
fi

# Copy-trading backend deps
if [[ ! -f "$ROOT/autopilot-local/.venv/bin/uvicorn" ]] 2>/dev/null; then
  python3 -m venv "$ROOT/autopilot-local/.venv" 2>/dev/null || true
  "$ROOT/autopilot-local/.venv/bin/pip" install -q -r "$ROOT/autopilot-local/backend/requirements.txt"
fi
if [[ ! -d "$ROOT/autopilot-local/frontend/node_modules" ]]; then
  (cd "$ROOT/autopilot-local/frontend" && npm install)
fi

echo "Starting APEX Autopilot (scheduler)…"
nohup .venv/bin/apex-autopilot >>"$ROOT/logs/autopilot.log" 2>&1 &

echo "Starting health :8088…"
APEX_HEALTH_BIND=0.0.0.0 nohup .venv/bin/apex-healthz >>"$ROOT/logs/health.log" 2>&1 &

echo "Starting Streamlit ops :8501…"
# Streamlit ops dashboard removed; skip starting it.

echo "Starting APEX trading API (backend_api) :8000…"
(
  cd "$ROOT"
  PYTHONPATH="$ROOT/src:${PYTHONPATH:-}" .venv/bin/python -m uvicorn backend_api:app \
    --host 0.0.0.0 --port 8000 >>"$ROOT/logs/backend-api.log" 2>&1
) &

echo "Starting copy-trading API (main) :8001…"
(
  cd "$ROOT/autopilot-local/backend"
  PYTHONPATH="$ROOT/src:${PYTHONPATH:-}" "$ROOT/autopilot-local/.venv/bin/python" -m uvicorn main:app \
    --host 0.0.0.0 --port 8001 >>"$ROOT/logs/marketplace-api.log" 2>&1
) &

echo "Starting copy-trading UI :3000…"
(
  cd "$ROOT/autopilot-local/frontend"
  nohup npm run dev >>"$ROOT/logs/copy-trading-web.log" 2>&1
) &

sleep 4
echo ""
echo "APEX stack URLs:"
echo "APEX stack URLs:"
echo "  Health:            http://127.0.0.1:${APEX_HEALTH_PORT:-8088}/healthz"
echo "  Trading UI:        http://127.0.0.1:3000"
echo "  APEX API:          http://127.0.0.1:8000/health"
echo "  Marketplace API:   http://127.0.0.1:8001/api/health"
echo "Logs: $ROOT/logs/"
