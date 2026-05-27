"""Kalshi + Polymarket public market fetchers.

This module intentionally uses a multi-strategy discovery approach because:
- Kalshi series tickers change
- Polymarket endpoints / response shapes vary across CLOB vs Gamma
"""

from __future__ import annotations

import json
import os
import base64
import time
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import requests

from config import get_logger

LOGGER = get_logger(__name__)

# Current public Kalshi Trade API base.
# Some environments cannot reach trading-api.kalshi.com, so prefer this host.
KALSHI_BASES = ("https://api.elections.kalshi.com/trade-api/v2",)

POLYMARKET_ENDPOINTS = [
    "https://clob.polymarket.com/markets",
    "https://gamma-api.polymarket.com/markets",
]

POLYMARKET_PARAMS_STRATEGIES: list[dict[str, Any]] = [
    {"active": "true", "closed": "false", "limit": 500},
    {"active": "true", "limit": 1000},
    {"limit": 500},
    {},
]

KALSHI_WC_SEARCH_STRATEGIES: list[dict[str, Any]] = [
    {"params": {"series_ticker": "FIFAWC", "limit": 1000}},
    {"params": {"series_ticker": "WC2026", "limit": 1000}},
    {"params": {"series_ticker": "SOCCER", "limit": 1000}},
    {"params": {"search": "World Cup", "limit": 1000}},
    {"params": {"search": "FIFA", "limit": 1000}},
    {"params": {"search": "soccer 2026", "limit": 1000}},
    {"params": {"status": "open", "limit": 1000}},
]

WC_KEYWORDS = [
    "world cup",
    "fifa",
    "wc2026",
    "soccer 2026",
    "football 2026",
    "argentina",
    "brazil",
    "france",
    "germany",
    "england",
    "group stage",
    "knockout",
    "semifinal",
    "semifinals",
    "final 2026",
]

_FIFA_RE = re.compile(r"fifa|world\s*cup|worldcup|wc\s*26|wc26", re.I)


def _kalshi_signed_headers(method: str, path: str) -> dict[str, str] | None:
    """
    Kalshi Trade API v2 auth: RSA-PSS signature headers.
    Uses:
      - KALSHI_API_KEY (access key id)
      - KALSHI_API_PRIVATE_KEY (PEM)
    """
    access_key = (os.getenv("KALSHI_API_KEY") or "").strip()
    pem = (os.getenv("KALSHI_API_PRIVATE_KEY") or "").strip().strip('"')
    if not access_key or not pem or "BEGIN" not in pem:
        return None
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding as asym_padding

        private_key = serialization.load_pem_private_key(pem.encode(), password=None)
        ts = str(int(time.time() * 1000))
        msg = (ts + method.upper() + path).encode()
        sig = private_key.sign(
            msg,
            asym_padding.PSS(
                mgf=asym_padding.MGF1(hashes.SHA256()),
                salt_length=asym_padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )
        return {
            "KALSHI-ACCESS-KEY": access_key,
            "KALSHI-ACCESS-TIMESTAMP": ts,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode(),
            "Content-Type": "application/json",
        }
    except Exception as exc:
        LOGGER.warning("Kalshi signed header build failed: %s", exc)
        return None


@dataclass
class Market:
    platform: str
    market_id: str
    question: str
    implied_prob: float
    volume: float
    open_interest: float
    closes_at: str
    home_team: str = ""
    away_team: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clamp_prob(p: float) -> float:
    if p <= 0:
        return 0.01
    if p >= 1:
        return 0.99
    return p


def _kalshi_get(path: str, params: dict | None = None) -> dict[str, Any]:
    last_err: Exception | None = None
    # Prefer signed auth if private key is available. If not, fall back to Bearer
    # (some accounts/tools issue read tokens even though official auth is signed).
    headers: dict[str, str] = _kalshi_signed_headers("GET", f"/trade-api/v2{path}") or {}
    if not headers:
        api_key = (os.getenv("KALSHI_API_KEY") or "").strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
    for base in KALSHI_BASES:
        try:
            resp = requests.get(f"{base}{path}", params=params or {}, headers=headers or None, timeout=20)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 401:
                LOGGER.warning("Kalshi fetch unauthorized (401); set KALSHI_API_KEY for read access")
        except Exception as exc:
            last_err = exc
    if last_err:
        LOGGER.warning("Kalshi fetch failed: %s", last_err)
    return {}

def is_wc_market(market: dict[str, Any]) -> bool:
    text = " ".join(
        [
            str(market.get("title", "")),
            str(market.get("subtitle", "")),
            str(market.get("ticker", "")),
            str(market.get("series_ticker", "")),
        ]
    ).lower()
    return any(kw in text for kw in WC_KEYWORDS)


def is_polymarket_wc(market: dict[str, Any]) -> bool:
    text = " ".join(
        [
            str(market.get("question", "")),
            str(market.get("description", "")),
            str(market.get("category", "")),
            str(market.get("slug", "")),
            str(market.get("title", "")),
        ]
    ).lower()
    return any(kw in text for kw in WC_KEYWORDS)


def _normalize_kalshi_market(m: dict[str, Any]) -> Market:
    title = str(m.get("title") or m.get("ticker") or "")
    yes_bid = float(m.get("yes_bid") or m.get("yes_bid_dollars") or 0)
    yes_ask = float(m.get("yes_ask") or m.get("yes_ask_dollars") or 0)
    if yes_bid > 1:
        yes_bid /= 100.0
    if yes_ask > 1:
        yes_ask /= 100.0
    if yes_bid <= 0 and yes_ask <= 0:
        last = float(m.get("last_price") or 0)
        if last > 1:
            last /= 100.0
        implied = last or 0.5
    else:
        implied = (yes_bid + yes_ask) / 2.0 if (yes_bid or yes_ask) else 0.5
    return Market(
        platform="kalshi",
        market_id=str(m.get("ticker") or ""),
        question=title,
        implied_prob=_clamp_prob(implied),
        volume=float(m.get("volume") or m.get("volume_24h") or 0),
        open_interest=float(m.get("open_interest") or 0),
        closes_at=str(m.get("close_time") or m.get("expiration_time") or ""),
    )


def _normalize_polymarket_market(m: dict[str, Any]) -> Market | None:
    q = str(m.get("question") or m.get("title") or "")
    prices = m.get("outcomePrices") or m.get("outcome_prices") or m.get("outcomes") or []
    if isinstance(prices, str):
        try:
            prices = json.loads(prices)
        except json.JSONDecodeError:
            prices = []
    implied = 0.5
    if isinstance(prices, list) and prices:
        try:
            implied = float(prices[0] if not isinstance(prices[0], dict) else prices[0].get("price", 0.5))
        except (TypeError, ValueError):
            implied = 0.5
    market_id = str(m.get("condition_id") or m.get("id") or m.get("market_slug") or m.get("slug") or "")
    if not market_id:
        return None
    return Market(
        platform="polymarket",
        market_id=market_id,
        question=q,
        implied_prob=_clamp_prob(implied),
        volume=float(m.get("volume") or m.get("volumeNum") or m.get("volumeUSD") or 0),
        open_interest=float(m.get("liquidity") or m.get("liquidityNum") or m.get("liquidityUSD") or 0),
        closes_at=str(m.get("endDate") or m.get("end_date_iso") or m.get("end_date") or ""),
    )

def fetch_kalshi_markets(series_ticker: str = "FIFAWC", limit: int = 100) -> list[Market]:
    # If caller explicitly passes series_ticker, keep old behavior.
    if series_ticker and series_ticker != "FIFAWC":
        data = _kalshi_get("/markets", {"limit": limit, "series_ticker": series_ticker})
        return [_normalize_kalshi_market(m) for m in (data.get("markets") or [])]

    for strat in KALSHI_WC_SEARCH_STRATEGIES:
        params = dict(strat.get("params") or {})
        params.setdefault("limit", max(limit, int(params.get("limit") or 0) or limit))
        cursor: str | None = None
        pages = 0
        while pages < 10:
            if cursor:
                params["cursor"] = cursor
            data = _kalshi_get("/markets", params)
            raw = data.get("markets") or []
            wc = [m for m in raw if is_wc_market(m) or _FIFA_RE.search(str(m.get("title") or ""))]
            if wc:
                LOGGER.info("Kalshi: found %s WC markets via %s", len(wc), params)
                return [_normalize_kalshi_market(m) for m in wc]
            cursor = data.get("cursor") or None
            pages += 1
            if not cursor:
                break
    LOGGER.warning("Kalshi: 0 WC markets found across all strategies")
    return []


def fetch_kalshi_market(ticker: str) -> Market | None:
    data = _kalshi_get(f"/markets/{ticker}")
    m = data.get("market") or data
    if not m:
        return None
    rows = fetch_kalshi_markets(limit=1)
    # Re-parse single market inline
    yes_bid = float(m.get("yes_bid") or 0)
    yes_ask = float(m.get("yes_ask") or 0)
    if yes_bid > 1:
        yes_bid /= 100.0
    if yes_ask > 1:
        yes_ask /= 100.0
    implied = (yes_bid + yes_ask) / 2.0 if (yes_bid or yes_ask) else 0.5
    return Market(
        platform="kalshi",
        market_id=ticker,
        question=str(m.get("title") or ticker),
        implied_prob=_clamp_prob(implied),
        volume=float(m.get("volume") or 0),
        open_interest=float(m.get("open_interest") or 0),
        closes_at=str(m.get("close_time") or ""),
    )


def fetch_polymarket_markets(limit: int = 500) -> list[Market]:
    for endpoint in POLYMARKET_ENDPOINTS:
        for params in POLYMARKET_PARAMS_STRATEGIES:
            try:
                req_params = dict(params)
                if "limit" in req_params:
                    req_params["limit"] = max(int(req_params.get("limit") or 0), limit)
                resp = requests.get(endpoint, params=req_params or None, timeout=25)
                if resp.status_code != 200:
                    continue
                payload = resp.json()
            except Exception as exc:
                LOGGER.warning("Polymarket fetch failed (%s): %s", endpoint, exc)
                continue

            if isinstance(payload, list):
                raw = payload
            elif isinstance(payload, dict):
                raw = payload.get("data") or payload.get("markets") or []
            else:
                continue
            if not isinstance(raw, list):
                continue
            wc = [m for m in raw if isinstance(m, dict) and (is_polymarket_wc(m) or _FIFA_RE.search(str(m.get("question") or m.get("title") or "")))]
            if not wc:
                continue
            out: list[Market] = []
            for m in wc:
                nm = _normalize_polymarket_market(m)
                if nm:
                    out.append(nm)
            if out:
                LOGGER.info("Polymarket: found %s WC markets via %s", len(out), endpoint)
                return out
    LOGGER.warning("Polymarket: 0 WC markets found across all strategies")
    return []


def fetch_all_wc_markets() -> list[Market]:
    kalshi = fetch_kalshi_markets()
    if not kalshi:
        # Broader scan when series ticker empty
        data = _kalshi_get("/markets", {"limit": 200, "status": "open"})
        for m in data.get("markets") or []:
            title = str(m.get("title") or "")
            if _FIFA_RE.search(title):
                kalshi.extend(fetch_kalshi_markets(series_ticker=str(m.get("series_ticker") or "FIFAWC")))
                break
        # Manual filter fallback
        if not kalshi:
            data = _kalshi_get("/markets", {"limit": 200})
            for m in data.get("markets") or []:
                title = str(m.get("title") or "")
                if not _FIFA_RE.search(title):
                    continue
                yes_bid = float(m.get("yes_bid") or 0)
                yes_ask = float(m.get("yes_ask") or 0)
                if yes_bid > 1:
                    yes_bid /= 100.0
                if yes_ask > 1:
                    yes_ask /= 100.0
                implied = (yes_bid + yes_ask) / 2.0 if (yes_bid or yes_ask) else 0.5
                kalshi.append(
                    Market(
                        platform="kalshi",
                        market_id=str(m.get("ticker") or ""),
                        question=title,
                        implied_prob=_clamp_prob(implied),
                        volume=float(m.get("volume") or 0),
                        open_interest=float(m.get("open_interest") or 0),
                        closes_at=str(m.get("close_time") or ""),
                    )
                )
    poly = fetch_polymarket_markets()
    return kalshi + poly


def snapshot_markets(conn, markets: list[Market]) -> int:
    from db.schema import init_db

    init_db(conn)
    ts = datetime.now(timezone.utc).isoformat()
    rows = [
        (
            ts,
            m.platform,
            m.market_id,
            m.question,
            m.implied_prob,
            m.volume,
            m.open_interest,
            m.closes_at,
            m.home_team,
            m.away_team,
        )
        for m in markets
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO market_snapshots
        (captured_at, platform, market_id, question, implied_prob, volume,
         open_interest, closes_at, home_team, away_team)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return len(rows)
