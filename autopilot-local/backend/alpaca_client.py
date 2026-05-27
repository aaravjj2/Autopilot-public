from __future__ import annotations

import time
from typing import Any

import httpx

from config import get_settings


class AlpacaClient:
  def __init__(self) -> None:
    s = get_settings()
    self.api_key = s["alpaca_api_key"]
    self.api_secret = s["alpaca_api_secret"]
    self.base_url = s["alpaca_base_url"].rstrip("/")
    self.data_url = s["alpaca_data_url"].rstrip("/")

  @property
  def configured(self) -> bool:
    return bool(self.api_key and self.api_secret)

  def _headers(self) -> dict[str, str]:
    return {
      "APCA-API-KEY-ID": self.api_key,
      "APCA-API-SECRET-KEY": self.api_secret,
      "Content-Type": "application/json",
    }

  def ping(self) -> dict[str, Any]:
    if not self.configured:
      return {"ok": False, "error": "missing Alpaca credentials"}
    try:
      with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{self.base_url}/v2/account", headers=self._headers())
        if r.status_code == 200:
          data = r.json()
          return {
            "ok": True,
            "equity": float(data.get("equity", 0)),
            "cash": float(data.get("cash", 0)),
            "buying_power": float(data.get("buying_power", 0)),
          }
        return {"ok": False, "error": r.text}
    except Exception as exc:
      return {"ok": False, "error": str(exc)}

  def get_account(self) -> dict[str, Any]:
    with httpx.Client(timeout=10.0) as client:
      r = client.get(f"{self.base_url}/v2/account", headers=self._headers())
      r.raise_for_status()
      return r.json()

  def get_positions(self) -> list[dict[str, Any]]:
    with httpx.Client(timeout=10.0) as client:
      r = client.get(f"{self.base_url}/v2/positions", headers=self._headers())
      if r.status_code != 200:
        return []
      return r.json()

  def get_latest_prices(self, symbols: list[str]) -> dict[str, float]:
    if not symbols:
      return {}
    prices: dict[str, float] = {}
    if self.configured:
      try:
        params = {"symbols": ",".join(symbols), "feed": "iex"}
        with httpx.Client(timeout=10.0) as client:
          r = client.get(
            f"{self.data_url}/v2/stocks/snapshots",
            headers=self._headers(),
            params=params,
          )
          if r.status_code == 200:
            for sym, snap in (r.json() or {}).items():
              latest = snap.get("latestTrade") or snap.get("minuteBar") or {}
              p = latest.get("p") or latest.get("c")
              if p:
                prices[sym.upper()] = float(p)
      except Exception:
        pass
    missing = [s for s in symbols if s.upper() not in prices]
    if missing:
      import yfinance as yf

      for sym in missing:
        try:
          t = yf.Ticker(sym)
          hist = t.history(period="1d")
          if not hist.empty:
            prices[sym.upper()] = float(hist["Close"].iloc[-1])
        except Exception:
          continue
    return prices

  def place_market_order(
    self, symbol: str, qty: float, side: str, time_in_force: str = "day"
  ) -> dict[str, Any]:
    payload = {
      "symbol": symbol.upper(),
      "qty": str(max(0.0001, round(qty, 4))),
      "side": side.lower(),
      "type": "market",
      "time_in_force": time_in_force,
    }
    with httpx.Client(timeout=15.0) as client:
      r = client.post(
        f"{self.base_url}/v2/orders", headers=self._headers(), json=payload
      )
      if r.status_code in (200, 201):
        return r.json()
      return {"error": r.text, "status": "failed"}

  def wait_for_order(self, order_id: str, timeout_sec: float = 30.0) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
      with httpx.Client(timeout=10.0) as client:
        r = client.get(
          f"{self.base_url}/v2/orders/{order_id}", headers=self._headers()
        )
        if r.status_code != 200:
          time.sleep(1)
          continue
        data = r.json()
        status = data.get("status", "")
        if status in {"filled", "partially_filled", "canceled", "expired", "rejected"}:
          return data
      time.sleep(1)
    return {"status": "timeout", "id": order_id}

  def close_position(self, symbol: str) -> dict[str, Any]:
    sym = symbol.upper()
    with httpx.Client(timeout=15.0) as client:
      r = client.delete(
        f"{self.base_url}/v2/positions/{sym}", headers=self._headers()
      )
      if r.status_code in (200, 204):
        return {"status": "closed", "symbol": sym}
      return {"error": r.text, "status": "failed"}
