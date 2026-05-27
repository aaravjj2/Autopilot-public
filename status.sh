#!/bin/bash
# APEX Autopilot - System Status Check

APEX_DIR="/home/aarav/Aarav/Autopilot"
LOG_DIR="/tmp/apex-logs"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== APEX Autopilot Status ===${NC}"
echo ""

# Backend
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    HEALTH=$(curl -s http://localhost:8000/health | python3 -c "import sys, json; d = json.load(sys.stdin); ws=d.get('kalshi_ws',{}); sch=d.get('scheduler',{}); print(f'Status: {d.get(\"status\")} | Alpaca: {d.get(\"alpaca_connected\")} | Positions: {d.get(\"positions\")} | Orders: {d.get(\"orders\")} | KalshiWS stale: {ws.get(\"stale\")} | Scheduler: {sch.get(\"mode\")} ({sch.get(\"status\")})')")
    echo -e "${GREEN}✓${NC} Backend API: $HEALTH"
else
    echo -e "${RED}✗${NC} Backend API: Not running"
fi

# Frontend
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Frontend: Running (http://localhost:3000)"
else
    echo -e "${RED}✗${NC} Frontend: Not running"
fi

# Scheduler
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    SCHED_INFO=$(curl -s http://localhost:8000/health | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('scheduler') or {}; print(f\"{s.get('mode')}|{s.get('status')}|{s.get('separate_process_running')}\")")
    SCHED_MODE=$(echo "$SCHED_INFO" | cut -d'|' -f1)
    SCHED_STATUS=$(echo "$SCHED_INFO" | cut -d'|' -f2)
    SCHED_PROC=$(echo "$SCHED_INFO" | cut -d'|' -f3)
    if [ "$SCHED_MODE" = "in_process_loops" ] && [ "$SCHED_STATUS" = "ok" ]; then
        echo -e "${GREEN}✓${NC} APEX Scheduler: In-process loops active"
    elif [ "$SCHED_PROC" = "True" ]; then
        echo -e "${GREEN}✓${NC} APEX Scheduler: Separate scheduler process running"
    else
        echo -e "${YELLOW}⚠${NC} APEX Scheduler: Mode=$SCHED_MODE Status=$SCHED_STATUS"
    fi
else
    echo -e "${RED}✗${NC} APEX Scheduler: Backend unavailable"
fi

# Discord Bot
DISCORD_PID=$(pgrep -f "run_discord_bot" | head -1)
if [ -n "$DISCORD_PID" ]; then
    TRADES=$(curl -s http://localhost:8000/discord/stats 2>/dev/null | python3 -c "import sys, json; d = json.load(sys.stdin); print(f'Open: {d[\"open_trades\"]}, Closed: {d[\"closed_trades\"]}')")
    echo -e "${GREEN}✓${NC} Discord Bot: Running (PID $DISCORD_PID) | $TRADES"
else
    echo -e "${RED}✗${NC} Discord Bot: Not running"
fi

echo ""

# Integrations
if curl -s http://localhost:8000/integrations > /dev/null 2>&1; then
    echo -e "${GREEN}=== Integrations ===${NC}"
    curl -s http://localhost:8000/integrations | python3 -c "
import sys, json
d = json.load(sys.stdin)
for k, v in d.items():
    status = '✓' if v else '✗'
    print(f'  {status} {k.capitalize()}')
"
fi

echo ""
echo "Logs: $LOG_DIR/"
