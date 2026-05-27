#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/autopilot-local/frontend"
LOG_DIR="${ROOT_DIR}/logs/unified"
PID_DIR="${ROOT_DIR}/autopilot-local/.pids"

mkdir -p "${LOG_DIR}" "${PID_DIR}"

BACKEND_LOG="${LOG_DIR}/backend.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"
BACKEND_PID_FILE="${PID_DIR}/backend_8000.pid"
FRONTEND_PID_FILE="${PID_DIR}/frontend_3000.pid"

if curl -sf "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
  EXISTING_BACKEND_PID="$(ss -ltnp 2>/dev/null | awk '/127\.0\.0\.1:8000/ {print $NF}' | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | head -1)"
  if [[ -n "${EXISTING_BACKEND_PID}" ]]; then
    echo "${EXISTING_BACKEND_PID}" >"${BACKEND_PID_FILE}"
    echo "Backend already running on :8000 (PID ${EXISTING_BACKEND_PID})"
  else
    echo "Backend already running on :8000"
  fi
elif [[ -f "${BACKEND_PID_FILE}" ]] && kill -0 "$(cat "${BACKEND_PID_FILE}")" 2>/dev/null; then
  echo "Backend already running with PID $(cat "${BACKEND_PID_FILE}")"
else
  (
    cd "${ROOT_DIR}"
    PYTHONPATH=src ALPACA_PAPER_TRADE=true python -m uvicorn backend_api:app --host 127.0.0.1 --port 8000
  ) >"${BACKEND_LOG}" 2>&1 &
  echo $! >"${BACKEND_PID_FILE}"
  echo "Started backend :8000 (PID $(cat "${BACKEND_PID_FILE}"))"
fi

for _ in {1..40}; do
  if curl -sf "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    echo "Backend health check passed"
    break
  fi
  sleep 1
done

if ! curl -sf "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
  echo "Backend failed health check after startup"
  exit 1
fi

if curl -sf "http://127.0.0.1:3000" >/dev/null 2>&1; then
  EXISTING_FRONTEND_PID="$(ss -ltnp 2>/dev/null | awk '/:3000/ {print $NF}' | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | head -1)"
  if [[ -n "${EXISTING_FRONTEND_PID}" ]]; then
    echo "${EXISTING_FRONTEND_PID}" >"${FRONTEND_PID_FILE}"
    echo "Frontend already running on :3000 (PID ${EXISTING_FRONTEND_PID})"
  else
    echo "Frontend already running on :3000"
  fi
elif [[ -f "${FRONTEND_PID_FILE}" ]] && kill -0 "$(cat "${FRONTEND_PID_FILE}")" 2>/dev/null; then
  echo "Frontend already running with PID $(cat "${FRONTEND_PID_FILE}")"
else
  (
    cd "${FRONTEND_DIR}"
    npm run dev -- --port 3000
  ) >"${FRONTEND_LOG}" 2>&1 &
  echo $! >"${FRONTEND_PID_FILE}"
  echo "Started frontend :3000 (PID $(cat "${FRONTEND_PID_FILE}"))"
fi

echo "Unified stack started."
echo "- Backend: http://127.0.0.1:8000 (log: ${BACKEND_LOG})"
echo "- Frontend: http://127.0.0.1:3000 (log: ${FRONTEND_LOG})"
