"""Discover FIFA World Cup 2026 contracts on Kalshi and Polymarket."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from apex.core.config import Settings, get_settings
from apex.core.logging import get_logger
from apex.integrations.kalshi_adapter import (
    fetch_orderbook,
    fetch_world_cup_markets,
    reconstruct_asks,
)
from apex.integrations.polymarket_gamma_public import (
    fetch_active_liquid_markets,
    market_primary_id,
    yes_implied_probability,
)

LOGGER = get_logger(__name__)

_FIFA_RE = re.compile(r"fifa|world\s*cup|worldcup|wc\s*26|wc26", re.I)


@dataclass
class WorldCupContract:
    id: str
    venue: str
    ticker_or_market_id: str
    question: str
    contract_type: str
    team_a: str
    team_b: str
    kickoff_ts: str
    market_yes_ask: float
    volume_24h: float
    poly_market_id: str = ""
    kalshi_ticker: str = ""
    net_edge: float = 0.0
    gross_spread: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _is_fifa_text(text: str) -> bool:
    return bool(_FIFA_RE.search(text))


def discover_kalshi_world_cup(settings: Settings) -> list[WorldCupContract]:
    out: list[WorldCupContract] = []
    min_vol = float(settings.world_cup_min_volume_24h)
    limit = int(settings.world_cup_discovery_limit)
    for m in fetch_world_cup_markets(min_volume=min_vol, limit=limit):
        ticker = str(m.get("ticker", ""))
        try:
            ob = fetch_orderbook(ticker)
            asks = reconstruct_asks(ob)
            yes_ask = asks["best_ask_yes"]
        except Exception:
            yes_ask = float(m.get("yes_ask", 0.5) or 0.5)
        title = str(m.get("title", ticker))
        out.append(
            WorldCupContract(
                id=f"wc-k-{ticker}",
                venue="kalshi",
                ticker_or_market_id=ticker,
                kalshi_ticker=ticker,
                question=title,
                contract_type="match_winner",
                team_a="",
                team_b="",
                kickoff_ts=str(m.get("close_time", "")),
                market_yes_ask=yes_ask,
                volume_24h=float(m.get("volume_24h", 0) or 0),
            )
        )
    return out


def discover_polymarket_world_cup(settings: Settings) -> list[WorldCupContract]:
    out: list[WorldCupContract] = []
    limit = int(settings.world_cup_discovery_limit)
    try:
        markets = fetch_active_liquid_markets(
            limit=limit * 3,
            min_volume=float(settings.world_cup_min_volume_24h),
            enrich_for_arb=False,
        )
    except Exception as exc:
        LOGGER.warning("Poly WC discovery failed: %s", exc)
        return out

    for m in markets:
        q = str(m.get("question") or m.get("title") or "")
        if not _is_fifa_text(q):
            continue
        mid = market_primary_id(m)
        yes_p = yes_implied_probability(m)
        out.append(
            WorldCupContract(
                id=f"wc-p-{mid}",
                venue="polymarket",
                ticker_or_market_id=mid,
                poly_market_id=mid,
                question=q,
                contract_type="match_winner",
                team_a="",
                team_b="",
                kickoff_ts=str(m.get("endDate") or m.get("end_date_iso") or ""),
                market_yes_ask=yes_p,
                volume_24h=float(m.get("volume24hr") or m.get("volume") or 0),
            )
        )
        if len(out) >= limit:
            break
    return out


def discover_world_cup_markets(settings: Settings | None = None) -> list[dict[str, Any]]:
    settings = settings or get_settings()
    if not settings.world_cup_enabled:
        return []
    rows: list[WorldCupContract] = []
    rows.extend(discover_kalshi_world_cup(settings))
    rows.extend(discover_polymarket_world_cup(settings))
    return [r.to_dict() for r in rows]


def pair_cross_venue(contracts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach net_edge when Kalshi YES + Poly NO style pairing is possible (simplified)."""
    kalshi = [c for c in contracts if c.get("venue") == "kalshi"]
    poly = [c for c in contracts if c.get("venue") == "polymarket"]
    paired: list[dict[str, Any]] = []
    for k in kalshi:
        for p in poly:
            kq = k.get("question", "").lower()
            pq = p.get("question", "").lower()
            if not kq or not pq:
                continue
            overlap = len(set(kq.split()) & set(pq.split()))
            if overlap < 3:
                continue
            k_yes = float(k.get("market_yes_ask") or 0.5)
            p_no = 1.0 - float(p.get("market_yes_ask") or 0.5)
            gross = round(1.0 - k_yes - p_no, 4)
            fee = 0.07 * (1.0 - k_yes)
            net = round(gross - fee, 4)
            merged = {
                **k,
                "poly_market_id": p.get("poly_market_id"),
                "poly_no_ask": p_no,
                "gross_spread": gross,
                "net_edge": net,
                "pair_id": f"wc-pair-{uuid4().hex[:8]}",
            }
            paired.append(merged)
    return paired if paired else contracts
