#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
ROOT_PARENT="$(cd "$ROOT/.." && pwd)"

if [[ ! -f .env.local ]]; then
  echo "Copy .env.local.example to .env.local and add Alpaca paper keys."
  exit 1
fi

if [[ ! -d "$ROOT_PARENT/.venv" ]]; then
  echo "Create root .venv: python3 -m venv .venv && .venv/bin/pip install -e \"[dev]\""
  exit 1
fi

# Backend venv (optional)
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -r backend/requirements.txt
fi

if [[ ! -d frontend/node_modules ]]; then
  (cd frontend && npm install)
fi

if [[ ! -d node_modules ]]; then
  npm install
fi

export PYTHONPATH="$ROOT_PARENT/src:${PYTHONPATH:-}"
npm run dev
