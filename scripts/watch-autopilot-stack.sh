#!/usr/bin/env bash
# Health watchdog: restart APEX API, marketplace, frontend, or apex-autopilot if down.
# Intended for cron (see scripts/install-autopilot-cron.sh).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${APEX_LOG_DIR:-/tmp/apex-logs}"
mkdir -p "$LOG_DIR"

http_ok() {
  local url="$1"
  local code
  code=$(curl -s -m 5 -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
  [[ "$code" == "200" ]]
}

need_restart=0
http_ok "http://127.0.0.1:8000/health" || need_restart=1
http_ok "http://127.0.0.1:8001/api/health" || need_restart=1
http_ok "http://127.0.0.1:3000/" || need_restart=1
pgrep -f 'apex-autopilot' >/dev/null 2>&1 || need_restart=1

if [[ "$need_restart" -eq 1 ]]; then
  echo "$(date -Is) watch-autopilot-stack: unhealthy — running dev-stack.sh"
  exec bash "$ROOT/scripts/dev-stack.sh"
fi

echo "$(date -Is) watch-autopilot-stack: all services healthy"
