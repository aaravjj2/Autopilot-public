from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, select

from db import PolymarketPosition, PolymarketSnapshot, PolymarketTrade, get_engine

LOGGER = logging.getLogger(__name__)

APEX_AUDIT_DB = Path(__file__).resolve().parents[2] / "data" / "audit.db"


def _connect_apex() -> sqlite3.Connection | None:
    if not APEX_AUDIT_DB.exists():
        LOGGER.warning("APEX audit.db not found at %s", APEX_AUDIT_DB)
        return None
    conn = sqlite3.connect(str(APEX_AUDIT_DB))
    conn.row_factory = sqlite3.Row
    return conn


def sync_polymarket_from_apex() -> dict[str, int]:
    """Read Polymarket data from APEX audit.db and sync to marketplace DB.

    Returns counts of synced records.
    """
    apex_conn = _connect_apex()
    if apex_conn is None:
        return {"positions": 0, "trades": 0, "snapshots": 0}

    stats: dict[str, int] = {"positions": 0, "trades": 0, "snapshots": 0}

    try:
        stats["positions"] = _sync_positions(apex_conn)
        stats["trades"] = _sync_trades(apex_conn)
        stats["snapshots"] = _sync_snapshots(apex_conn)
    except Exception:
        LOGGER.exception("Polymarket sync failed")
    finally:
        apex_conn.close()

    return stats


def _sync_positions(apex_conn: sqlite3.Connection) -> int:
    """Sync open Polymarket positions from APEX audit.db."""
    cursor = apex_conn.cursor()

    cursor.execute("""
        SELECT raw_payload, timestamp
        FROM audit_log
        WHERE event_type = 'ORDER_FILLED'
          AND json_extract(raw_payload, '$.venue') = 'polymarket_paper'
        ORDER BY timestamp ASC
    """)
    rows = cursor.fetchall()

    engine = get_engine()
    count = 0

    with Session(engine) as session:
        existing: dict[str, PolymarketPosition] = {}
        for row in session.exec(select(PolymarketPosition)).all():
            key = f"{row.market_id}:{row.side}"
            existing[key] = row

        for row in rows:
            payload = json.loads(row["raw_payload"])
            market_id = payload.get("polymarket_market_id", "")
            side = payload.get("polymarket_outcome_side", "YES")
            key = f"{market_id}:{side}"

            if key in existing:
                continue

            question = payload.get("polymarket_question", "")
            slug = payload.get("event_slug", "")
            entry_price = float(payload.get("entry_price", 0.5))
            stake = float(payload.get("polymarket_stake_usd", 50))

            position = PolymarketPosition(
                market_id=market_id,
                question=question,
                slug=slug,
                side=side,
                entry_price=entry_price,
                stake_usd=stake,
                quantity=stake / entry_price if entry_price > 0 else stake,
                current_value=stake,
                status="open",
                opened_at=datetime.fromisoformat(row["timestamp"]) if row["timestamp"] else datetime.now(timezone.utc),
            )
            session.add(position)
            count += 1

        session.commit()

    return count


def _sync_trades(apex_conn: sqlite3.Connection) -> int:
    """Sync Polymarket trade history from APEX audit.db."""
    cursor = apex_conn.cursor()

    cursor.execute("""
        SELECT raw_payload, timestamp
        FROM audit_log
        WHERE event_type IN ('ORDER_FILLED', 'ORDER_CANCELLED')
          AND json_extract(raw_payload, '$.venue') = 'polymarket_paper'
        ORDER BY timestamp ASC
    """)
    rows = cursor.fetchall()

    engine = get_engine()
    count = 0

    with Session(engine) as session:
        existing_order_ids = {
            t.order_id for t in session.exec(select(PolymarketTrade)).all()
        }

        for row in rows:
            payload = json.loads(row["raw_payload"])
            order_id = payload.get("order_id", "")

            if not order_id or order_id in existing_order_ids:
                continue

            market_id = payload.get("polymarket_market_id", "")
            side = payload.get("polymarket_outcome_side", "YES")
            question = payload.get("polymarket_question", "")
            stake = float(payload.get("polymarket_stake_usd", 50))
            entry_price = float(payload.get("entry_price", 0.5))
            status = "filled" if row["event_type"] == "ORDER_FILLED" else "cancelled"

            trade = PolymarketTrade(
                market_id=market_id,
                question=question,
                side=side,
                stake_usd=stake,
                entry_price=entry_price,
                order_id=order_id,
                status=status,
                executed_at=datetime.fromisoformat(row["timestamp"]) if row["timestamp"] else datetime.now(timezone.utc),
            )
            session.add(trade)
            existing_order_ids.add(order_id)
            count += 1

        session.commit()

    return count


def _sync_snapshots(apex_conn: sqlite3.Connection) -> int:
    """Sync Polymarket bankroll snapshots from APEX equity_curve table."""
    cursor = apex_conn.cursor()

    cursor.execute("""
        SELECT timestamp, total_equity
        FROM equity_curve
        WHERE source = 'polymarket_paper'
        ORDER BY timestamp ASC
    """)
    rows = cursor.fetchall()

    if not rows:
        return 0

    engine = get_engine()
    count = 0

    with Session(engine) as session:
        existing_dates = {
            s.date for s in session.exec(select(PolymarketSnapshot)).all()
        }

        prev_equity = None
        for row in rows:
            ts = row["timestamp"]
            try:
                dt = datetime.fromisoformat(ts)
                snapshot_date = dt.date()
            except (ValueError, TypeError):
                continue

            if snapshot_date in existing_dates:
                prev_equity = float(row["total_equity"])
                continue

            equity = float(row["total_equity"])
            daily_pl = equity - prev_equity if prev_equity is not None else 0.0
            daily_pl_pct = (daily_pl / prev_equity * 100) if prev_equity and prev_equity > 0 else 0.0

            snapshot = PolymarketSnapshot(
                date=snapshot_date,
                bankroll_usd=equity,
                buying_power_usd=equity,
                daily_pl=round(daily_pl, 2),
                daily_pl_pct=round(daily_pl_pct, 4),
            )
            session.add(snapshot)
            existing_dates.add(snapshot_date)
            count += 1
            prev_equity = equity

        session.commit()

    return count
