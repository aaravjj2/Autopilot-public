#!/usr/bin/env bash
# Free TCP :8000 when a non-APEX process is bound (common on WSL dev machines).
# APEX health includes proposals/events; foreign APIs return a different JSON shape.
set -euo pipefail

PORT="${APEX_PORT:-8000}"
HEALTH_URL="http://127.0.0.1:${PORT}/health"

apex_health_ok() {
  local body
  body="$(curl -sf --max-time 3 "$HEALTH_URL" 2>/dev/null || true)"
  [[ -n "$body" ]] || return 1
  # APEX /health includes these keys (see backend_api.py)
  echo "$body" | grep -q '"proposals"' && echo "$body" | grep -q '"timestamp"'
}

pids_on_port() {
  if command -v ss >/dev/null 2>&1; then
    ss -tlnp "sport = :${PORT}" 2>/dev/null | grep -oP 'pid=\K[0-9]+' || true
  elif command -v lsof >/dev/null 2>&1; then
    lsof -ti ":${PORT}" 2>/dev/null || true
  fi
}

free_port_if_not_apex() {
  if apex_health_ok; then
    return 0
  fi
  local pid
  for pid in $(pids_on_port); do
    [[ -n "$pid" ]] || continue
    echo "[ensure_apex_port_8000] Stopping PID ${pid} on :${PORT} (not APEX health)"
    kill "$pid" 2>/dev/null || true
  done
  sleep 2
  if apex_health_ok; then
    return 0
  fi
  # Still occupied — force kill anything left on the port
  for pid in $(pids_on_port); do
    [[ -n "$pid" ]] || continue
    kill -9 "$pid" 2>/dev/null || true
  done
  sleep 1
}

free_port_if_not_apex

if ! apex_health_ok; then
  echo "[ensure_apex_port_8000] Port :${PORT} is free for APEX (or APEX not started yet)." >&2
fi
