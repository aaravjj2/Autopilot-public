#!/usr/bin/env bash
# Start APEX backend (:8000) + Marketplace backend (:8001) + Next.js frontend (:3000)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND="$ROOT/autopilot-local/frontend"
BACKEND_LOCAL="$ROOT/autopilot-local/backend"
LOG_DIR="${APEX_LOG_DIR:-/tmp/apex-logs}"
mkdir -p "$LOG_DIR"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'
ok() { echo -e "${GREEN}[ok]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC} $*"; }
fail() { echo -e "${RED}[fail]${NC} $*"; exit 1; }

http_ok() {
  local url="$1"
  local code
  code=$(curl -s -m 3 -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
  [[ "$code" == "200" ]]
}

wait_url() {
  local url="$1"
  local label="$2"
  local max="${3:-90}"
  for i in $(seq 1 "$max"); do
    local code
    code=$(curl -s -m 3 -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    if [[ "$code" == "200" ]]; then
      ok "$label ($url) -> HTTP $code"
      return 0
    fi
    sleep 1
  done
  fail "$label did not respond with HTTP 200 at $url (last code: ${code:-timeout})"
}

stop_stale() {
  warn "Stopping stale processes on :8000 / :8001 / :3000 and apex-autopilot"
  pkill -9 -f 'uvicorn backend_api:app' 2>/dev/null || true
  pkill -9 -f 'uvicorn main:app' 2>/dev/null || true
  pkill -f 'apex-autopilot' 2>/dev/null || true
  pkill -f 'next dev -p 3000' 2>/dev/null || true
  pkill -f 'next-server' 2>/dev/null || true
  sleep 2
  # Free ports if something still holds them
  for port in 8000 8001 3000; do
    if command -v fuser >/dev/null 2>&1; then
      fuser -k "${port}/tcp" 2>/dev/null || true
    fi
  done
  sleep 1
}

apex_healthy() {
  http_ok "http://127.0.0.1:8000/health"
}

market_healthy() {
  http_ok "http://127.0.0.1:8001/api/health"
}

if [[ "${1:-}" == "--restart" ]]; then
  stop_stale
fi

cd "$ROOT"
export PYTHONPATH="$ROOT/src:${PYTHONPATH:-}"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
else
  PY="python3"
fi

"$PY" -c "import sys; sys.path.insert(0,'src'); from apex.core.env_bootstrap import bootstrap_environment; bootstrap_environment(force=True)" 2>/dev/null || true

bash "$ROOT/scripts/ensure-apex-deps.sh" 2>/dev/null || true

export APEX_PM_AGENTS_LOOP="${APEX_PM_AGENTS_LOOP:-true}"
export APEX_ARB_SCAN_LOOP="${APEX_ARB_SCAN_LOOP:-true}"

bash "$ROOT/scripts/sync-copy-trading-env.sh" 2>/dev/null || true
cp -f "$ROOT/autopilot-local/.env.local" "$FRONTEND/.env.local" 2>/dev/null || true

AUTOPILOT_BIN="$ROOT/.venv/bin/apex-autopilot"
start_autopilot_scheduler() {
  if [[ ! -x "$AUTOPILOT_BIN" ]]; then
    warn "apex-autopilot not installed (.venv/bin/apex-autopilot missing)"
    return 0
  fi
  if pgrep -f 'apex-autopilot' >/dev/null 2>&1; then
    ok "apex-autopilot scheduler already running"
    return 0
  fi
  ok "Starting apex-autopilot (APScheduler cron jobs)"
  (
    cd "$ROOT"
    PYTHONPATH="$ROOT/src:${PYTHONPATH:-}" nohup "$AUTOPILOT_BIN" >>"$LOG_DIR/autopilot.log" 2>&1 &
    echo $! >"$LOG_DIR/autopilot.pid"
  )
}

# Wrong app on :8000 (copy-trading main:app) returns 404 on /health — always replace if not APEX
if [[ "${1:-}" == "--restart" ]] && apex_healthy; then
  warn "Restarting APEX API to reload .env"
  pkill -9 -f 'uvicorn backend_api:app' 2>/dev/null || true
  fuser -k 8000/tcp 2>/dev/null || true
  sleep 2
fi

if ! apex_healthy; then
  if curl -s -m 2 -o /dev/null http://127.0.0.1:8000/ 2>/dev/null; then
    warn "Port 8000 is up but not APEX /health — killing and restarting backend_api"
    pkill -9 -f 'uvicorn main:app' 2>/dev/null || true
    fuser -k 8000/tcp 2>/dev/null || true
    sleep 2
  fi
  ok "Starting APEX engine API on :8000"
  nohup "$PY" -m uvicorn backend_api:app --host 0.0.0.0 --port 8000 \
    >"$LOG_DIR/backend-apex.log" 2>&1 &
  echo $! >"$LOG_DIR/backend-apex.pid"
else
  ok "APEX API healthy on :8000"
fi

if ! market_healthy; then
  ok "Starting marketplace API on :8001"
  # Prefer root venv (has apex deps); fallback to autopilot-local venv
  MARKET_PY="$PY"
  if [[ -x "$ROOT/autopilot-local/.venv/bin/python" ]]; then
    if "$ROOT/autopilot-local/.venv/bin/python" -c "import pydantic_settings" 2>/dev/null; then
      MARKET_PY="$ROOT/autopilot-local/.venv/bin/python"
    else
      "$ROOT/autopilot-local/.venv/bin/pip" install -q -r "$BACKEND_LOCAL/requirements.txt" pydantic-settings 2>/dev/null || true
      if "$ROOT/autopilot-local/.venv/bin/python" -c "import pydantic_settings" 2>/dev/null; then
        MARKET_PY="$ROOT/autopilot-local/.venv/bin/python"
      fi
    fi
  fi
  (
    cd "$BACKEND_LOCAL"
    PYTHONPATH="$ROOT/src:${PYTHONPATH:-}" nohup "$MARKET_PY" -m uvicorn main:app --host 0.0.0.0 --port 8001 \
      >"$LOG_DIR/backend-market.log" 2>&1
  ) &
  echo $! >"$LOG_DIR/backend-market.pid"
else
  ok "Marketplace API healthy on :8001"
fi

if ! http_ok "http://127.0.0.1:3000/"; then
  ok "Starting frontend on :3000"
  if [[ ! -d "$FRONTEND/node_modules" ]]; then
    (cd "$FRONTEND" && npm install)
  fi
  (cd "$FRONTEND" && nohup npm run dev >"$LOG_DIR/frontend.log" 2>&1 & echo $! >"$LOG_DIR/frontend.pid")
else
  ok "Frontend already on :3000"
fi

start_autopilot_scheduler

wait_url "http://localhost:8000/health" "APEX API"
wait_url "http://localhost:8001/api/health" "Marketplace API"
wait_url "http://localhost:3000/dashboard" "Dashboard"

echo ""
ok "Stack ready:"
echo "  Frontend:     http://localhost:3000/"
echo "  Dashboard:    http://localhost:3000/dashboard"
echo "  Marketplace:  http://localhost:3000/dashboard/marketplace"
echo "  APEX API:     http://localhost:8000/health"
echo "  Market API:   http://localhost:8001/api/health"
echo "  Logs:         $LOG_DIR/"
