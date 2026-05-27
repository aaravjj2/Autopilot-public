#!/usr/bin/env bash
# Install a 5-minute cron job to keep the APEX stack + apex-autopilot scheduler up.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${APEX_LOG_DIR:-/tmp/apex-logs}"
mkdir -p "$LOG_DIR"
chmod +x "$ROOT/scripts/watch-autopilot-stack.sh" "$ROOT/scripts/dev-stack.sh"

LINE="*/5 * * * * cd $ROOT && APEX_LOG_DIR=$LOG_DIR bash scripts/watch-autopilot-stack.sh >>$LOG_DIR/watch-autopilot.log 2>&1 # apex-autopilot-watch"

existing="$(crontab -l 2>/dev/null || true)"
filtered="$(printf '%s\n' "$existing" | grep -v 'apex-autopilot-watch' | grep -v 'watch-autopilot-stack.sh' || true)"
{
  printf '%s\n' "$filtered" | sed '/^$/d'
  echo "$LINE"
} | crontab -

echo "Installed cron (every 5 min): watch-autopilot-stack.sh"
echo "  Log: $LOG_DIR/watch-autopilot.log"
crontab -l | grep -F watch-autopilot-stack || true
