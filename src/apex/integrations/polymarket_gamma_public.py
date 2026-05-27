"""
Public Polymarket Gamma REST helpers (no Alpaca, no auth).

Used for event discovery, paper-trade proposal sourcing, and offline training
exports from resolved markets.
"""

from __future__ import annotations

import json
from typing import Any

import requests

from apex.core.logging import get_logger

LOGGER = get_logger(__name__)

GAMMA_API = "https://gamma-api.polymarket.com"


def fetch_gamma_markets(params: dict[str, Any], *, timeout: int = 30) -> list[dict[str, Any]]:
    """GET ``/markets`` and return a list of raw market dicts."""
    try:
        resp = requests.get(f"{GAMMA_API}/markets", params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return [m for m in data if isinstance(m, dict)]
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            return [m for m in data["data"] if isinstance(m, dict)]
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Gamma /markets request failed: %s", exc)
    return []


def _parse_outcome_prices(market: dict[str, Any]) -> list[float] | None:
    raw = market.get("outcomePrices") or market.get("outcome_prices")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return None
    if not isinstance(raw, list) or len(raw) < 2:
        return None
    out: list[float] = []
    for x in raw[:2]:
        try:
            out.append(float(x))
        except (TypeError, ValueError):
            return None
    return out

def parse_outcome_prices(market: dict[str, Any]) -> tuple[float, float]:
    """
    Returns (yes_price, no_price) where both are 0.0–1.0.
    """
    raw = market.get("outcomePrices") or market.get("outcome_prices")
    if isinstance(raw, str):
        try:
            prices = json.loads(raw)
        except json.JSONDecodeError:
            return 0.5, 0.5
    elif isinstance(raw, list):
        prices = raw
    else:
        return 0.5, 0.5

    if len(prices) >= 2:
        yes = float(prices[0])
        no  = float(prices[1])
    elif len(prices) == 1:
        yes = float(prices[0])
        no  = 1.0 - yes
    else:
        return 0.5, 0.5

    return round(yes, 4), round(no, 4)


def infer_yes_won(market: dict[str, Any]) -> bool | None:
    """
    Best-effort: for a resolved binary market, return True if YES (index 0) won.
    Returns None if ambiguous.
    """
    prices = _parse_outcome_prices(market)
    if prices is None or len(prices) < 2:
        return None
    p_yes, p_no = prices[0], prices[1]
    if p_yes >= 0.97:
        return True
    if p_no >= 0.97:
        return False
    return None


def yes_implied_probability(market: dict[str, Any]) -> float:
    """First outcome price as YES probability, or 0.5."""
    prices = _parse_outcome_prices(market)
    if prices is None:
        for key in ("lastTradePrice", "bestBid", "oneDayPriceChange"):
            v = market.get(key)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass
        return 0.5
    return float(prices[0])


def market_primary_id(market: dict[str, Any]) -> str:
    for key in ("id", "conditionId", "condition_id", "slug"):
        v = market.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    return "unknown"


def fetch_active_liquid_markets(
    *,
    limit: int = 25,
    min_volume: float = 0.0,
    enrich_for_arb: bool = False,
) -> list[dict[str, Any]]:
    """High-volume open markets (public)."""
    params: dict[str, Any] = {
        "limit": max(1, min(200, int(limit))),
        "active": "true",
        "closed": "false",
        "order": "volume24hr",
        "ascending": "false",
    }
    rows = fetch_gamma_markets(params)
    filtered: list[dict[str, Any]] = []
    
    for m in rows:
        try:
            v = float(m.get("volume", 0) or m.get("volumeNum", 0) or m.get("volume24hr", 0) or 0)
        except (TypeError, ValueError):
            v = 0.0
        
        if min_volume > 0 and v < min_volume:
            continue
            
        if enrich_for_arb:
            yes_p, no_p = parse_outcome_prices(m)
            m["bestAsk_yes"] = yes_p
            m["bestAsk_no"]  = no_p
            m["id"] = m.get("conditionId") or m.get("id", "")
            
        filtered.append(m)
        
    return filtered


def fetch_closed_markets_for_training(
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Resolved / closed markets for supervised labels (public)."""
    params: dict[str, Any] = {
        "limit": max(1, min(500, int(limit))),
        "offset": max(0, int(offset)),
        "closed": "true",
        "order": "volume",
        "ascending": "false",
    }
    return fetch_gamma_markets(params)


def training_row_from_market(market: dict[str, Any]) -> dict[str, Any]:
    """Flatten a Gamma market into a JSON-serializable training row."""
    mid = market_primary_id(market)
    yes_p = yes_implied_probability(market)
    won = infer_yes_won(market)
    try:
        vol = float(market.get("volume", 0) or market.get("volumeNum", 0) or 0)
    except (TypeError, ValueError):
        vol = 0.0
    outcomes = market.get("outcomes")
    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except json.JSONDecodeError:
            pass
    op_raw = market.get("outcomePrices") or market.get("outcome_prices")
    return {
        "market_id": mid,
        "question": market.get("question") or market.get("title") or "",
        "slug": market.get("slug"),
        "closed": bool(market.get("closed")),
        "volume": vol,
        "yes_implied_at_snapshot": yes_p,
        "yes_won": won,
        "outcomes": outcomes,
        "outcome_prices": op_raw,
        "uma_resolution_status": market.get("umaResolutionStatus") or market.get("uma_resolution_status"),
        "end_date": market.get("endDate") or market.get("end_date_iso"),
    }
