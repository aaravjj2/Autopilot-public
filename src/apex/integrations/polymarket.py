from __future__ import annotations

from datetime import datetime, timezone


class StubPredictionMarketClient:
    def get_macro_snapshot(self) -> list[dict]:
        return [
            {"market": "Fed cuts before year-end", "probability": 0.42, "updated_at": datetime.now(tz=timezone.utc).isoformat()},
            {"market": "US recession this year", "probability": 0.28, "updated_at": datetime.now(tz=timezone.utc).isoformat()},
            {"market": "Core CPI above 3%", "probability": 0.31, "updated_at": datetime.now(tz=timezone.utc).isoformat()},
        ]

    def get_ticker_signal(self, symbol: str) -> dict | None:
        if symbol.upper() in {"SPY", "QQQ", "IWM"}:
            return {"signal": "BULLISH", "divergence": 0.2, "whale_alignment": 0.55}
        return None

    def get_intraday_macro_shift(self) -> list[dict]:
        return []
