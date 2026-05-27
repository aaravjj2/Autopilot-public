#!/usr/bin/env bash
# Smoke test APEX (:8000) + Marketplace (:8001) + key frontend routes.
set -euo pipefail

APEX="${APEX_URL:-http://127.0.0.1:8000}"
MKT="${MARKET_URL:-http://127.0.0.1:8001}"
WEB="${WEB_URL:-http://127.0.0.1:3000}"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'
fail=0

check_http() {
  local name="$1" url="$2"
  local code
  code=$(curl -s -m 20 -o /tmp/smoke-body.json -w "%{http_code}" "$url" || echo "000")
  if [[ "$code" != "200" ]]; then
    echo -e "${RED}FAIL${NC} $name ($url) HTTP $code"
    fail=1
    return
  fi
  echo -e "${GREEN}OK${NC}   $name HTTP $code"
}

echo "=== Dual-stack smoke test ==="
check_http "APEX /health" "$APEX/health"
check_http "APEX /account" "$APEX/account"
check_http "APEX /positions" "$APEX/positions"
check_http "APEX /integrations" "$APEX/integrations"
check_http "Market /api/health" "$MKT/api/health"
check_http "Market /api/portfolios" "$MKT/api/portfolios"
check_http "Market /api/dashboard" "$MKT/api/dashboard"
check_http "Web /dashboard" "$WEB/dashboard"
check_http "Web /dashboard/marketplace" "$WEB/dashboard/marketplace"
check_http "Web /dashboard/settings" "$WEB/dashboard/settings"

if [[ "$fail" -ne 0 ]]; then
  echo -e "${RED}Smoke test failed${NC}"
  exit 1
fi
echo -e "${GREEN}All smoke checks passed${NC}"
