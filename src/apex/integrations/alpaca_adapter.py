from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from apex.core.logging import get_logger

LOGGER = get_logger(__name__)


@dataclass
class AlpacaMCPAdapter:
    repo_path: str
    api_key: str = ""
    secret_key: str = ""
    base_url: str = "https://paper-api.alpaca.markets"
    paper_trade: bool = True
    toolsets: str = "all"
    _available: bool = field(default=False, init=False, repr=False)
    _server_script: Path | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.repo_path:
            LOGGER.warning("Alpaca MCP repo path not configured")
            return
        candidate = Path(self.repo_path).expanduser().resolve()
        if not candidate.exists():
            LOGGER.warning("Alpaca MCP repo not found at %s", candidate)
            return
        self._repo_root = candidate

        for script_name in ["alpaca_mcp_server/cli.py", "cli.py", "main.py"]:
            script_path = self._repo_root / script_name
            if script_path.exists():
                self._server_script = script_path
                break

        if not self._server_script:
            for root, _, files in self._repo_root.rglob("*.py"):
                if "cli" in root.lower() or "main" in root.lower():
                    self._server_script = Path(root)
                    break

        if self._server_script:
            self._available = True
            LOGGER.info("Alpaca MCP adapter initialized from %s", candidate)

    @property
    def available(self) -> bool:
        return self._available

    def get_server_command(self) -> list[str]:
        env = os.environ.copy()
        env["ALPACA_API_KEY"] = self.api_key or os.environ.get("APCA_API_KEY_ID", "")
        env["ALPACA_SECRET_KEY"] = self.secret_key or os.environ.get(
            "APCA_API_SECRET_KEY", ""
        )
        env["ALPACA_PAPER_TRADE"] = str(self.paper_trade).lower()
        env["ALPACA_BASE_URL"] = self.base_url
        env["ALPACA_TOOLSETS"] = self.toolsets

        cmd = [sys.executable, "-m", "alpaca_mcp_server.cli"]
        return cmd

    def start_server(self) -> subprocess.Popen[bytes]:
        if not self._available:
            raise RuntimeError("Alpaca MCP server not available")

        cmd = self.get_server_command()
        return subprocess.Popen(
            cmd,
            cwd=self._repo_root,
            env={
                **os.environ.copy(),
                **{
                    "ALPACA_API_KEY": self.api_key
                    or os.environ.get("APCA_API_KEY_ID", ""),
                    "ALPACA_SECRET_KEY": self.secret_key
                    or os.environ.get("APCA_API_SECRET_KEY", ""),
                    "ALPACA_PAPER_TRADE": str(self.paper_trade).lower(),
                },
            },
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def get_account_info(self) -> dict[str, Any]:
        return self._mock_account_info()

    def _mock_account_info(self) -> dict[str, Any]:
        return {
            "account_id": "paper_account",
            "status": "ACTIVE",
            "currency": "USD",
            "buying_power": 100000.0,
            "cash": 100000.0,
            "portfolio_value": 100000.0,
            "equity": 100000.0,
            "daytrade_count": 0,
            "pattern_day_trader": False,
            "trading_blocked": False,
            "account_blocked": False,
        }

    def get_stock_bars(
        self, symbol: str, timeframe: str = "1D", limit: int = 100
    ) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "bars": [],
            "note": "Use yfinance for price data; Alpaca MCP for real trading",
        }

    def get_options_chains(self, symbol: str) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "expirations": [],
            "strikes": [],
            "note": "Configure Tradier for options data",
        }

    def place_order(self, order_params: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": f"paper_order_{order_params.get('symbol', 'unknown')}_{self._gen_order_id()}",
            "symbol": order_params.get("symbol"),
            "qty": order_params.get("qty"),
            "side": order_params.get("side"),
            "type": order_params.get("type", "market"),
            "status": "accepted",
            "paper": True,
            "message": "Paper order accepted - use PaperBrokerSimulator for simulation",
        }

    def _gen_order_id(self) -> str:
        import time

        return str(int(time.time() * 1000))[-10:]

    def get_positions(self) -> list[dict[str, Any]]:
        return []

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        return {
            "id": order_id,
            "status": "cancelled",
            "paper": True,
        }


@dataclass
class AlpacaDirectIntegration:
    api_key: str = ""
    secret_key: str = ""
    base_url: str = "https://paper-api.alpaca.markets"

    def __post_init__(self) -> None:
        self._api_key = self.api_key or os.environ.get("APCA_API_KEY_ID", "")
        self._secret_key = self.secret_key or os.environ.get("APCA_API_SECRET_KEY", "")
        self._base_url = self.base_url or os.environ.get(
            "APCA_ENDPOINT", "https://paper-api.alpaca.markets"
        )

    @property
    def available(self) -> bool:
        return bool(self._api_key and self._secret_key)

    def _headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": self._api_key,
            "APCA-API-SECRET-KEY": self._secret_key,
            "Content-Type": "application/json",
        }

    def get_account(self) -> dict[str, Any]:
        import requests

        try:
            resp = requests.get(
                f"{self._base_url}/v2/account", headers=self._headers(), timeout=10
            )
            if resp.ok:
                return resp.json()
            return {"error": resp.text, "status": "error"}
        except Exception as exc:
            return {"error": str(exc), "status": "exception"}

    def get_positions(self) -> list[dict[str, Any]]:
        import requests

        try:
            resp = requests.get(
                f"{self._base_url}/v2/positions", headers=self._headers(), timeout=10
            )
            if resp.ok:
                return resp.json()
            return []
        except Exception:
            return []

    def get_orders(self, status: str = "open", limit: int = 50) -> list[dict[str, Any]]:
        import requests

        params = {"status": status, "limit": limit}
        try:
            resp = requests.get(
                f"{self._base_url}/v2/orders",
                headers=self._headers(),
                params=params,
                timeout=10,
            )
            if resp.ok:
                return resp.json()
            return []
        except Exception:
            return []

    def get_order_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.get_orders(status="closed", limit=limit)

    def get_bars(
        self,
        symbols: list[str],
        timeframe: str = "1Day",
        start: str | None = None,
        end: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        import requests

        params = {
            "symbols": ",".join(symbols),
            "timeframe": timeframe,
            "limit": limit,
        }
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        try:
            resp = requests.get(
                f"{self._base_url}/v2/stocks/bars",
                headers=self._headers(),
                params=params,
                timeout=10,
            )
            if resp.ok:
                return resp.json()
            return {"error": resp.text}
        except Exception as exc:
            return {"error": str(exc)}

    def get_option_contracts(
        self,
        underlying_symbol: str,
        expiration_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch option contracts for an underlying, optionally filtered by expiry."""
        import requests

        params: dict[str, str] = {"underlying_symbol": underlying_symbol, "status": "active"}
        if expiration_date:
            params["expiration_date"] = expiration_date
        try:
            resp = requests.get(
                f"{self._base_url}/v2/options/contracts",
                headers=self._headers(),
                params=params,
                timeout=15,
            )
            if resp.ok:
                return (resp.json() or {}).get("option_contracts", [])
            return []
        except Exception:
            return []

    def get_valid_occ_symbols(
        self,
        underlying_symbol: str,
        expiration_date: str,
    ) -> set[str]:
        """Return set of valid OCC symbols for a given underlying & expiry."""
        contracts = self.get_option_contracts(underlying_symbol, expiration_date)
        return {c.get("symbol", "").upper() for c in contracts if c.get("tradable")}

    def place_notional_market_order(
        self,
        symbol: str,
        notional_usd: float,
        side: str,
        time_in_force: str = "day",
    ) -> dict[str, Any]:
        """Market order by dollar notional (Alpaca fractional / notional API)."""
        import requests

        payload = {
            "symbol": symbol,
            "notional": str(round(max(1.0, notional_usd), 2)),
            "side": side.lower(),
            "type": "market",
            "time_in_force": time_in_force,
        }
        try:
            resp = requests.post(
                f"{self._base_url}/v2/orders",
                headers=self._headers(),
                json=payload,
                timeout=15,
            )
            if resp.ok:
                return resp.json()
            return {"error": resp.text, "status": "failed"}
        except Exception as exc:
            from apex.core.retry import is_transient_exception

            if is_transient_exception(exc):
                raise
            return {"error": str(exc), "status": "exception"}

    def place_order(
        self,
        symbol: str,
        qty: int | float,
        side: str,
        order_type: str = "market",
        time_in_force: str = "day",
        limit_price: float | None = None,
        stop_price: float | None = None,
    ) -> dict[str, Any]:
        import requests

        payload = {
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "type": order_type,
            "time_in_force": time_in_force,
        }
        if limit_price:
            payload["limit_price"] = limit_price
        if stop_price:
            payload["stop_price"] = stop_price

        try:
            resp = requests.post(
                f"{self._base_url}/v2/orders",
                headers=self._headers(),
                json=payload,
                timeout=10,
            )
            if resp.ok:
                return resp.json()
            return {"error": resp.text, "status": "failed"}
        except Exception as exc:
            return {"error": str(exc), "status": "exception"}

    def place_single_option_market_order(
        self,
        occ_symbol: str,
        qty: int,
        side: str,
        time_in_force: str = "day",
    ) -> dict[str, Any]:
        """Single-leg US option by OCC symbol (Alpaca options tier 2+)."""
        import requests

        payload = {
            "symbol": occ_symbol,
            "qty": str(max(1, int(qty))),
            "side": side.lower(),
            "type": "market",
            "time_in_force": time_in_force,
        }
        try:
            resp = requests.post(
                f"{self._base_url}/v2/orders",
                headers=self._headers(),
                json=payload,
                timeout=20,
            )
            if resp.ok:
                return resp.json()
            return {"error": resp.text, "status": "failed"}
        except Exception as exc:
            from apex.core.retry import is_transient_exception

            if is_transient_exception(exc):
                raise
            return {"error": str(exc), "status": "exception"}

    def place_multileg_option_order(
        self,
        legs: list[dict[str, str]],
        *,
        order_type: str = "market",
        time_in_force: str = "day",
        limit_price: str | None = None,
    ) -> dict[str, Any]:
        """Multi-leg options (spreads, straddles, condors) via ``order_class=mleg``."""
        import requests

        total = sum(int(x.get("ratio_qty", "1")) for x in legs)
        payload: dict[str, Any] = {
            "type": order_type,
            "time_in_force": time_in_force,
            "order_class": "mleg",
            "legs": legs,
            "qty": str(max(1, total)),
        }
        if order_type == "limit" and limit_price:
            payload["limit_price"] = str(limit_price)
        try:
            resp = requests.post(
                f"{self._base_url}/v2/orders",
                headers=self._headers(),
                json=payload,
                timeout=25,
            )
            if resp.ok:
                return resp.json()
            return {"error": resp.text, "status": "failed"}
        except Exception as exc:
            from apex.core.retry import is_transient_exception

            if is_transient_exception(exc):
                raise
            return {"error": str(exc), "status": "exception"}

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        import requests

        try:
            resp = requests.delete(
                f"{self._base_url}/v2/orders/{order_id}",
                headers=self._headers(),
                timeout=10,
            )
            return {
                "status": "cancelled" if resp.ok else "failed",
                "response": resp.text,
            }
        except Exception as exc:
            return {"error": str(exc)}

    def get_order(self, order_id: str) -> dict[str, Any]:
        import requests

        try:
            resp = requests.get(
                f"{self._base_url}/v2/orders/{order_id}",
                headers=self._headers(),
                timeout=10,
            )
            if resp.ok:
                return resp.json()
            return {"error": resp.text, "status": "error"}
        except Exception as exc:
            from apex.core.retry import is_transient_exception

            if is_transient_exception(exc):
                raise
            return {"error": str(exc), "status": "exception"}


class AlpacaStreamClient:
    """WebSocket streaming client for Alpaca real-time data (options quotes + trade updates)."""

    def __init__(
        self,
        api_key: str = "",
        secret_key: str = "",
        data_url: str = "wss://stream.data.alpaca.markets/v2/sip",
    ):
        self._api_key = api_key or os.environ.get("APCA_API_KEY_ID", "")
        self._secret_key = secret_key or os.environ.get("APCA_API_SECRET_KEY", "")
        self._data_url = data_url
        self._ws: Any = None
        self._running = False
        self._message_queue: list[dict[str, Any]] = []

    @property
    def available(self) -> bool:
        return bool(self._api_key and self._secret_key)

    def _ensure_ws(self) -> Any:
        import json
        import websocket
        if self._ws is not None:
            return self._ws
        ws = websocket.WebSocket()
        ws.connect(self._data_url, timeout=10)
        auth = {"action": "auth", "key": self._api_key, "secret": self._secret_key}
        ws.send(json.dumps(auth))
        resp = ws.recv()
        LOGGER.debug("Alpaca WS auth: %.200s", resp)
        self._ws = ws
        self._running = True
        return ws

    def start(self) -> None:
        """Open the WebSocket connection and authenticate."""
        self._ensure_ws()

    def stop(self) -> None:
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None

    def subscribe_option_quotes(self, symbols: list[str]) -> None:
        """Subscribe to real-time option quotes (P2.6)."""
        import json
        ws = self._ensure_ws()
        sub = {"action": "subscribe", "quotes": symbols}
        ws.send(json.dumps(sub))
        LOGGER.info("Subscribed to option quotes: %d symbols", len(symbols))

    def subscribe_trade_updates(self) -> None:
        """Subscribe to trade updates for fill confirmation (P2.7)."""
        import json
        ws = self._ensure_ws()
        sub = {"action": "subscribe", "tradeUpdates": ["*"]}
        ws.send(json.dumps(sub))
        LOGGER.info("Subscribed to trade updates")

    def read(self, timeout: float = 5.0) -> list[dict[str, Any]]:
        """Read pending messages with an optional timeout."""
        import json
        if not self._running or not self._ws:
            return []
        try:
            raw = self._ws.recv()
        except Exception:
            return []
        if not raw:
            return []
        try:
            msgs = json.loads(raw)
        except Exception:
            return []
        if not isinstance(msgs, list):
            msgs = [msgs]
        for m in msgs:
            if m.get("T") == "error":
                LOGGER.error("Alpaca WS error: %s", m.get("msg", m))
        return msgs

    def wait_for_fill(self, order_id: str, timeout: float = 60.0) -> dict[str, Any] | None:
        """Block until a fill message matching *order_id* arrives (P2.7).

        Returns the fill message dict or ``None`` on timeout.
        """
        import time
        deadline = time.monotonic() + timeout
        self.subscribe_trade_updates()
        while time.monotonic() < deadline:
            msgs = self.read(timeout=2.0)
            for m in msgs:
                if isinstance(m, dict) and m.get("T") == "trade_update":
                    order = m.get("order", {}) or {}
                    if str(order.get("id", "")).replace("-", "").lower() == order_id.replace("-", "").lower():
                        return m
        return None

    def close_stock_position(self, symbol: str) -> dict[str, Any]:
        """Liquidate an entire stock position (market). DELETE /v2/positions/{symbol}."""
        import urllib.parse

        import requests

        sym = urllib.parse.quote(symbol, safe="")
        try:
            resp = requests.delete(
                f"{self._base_url}/v2/positions/{sym}",
                headers=self._headers(),
                timeout=30,
            )
            if resp.status_code in (200, 201, 204):
                if resp.text:
                    try:
                        return resp.json()
                    except Exception:
                        return {"status": "closed", "symbol": symbol}
                return {"status": "closed", "symbol": symbol}
            return {"error": resp.text, "http_status": resp.status_code}
        except Exception as exc:
            return {"error": str(exc), "status": "exception"}
