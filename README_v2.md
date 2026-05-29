# Autopilot v2.0 — Continuous Improvement Loop

## What Changed

**Old (v1.0):** Discrete 2-hour cycles via cronjob
**New (v2.0):** Continuous 2-5 min cycles with model switching + rate-limit recovery

- ✅ Runs forever (no cronjob sleep)
- ✅ Smart model selection per phase (Analyze: gpt-4o, Execute: agy-switch)
- ✅ Automatic fallback when rate-limited (deepseek → gpt4o-mini → claude)
- ✅ Adaptive cycle duration (faster for complex tasks)
- ✅ Per-phase cost optimization

## Quick Start

### 1. Install Dependencies
```bash
agy-switch --model deepseek-v4-flash-free -p "respond with: ready"
hermes mcp list | grep -E "(playwright|figma)"
```

### 2. Start the Daemon
```bash
# Foreground (monitor logs)
autopilot-continuous-daemon

# Background (persist across sessions)
nohup autopilot-continuous-daemon > ~/Aarav/Autopilot/logs/daemon.log 2>&1 &
ps aux | grep autopilot-continuous-daemon
```

### 3. Monitor Progress
```bash
# Real-time logs
tail -f ~/Aarav/Autopilot/logs/daemon.log

# Latest cycle report
tail -f ~/Aarav/Autopilot/logs/cycle-*.json

# Git commits from autopilot
cd ~/Aarav/Autopilot && git log --oneline | head -10
```

## Architecture

### Phase Model Switching

| Phase | Model | Provider | Duration | Purpose |
|-------|-------|----------|----------|---------|
| 1. Analyze | gpt-4o | openrouter | 60-120s | Deep codebase audit (128k context) |
| 2. Plan | deepseek-v4-flash | opencode | 20-40s | Fast task planning |
| 3. Execute | agy-switch | opencode | 90-180s | Code edits (auto-fallback) |
| 4. Test | gpt-4o-mini | opencode | 60-120s | Test harness + assertions |
| 5. Commit | deepseek-v4-flash | opencode | 5-15s | Conventional commit msgs |
| 6. Report | gpt-4o-mini | opencode | 2-5s | Summary generation |

**Total per cycle:** 240-530s (~4-9 min)
**Adaptive sleep:** 1-3 min based on issues found
**Actual cycle time:** 5-12 min

### agy-switch Fallback Chain

If Phase 3 (Execute) hits rate limits, automatically retry with:
1. deepseek-v4-flash-free (opencode) ← primary
2. gpt-4o-mini (opencode) ← fallback 1
3. gpt-4o (openrouter) ← fallback 2
4. claude-opus-4 (anthropic) ← fallback 3
5. qwen2.5-72b (openrouter) ← fallback 4

**User impact:** None. The system handles this transparently.

## Configuration

Edit per-phase models in:
```yaml
# ~/.hermes/profiles/autopilot-worker/config.yaml
agent:
  autopilot_phase_models:
    analyze:   { model: "gpt-4o", provider: "openrouter" }
    plan:      { model: "deepseek-v4-flash-free", provider: "opencode" }
    execute:   { model: "agy-switch", provider: "opencode" }
    test:      { model: "gpt-4o-mini", provider: "opencode" }
    commit:    { model: "deepseek-v4-flash-free", provider: "opencode" }
    report:    { model: "gpt-4o-mini", provider: "opencode" }
```

## Logs

### Daemon Log
```bash
tail -f ~/Aarav/Autopilot/logs/daemon.log
```

Output:
```
[2026-05-28 14:00:32] 🤖 Autopilot Continuous Daemon started
[2026-05-28 14:00:32] Profile: autopilot-worker | Working dir: /home/aarav/Aarav/Autopilot
[2026-05-28 14:00:32] 🔄 Starting cycle #1 [cycle-20260528_140032]
[2026-05-28 14:00:38] ℹ️  [Phase 0] Bootstrap & setup
[2026-05-28 14:01:43] ℹ️  [Phase 1] Analyzing codebase...
[2026-05-28 14:02:13] ℹ️  [Phase 2] Planning tasks...
[2026-05-28 14:03:51] ℹ️  [Phase 3] Executing tasks (4 tasks)...
```

### Cycle Reports
```bash
jq . ~/Aarav/Autopilot/logs/cycle-20260528_140032.json
```

Output:
```json
{
  "cycle_id": "cycle-20260528_140032",
  "cycle_number": 1,
  "duration_sec": 487,
  "phases": {
    "analyze": { "duration_sec": 65, "model": "gpt-4o" },
    "plan": { "duration_sec": 30, "model": "deepseek-v4-flash-free", "tasks": 4 },
    "execute": { "duration_sec": 98, "model": "agy-switch" },
    "test": { "duration_sec": 180, "model": "gpt-4o-mini" },
    "commit": { "duration_sec": 10, "model": "deepseek-v4-flash-free" },
    "report": { "model": "gpt-4o-mini" }
  },
  "git_status": "chore: autopilot improvements (cycle cycle-20260528_140032)",
  "changes_pending": 0,
  "consecutive_no_changes": 0
}
```

## Troubleshooting

### agy-switch falls back too many times
Check OpenCode quota:
```bash
agy-switch --model deepseek-v4-flash-free -p "test" 2>&1 | grep -i "rate\|quota\|limit"
```

### Daemon hangs on a phase
Kill and restart:
```bash
pkill -f autopilot-continuous-daemon
autopilot-continuous-daemon  # or nohup ... &
```

### Discord not receiving cycle reports
Verify webhook:
```bash
curl -X POST https://discord.com/api/webhooks/YOUR_WEBHOOK_HERE \
  -H "Content-Type: application/json" \
  -d '{"content":"test"}'
```

## Stopping the Daemon

Graceful stop:
```bash
pkill autopilot-continuous-daemon
```

Immediate stop:
```bash
pkill -9 autopilot-continuous-daemon
```

---

Status: Ready to run | Version: v2.0 (continuous + model switching)
