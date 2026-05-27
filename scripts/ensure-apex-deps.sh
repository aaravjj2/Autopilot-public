#!/usr/bin/env bash
# Install optional runtime deps (TradingAgents + langgraph) into repo .venv.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python"
PIP="${ROOT}/.venv/bin/pip"

if [[ ! -x "$PY" ]]; then
  echo "Missing .venv — run: python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'"
  exit 1
fi

if [[ -d "${ROOT}/external/TradingAgents" ]]; then
  if ! "$PY" -c "import tradingagents" 2>/dev/null; then
    echo "Installing TradingAgents (editable) + langgraph stack..."
    "$PIP" install -q -e "${ROOT}/external/TradingAgents"
  fi
fi

"$PY" -c "import langgraph" 2>/dev/null || "$PIP" install -q 'langgraph>=0.4.8' 'stockstats>=0.6.5'

echo "APEX optional deps OK"
