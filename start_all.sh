#!/bin/bash
# APEX Autopilot - Complete System Launcher
# Starts all services in proper order with health checks

set -e

APEX_DIR="/home/aarav/Aarav/Autopilot"
FRONTEND_DIR="$APEX_DIR/autopilot-local/frontend"
LOG_DIR="/tmp/apex-logs"
mkdir -p "$LOG_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log() { echo -e "${GREEN}[APEX]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Kill existing instances
log "Stopping existing services..."
pkill -f "uvicorn backend_api" 2>/dev/null || true
pkill -f "uvicorn main:app.*8001" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
pkill -f "scheduler.py" 2>/dev/null || true
pkill -f "run_discord_bot" 2>/dev/null || true
sleep 2

# Load environment (keys.env + .env via Python bootstrap)
log "Loading environment..."
cd "$APEX_DIR"
python3 -c "import sys; sys.path.insert(0,'src'); from apex.core.env_bootstrap import bootstrap_environment; bootstrap_environment(force=True)" 2>/dev/null || true

# 1. Start Backend API
log "Starting Backend API (port 8000)..."
cd "$APEX_DIR"
nohup python3 -m uvicorn backend_api:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$LOG_DIR/backend.pid"
log "  Backend PID: $BACKEND_PID"

# Wait for APEX backend to be ready
log "  Waiting for APEX backend..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        log "  APEX backend ready!"
        break
    fi
    sleep 1
done

# 1b. Start Marketplace Backend (copy-trading API on :8001)
log "Starting Marketplace API (port 8001)..."
MARKET_DIR="$APEX_DIR/autopilot-local/backend"
if [[ ! -d "$APEX_DIR/autopilot-local/.venv" ]]; then
    python3 -m venv "$APEX_DIR/autopilot-local/.venv" 2>/dev/null || true
    "$APEX_DIR/autopilot-local/.venv/bin/pip" install -q -r "$MARKET_DIR/requirements.txt" 2>/dev/null || true
fi
MARKET_PY="$APEX_DIR/autopilot-local/.venv/bin/python"
[[ -x "$MARKET_PY" ]] || MARKET_PY="python3"
(
  cd "$MARKET_DIR"
  PYTHONPATH="$APEX_DIR/src:${PYTHONPATH:-}" nohup "$MARKET_PY" -m uvicorn main:app --host 0.0.0.0 --port 8001 \
    > "$LOG_DIR/marketplace.log" 2>&1
) &
MARKET_PID=$!
echo $MARKET_PID > "$LOG_DIR/marketplace.pid"
log "  Marketplace PID: $MARKET_PID"

log "  Waiting for marketplace..."
for i in {1..30}; do
    if curl -s http://localhost:8001/api/health > /dev/null 2>&1; then
        log "  Marketplace ready!"
        break
    fi
    sleep 1
done

bash "$APEX_DIR/scripts/sync-copy-trading-env.sh" 2>/dev/null || true

# 2. Start Frontend
log "Starting Frontend (port 3000)..."
cd "$FRONTEND_DIR"
nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$LOG_DIR/frontend.pid"
log "  Frontend PID: $FRONTEND_PID"

# Wait for frontend to be ready
log "  Waiting for frontend..."
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        log "  Frontend ready!"
        break
    fi
    sleep 1
done

# 3. Start APEX Scheduler
log "Starting APEX Scheduler..."
cd "$APEX_DIR"
nohup python3 -c "from apex.main import run_scheduler; run_scheduler()" > "$LOG_DIR/scheduler.log" 2>&1 &
SCHEDULER_PID=$!
echo $SCHEDULER_PID > "$LOG_DIR/scheduler.pid"
log "  Scheduler PID: $SCHEDULER_PID"

# 4. Start Discord Bot & Exit Manager (optional)
# To keep the Discord bot as a separate service, it will only be started
# by this script when DISCORD_AUTOSTART=1 in the environment. Otherwise
# the Docker/systemd service or a separate runner should manage it.
if [ "$DISCORD_AUTOSTART" = "1" ] || [ "$DISCORD_AUTOSTART" = "true" ]; then
    log "Starting Discord Bot & Exit Manager..."
    cd "$APEX_DIR"
    nohup python3 run_discord_bot.py > "$LOG_DIR/discord.log" 2>&1 &
    DISCORD_PID=$!
    echo $DISCORD_PID > "$LOG_DIR/discord.pid"
    log "  Discord Bot PID: $DISCORD_PID"

    # Wait for Discord bot to connect
    log "  Waiting for Discord bot..."
    for i in {1..30}; do
            if grep -q "Connected to Gateway" "$LOG_DIR/discord.log" 2>/dev/null; then
                    log "  Discord bot connected!"
                    break
            fi
            sleep 1
    done
else
    warn "Discord bot autostart skipped (set DISCORD_AUTOSTART=1 to enable)"
fi

# Final status
echo ""
log "=== APEX System Status ==="
echo ""

# Check each service
check_service() {
    local name=$1
    local pid_file=$2
    local check_url=$3
    
    if [ -f "$pid_file" ] && kill -0 $(cat "$pid_file") 2>/dev/null; then
        if [ -n "$check_url" ] && curl -s "$check_url" > /dev/null 2>&1; then
            echo -e "  ${GREEN}✓${NC} $name: Running (PID $(cat $pid_file))"
        elif [ -z "$check_url" ]; then
            echo -e "  ${GREEN}✓${NC} $name: Running (PID $(cat $pid_file))"
        else
            echo -e "  ${YELLOW}⚠${NC} $name: Process running but not responding"
        fi
    else
        echo -e "  ${RED}✗${NC} $name: Not running"
    fi
}

check_service "APEX API" "$LOG_DIR/backend.pid" "http://localhost:8000/health"
check_service "Marketplace API" "$LOG_DIR/marketplace.pid" "http://localhost:8001/api/health"
check_service "Frontend" "$LOG_DIR/frontend.pid" "http://localhost:3000"
check_service "APEX Scheduler" "$LOG_DIR/scheduler.pid" ""
check_service "Discord Bot" "$LOG_DIR/discord.pid" ""

echo ""
log "=== Quick Links ==="
echo "  Frontend:    http://localhost:3000"
echo "  APEX API:      http://localhost:8000/docs"
echo "  Marketplace:   http://localhost:8001/docs"
echo "  Health:      http://localhost:8000/health"
echo "  Discord:     http://localhost:8000/discord/trades"
echo ""
log "Logs: $LOG_DIR/"
log "  backend.log, frontend.log, scheduler.log, discord.log"
echo ""
log "To stop all services: $APEX_DIR/stop_all.sh"
