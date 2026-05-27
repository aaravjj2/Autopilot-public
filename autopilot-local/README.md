# Autopilot Local

Local copy-trading marketplace (browse → follow → mirror trades on **Alpaca paper**). Implements [autopilot-local-PRD.md](../autopilot-local-PRD.md).

## Stack

- **Frontend:** Next.js 15 + Tailwind + Recharts → http://localhost:3000
- **Backend:** FastAPI + SQLModel + APScheduler → http://localhost:8000
- **Database:** `autopilot.db` (SQLite, gitignored)

## Quick start

```bash
cd autopilot-local
python3 -m venv ../.venv
../.venv/bin/pip install -e ".[dev]"
cp .env.local.example .env.local
# Edit .env.local with Alpaca paper API keys (and optional QUIVER_API_KEY)

chmod +x start.sh
./start.sh
```

Or manually:

```bash
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
npm install
npm run dev
```

## API

| Route | Description |
|-------|-------------|
| `GET /api/portfolios` | Marketplace list |
| `GET /api/portfolios/{id}` | Detail + holdings + chart |
| `POST /api/portfolios/{id}/follow` | Mirror to Alpaca paper |
| `DELETE /api/portfolios/{id}/follow` | Close tagged positions |
| `GET /api/dashboard` | Account + positions |
| `GET /api/stream/pnl` | SSE live quotes |
| `POST /api/refresh/all` | Refresh Quiver/EDGAR + performance |
| `GET /api/health` | Alpaca ping + last refresh |

## Portfolios (8 seed)

Political: Pelosi, Trump, Senate · Hedge: Simons, Burry, Dalio · Thematic: Inverse Cramer, AI basket

Without `QUIVER_API_KEY`, political refresh keeps seed holdings. 13F refresh uses SEC EDGAR when available.

## Note

This app is separate from **APEX Autopilot Engine** (`src/apex/`) in the parent repo.
