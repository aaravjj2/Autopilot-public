# External integrations (local clones)

Vendored GitHub repos are **not** committed. Clone the ones you need into this directory and point APEX at them via env vars (see root `.env.example` and `README.md`).

Suggested layout:

```bash
cd external

# Examples — use your preferred forks/URLs
git clone https://github.com/TauricResearch/TradingAgents.git
git clone https://github.com/virattt/dexter.git
git clone https://github.com/anthropics/financial-services.git
git clone https://github.com/your-org/daily_stock_analysis.git
git clone https://github.com/your-org/Kronos.git
git clone https://github.com/your-org/PolyMarket-MCP.git
git clone https://github.com/your-org/polymarket-mcp-server.git
git clone https://github.com/alpacahq/alpaca-mcp-server.git
```

Set paths in `.env` (after copying from `.env.example`):

```bash
TRADINGAGENTS_REPO_PATH=/absolute/path/Autopilot/external/TradingAgents
DEXTER_REPO_PATH=/absolute/path/Autopilot/external/dexter
DAILY_STOCK_ANALYSIS_REPO_PATH=/absolute/path/Autopilot/external/daily_stock_analysis
# ... etc.
```

APEX logs which integrations are available at startup. Use `STRICT_INTEGRATIONS=true` to fail fast when required repos or keys are missing.
