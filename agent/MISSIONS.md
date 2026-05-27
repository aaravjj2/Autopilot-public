# Canned missions (Rapid Agent demo)

Run via `POST /api/agent/run/{mission_id}` or MCP tool `run_mission`.

## 1. morning_arb_briefing

**Goal:** Scan → rank top 3 → explain edges.

```bash
curl -X POST http://127.0.0.1:8000/api/agent/run/morning_arb_briefing
```

**Arize spans:** `mission.start`, `tool.scan_arbitrage`

## 2. governed_paper_execution

**Goal:** Select best opp → risk gates → paper trade (or rejection).

```bash
curl -X POST http://127.0.0.1:8000/api/agent/run/governed_paper_execution
```

Use `demo-reject-demo` id manually via `{"arb_id": "demo-reject-demo"}` to show failure path.

**Arize spans:** `select_opportunity`, `explain_risk_gates`, `paper_trade_arb`

## 3. incident_post_mortem

**Goal:** Audit tail → failed gates → recommendation.

```bash
curl -X POST http://127.0.0.1:8000/api/agent/run/incident_post_mortem
```

**Arize spans:** `get_audit_tail`

## Video beat sheet (~3 min)

1. Agent Builder + mission picker (15s)
2. Run `governed_paper_execution` — show tool calls in UI (60s)
3. Cut to APEX Terminal Arb Radar same ticker (30s)
4. Open `GET /api/agent/traces` or Arize UI with `trace_id` (30s)
5. Impact close: governed autonomous finance for students (15s)
