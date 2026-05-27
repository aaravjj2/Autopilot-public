"""Authenticated Kalshi Trade API — demo or production order placement."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from apex.core.config import Settings
from apex.core.logging import get_logger
from apex.integrations.kalshi_adapter import KalshiAuth

LOGGER = get_logger(__name__)

DEFAULT_DEMO_BASE = "https://demo-api.kalshi.co/trade-api/v2"


def kalshi_api_base(settings: Settings) -> str:
    base = (settings.kalshi_base_url or DEFAULT_DEMO_BASE).rstrip("/")
    return base


def kalshi_execution_venue(settings: Settings) -> str:
    return "kalshi_demo" if settings.kalshi_demo_trading_enabled else "kalshi_paper"


def kalshi_execution_mode_label(settings: Settings) -> str:
    if settings.kalshi_demo_trading_enabled:
        return "kalshi_demo"
    return "paper_simulated"


def resolve_kalshi_private_key_pem(settings: Settings) -> str | None:
    inline = (settings.kalshi_api_private_key or "").strip()
    if inline and "BEGIN" in inline:
        return inline
    path = Path(settings.kalshi_private_key_path)
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return None


def kalshi_credentials_configured(settings: Settings) -> bool:
    key = (settings.kalshi_access_key or "").strip()
    pem = resolve_kalshi_private_key_pem(settings)
    return bool(key and pem)


class KalshiTradingClient:
    """Signed REST client for Kalshi portfolio orders."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = kalshi_api_base(settings)
        access_key = (settings.kalshi_access_key or "").strip()
        pem = resolve_kalshi_private_key_pem(settings)
        if not access_key or not pem:
            raise ValueError("Kalshi API key and private key are required for demo trading")
        self._auth = KalshiAuth(access_key, pem)
        self._http = httpx.Client(timeout=30.0, base_url=self.base_url)

    def _sign_path(self, path: str) -> str:
        """Kalshi signatures use the full URL path (e.g. /trade-api/v2/portfolio/orders)."""
        if path.startswith("/trade-api/"):
            return path
        return urlparse(self.base_url + path).path

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sign_path = self._sign_path(path)
        headers = self._auth.headers(method, sign_path)
        resp = self._http.request(method, path, headers=headers, json=json_body)
        if resp.status_code >= 400:
            LOGGER.error("Kalshi %s %s failed: %s %s", method, path, resp.status_code, resp.text[:500])
            resp.raise_for_status()
        if not resp.content:
            return {}
        return resp.json()

    @staticmethod
    def _price_to_cents(price: float) -> int:
        return max(1, min(99, int(round(float(price) * 100))))

    @staticmethod
    def _stake_to_contract_count(stake_usd: float, price: float) -> int:
        p = max(0.01, float(price))
        return max(1, int(float(stake_usd) / p))

    def create_yes_limit_buy(
        self,
        ticker: str,
        stake_usd: float,
        price: float,
        *,
        client_order_id: str | None = None,
    ) -> dict[str, Any]:
        """Place a limit buy for YES contracts. Returns API order dict."""
        cid = client_order_id or str(uuid4())
        yes_cents = self._price_to_cents(price)
        count = self._stake_to_contract_count(stake_usd, yes_cents / 100.0)
        body = {
            "ticker": ticker,
            "action": "buy",
            "side": "yes",
            "count": count,
            "type": "limit",
            "yes_price": yes_cents,
            "client_order_id": cid,
        }
        data = self._request("POST", "/portfolio/orders", json_body=body)
        order = data.get("order") or data
        order_id = str(order.get("order_id") or order.get("id") or cid)
        LOGGER.info(
            "Kalshi demo order %s %s YES x%d @ %dc",
            order_id,
            ticker,
            count,
            yes_cents,
        )
        return {
            "order_id": order_id,
            "client_order_id": cid,
            "count": count,
            "yes_price_cents": yes_cents,
            "status": order.get("status"),
            "raw": order,
        }

    def get_order(self, order_id: str) -> dict[str, Any]:
        data = self._request("GET", f"/portfolio/orders/{order_id}")
        return data.get("order") or data

    def wait_for_fill(
        self,
        order_id: str,
        timeout_seconds: int = 60,
        poll_interval: float = 1.0,
    ) -> tuple[bool, str]:
        deadline = time.time() + timeout_seconds
        terminal_ok = {"executed", "filled", "complete", "completed"}
        terminal_bad = {"canceled", "cancelled", "rejected", "failed"}
        while time.time() < deadline:
            try:
                order = self.get_order(order_id)
            except Exception as exc:
                return False, f"order_lookup_failed:{exc}"
            status = str(order.get("status") or "").lower()
            if status in terminal_ok:
                return True, f"filled:{status}"
            if status in terminal_bad:
                return False, f"terminal:{status}"
            time.sleep(poll_interval)
        return False, "timeout"

    def close(self) -> None:
        self._http.close()
