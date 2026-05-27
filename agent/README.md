# APEX FinOps Agent (Google Rapid Agent — Arize track)

Thin agent layer on top of the existing APEX L0–L4 engine. **Gemini 3 + Google Cloud Agent Builder** orchestrates; **APEX MCP** executes tools; **Arize** records traces.

## Quick test (local)

```bash
export DEMO_MODE=true
python scripts/seed_demo.py
uvicorn backend_api:app --port 8000
curl http://127.0.0.1:8000/api/agent/missions
curl -X POST http://127.0.0.1:8000/api/agent/run/governed_paper_execution
curl http://127.0.0.1:8000/api/agent/traces
```

## MCP server (stdio)

Point Agent Builder or Claude Desktop at:

```json
{
  "mcpServers": {
    "apex": {
      "command": "python",
      "args": ["agent/mcp_apex_server.py"],
      "env": {
        "APEX_AGENT_API_BASE": "http://127.0.0.1:8000"
      }
    }
  }
}
```

## Google Cloud Agent Builder

1. Create an Agent Builder app with **Gemini 3**.
2. Add MCP server `apex` (command above).
3. Add **Arize partner MCP** per [Rapid Agent resources](https://rapid-agent.devpost.com/).
4. System prompt: multi-step missions only — use `run_mission` or chain `scan_arbitrage` → `explain_risk_gates` → `paper_trade_arb`.
5. Hosted URL: same terminal as Beyond Tomorrow (`PUBLIC_DEMO_URL`) or Agent Builder preview URL.

## Arize

Set `ARIZE_ENABLED=true`, `ARIZE_PROJECT_NAME=apex-finops-agent`. Spans are logged locally and exposed at `GET /api/agent/traces`. Wire Arize MCP to export OTLP in production.

## Missions

See [MISSIONS.md](MISSIONS.md).
