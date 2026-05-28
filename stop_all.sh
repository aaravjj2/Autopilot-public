#!/bin/bash
# APEX Autopilot - Stop All Services

APEX_DIR="/home/aarav/Aarav/Autopilot"
LOG_DIR="/tmp/apex-logs"

echo "Stopping APEX services..."

# Stop APEX Backend
if [ -f "$LOG_DIR/backend.pid" ]; then
    kill $(cat "$LOG_DIR/backend.pid") 2>/dev/null && echo "✓ APEX backend stopped" || echo "✗ APEX backend not running"
    rm -f "$LOG_DIR/backend.pid"
fi

# Stop Marketplace Backend
if [ -f "$LOG_DIR/marketplace.pid" ]; then
    kill $(cat "$LOG_DIR/marketplace.pid") 2>/dev/null && echo "✓ Marketplace stopped" || echo "✗ Marketplace not running"
    rm -f "$LOG_DIR/marketplace.pid"
fi
pkill -f "uvicorn main:app.*8001" 2>/dev/null || true

# Stop Frontend
if [ -f "$LOG_DIR/frontend.pid" ]; then
    kill $(cat "$LOG_DIR/frontend.pid") 2>/dev/null && echo "✓ Frontend stopped" || echo "✗ Frontend not running"
    rm -f "$LOG_DIR/frontend.pid"
fi

# Stop Scheduler
if [ -f "$LOG_DIR/scheduler.pid" ]; then
    kill $(cat "$LOG_DIR/scheduler.pid") 2>/dev/null && echo "✓ Scheduler stopped" || echo "✗ Scheduler not running"
    rm -f "$LOG_DIR/scheduler.pid"
fi
pkill -f "apex.main" 2>/dev/null || true

# Stop Discord Bot
if [ -f "$LOG_DIR/discord.pid" ]; then
    kill $(cat "$LOG_DIR/discord.pid") 2>/dev/null && echo "✓ Discord Bot stopped" || echo "✗ Discord Bot not running"
    rm -f "$LOG_DIR/discord.pid"
fi

# Kill any remaining processes
pkill -f "uvicorn backend_api" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
pkill -f "scheduler.py" 2>/dev/null || true
pkill -f "run_discord_bot" 2>/dev/null || true

# Release :8000 if a stale non-APEX listener remains
if [[ -x "$APEX_DIR/scripts/ensure_apex_port_8000.sh" ]]; then
    bash "$APEX_DIR/scripts/ensure_apex_port_8000.sh" 2>/dev/null || true
fi

echo "All APEX services stopped."
