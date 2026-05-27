from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

import httpx

from config import get_settings
from portfolios import get_portfolio_spec


def _quiver_headers() -> dict[str, str]:
    key = get_settings()["quiver_api_key"]
    return {"Authorization": f"Token {key}"} if key else {}


def fetch_congress_trades() -> list[dict[str, Any]]:
    """Fetch recent congressional trades from Quiver (or return empty)."""
    key = get_settings()["quiver_api_key"]
    if not key:
        return []
    url = "https://api.quiverquant.com/beta/live/congresstrading"
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(url, headers=_quiver_headers())
            if r.status_code != 200:
                return []
            data = r.json()
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _filter_by_name(rows: list[dict[str, Any]], *needles: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    needles_l = [n.lower() for n in needles]
    for row in rows:
        name = str(row.get("Representative") or row.get("Name") or "").lower()
        if any(n in name for n in needles_l):
            out.append(row)
    return out


def _holdings_from_trades(
    trades: list[dict[str, Any]], top_n: int = 8
) -> list[tuple[str, float]]:
    scores: dict[str, float] = defaultdict(float)
    cutoff = datetime.utcnow() - timedelta(days=90)
    for row in trades:
        try:
            raw_dt = row.get("TransactionDate") or row.get("Date")
            if raw_dt:
                dt = datetime.fromisoformat(str(raw_dt).replace("Z", "+00:00"))
                if dt.replace(tzinfo=None) < cutoff:
                    continue
        except Exception:
            pass
        ticker = str(row.get("Ticker") or row.get("ticker") or "").upper().strip()
        if not ticker or ticker in {"--", "N/A"}:
            continue
        amount = str(row.get("Amount") or row.get("Transaction") or "")
        side = str(row.get("Transaction") or row.get("Type") or "").lower()
        weight = 1.0
        if "purchase" in side or "buy" in amount.lower():
            weight = 1.2
        elif "sale" in side or "sell" in amount.lower():
            weight = 0.3
        scores[ticker] += weight
    if not scores:
        return []
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    total = sum(v for _, v in ranked) or 1.0
    return [(t, v / total) for t, v in ranked]


def refresh_political_portfolio(portfolio_id: str) -> list[tuple[str, float]] | None:
    spec = get_portfolio_spec(portfolio_id)
    if not spec or spec.get("category") != "political":
        return None
    rows = fetch_congress_trades()
    if not rows:
        return None
    if portfolio_id == "pelosi-tracker":
        filtered = _filter_by_name(rows, "pelosi")
    elif portfolio_id == "trump-portfolio":
        filtered = _filter_by_name(rows, "trump", "donald")
    elif portfolio_id == "senate-buys":
        filtered = [r for r in rows if "senate" in str(r.get("House", "")).lower()]
        if not filtered:
            filtered = rows
    else:
        filtered = rows
    holdings = _holdings_from_trades(filtered)
    return holdings if holdings else None
