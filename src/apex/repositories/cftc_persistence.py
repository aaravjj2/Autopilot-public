"""CFTC exposure persistence: flush to SQLite after each fill, hydrate on startup."""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apex.repositories.sqlite_store import SQLiteStore

LOGGER = logging.getLogger(__name__)
_TABLE = "cftc_exposure"


def ensure_table(store: "SQLiteStore") -> None:
    """Create the cftc_exposure table if it doesn't exist."""
    with store._conn() as conn:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {_TABLE} (
                ticker TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                notional_usd REAL NOT NULL DEFAULT 0.0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (ticker, trade_date)
            )
            """
        )


def flush_exposure(store: "SQLiteStore", ticker: str, notional_usd: float) -> None:
    """Upsert current notional for a ticker on today's trade date."""
    today = date.today().isoformat()
    now = datetime.now(timezone.utc).isoformat()
    try:
        ensure_table(store)
        with store._conn() as conn:
            conn.execute(
                f"""
                INSERT INTO {_TABLE} (ticker, trade_date, notional_usd, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(ticker, trade_date) DO UPDATE SET
                    notional_usd = excluded.notional_usd,
                    updated_at = excluded.updated_at
                """,
                (ticker, today, notional_usd, now),
            )
    except Exception as exc:
        LOGGER.warning("flush_exposure failed for %s: %s", ticker, exc)


def hydrate_tracker(store: "SQLiteStore") -> dict[str, float]:
    """Load today's exposures from SQLite. Returns {ticker: notional_usd}."""
    today = date.today().isoformat()
    try:
        ensure_table(store)
        with store._conn() as conn:
            rows = conn.execute(
                f"SELECT ticker, notional_usd FROM {_TABLE} WHERE trade_date = ?",
                (today,),
            ).fetchall()
        return {row[0]: row[1] for row in rows}
    except Exception as exc:
        LOGGER.warning("hydrate_tracker failed: %s", exc)
        return {}
