![Tests](https://img.shields.io/badge/tests-489/492-green)

# APEX Autopilot

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

**Institutional-grade, paper-only** autonomous execution for cross-market prediction arbitrage (Kalshi × Polymarket) with a fail-fast risk stack (M01–M09), multi-agent intelligence, and a Bloomberg-style operator terminal.

**Repository:** [github.com/aaravjj2/Autopilot-public](https://github.com/aaravjj2/Autopilot-public)

Hackathon / judge materials: **[HACKATHON.md](HACKATHON.md)** · Pitch brief: **[docs/pitch/APEX_Autopilot_Pitch_Brief_and_Speech.md](docs/pitch/APEX_Autopilot_Pitch_Brief_and_Speech.md)**

---

## What it does

APEX Autopilot runs a disciplined **L0–L4 pipeline**:

| Layer | Role |
|-------|------|
| **L0** | Ingestion — Kalshi, Polymarket, retries, cache hydration |
| **L1** | Finance brain — scoring, spreads, confidence |
| **L2** | Agent panel — multi-agent thesis / verdicts |
| **L3** | Execution + risk — dual-leg paper routing, **M01 paper-first** gates |
| **L4** | Observability — audit stream, telemetry |

The **Next.js terminal** (`autopilot-local/frontend`) provides Arb Radar, Autopilot proposals, risk views, and live audit feeds.

---

## Quickstart (full stack)

**Requirements:** Python 3.11+ with `uvicorn`, Node 18+, `npm`

```bash
git clone https://github.com/aaravjj2/Autopilot-public.git
cd Autopilot-public
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -e ".[dev]"
cp keys.env.example keys.env    # API keys (gitignored)
cp .env.example .env            # feature flags

# Start API (:8000), marketplace (:8001), frontend (:3000), scheduler
bash start_all.sh
```

| Service | URL |
|---------|-----|
| **Terminal** | http://localhost:3000 |
| **APEX API docs** | http://127.0.0.1:8000/docs |
| **Health** | http://127.0.0.1:8000/health |
| **Arb opportunities** | http://127.0.0.1:8000/api/arb/opportunities |

Stop everything:

```bash
bash stop_all.sh
```

### Verify APEX owns port 8000

Another local app may already use `:8000`. APEX health includes `proposals` and `timestamp` — not a generic `"service"` string from unrelated APIs.

```bash
curl -s http://127.0.0.1:8000/health | python3 -m json.tool | head -20
curl -s http://127.0.0.1:8000/api/arb/opportunities | python3 -c "import sys,json;d=json.load(sys.stdin);print('count',len(d) if isinstance(d,list) else 'see shape')"
```

If health looks wrong or arb returns 404:

```bash
bash scripts/ensure_apex_port_8000.sh
bash start_all.sh
```

---

## Judge demo (no live venue keys)

```bash
export DEMO_MODE=true
python scripts/seed_demo.py
PYTHONPATH=src python -m uvicorn backend_api:app --host 127.0.0.1 --port 8000
# Other terminal:
cd autopilot-local/frontend && npm install && npm run dev
```

Open **http://localhost:3000/dashboard/arb-radar**

---

## Submission / demo artifacts

Record screenshots + walkthrough video for Devpost:

```bash
bash start_all.sh
bash scripts/build_submission_artifacts.sh
```

Outputs under `artifacts/submission/`:

- `APEX_Autopilot_Demo.mp4` — product tour
- `screenshots/` — gallery images
- `api-*.json` — live API proof
- `pitch/` — PDF, PPTX, spoken brief
- `APEX_Autopilot_Submission_Artifacts.zip` — one-click bundle (generated at repo root)

---

## Tests

```bash
python -m pytest tests/ -v
cd autopilot-local/frontend && npx playwright test
```

Roadmap day-file verifier:

```bash
python scripts/verification/verify_roadmap_daily.py --start 1 --end 20
```

---

## Configuration

- Secrets: `keys.env` (gitignored) — see `keys.env.example`
- Settings: `.env` / Pydantic `src/apex/core/config.py`
- Integrations under `external/` — [external/README.md](external/README.md)

**Paper trading only** — `M01_PAPER_REQUIRED` runs first on every arb execution path.

Strict integration mode:

```bash
export STRICT_INTEGRATIONS=true
apex-engine
```

---

## Architecture & roadmap

- Deep architecture: [docs/architecture/master_plan_arch.md](docs/architecture/master_plan_arch.md)
- Execution control plane: [master_plan.md](master_plan.md)
- Daily runbooks: `one-year-daily/day-001.md` … `day-260.md`

---

## Other entry points

| Command | Purpose |
|---------|---------|
| `apex-engine` | Core engine CLI |
| `apex-scheduler` | Background loops |
| `apex-healthz` | Health on `:8088` |
| `apex-dashboard` | Streamlit ops `:8501` |
| `bash scripts/start-apex-stack.sh` | Copy-trading stack variant |

Details: [autopilot-local/README.md](autopilot-local/README.md) · [AGENTS.md](AGENTS.md)

---

## License

Apache-2.0 — see [LICENSE](LICENSE).
