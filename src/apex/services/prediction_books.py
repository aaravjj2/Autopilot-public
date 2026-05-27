"""Kalshi & Polymarket paper books from APEX audit_log (not copy-trading)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from apex.core.config import Settings, get_settings
from apex.integrations.kalshi_trading import kalshi_execution_mode_label
from apex.repositories.sqlite_store import SQLiteStore
from apex.services.pm_brain import build_pm_brain

_KALSHI_VENUES = frozenset({"kalshi_paper", "kalshi_demo"})


def _parse_payload(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
    return {}


def _read_audit_rows(store: SQLiteStore, venue: str, limit: int = 800) -> list[dict[str, Any]]:
    """Audit rows for a PM venue tag, plus arb submits that only carry order ids."""
    try:
        rows = store.read_table("audit_log", limit=limit)
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        payload = _parse_payload(row.get("raw_payload"))
        et = str(row.get("event_type") or "")
        oid = str(row.get("order_id") or payload.get("kalshi_order_id") or "")
        is_kalshi = payload.get("venue") == venue
        if venue in _KALSHI_VENUES and not is_kalshi:
            if payload.get("venue") in _KALSHI_VENUES:
                is_kalshi = True
            elif et == "ARB_PAPER_SUBMITTED" and payload.get("kalshi_order_id"):
                is_kalshi = True
            elif oid.startswith("KALSHI_PAPER_"):
                is_kalshi = True
                payload.setdefault("venue", venue)
        if not is_kalshi:
            continue
        key = oid or f"{et}:{row.get('event_id')}"
        if key in seen:
            continue
        seen.add(key)
        out.append({**row, "_payload": payload})
    return out


def _merge_audit_rows(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for group in groups:
        for row in group:
            key = str(row.get("order_id") or row.get("event_id") or "")
            if key in seen:
                continue
            seen.add(key)
            out.append(row)
    return out


def build_kalshi_book(store: SQLiteStore | None = None) -> dict[str, Any]:
    settings = get_settings()
    store = store or SQLiteStore(settings.sqlite_path)
    brain = build_pm_brain(store)
    venue_tag = "kalshi_demo" if settings.kalshi_demo_trading_enabled else "kalshi_paper"
    rows = _read_audit_rows(store, venue_tag)
    if settings.kalshi_demo_trading_enabled:
        rows = _merge_audit_rows(_read_audit_rows(store, "kalshi_paper"), rows)
    positions: dict[str, dict[str, Any]] = {}
    trades: list[dict[str, Any]] = []

    for row in rows:
        p = row["_payload"]
        et = str(row.get("event_type") or "")
        ts = str(row.get("timestamp") or "")
        ticker = p.get("kalshi_ticker") or p.get("ticker") or row.get("symbol") or ""
        if not ticker and et == "ARB_PAPER_SUBMITTED":
            ticker = row.get("symbol") or ""
        if not ticker:
            continue
        if et in ("ORDER_FILLED", "ARB_PAPER_SUBMITTED"):
            stake = float(p.get("stake_usd") or p.get("kalshi_stake_usd") or 50)
            price = float(p.get("entry_price") or p.get("kalshi_yes_ask") or 0.5)
            key = f"{ticker}:YES"
            positions[key] = {
                "id": key,
                "ticker": ticker,
                "question": p.get("question") or ticker,
                "side": "YES",
                "stake_usd": stake,
                "entry_price": price,
                "unrealized_pl": 0.0,
                "opened_at": ts,
            }
            trades.append({
                "id": p.get("kalshi_order_id") or row.get("order_id") or key,
                "ticker": ticker,
                "side": "YES",
                "stake_usd": stake,
                "status": "filled",
                "executed_at": ts,
            })
            if et == "ARB_PAPER_SUBMITTED" and p.get("poly_order_id"):
                continue
        elif et in ("ORDER_CANCELLED", "POSITION_CLOSED"):
            key = f"{ticker}:YES"
            positions.pop(key, None)

    bankroll = float(settings.kalshi_paper_bankroll_usd)
    open_stake = sum(float(x["stake_usd"]) for x in positions.values())
    return {
        "venue": "kalshi",
        "execution_mode": kalshi_execution_mode_label(settings),
        "bankroll_usd": bankroll,
        "buying_power_usd": max(0.0, bankroll - open_stake),
        "open_positions": len(positions),
        "unrealized_pl": 0.0,
        "daily_pl": 0.0,
        "status": brain["kalshi"],
        "positions": list(positions.values()),
        "trades": trades[-50:],
        "active_markets": brain.get("recent_opportunities") or [],
    }


def build_polymarket_book(store: SQLiteStore | None = None) -> dict[str, Any]:
    settings = get_settings()
    store = store or SQLiteStore(settings.sqlite_path)
    brain = build_pm_brain(store)
    rows = _read_audit_rows(store, "polymarket_paper")
    for raw in store.read_table("audit_log", limit=500):
        if str(raw.get("event_type") or "") != "ARB_PAPER_SUBMITTED":
            continue
        p = _parse_payload(raw.get("raw_payload"))
        if p.get("poly_order_id") or p.get("polymarket_market_id"):
            rows.append({**raw, "_payload": p})
    positions: dict[str, dict[str, Any]] = {}
    trades: list[dict[str, Any]] = []
    curve: list[dict[str, Any]] = []

    for row in rows:
        p = row["_payload"]
        et = str(row.get("event_type") or "")
        ts = str(row.get("timestamp") or "")
        market_id = p.get("polymarket_market_id") or ""
        side = p.get("polymarket_outcome_side") or ("NO" if et == "ARB_PAPER_SUBMITTED" else "YES")
        if not market_id and et == "ARB_PAPER_SUBMITTED":
            continue
        if not market_id:
            continue
        key = f"{market_id}:{side}"
        if et in ("ORDER_FILLED", "ARB_PAPER_SUBMITTED"):
            stake = float(p.get("polymarket_stake_usd") or 50)
            entry = float(p.get("entry_price") or 0.5)
            positions[key] = {
                "id": key,
                "market_id": market_id,
                "question": p.get("polymarket_question") or market_id,
                "side": side,
                "stake_usd": stake,
                "entry_price": entry,
                "unrealized_pl": 0.0,
                "opened_at": ts,
            }
            trades.append({
                "id": p.get("poly_order_id") or row.get("order_id") or key,
                "market_id": market_id,
                "side": side,
                "stake_usd": stake,
                "status": "filled",
                "executed_at": ts,
            })

    try:
        for pt in store.get_equity_curve(days=90):
            curve.append({
                "date": pt.get("timestamp"),
                "bankroll_usd": float(pt.get("equity") or 0),
            })
    except Exception:
        pass

    if not curve:
        curve = [
            {
                "date": datetime.now(timezone.utc).isoformat(),
                "bankroll_usd": float(settings.polymarket_paper_bankroll_usd),
            }
        ]

    bankroll = float(settings.polymarket_paper_bankroll_usd)
    open_stake = sum(float(x["stake_usd"]) for x in positions.values())
    return {
        "venue": "polymarket",
        "execution_mode": "paper_simulated",
        "summary": {
            "bankroll_usd": bankroll,
            "open_positions": len(positions),
            "unrealized_pl": 0.0,
            "daily_pl": 0.0,
            "buying_power_usd": max(0.0, bankroll - open_stake),
        },
        "status": brain["polymarket"],
        "positions": list(positions.values()),
        "trades": trades[-50:],
        "equity_curve": curve[-60:],
    }
