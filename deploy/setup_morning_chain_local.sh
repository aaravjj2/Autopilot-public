#!/usr/bin/env bash
# Install the standalone APEX morning-chain scheduler as a systemd unit (Linux).
# Production uses in-process APEX_MORNING_CHAIN=true (set via env / Docker).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
USER_NAME="${SUDO_USER:-$(whoami)}"
UNIT="/etc/systemd/system/apex-scheduler.service"

sed "s/%(U)s/${USER_NAME}/g" "${ROOT}/deploy/apex-scheduler.service" | sudo tee "${UNIT}" >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now apex-scheduler
echo ">> apex-scheduler enabled. Status:"
systemctl status apex-scheduler --no-pager || true
