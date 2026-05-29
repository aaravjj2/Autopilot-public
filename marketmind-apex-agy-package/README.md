# MarketMind × APEX — Antigravity CLI Package

Full agentic package for the **MarketMind** prediction-market arb detector built on the **APEX Autopilot Engine**, designed for the **Antigravity CLI (`agy`)**.

---

## Package Layout

```
.agent/
  agents/
    agents.md              ← Multi-agent team roster
  skills/
    apex-dev/SKILL.md      ← APEX engine development patterns
    arb-engine/SKILL.md    ← Arb scanner + settlement auditor logic
    kalshi-api/SKILL.md    ← Kalshi RSA-PSS auth + orderbook patterns
    thesis-card/SKILL.md   ← Claude streaming thesis card (SSE)
    risk-stack/SKILL.md    ← M01–M06 arb risk checks
    backtest/SKILL.md      ← Backtest + Sharpe engine
    frontend-arb/SKILL.md  ← Next.js arb-radar page + ThesisCard
    polymarket/SKILL.md    ← Polymarket Gamma REST patterns
  rules/
    apex-conventions.md    ← Python/typing/logging conventions
    paper-only.md          ← Paper-trading enforcement rules
    streaming.md           ← Anthropic streaming API rules
  workflows/
    /build-arb-layer       ← Full arb pipeline scaffold
    /add-thesis-stream     ← Thesis SSE endpoint + frontend card
    /run-backtest          ← Replay resolved markets → Sharpe
    /daily-cycle           ← Full APEX daily cycle debug
    /health-check          ← Integration health + env audit
```

---

## Quick Start

```bash
# Install Antigravity CLI
npm install -g @google/antigravity-cli   # or: pip install antigravity-cli

# Clone this package into your APEX project root
cp -r .agent/ /path/to/Autopilot-main/.agent/

# Start Antigravity CLI in your project
cd /path/to/Autopilot-main
agy

# Run a workflow
/build-arb-layer
/add-thesis-stream
/run-backtest
```

---

## Compatibility

| Tool | Path | Status |
|------|------|--------|
| **Antigravity** IDE/CLI (`agy`) | `.agent/skills/` | ✅ Primary target |
| **Claude Code** | `.claude/skills/` | ✅ Full compat — copy `.agent/skills/` → `.claude/skills/` |
| **Gemini CLI** | `.gemini/skills/` | ✅ Full compat |
| **Cursor** | `.cursor/skills/` | ✅ Full compat |
