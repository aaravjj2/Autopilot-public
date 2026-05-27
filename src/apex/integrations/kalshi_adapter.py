"""Kalshi adapter - public endpoints + RSA-PSS authentication."""

from __future__ import annotations

import base64
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding

import httpx

from apex.core.config import Settings, get_settings
from apex.core.logging import get_logger

LOGGER = get_logger(__name__)
KALSHI_BASE = "https://external-api.kalshi.com/trade-api/v2"
KALSHI_PROD_BASE = KALSHI_BASE

# Last scan metrics for observability / API status
_last_scan_metrics: dict[str, Any] = {}


def resolve_kalshi_rest_base(settings: Settings | None = None) -> str:
    """Public REST base for market lists/orderbooks (demo API when demo trading is on)."""
    if settings is None:
        settings = get_settings()
    if settings.kalshi_demo_trading_enabled:
        return (settings.kalshi_base_url or "https://demo-api.kalshi.co/trade-api/v2").rstrip("/")
    return KALSHI_PROD_BASE.rstrip("/")


def market_volume_24h(market: dict[str, Any]) -> float:
    """Kalshi volume: legacy ``volume_24h`` or newer ``volume_24h_fp`` / ``liquidity_dollars``."""
    for key in ("volume_24h", "volume_24h_fp", "volume_fp", "open_interest_fp"):
        raw = market.get(key)
        if raw is None or raw == "":
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    try:
        return float(market.get("liquidity_dollars") or 0)
    except (TypeError, ValueError):
        return 0.0


def normalize_orderbook(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy cent books and newer ``orderbook_fp`` dollar books."""
    if "yes" in data or "no" in data:
        return data
    ob = data.get("orderbook_fp") or data.get("orderbook") or data
    if not isinstance(ob, dict):
        return data

    def _legs(key: str) -> list[list[float]]:
        rows = ob.get(key) or []
        legs: list[list[float]] = []
        for row in rows:
            if not isinstance(row, (list, tuple)) or len(row) < 2:
                continue
            try:
                legs.append([float(row[0]), float(row[1])])
            except (TypeError, ValueError):
                continue
        return legs

    if "yes_dollars" in ob or "no_dollars" in ob:
        return {"yes": _legs("yes_dollars"), "no": _legs("no_dollars")}
    return ob if isinstance(ob, dict) else data


def is_combo_parlay_ticker(ticker: str) -> bool:
    """Skip multivariate combo tickers that rarely arb-match Polymarket."""
    t = (ticker or "").upper()
    return t.startswith("KXMV") or "MULTIGAME" in t


def get_last_kalshi_scan_metrics() -> dict[str, Any]:
    return dict(_last_scan_metrics)


class KalshiAuth:
    def __init__(self, access_key: str, private_key_pem: str):
        self.access_key = access_key
        self._private_key = serialization.load_pem_private_key(
            private_key_pem.encode(), password=None
        )

    def headers(self, method: str, path: str) -> dict[str, str]:
        ts = str(int(time.time() * 1000))
        msg = (ts + method.upper() + path).encode()
        sig = self._private_key.sign(
            msg,
            asym_padding.PSS(
                mgf=asym_padding.MGF1(hashes.SHA256()),
                salt_length=asym_padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )
        return {
            "KALSHI-ACCESS-KEY": self.access_key,
            "KALSHI-ACCESS-TIMESTAMP": ts,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode(),
            "Content-Type": "application/json",
        }


def fetch_open_markets(
    category: str | None = None,
    limit: int = 100,
    *,
    max_pages: int | None = None,
    max_markets: int | None = None,
    base_url: str | None = None,
) -> list[dict]:
    """List open markets with cursor pagination (bounded)."""
    rest_base = (base_url or KALSHI_BASE).rstrip("/")
    markets: list[dict] = []
    cursor: str | None = None
    pages = 0
    while True:
        params: dict[str, Any] = {"status": "open", "limit": limit}
        if cursor:
            params["cursor"] = cursor
        if category:
            params["category"] = category
        resp = httpx.get(f"{rest_base}/markets", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("markets", [])
        markets.extend(batch)
        pages += 1
        if max_markets is not None and len(markets) >= max_markets:
            markets = markets[:max_markets]
            break
        cursor = data.get("cursor")
        if not cursor:
            break
        if max_pages is not None and pages >= max_pages:
            break
    return markets


def fetch_orderbook(ticker: str, *, base_url: str | None = None) -> dict:
    rest_base = (base_url or KALSHI_BASE).rstrip("/")
    resp = httpx.get(
        f"{rest_base}/markets/{ticker}/orderbook",
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    ob = normalize_orderbook(data.get("orderbook", data))
    try:
        from apex.cache.orderbook_l2 import ingest_orderbook
        from apex.ingestion.kalshi_tick_mmap import KalshiTickMmapReader

        ingest_orderbook("KALSHI", ticker, ob)
        settings = get_settings()
        KalshiTickMmapReader.append_tick(
            settings.kalshi_tick_mmap_path,
            {"ticker": ticker, "orderbook": ob, "source": "rest"},
        )
    except Exception:
        pass
    return ob


def reconstruct_asks(orderbook: dict) -> dict:
    yes_bids = orderbook.get("yes", [])
    no_bids = orderbook.get("no", [])

    best_bid_yes = max((b[0] for b in yes_bids), default=0.0)
    best_bid_no = max((b[0] for b in no_bids), default=0.0)

    best_ask_yes = round(1.00 - best_bid_no, 4)
    best_ask_no = round(1.00 - best_bid_yes, 4)

    return {
        "best_bid_yes": best_bid_yes,
        "best_bid_no": best_bid_no,
        "best_ask_yes": best_ask_yes,
        "best_ask_no": best_ask_no,
    }


@dataclass
class KalshiMarket:
    ticker: str
    event_ticker: str
    title: str
    category: str
    best_ask_yes: float
    best_ask_no: float
    volume_24h: float
    close_time: str


@dataclass
class KalshiScanMetrics:
    kalshi_markets_seen: int = 0
    orderbooks_fetched: int = 0
    orderbooks_failed: int = 0
    markets_returned: int = 0
    elapsed_ms: float = 0.0
    scan_partial: bool = False
    categories_scanned: list[str] = field(default_factory=list)


def _market_to_kalshi(m: dict[str, Any], asks: dict[str, float]) -> KalshiMarket:
    return KalshiMarket(
        ticker=str(m.get("ticker", "")),
        event_ticker=str(m.get("event_ticker", "")),
        title=str(m.get("title", "")),
        category=str(m.get("category", "")),
        best_ask_yes=asks["best_ask_yes"],
        best_ask_no=asks["best_ask_no"],
        volume_24h=market_volume_24h(m),
        close_time=str(m.get("close_time", "")),
    )


def _fetch_one_orderbook(
    m: dict[str, Any],
    min_volume: float,
    *,
    base_url: str | None = None,
) -> KalshiMarket | None:
    ticker = str(m.get("ticker", ""))
    if not ticker:
        return None
    vol = market_volume_24h(m)
    if vol < min_volume:
        return None
    try:
        ob = fetch_orderbook(ticker, base_url=base_url)
        asks = reconstruct_asks(ob)
        return _market_to_kalshi(m, asks)
    except Exception as exc:
        LOGGER.debug("Kalshi orderbook failed for %s: %s", ticker, exc)
        return None


class KalshiEventClient:
    BASE = KALSHI_BASE
    MACRO_CATEGORIES = ["ECON", "FED", "CRYPTO", "POLITICS", "FINANCE", "SPORTS"]

    def __init__(self, settings: Settings):
        self.settings = settings
        self._http = httpx.Client(timeout=15)
        self._rest_base = resolve_kalshi_rest_base(settings)

    def get_macro_markets(
        self,
        min_volume: float = 10_000,
        *,
        fast: bool = True,
    ) -> list[KalshiMarket]:
        """Bounded Kalshi scan: pre-filter volume, cap pagination, parallel orderbooks."""
        global _last_scan_metrics
        t0 = time.perf_counter()
        s = self.settings
        max_per_cat = int(getattr(s, "kalshi_scan_max_markets_per_category", 50))
        max_ob = int(getattr(s, "kalshi_scan_max_orderbooks", 80))
        concurrency = int(getattr(s, "kalshi_scan_orderbook_concurrency", 8))
        max_pages = 3 if fast else None
        rest_base = self._rest_base

        all_markets: list[dict] = []
        raw_pool: list[dict] = []
        categories = list(self.MACRO_CATEGORIES)
        for cat in categories:
            try:
                raw = fetch_open_markets(
                    category=cat,
                    limit=100,
                    max_pages=max_pages,
                    max_markets=max_per_cat,
                    base_url=rest_base,
                )
                for m in raw:
                    ticker = str(m.get("ticker", ""))
                    if is_combo_parlay_ticker(ticker):
                        continue
                    raw_pool.append(m)
                    if market_volume_24h(m) >= min_volume:
                        all_markets.append(m)
            except Exception as e:
                LOGGER.warning("Kalshi fetch failed for category %s: %s", cat, e)

        volume_relaxed = False
        if not all_markets and raw_pool:
            volume_relaxed = True
            raw_pool.sort(key=market_volume_24h, reverse=True)
            all_markets = raw_pool[: max_ob * 2]
            LOGGER.info(
                "Kalshi scan: no markets above min_volume=%.0f on %s; using top %d by liquidity/volume",
                min_volume,
                rest_base,
                len(all_markets),
            )

        all_markets.sort(key=market_volume_24h, reverse=True)
        candidates = all_markets[:max_ob]
        scan_partial = len(all_markets) > len(candidates)

        result: list[KalshiMarket] = []
        ob_ok = 0
        ob_fail = 0
        relaxed_min = 0.0 if volume_relaxed else min_volume
        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
            futures = {
                pool.submit(
                    _fetch_one_orderbook, m, relaxed_min, base_url=rest_base
                ): m
                for m in candidates
            }
            for fut in as_completed(futures):
                km = fut.result()
                if km is not None:
                    result.append(km)
                    ob_ok += 1
                else:
                    ob_fail += 1

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        metrics = KalshiScanMetrics(
            kalshi_markets_seen=len(all_markets),
            orderbooks_fetched=ob_ok,
            orderbooks_failed=ob_fail,
            markets_returned=len(result),
            elapsed_ms=round(elapsed_ms, 1),
            scan_partial=scan_partial,
            categories_scanned=categories,
        )
        _last_scan_metrics = {
            "kalshi_markets_seen": metrics.kalshi_markets_seen,
            "orderbooks_fetched": metrics.orderbooks_fetched,
            "orderbooks_failed": metrics.orderbooks_failed,
            "markets_returned": metrics.markets_returned,
            "elapsed_ms": metrics.elapsed_ms,
            "scan_partial": metrics.scan_partial,
            "categories_scanned": metrics.categories_scanned,
        }
        LOGGER.info(
            "Kalshi scan: seen=%d ob_ok=%d ob_fail=%d returned=%d partial=%s %.0fms",
            metrics.kalshi_markets_seen,
            metrics.orderbooks_fetched,
            metrics.orderbooks_failed,
            metrics.markets_returned,
            metrics.scan_partial,
            metrics.elapsed_ms,
        )
        return result


def fetch_world_cup_markets(
    min_volume: float = 1000.0,
    limit: int = 100,
) -> list[dict]:
    """Fetch open Kalshi markets matching FIFA / World Cup keywords."""
    keywords = ("fifa", "world cup", "worldcup", "wc26", "wc 26")
    seen: set[str] = set()
    out: list[dict] = []
    try:
        raw = fetch_open_markets(category="SPORTS", limit=100, max_pages=5, max_markets=500)
    except Exception as exc:
        LOGGER.warning("Kalshi SPORTS fetch failed: %s", exc)
        raw = []
    for m in raw:
        text = f"{m.get('title', '')} {m.get('ticker', '')}".lower()
        if not any(k in text for k in keywords):
            continue
        ticker = str(m.get("ticker", ""))
        if ticker in seen:
            continue
        seen.add(ticker)
        if market_volume_24h(m) < min_volume:
            continue
        out.append(m)
        if len(out) >= limit:
            break
    return out


def compute_net_edge(kalshi_yes_ask: float, poly_no_ask: float) -> float:
    gross = 1.00 - kalshi_yes_ask - poly_no_ask
    fee = 0.07 * (1.00 - kalshi_yes_ask)
    return round(gross - fee, 4)
