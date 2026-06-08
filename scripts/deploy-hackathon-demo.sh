#!/usr/bin/env bash
# Deploy hackathon judge stack locally or on any Docker host.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export DEMO_MODE="${DEMO_MODE:-true}"
export ALPACA_PAPER_TRADE="${ALPACA_PAPER_TRADE:-true}"

echo "Building hackathon stack (DEMO_MODE=$DEMO_MODE)..."
docker compose -f docker-compose.hackathon.yml build

echo "Starting services..."
docker compose -f docker-compose.hackathon.yml up -d

echo "Waiting for API health..."
for i in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:8000/api/demo/status" >/dev/null 2>&1; then
    echo "API ready."
    curl -s "http://127.0.0.1:8000/api/demo/status" | python3 -m json.tool
    echo ""
    echo "Terminal:  http://127.0.0.1:3000/dashboard/arb-radar"
    echo "Agent API: http://127.0.0.1:8000/api/agent/missions"
    echo "Set PUBLIC_DEMO_URL in .env after publishing your Docker image."
    exit 0
  fi
  sleep 2
done

echo "Health check timed out — run: docker compose -f docker-compose.hackathon.yml logs backend"
exit 1
