from __future__ import annotations
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from apex.domain.models import SettlementVerdict

TIMING_PATTERNS  = [r"\d{4}-\d{2}-\d{2}", r"end of \w+", r"by \w+ \d+"]
SOURCE_KEYWORDS  = ["BLS", "BEA", "Fed", "FOMC", "CME", "CoinGecko", "Binance"]
ROUND_PATTERNS   = [r"\d+\.\d+ ?%", r"rounded to"]

@dataclass
class SettlementAuditor:

    def _parse_ts(self, ts_str: str | None) -> float | None:
        if not ts_str:
            return None
        try:
            if ts_str.endswith("Z"):
                ts_str = ts_str[:-1] + "+00:00"
            return datetime.fromisoformat(ts_str).timestamp()
        except Exception:
            return None

    def verify(
        self, 
        kalshi_title: str, 
        poly_question: str,
        kalshi_market: Any = None,
        poly_market: dict[str, Any] | None = None
    ) -> SettlementVerdict:
        flags = []
        score = 1.0

        # 1. Check timing alignment
        k_dates = set(re.findall(r"\d{4}-\d{2}-\d{2}|\b(?:Q[1-4])\s?\d{4}\b", kalshi_title, re.I))
        p_dates = set(re.findall(r"\d{4}-\d{2}-\d{2}|\b(?:Q[1-4])\s?\d{4}\b", poly_question, re.I))
        if k_dates and p_dates and k_dates != p_dates:
            flags.append("timing_mismatch")
            score -= 0.35

        # 2. Check resolution source alignment
        k_sources = {kw for kw in SOURCE_KEYWORDS if kw.lower() in kalshi_title.lower()}
        p_sources = {kw for kw in SOURCE_KEYWORDS if kw.lower() in poly_question.lower()}
        if k_sources and p_sources and k_sources != p_sources:
            flags.append("source_divergence")
            score -= 0.30

        # 3. Check rounding / threshold differences
        k_rounds = re.findall(r"\d+\.?\d*\s?%", kalshi_title)
        p_rounds = re.findall(r"\d+\.?\d*\s?%", poly_question)
        if k_rounds and p_rounds and k_rounds != p_rounds:
            flags.append("threshold_mismatch")
            score -= 0.25

        # 4. Check for entertainment/subjective resolution (highest risk)
        entertainment_terms = ["perform", "appear", "win award", "nominated", "announce"]
        if any(t in kalshi_title.lower() or t in poly_question.lower() for t in entertainment_terms):
            flags.append("subjective_resolution_risk")
            score -= 0.20

        # 5. Check resolution time mismatch
        kalshi_ts = None
        poly_ts = None

        if kalshi_market and hasattr(kalshi_market, "close_time"):
            kalshi_ts = self._parse_ts(kalshi_market.close_time)
        elif isinstance(kalshi_market, dict) and "close_time" in kalshi_market:
            kalshi_ts = self._parse_ts(kalshi_market["close_time"])
            
        if poly_market:
            p_date = poly_market.get("end_date") or poly_market.get("endDate")
            if p_date:
                poly_ts = self._parse_ts(p_date)
                
        if kalshi_ts and poly_ts:
            if abs(kalshi_ts - poly_ts) > 4 * 3600:
                flags.append("RESOLUTION_TIME_MISMATCH")
                score -= 0.20

        score = max(0.0, round(score, 2))

        if score >= 0.75:
            recommendation = "SAFE"
        elif score >= 0.45:
            recommendation = "CAUTION"
        else:
            recommendation = "BLOCK"

        return SettlementVerdict(
            match_score=score,
            flags=flags,
            recommendation=recommendation,
        )
