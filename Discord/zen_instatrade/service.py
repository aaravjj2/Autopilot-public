from fastapi import FastAPI, HTTPException
from typing import List
import sqlite3
from pathlib import Path
from pydantic import BaseModel

DB_PATH = Path(__file__).resolve().parent / "trades.db"

app = FastAPI(title="APEX Discord Bot API")


class Trade(BaseModel):
    id: str
    symbol: str
    ticker: str
    strike: float
    expiration: str
    type: str
    entry_price: float | None = None
    target: float | None = None
    stop_loss: float | None = None
    status: str
    placed_at: str
    exit_price: float | None = None
    exit_at: str | None = None


def _connect():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/discord/trades", response_model=List[Trade])
def list_trades(limit: int = 50):
    if not DB_PATH.exists():
        return []
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM trades ORDER BY placed_at DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/discord/trades/open", response_model=List[Trade])
def list_open_trades():
    if not DB_PATH.exists():
        return []
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM trades WHERE status = 'open' ORDER BY placed_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/discord/stats")
def stats():
    if not DB_PATH.exists():
        return {"total": 0, "open": 0, "closed": 0}
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM trades")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) as c FROM trades WHERE status='open'")
    open_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) as c FROM trades WHERE status!='open'")
    closed = cur.fetchone()[0]
    conn.close()
    return {"total": total, "open": open_count, "closed": closed}


@app.get("/discord/brain/stats")
def brain_stats():
    # Placeholder: the Discord bot does not implement a separate brain service yet.
    return {"evaluations": [], "note": "discord local brain not implemented"}


@app.get("/discord/brain/config")
def brain_config():
    return {"max_daily_discord_trades": 5}
