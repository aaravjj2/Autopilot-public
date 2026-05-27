from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from apex.core.logging import get_logger
from apex.integrations.polymarket_gamma_public import GAMMA_API, fetch_gamma_markets

LOGGER = get_logger(__name__)


def _parse_gamma_probability(market: dict[str, Any]) -> float:
    raw = market.get("outcomePrices") or market.get("outcome_prices")
    if isinstance(raw, str):
        try:
            arr = json.loads(raw)
            if arr:
                return float(arr[0])
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    if isinstance(raw, list) and raw:
        try:
            return float(raw[0])
        except (ValueError, TypeError):
            pass
    for key in ("lastTradePrice", "bestBid", "oneDayPriceChange"):
        v = market.get(key)
        if v is not None:
            try:
                return float(v)
            except (ValueError, TypeError):
                pass
    return 0.5


def _normalize_gamma_market(m: dict[str, Any]) -> dict[str, Any]:
    prob = _parse_gamma_probability(m)
    return {
        "id": m.get("id") or m.get("conditionId") or m.get("slug"),
        "question": m.get("question") or m.get("title") or "Unknown",
        "price": prob,
        "volume": float(m.get("volume", 0) or m.get("volumeNum", 0) or 0),
    }


@dataclass
class PolymarketMCPAdapter:
    repo_path: str
    demo_mode: bool = False
    _server_process: Any = field(default=None, init=False, repr=False)
    _available: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.repo_path:
            LOGGER.warning("Polymarket MCP repo path not configured")
            return
        candidate = Path(self.repo_path).expanduser().resolve()
        if not candidate.exists():
            LOGGER.warning("Polymarket MCP repo not found at %s", candidate)
            return
        self._repo_root = candidate
        self._available = True
        LOGGER.info(
            "Polymarket MCP adapter initialized from %s (demo_mode=%s)",
            candidate,
            self.demo_mode,
        )

    def _fetch_gamma_markets(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        return fetch_gamma_markets(params, timeout=25)

    def _mcp_python_src(self) -> Path | None:
        src = self._repo_root / "src"
        return src if src.is_dir() else None

    def _mcp_async_eval(self, await_expr: str, *, timeout: int = 55) -> Any:
        """
        Run ``await <expr>`` via ``polymarket_mcp.tools.market_discovery`` in a subprocess.
        Install: ``pip install -e /path/to/polymarket-mcp-server`` so ``mcp`` and ``httpx`` resolve.
        """
        src = self._mcp_python_src()
        if not src:
            return None
        env = os.environ.copy()
        prev = env.get("PYTHONPATH", "").strip()
        env["PYTHONPATH"] = str(src) + (os.pathsep + prev if prev else "")
        script = (
            "import asyncio, json, sys\n"
            f"sys.path.insert(0, {json.dumps(str(src))})\n"
            "from polymarket_mcp.tools import market_discovery as md\n"
            "async def _fn():\n"
            f"    return await {await_expr}\n"
            "_out = asyncio.run(_fn())\n"
            "print(json.dumps(_out, default=str))\n"
        )
        try:
            proc = subprocess.run(
                [sys.executable, "-c", script],
                cwd=str(self._repo_root),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            if proc.returncode != 0:
                LOGGER.debug(
                    "Polymarket MCP python bridge rc=%s stderr=%s",
                    proc.returncode,
                    (proc.stderr or "")[:800],
                )
                return None
            out = (proc.stdout or "").strip()
            if not out:
                return None
            return json.loads(out.splitlines()[-1])
        except Exception as exc:  # noqa: BLE001
            LOGGER.info("Polymarket MCP python bridge skipped (%s); using Gamma REST", exc)
            return None

    @property
    def available(self) -> bool:
        return self._available

    def get_markets(
        self,
        limit: int = 10,
        active: bool = True,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        if self.demo_mode:
            mcp_rows = self._mcp_async_eval(
                f"md.get_trending_markets(timeframe='24h', limit={int(limit)})"
            )
            if isinstance(mcp_rows, list) and mcp_rows:
                return [_normalize_gamma_market(m) for m in mcp_rows if isinstance(m, dict)]

        params: dict[str, Any] = {
            "limit": limit,
            "active": str(active).lower(),
            "closed": "false",
            "order": "volume24hr",
            "ascending": "false",
        }
        if category:
            params["tag"] = category
        raw = self._fetch_gamma_markets(params)
        if not raw and not self.demo_mode:
            mcp_rows = self._mcp_async_eval(f"md.get_trending_markets(timeframe='24h', limit={int(limit)})")
            if isinstance(mcp_rows, list):
                raw = [x for x in mcp_rows if isinstance(x, dict)]
        return [_normalize_gamma_market(m) for m in raw if isinstance(m, dict)]

    def get_market_prices(
        self,
        market_id: str,
        history: bool = False,
    ) -> dict[str, Any]:
        _ = history
        raw = self._fetch_gamma_markets({"id": market_id, "limit": 1})
        if raw and isinstance(raw[0], dict):
            return {"market": _normalize_gamma_market(raw[0])}
        raw2 = self._fetch_gamma_markets({"slug": market_id, "limit": 1})
        if raw2 and isinstance(raw2[0], dict):
            return {"market": _normalize_gamma_market(raw2[0])}
        return {"error": "market_not_found", "id": market_id}

    def search_markets(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        if self.demo_mode:
            mcp_rows = self._mcp_async_eval(
                f"md.search_markets({json.dumps(query)}, limit={int(limit)})"
            )
            if isinstance(mcp_rows, list) and mcp_rows:
                return [_normalize_gamma_market(m) for m in mcp_rows if isinstance(m, dict)]

        mcp_rows = self._mcp_async_eval(f"md.search_markets({json.dumps(query)}, limit={int(limit)})")
        if isinstance(mcp_rows, list) and mcp_rows:
            return [_normalize_gamma_market(m) for m in mcp_rows if isinstance(m, dict)]

        params = {
            "query": query,
            "limit": limit,
            "active": "true",
            "closed": "false",
            "order": "volume24hr",
            "ascending": "false",
        }
        raw = self._fetch_gamma_markets(params)
        return [_normalize_gamma_market(m) for m in raw if isinstance(m, dict)]

    def _equity_rsi_14(self, symbol: str) -> float | None:
        try:
            import yfinance as yf

            hist = yf.Ticker(symbol).history(period="3mo")
            if hist is None or len(hist) < 20:
                return None
            closes = hist["Close"].astype(float)
            delta = closes.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / loss.replace(0, 1e-9)
            rsi = 100 - (100 / (1 + rs))
            val = float(rsi.iloc[-1])
            return val if val == val else None  # NaN check
        except Exception:
            return None

    def get_ticker_signal(self, symbol: str) -> dict[str, Any]:
        markets = self.search_markets(symbol, limit=4)
        if not markets:
            markets = self.search_markets(f"{symbol} stock", limit=4)
        if not markets:
            return {"signal": "NO_MARKET", "divergence": 0.0}

        market = markets[0]
        prob = float(market.get("price", 0.5))
        prob_percent = prob * 100

        signal = "NEUTRAL"
        if prob_percent >= 65:
            signal = "BULLISH"
        elif prob_percent <= 35:
            signal = "BEARISH"

        rsi = self._equity_rsi_14(symbol)
        divergence = 0.0
        if rsi is not None:
            divergence = max(-1.0, min(1.0, (prob_percent - rsi) / 100.0))

        return {
            "signal": signal,
            "probability": prob_percent,
            "divergence": divergence,
            "market_id": market.get("id"),
            "question": market.get("question"),
            "equity_rsi_14": rsi,
            "whale_alignment": self._check_whale_alignment(market),
        }

    def _check_whale_alignment(self, market: dict[str, Any]) -> float:
        return 0.0

    def get_macro_snapshot(self) -> list[dict[str, Any]]:
        if self.demo_mode:
            return [
                {
                    "market": "Demo: Fed policy path",
                    "probability": 0.42,
                    "volume": 0.0,
                    "market_id": "demo-1",
                },
                {
                    "market": "Demo: US recession window",
                    "probability": 0.28,
                    "volume": 0.0,
                    "market_id": "demo-2",
                },
                {
                    "market": "Demo: Core CPI path",
                    "probability": 0.31,
                    "volume": 0.0,
                    "market_id": "demo-3",
                },
            ]

        raw = self._fetch_gamma_markets(
            {
                "limit": 24,
                "active": "true",
                "closed": "false",
                "order": "volume24hr",
                "ascending": "false",
            }
        )
        mcp_rows = self._mcp_async_eval("md.get_trending_markets(timeframe='24h', limit=24)")
        if isinstance(mcp_rows, list) and len(mcp_rows) >= 3:
            raw = [x for x in mcp_rows if isinstance(x, dict)]

        out: list[dict[str, Any]] = []
        for m in raw[:12]:
            if not isinstance(m, dict):
                continue
            norm = _normalize_gamma_market(m)
            out.append(
                {
                    "market": norm["question"],
                    "probability": float(norm["price"]),
                    "volume": norm["volume"],
                    "market_id": norm["id"],
                }
            )
        if len(out) < 3:
            LOGGER.warning("Gamma macro snapshot thin (%s rows); padding stub", len(out))
            return [
                {"market": "Gamma thin", "probability": 0.5, "volume": 0.0},
                {"market": "Gamma thin", "probability": 0.5, "volume": 0.0},
                {"market": "Gamma thin", "probability": 0.5, "volume": 0.0},
            ]
        return out

    def detect_macro_shifts(
        self, baseline: list[dict[str, Any]], current: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        shifts: list[dict[str, Any]] = []
        base_map = {str(x.get("market")): x for x in baseline}
        for row in current:
            key = str(row.get("market"))
            if key not in base_map:
                continue
            b = base_map[key]
            try:
                cur_p = float(row.get("probability", 0)) * 100
                base_p = float(b.get("probability", 0)) * 100
            except (TypeError, ValueError):
                continue
            shift = abs(cur_p - base_p)
            if shift >= 10:
                shifts.append(
                    {
                        "question": key,
                        "shift_pct": shift,
                        "direction": "UP" if cur_p > base_p else "DOWN",
                        "baseline_prob": base_p,
                        "current_prob": cur_p,
                    }
                )
        return shifts

    def get_order_book(self, market_id: str) -> dict[str, Any]:
        _ = market_id
        return {
            "bids": [],
            "asks": [],
            "spread": 0.0,
            "note": "APEX uses Gamma for discovery; full CLOB book requires authenticated Polymarket client.",
        }

    def get_user_positions(self) -> list[dict[str, Any]]:
        return []

    def get_intraday_macro_shift(self) -> list[dict[str, Any]]:
        snapshot = self.get_macro_snapshot()
        shifts: list[dict[str, Any]] = []
        for row in snapshot:
            prob = float(row.get("probability", 0.5)) * 100
            q = str(row.get("market", ""))
            if prob >= 60:
                shifts.append(
                    {
                        "question": q,
                        "probability": prob,
                        "direction": "BULLISH" if prob > 55 else "NEUTRAL",
                    }
                )
            elif prob <= 40:
                shifts.append(
                    {
                        "question": q,
                        "probability": prob,
                        "direction": "BEARISH",
                    }
                )
        return shifts


@dataclass
class PolymarketWebSocketAdapter:
    repo_path: str
    _available: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.repo_path:
            LOGGER.warning("polymarket-mcp-server repo path not configured")
            return
        candidate = Path(self.repo_path).expanduser().resolve()
        if not candidate.exists():
            LOGGER.warning("polymarket-mcp-server not found at %s", candidate)
            return
        self._repo_root = candidate
        self._available = True
        LOGGER.info("Polymarket WebSocket adapter initialized from %s", candidate)

    @property
    def available(self) -> bool:
        return self._available

    def subscribe_market_prices(self, market_ids: list[str]) -> dict[str, Any]:
        if not self._available:
            return {"status": "unavailable"}

        return {
            "status": "subscribed",
            "market_ids": market_ids,
            "endpoint": "wss://ws-subscriptions-clob.polymarket.com/ws/",
            "message": "Connect WebSocket and send: subscribe_market_prices",
        }

    def subscribe_orderbook_updates(self, market_id: str) -> dict[str, Any]:
        return {
            "status": "subscribed",
            "market_id": market_id,
            "endpoint": "wss://ws-live-data.polymarket.com",
            "message": "Connect to orderbook endpoint for live updates",
        }

    def get_realtime_status(self) -> dict[str, Any]:
        return {
            "status": "active" if self._available else "inactive",
            "subscriptions": [],
            "last_update": None,
        }

    def unsubscribe_realtime(self, subscription_id: str) -> dict[str, Any]:
        return {"status": "unsubscribed", "subscription_id": subscription_id}
