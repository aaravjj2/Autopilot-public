from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from apex.core.logging import get_logger
from apex.core.retry import call_with_retries
from apex.domain.contracts import MarketDataClient, OptionsDataClient, PredictionMarketClient

LOGGER = get_logger(__name__)


@dataclass
class IngestionCache:
    market: dict[str, dict[str, Any]] = field(default_factory=dict)
    options: dict[str, dict[str, Any]] = field(default_factory=dict)
    polymarket_macro: list[dict[str, Any]] = field(default_factory=list)
    news: dict[str, Any] = field(default_factory=dict)
    refreshed_at: dict[str, datetime] = field(default_factory=dict)
    watchlist: list[str] = field(default_factory=list)


class DataIngestionService:
    def __init__(
        self,
        market_data: MarketDataClient,
        options_data: OptionsDataClient,
        pm_client: PredictionMarketClient,
        *,
        mirofish: Any | None = None,
        daily_stock: Any | None = None,
        max_fetch_attempts: int = 2,
        fetch_backoff_sec: float = 1.5,
        inter_symbol_delay_ms: int = 0,
        fetch_workers: int = 8,
    ):
        self.market_data = market_data
        self.options_data = options_data
        self.pm_client = pm_client
        self._mirofish = mirofish
        self._daily_stock = daily_stock
        self._max_fetch_attempts = max(1, min(int(max_fetch_attempts), 20))
        self._fetch_backoff_sec = max(0.0, float(fetch_backoff_sec))
        self._inter_symbol_delay_ms = max(0, min(int(inter_symbol_delay_ms), 30_000))
        self._fetch_workers = max(1, min(int(fetch_workers), 32))
        self.cache = IngestionCache()

    def _map_symbols(self, symbols: list[str], worker: Callable[[str], None]) -> None:
        """Run ``worker`` for each symbol, in parallel unless an inter-symbol
        delay is configured (in which case the delay implies rate-limiting and
        we stay sequential)."""
        delay = self._inter_symbol_delay_ms / 1000.0
        if delay > 0 or self._fetch_workers <= 1 or len(symbols) <= 1:
            for i, symbol in enumerate(symbols):
                if i > 0 and delay > 0:
                    time.sleep(delay)
                worker(symbol)
            return
        with ThreadPoolExecutor(
            max_workers=min(self._fetch_workers, len(symbols)),
            thread_name_prefix="apex-ingest",
        ) as pool:
            list(pool.map(worker, symbols))

    def _with_network_retries(self, label: str, fn: Callable[[], Any]) -> Any:
        return call_with_retries(
            fn,
            max_attempts=self._max_fetch_attempts,
            backoff_seconds=self._fetch_backoff_sec,
            log_label=label,
        )

    def refresh_market_data(self, symbols: list[str]) -> None:
        def worker(symbol: str) -> None:
            try:
                bars = self._with_network_retries(
                    f"market.bars:{symbol}", lambda: self.market_data.get_daily_bars(symbol)
                )
                fundamentals = self._with_network_retries(
                    f"market.fundamentals:{symbol}",
                    lambda: self.market_data.get_fundamentals(symbol),
                )
                sector = self._with_network_retries(
                    f"market.sector:{symbol}", lambda: self.market_data.get_sector(symbol)
                )
                earnings = self._with_network_retries(
                    f"market.earnings:{symbol}",
                    lambda: self.market_data.get_earnings_date(symbol),
                )
                self.cache.market[symbol] = {
                    "bars": bars,
                    "fundamentals": fundamentals,
                    "sector": sector,
                    "earnings_date": earnings,
                    "_cached_at": datetime.now(tz=timezone.utc).isoformat(),
                }
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Market data refresh failed for %s: %s", symbol, exc)

        self._map_symbols(symbols, worker)
        self.cache.refreshed_at["market"] = datetime.now(tz=timezone.utc)

    def refresh_options_data(self, symbols: list[str]) -> None:
        def worker(symbol: str) -> None:
            try:
                chain = self._with_network_retries(
                    f"options.chain:{symbol}", lambda: self.options_data.get_option_chain(symbol)
                )
                iv_rank = self._with_network_retries(
                    f"options.iv:{symbol}", lambda: self.options_data.get_iv_rank(symbol)
                )
                self.cache.options[symbol] = {"chain": chain, "iv_rank": iv_rank}
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Options data refresh failed for %s: %s", symbol, exc)

        self._map_symbols(symbols, worker)
        self.cache.refreshed_at["options"] = datetime.now(tz=timezone.utc)

    def refresh_polymarket_macro(self) -> None:
        self.cache.polymarket_macro = self._with_network_retries(
            "polymarket.macro", lambda: self.pm_client.get_macro_snapshot()
        )
        self.cache.refreshed_at["polymarket"] = datetime.now(tz=timezone.utc)

    def refresh_news_digest(self, symbols: list[str] | None = None) -> None:
        segments: list[dict[str, Any]] = []
        summaries: list[str] = []
        if self._mirofish is not None and self._mirofish.available:
            digest = self._mirofish.get_overnight_digest()
            segments.append({"source": "mirofish", "digest": digest})
            raw = digest.get("raw_output") or digest.get("note")
            if isinstance(raw, str) and raw.strip():
                summaries.append(raw.strip()[:4000])
        if self._daily_stock is not None and self._daily_stock.available:
            report = self._daily_stock.get_daily_market_report(symbols=symbols)
            segments.append({"source": "daily_stock_analysis", "report": report})
            raw_r = report.get("raw_report")
            if isinstance(raw_r, str) and raw_r.strip():
                summaries.append(raw_r.strip()[:12000])
            elif report.get("note"):
                summaries.append(str(report.get("note"))[:500])
        summary_text = (
            "\n\n".join(summaries).strip()
            or "No external digest configured; using neutral overnight context."
        )
        self.cache.news = {
            "summary": summary_text[:12000],
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "sources": segments,
        }
        self.cache.refreshed_at["news"] = datetime.now(tz=timezone.utc)

    def refresh_watchlist(
        self,
        candidates: list[str],
        max_size: int = 50,
        priority_symbols: list[str] | None = None,
    ) -> list[str]:
        """
        Applies PRD constraints:
        - max 50 symbols
        - no OTC checks delegated to upstream candidates source
        - liquidity proxy filter via average volume (>= 1M shares)
        - options availability proxy via non-null IV rank (relaxed for priority pins)
        """
        filtered: list[str] = []
        sectors: dict[str, int] = {}
        priority = [s.upper() for s in (priority_symbols or []) if s]
        queue = priority + [s for s in candidates if s.upper() not in set(priority)]

        # Prefetch the (bars, iv_rank, sector) triplet for every candidate in
        # parallel, then run the order-dependent filtering sequentially below.
        prefetched: dict[str, tuple[Any, Any, Any] | None] = {}

        def prefetch(symbol: str) -> None:
            try:
                bars = self._with_network_retries(
                    f"watchlist.bars:{symbol}",
                    lambda s=symbol: self.market_data.get_daily_bars(s, lookback_days=30),
                )
                iv_rank = self._with_network_retries(
                    f"watchlist.iv:{symbol}",
                    lambda s=symbol: self.options_data.get_iv_rank(s),
                )
                sector = self._with_network_retries(
                    f"watchlist.sector:{symbol}",
                    lambda s=symbol: self.market_data.get_sector(s),
                )
                prefetched[symbol] = (bars, iv_rank, sector)
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Watchlist skipped %s (fetch failed): %s", symbol, exc)
                prefetched[symbol] = None

        self._map_symbols(queue, prefetch)

        for symbol in queue:
            pin = symbol.upper() in set(priority)
            fetched = prefetched.get(symbol)
            if fetched is None:
                continue
            bars, iv_rank, sector = fetched
            if not bars:
                continue
            avg_volume = mean([bar["volume"] for bar in bars[-20:]])
            if avg_volume < 1_000_000 and not pin:
                continue
            if iv_rank is None and not pin:
                continue
            if not pin:
                projected = sectors.get(sector, 0) + 1
                if projected / max(1, len(filtered) + 1) > 0.30:
                    continue
            sectors[sector] = sectors.get(sector, 0) + 1
            if symbol.upper() in {f.upper() for f in filtered}:
                continue
            filtered.append(symbol)
            if len(filtered) >= max_size:
                break
        if not filtered:
            if self.cache.watchlist:
                LOGGER.warning("Watchlist refresh produced empty list; keeping prior watchlist.")
                return self.cache.watchlist
            fallback = candidates[: min(max_size, 10)]
            LOGGER.warning("Watchlist refresh produced empty list; using fallback seed symbols.")
            self.cache.watchlist = fallback
            self.cache.refreshed_at["watchlist"] = datetime.now(tz=timezone.utc)
            return fallback
        self.cache.watchlist = filtered
        self.cache.refreshed_at["watchlist"] = datetime.now(tz=timezone.utc)
        return filtered
