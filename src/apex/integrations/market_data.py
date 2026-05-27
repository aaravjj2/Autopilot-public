from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import requests
import yfinance as yf


class YFinanceMarketDataClient:
    def get_intraday_price(self, symbol: str) -> float:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d", interval="1m")
        if hist.empty:
            raise ValueError(f"No intraday data for {symbol}")
        return float(hist["Close"].iloc[-1])

    def get_daily_bars(self, symbol: str, lookback_days: int = 252) -> list[dict[str, Any]]:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=f"{lookback_days}d", interval="1d")
        if hist.empty:
            return []
        return [
            {
                "date": str(idx.date()),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": float(row["Volume"]),
            }
            for idx, row in hist.iterrows()
        ]

    def get_fundamentals(self, symbol: str) -> dict[str, Any]:
        try:
            info = yf.Ticker(symbol).info or {}
        except Exception:
            info = {}
        return {
            "pe": info.get("trailingPE"),
            "ev_to_ebitda": info.get("enterpriseToEbitda"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_date": info.get("earningsDate"),
            "analyst_recommendation": info.get("recommendationKey"),
        }

    def get_sector(self, symbol: str) -> str:
        try:
            return str((yf.Ticker(symbol).info or {}).get("sector", "UNKNOWN"))
        except Exception:
            return "UNKNOWN"

    def get_earnings_date(self, symbol: str) -> date | None:
        calendar = yf.Ticker(symbol).calendar
        if calendar is None or len(calendar) == 0:
            return None
        try:
            value = calendar.iloc[0, 0]
            if hasattr(value, "date"):
                return value.date()
        except Exception:
            return None
        return None


class YFinanceOptionsDataClient:
    def get_option_chain(self, symbol: str) -> dict[str, Any]:
        ticker = yf.Ticker(symbol)
        expirations = list(ticker.options or [])
        if not expirations:
            return {"symbol": symbol, "calls": [], "puts": [], "put_call_oi_ratio": 1.0, "put_call_volume_ratio": 1.0}

        expiry = expirations[0]
        chain = ticker.option_chain(expiry)
        calls = chain.calls.to_dict("records") if chain.calls is not None else []
        puts = chain.puts.to_dict("records") if chain.puts is not None else []
        put_oi = sum(float(item.get("openInterest") or 0) for item in puts) + 1e-9
        call_oi = sum(float(item.get("openInterest") or 0) for item in calls) + 1e-9
        put_vol = sum(float(item.get("volume") or 0) for item in puts) + 1e-9
        call_vol = sum(float(item.get("volume") or 0) for item in calls) + 1e-9
        return {
            "symbol": symbol,
            "expiry": expiry,
            "calls": calls,
            "puts": puts,
            "put_call_oi_ratio": put_oi / call_oi,
            "put_call_volume_ratio": put_vol / call_vol,
        }

    def get_iv_rank(self, symbol: str) -> float | None:
        ticker = yf.Ticker(symbol)
        expirations = list(ticker.options or [])
        if not expirations:
            return None
        chain = ticker.option_chain(expirations[0])
        calls = chain.calls
        puts = chain.puts
        if calls is None or puts is None or calls.empty or puts.empty:
            return None
        sample = np.concatenate(
            [
                calls["impliedVolatility"].fillna(0.0).to_numpy(dtype=float),
                puts["impliedVolatility"].fillna(0.0).to_numpy(dtype=float),
            ]
        )
        current_iv = float(np.nanmean(sample))
        hist = ticker.history(period="1y", interval="1d")
        if hist.empty:
            return max(0.0, min(100.0, current_iv * 100))
        returns = hist["Close"].pct_change().dropna()
        if returns.empty:
            return max(0.0, min(100.0, current_iv * 100))
        rolling = returns.rolling(21).std().dropna() * np.sqrt(252)
        if rolling.empty:
            return max(0.0, min(100.0, current_iv * 100))
        iv_min = float(rolling.min())
        iv_max = float(rolling.max())
        if iv_max <= iv_min:
            return 50.0
        iv_rank = ((current_iv - iv_min) / (iv_max - iv_min)) * 100
        return max(0.0, min(100.0, float(iv_rank)))


class TradierOptionsDataClient:
    def __init__(self, token: str, base_url: str = "https://sandbox.tradier.com"):
        self.token = token
        self.base_url = base_url.rstrip("/")

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }

    def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        response = requests.get(
            f"{self.base_url}{endpoint}",
            params=params,
            headers=self._headers,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def get_option_chain(self, symbol: str) -> dict[str, Any]:
        expirations_json = self._get("/v1/markets/options/expirations", {"symbol": symbol, "includeAllRoots": "true"})
        expiration_obj = (
            expirations_json.get("expirations", {}).get("date")
            if isinstance(expirations_json.get("expirations"), dict)
            else []
        )
        expirations = expiration_obj if isinstance(expiration_obj, list) else ([expiration_obj] if expiration_obj else [])
        if not expirations:
            return {"symbol": symbol, "calls": [], "puts": [], "put_call_oi_ratio": 1.0, "put_call_volume_ratio": 1.0}
        expiry = expirations[0]
        chain_json = self._get(
            "/v1/markets/options/chains",
            {"symbol": symbol, "expiration": expiry, "greeks": "true"},
        )
        options = (
            chain_json.get("options", {}).get("option")
            if isinstance(chain_json.get("options"), dict)
            else []
        )
        options = options if isinstance(options, list) else ([options] if options else [])
        calls = [item for item in options if item.get("option_type") == "call"]
        puts = [item for item in options if item.get("option_type") == "put"]
        put_oi = sum(float(item.get("open_interest") or 0) for item in puts) + 1e-9
        call_oi = sum(float(item.get("open_interest") or 0) for item in calls) + 1e-9
        put_vol = sum(float(item.get("volume") or 0) for item in puts) + 1e-9
        call_vol = sum(float(item.get("volume") or 0) for item in calls) + 1e-9
        return {
            "symbol": symbol,
            "expiry": expiry,
            "calls": calls,
            "puts": puts,
            "put_call_oi_ratio": put_oi / call_oi,
            "put_call_volume_ratio": put_vol / call_vol,
        }

    def get_iv_rank(self, symbol: str) -> float | None:
        chain = self.get_option_chain(symbol)
        sample = []
        for item in chain.get("calls", []) + chain.get("puts", []):
            greek_data = item.get("greeks") or {}
            iv = greek_data.get("mid_iv") or item.get("implied_volatility")
            if iv is None:
                continue
            sample.append(float(iv))
        if not sample:
            return None
        avg_iv = float(np.mean(sample))
        return max(0.0, min(100.0, avg_iv * 100))


class StubOptionsDataClient:
    def get_option_chain(self, symbol: str) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "calls": [],
            "puts": [],
            "put_call_oi_ratio": 1.0,
            "put_call_volume_ratio": 1.0,
        }

    def get_iv_rank(self, symbol: str) -> float | None:
        _ = symbol
        return 40.0
