"""Kalshi WebSocket L2 orderbook connection manager (DB13).

Connects to Kalshi's orderbook WebSocket, parses snapshot/delta frames,
and writes to Redis via orderbook_l2.ingest_orderbook().

Usage:
    mgr = KalshiWsConnectionManager(settings)
    await mgr.run(tickers=["KX-FED-25", "KX-CPI-25"])
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

LOGGER = logging.getLogger(__name__)

_WS_PROD = "wss://trading-api.kalshi.com/trade-api/ws/v2"
_WS_DEMO = "wss://demo-api.kalshi.co/trade-api/ws/v2"

_MIN_RECONNECT_SEC = 2.0
_MAX_RECONNECT_SEC = 60.0
_HEARTBEAT_SEC = 30.0
_WS_SIGN_PATH = "/trade-api/ws/v2"


class KalshiWsConnectionManager:
    """Maintains a persistent WS connection to Kalshi orderbook feed."""

    def __init__(self, settings: Any) -> None:
        self.settings = settings
        self._running = False
        self._reconnect_count = 0
        self._last_message_at: float = 0.0
        self._last_frame_at: float = 0.0
        self._connected_at: float = 0.0
        self._subscribed_tickers: list[str] = []

    @property
    def _ws_url(self) -> str:
        base = getattr(self.settings, "kalshi_base_url", "") or ""
        if "demo" in str(base).lower() or getattr(
            self.settings, "kalshi_demo_trading_enabled", False
        ):
            return _WS_DEMO
        return _WS_PROD

    def _auth_headers(self) -> dict[str, str]:
        from apex.integrations.kalshi_adapter import KalshiAuth
        from apex.integrations.kalshi_trading import (
            kalshi_credentials_configured,
            resolve_kalshi_private_key_pem,
        )

        if not kalshi_credentials_configured(self.settings):
            return {}
        access_key = (self.settings.kalshi_access_key or "").strip()
        pem = resolve_kalshi_private_key_pem(self.settings)
        if not access_key or not pem:
            return {}
        return KalshiAuth(access_key, pem).headers("GET", _WS_SIGN_PATH)

    def _subscribe_msg(self, tickers: list[str], cmd_id: int = 1) -> str:
        return json.dumps(
            {
                "id": cmd_id,
                "cmd": "subscribe",
                "params": {
                    "channels": ["orderbook_delta"],
                    "market_tickers": tickers,
                },
            }
        )

    def _parse_frame(self, raw: str) -> tuple[str | None, str | None, dict | None]:
        """Parse a WS message. Returns (msg_type, ticker, payload) or (None, None, None)."""
        try:
            msg = json.loads(raw)
            msg_type = msg.get("type") or msg.get("msg")
            ticker = (msg.get("params", {}) or {}).get("market_ticker")
            if not ticker:
                ticker = msg.get("market_ticker") or (msg.get("result", {}) or {}).get(
                    "market_ticker"
                )
            return msg_type, ticker, msg
        except Exception:
            return None, None, None

    def _apply_frame(self, msg_type: str, ticker: str, payload: dict) -> None:
        """Write snapshot or delta to Redis L2 cache."""
        try:
            from apex.cache.orderbook_l2 import ingest_orderbook

            result = payload.get("result") or payload.get("params", {}) or {}
            book: dict[str, Any] = {}

            if msg_type in ("orderbook_snapshot", "subscribed"):
                book["yes"] = result.get("yes") or []
                book["no"] = result.get("no") or []
            elif msg_type == "orderbook_delta":
                side = result.get("side", "yes")
                price = result.get("price")
                qty = result.get("quantity", result.get("qty", 0))
                if price is not None:
                    book[side] = [[float(price), float(qty)]]
            else:
                return

            if book:
                ingest_orderbook(
                    "KALSHI", ticker, book, redis_url=self.settings.redis_url
                )
                self._last_message_at = time.monotonic()
        except Exception as exc:
            LOGGER.debug("_apply_frame error for %s: %s", ticker, exc)

    async def run(self, tickers: list[str]) -> None:
        """Main loop: connect, subscribe, process, reconnect on failure."""
        import websockets

        self._running = True
        self._subscribed_tickers = tickers
        delay = _MIN_RECONNECT_SEC

        while self._running:
            try:
                headers = self._auth_headers()
                if not headers:
                    LOGGER.warning("KalshiWs: credentials not configured; stopping")
                    self._running = False
                    break
                LOGGER.info(
                    "KalshiWs connecting to %s (attempt %d)",
                    self._ws_url,
                    self._reconnect_count + 1,
                )
                connect_kwargs: dict[str, Any] = {
                    "ping_interval": _HEARTBEAT_SEC,
                    "ping_timeout": 10,
                    "close_timeout": 5,
                }
                import inspect

                ws_params = inspect.signature(websockets.connect).parameters
                if "additional_headers" in ws_params:
                    connect_kwargs["additional_headers"] = headers
                else:
                    connect_kwargs["extra_headers"] = headers
                async with websockets.connect(self._ws_url, **connect_kwargs) as ws:
                    await self._consume_ws(ws, tickers)
                delay = _MIN_RECONNECT_SEC

            except Exception as exc:
                if not self._running:
                    break
                self._reconnect_count += 1
                LOGGER.warning(
                    "KalshiWs disconnected (attempt %d): %s. Reconnecting in %.1fs",
                    self._reconnect_count,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, _MAX_RECONNECT_SEC)

    async def _consume_ws(self, ws: Any, tickers: list[str]) -> None:
        self._reconnect_count = 0
        now = time.monotonic()
        self._connected_at = now
        self._last_frame_at = now
        LOGGER.info("KalshiWs connected. Subscribing %d tickers.", len(tickers))
        await ws.send(self._subscribe_msg(tickers))

        async for raw in ws:
            if not self._running:
                break
            self._last_frame_at = time.monotonic()
            msg_type, ticker, payload = self._parse_frame(str(raw))
            if msg_type and ticker and payload:
                self._apply_frame(msg_type, ticker, payload)

    def stop(self) -> None:
        self._running = False

    @property
    def seconds_since_last_message(self) -> float:
        if self._last_message_at == 0.0:
            return float("inf")
        return time.monotonic() - self._last_message_at

    @property
    def seconds_since_last_frame(self) -> float:
        if self._last_frame_at == 0.0:
            return float("inf")
        return time.monotonic() - self._last_frame_at

    @property
    def is_stale(self) -> bool:
        """True when feed silence exceeds stale threshold outside startup grace."""
        stale_after = float(getattr(self.settings, "kalshi_ws_stale_after_sec", 90.0) or 90.0)
        startup_grace = float(
            getattr(self.settings, "kalshi_ws_startup_grace_sec", 180.0) or 180.0
        )
        if self._connected_at > 0.0 and (time.monotonic() - self._connected_at) < startup_grace:
            return False
        freshest = max(self._last_message_at, self._last_frame_at)
        if freshest == 0.0:
            return True
        return (time.monotonic() - freshest) > stale_after
