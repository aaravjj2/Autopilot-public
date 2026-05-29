#!/usr/bin/env bash
# Autopilot Worker Runner — persistent independent agent loop
# Launched via: terminal(background=true, pty=true)
# Runs the Hermes autopilot-worker profile in a continuous improvement loop.
set -e

AUTOPILOT_HOME="$HOME/Aarav/Autopilot"
cd "$AUTOPILOT_HOME"

while true; do
  TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
  echo ""
  echo "═══════════════════════════════════════════════════════════"
  echo "  [autopilot-worker] Cycle starting at $TIMESTAMP"
  echo "═══════════════════════════════════════════════════════════"

  # Run ONE complete cycle via the Hermes worker profile
  # The agent will auto-load the autopilot-continuous-improvement skill
  # because the prompt references it
  hermes -p autopilot-worker -z \
"YOU are the AUTOPILOT WORKER. Execute ONE full autopilot continuous improvement cycle on $AUTOPILOT_HOME.

You MUST first load the 'autopilot-continuous-improvement' skill with skill_view(name='autopilot-continuous-improvement') to get the 6-phase procedure, then follow it exactly.

Summary of phases:
1. ANALYZE — delegate_task to audit codebase (TODOs, lint errors, test gaps, security)
2. PLAN — delegate_task to produce prioritized task list (max 5 tasks)
3. EXECUTE — delegate_task up to 3 parallel subagents to implement improvements
4. TEST — pytest backend + Playwright MCP E2E for frontend. Auto-fix minor failures.
5. COMMIT — conventional commits, git push origin HEAD, tag cycle-$TIMESTAMP
6. REPORT — log to $AUTOPILOT_HOME/logs/cycle_$TIMESTAMP.json

After completing all phases, output: '===CYCLE_COMPLETE===' and stop."

  EXIT_CODE=$?
  echo "[autopilot-worker] Cycle finished (exit=$EXIT_CODE). Next cycle in 120s..."
  sleep 120
done
