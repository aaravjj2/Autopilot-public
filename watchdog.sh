#!/bin/bash
# APEX Autopilot - Service Watchdog
# Monitors services and restarts them if they crash
# Run via cron: * * * * * /home/aarav/Aarav/Autopilot/watchdog.sh

APEX_DIR="/home/aarav/Aarav/Autopilot"
LOG_DIR="/tmp/apex-logs"
WATCHDOG_LOG="$LOG_DIR/watchdog.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$WATCHDOG_LOG"
}

restart_service() {
    local name=$1
    local command=$2
    local log_file=$3
    local pid_file=$4
    
    log "Restarting $name..."
    
    # Kill old process
    if [ -f "$pid_file" ]; then
        kill $(cat "$pid_file") 2>/dev/null || true
        rm -f "$pid_file"
    fi
    pkill -f "$command" 2>/dev/null || true
    sleep 2
    
    # Start new process
    cd "$APEX_DIR"
    nohup $command > "$log_file" 2>&1 &
    echo $! > "$pid_file"
    log "$name restarted (PID $!)"
}

# Check Backend
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    log "Backend API not responding - restarting"
    restart_service "Backend API" "python3 -m uvicorn backend_api:app --host 0.0.0.0 --port 8000" "$LOG_DIR/backend.log" "$LOG_DIR/backend.pid"
fi

# Check Frontend
if ! curl -s http://localhost:3000 > /dev/null 2>&1; then
    log "Frontend not responding - restarting"
    restart_service "Frontend" "bash -c 'cd $APEX_DIR/autopilot-local/frontend && npm run dev'" "$LOG_DIR/frontend.log" "$LOG_DIR/frontend.pid"
fi

# Check Scheduler
if ! pgrep -f "apex.main" > /dev/null 2>&1; then
    log "Scheduler not running - restarting"
    cd "$APEX_DIR"
    restart_service "Scheduler" "python3 -c 'from apex.main import run_scheduler; run_scheduler()'" "$LOG_DIR/scheduler.log" "$LOG_DIR/scheduler.pid"
fi

# Check Discord Bot (only when autostart enabled)
if [ "$DISCORD_AUTOSTART" = "1" ] || [ "$DISCORD_AUTOSTART" = "true" ]; then
    if ! pgrep -f "run_discord_bot" > /dev/null 2>&1; then
            log "Discord Bot not running - restarting"
            export $(grep -v '^#' "$APEX_DIR/.env" | xargs) 2>/dev/null || true
            restart_service "Discord Bot" "python3 run_discord_bot.py" "$LOG_DIR/discord.log" "$LOG_DIR/discord.pid"
    fi
fi
