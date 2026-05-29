---
name: arb-engine
description: >
  Use this skill to build or debug the cross-platform arbitrage scanner (ArbEngine) and
  SettlementAuditor. Covers fuzzy market matching between Kalshi and Polymarket, executable
  spread computation, settlement rule comparison, and ArbOpportunity dataclass emission.
  Trigger when implementing arb_engine.py, settlement_auditor.py, or their tests.
compatibility: Antigravity CLI (agy), Claude Code, Gemini CLI
---

# Arb Engine Skill

## ArbOpportunity Dataclass

```python
# src/apex/domain/models.py  (add alongside existing models)
from dataclasses import dataclass, field
from datetime import datetime
import uuid

@dataclass
class ArbOpportunity:
    kalshi_ticker: str
    poly_market_id: str
    question: str                      # normalized question text
    kalshi_title: str                  # raw Kalshi title
    poly_title: str                    # raw Polymarket question
    kalshi_yes_ask: float              # reconstructed from bid
    poly_no_ask: float                 # from Gamma REST bestAsk
    gross_spread: float                # 1.00 - yes_ask - no_ask
    net_edge: float                    # after Kalshi 7% fee
    settlement_match_score: float      # 0.0–1.0
    settlement_flags: list[str]        # e.g. ["timing_mismatch", "source_diff"]
    detection_ts: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    resolution_ts: datetime | None = None
    outcome: str | None = None         # "WIN" | "LOSS" | "PUSH"
    pnl: float | None = None
    volume_kalshi: float = 0.0
    volume_poly: float = 0.0
```

---

## ArbEngine — Full Implementation

```python
# src/apex/services/arb_engine.py
from __future__ import annotations
import difflib
from dataclasses import dataclass
from apex.core.config import Settings
from apex.core.logging import get_logger
from apex.domain.models import ArbOpportunity
from apex.integrations.kalshi_adapter import KalshiEventClient
from apex.repositories.sqlite_store import SQLiteStore

LOGGER = get_logger(__name__)
FUZZY_THRESHOLD = 0.72      # SequenceMatcher ratio for market title matching
MIN_VOLUME_USD   = 10_000   # Both platforms must exceed this

@dataclass
class ArbEngine:
    settings: Settings
    store: SQLiteStore

    def scan(self) -> list[ArbOpportunity]:
        """Fetch Kalshi + Polymarket markets, find matching pairs, compute arb."""
        kalshi_client = KalshiEventClient(self.settings)
        kalshi_markets = kalshi_client.get_macro_markets(
            min_volume=self.settings.kalshi_min_volume_24h
        )

        from apex.integrations.polymarket_gamma_public import fetch_active_liquid_markets
        poly_markets = fetch_active_liquid_markets(
            min_volume=self.settings.kalshi_min_volume_24h
        )

        opportunities = []
        for k in kalshi_markets:
            match = self._fuzzy_match(k.title, poly_markets)
            if match is None:
                continue

            poly = match
            gross = round(1.00 - k.best_ask_yes - float(poly.get("bestAsk_no", 1.0)), 4)
            net   = self._compute_net_edge(k.best_ask_yes, float(poly.get("bestAsk_no", 1.0)))

            if net < self.settings.arb_min_net_edge:
                continue

            from apex.services.settlement_auditor import SettlementAuditor
            auditor = SettlementAuditor()
            verdict = auditor.verify(k.title, poly.get("question", ""))

            opp = ArbOpportunity(
                kalshi_ticker=k.ticker,
                poly_market_id=poly.get("id", ""),
                question=k.title,
                kalshi_title=k.title,
                poly_title=poly.get("question", ""),
                kalshi_yes_ask=k.best_ask_yes,
                poly_no_ask=float(poly.get("bestAsk_no", 1.0)),
                gross_spread=gross,
                net_edge=net,
                settlement_match_score=verdict.match_score,
                settlement_flags=verdict.flags,
                volume_kalshi=k.volume_24h,
                volume_poly=float(poly.get("volume24hr", 0)),
            )
            opportunities.append(opp)
            LOGGER.info(
                "Arb found: %s | net_edge=%.3f | settlement=%.2f",
                k.ticker, net, verdict.match_score
            )

        LOGGER.info("ArbEngine.scan(): found %d opportunities", len(opportunities))
        return opportunities

    def _fuzzy_match(
        self,
        kalshi_title: str,
        poly_markets: list[dict],
    ) -> dict | None:
        best_score = 0.0
        best_match = None
        k_norm = kalshi_title.lower().strip()
        for pm in poly_markets:
            p_norm = pm.get("question", "").lower().strip()
            score = difflib.SequenceMatcher(None, k_norm, p_norm).ratio()
            if score > best_score:
                best_score = score
                best_match = pm
        if best_score >= FUZZY_THRESHOLD:
            return best_match
        return None

    @staticmethod
    def _compute_net_edge(kalshi_yes_ask: float, poly_no_ask: float) -> float:
        gross = 1.00 - kalshi_yes_ask - poly_no_ask
        fee   = 0.07 * (1.00 - kalshi_yes_ask)  # Kalshi fee on YES win
        return round(gross - fee, 4)
```

---

## SettlementAuditor — Full Implementation

```python
# src/apex/services/settlement_auditor.py
from __future__ import annotations
import re
from dataclasses import dataclass, field

TIMING_PATTERNS  = [r"\d{4}-\d{2}-\d{2}", r"end of \w+", r"by \w+ \d+"]
SOURCE_KEYWORDS  = ["BLS", "BEA", "Fed", "FOMC", "CME", "CoinGecko", "Binance"]
ROUND_PATTERNS   = [r"\d+\.\d+ ?%", r"rounded to"]

@dataclass
class SettlementVerdict:
    match_score: float          # 0.0 (mismatch) – 1.0 (identical)
    flags: list[str]            # human-readable warning tags
    recommendation: str         # "SAFE" | "CAUTION" | "BLOCK"

    @property
    def is_safe(self) -> bool:
        return self.recommendation == "SAFE"

@dataclass
class SettlementAuditor:

    def verify(self, kalshi_title: str, poly_question: str) -> SettlementVerdict:
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
```

---

## Polymarket Gamma REST Additions Needed

Add to `src/apex/integrations/polymarket_gamma_public.py`:

```python
def fetch_active_liquid_markets(min_volume: float = 10_000) -> list[dict]:
    """
    Gamma REST endpoint: GET https://gamma-api.polymarket.com/markets
    Returns markets with bestAsk on YES and NO side.
    We need bestAsk_no for the arb formula.
    """
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "active": "true",
        "closed": "false",
        "limit": 200,
    }
    resp = httpx.get(url, params=params, timeout=20)
    resp.raise_for_status()
    raw = resp.json()
    result = []
    for m in raw:
        vol = float(m.get("volume24hr") or 0)
        if vol < min_volume:
            continue
        # bestAsk on the NO side = 1 - bestAsk on YES side
        # Polymarket Gamma returns outcomePrices as JSON array string
        try:
            prices = m.get("outcomePrices")
            if isinstance(prices, str):
                import json
                prices = json.loads(prices)
            yes_price = float(prices[0]) if prices else 0.5
            no_price  = float(prices[1]) if len(prices) > 1 else 1.0 - yes_price
        except Exception:
            yes_price, no_price = 0.5, 0.5
        m["bestAsk_no"] = no_price
        result.append(m)
    return result
```

---

## SQLite Schema Migration

Add in `SQLiteStore._migrate()`:

```sql
CREATE TABLE IF NOT EXISTS arb_opportunities (
    id TEXT PRIMARY KEY,
    kalshi_ticker TEXT NOT NULL,
    poly_market_id TEXT NOT NULL,
    question TEXT,
    kalshi_yes_ask REAL,
    poly_no_ask REAL,
    gross_spread REAL,
    net_edge REAL,
    settlement_match_score REAL,
    settlement_flags TEXT,        -- JSON array
    detection_ts TEXT,
    resolution_ts TEXT,
    outcome TEXT,
    pnl REAL,
    volume_kalshi REAL,
    volume_poly REAL
);
```

---

## Risk Gates (M05 + M06)

These gates must be added to `run_arb_paper()` in `src/apex/layers/l3/risk_checks.py`:

```python
# M05 — Settlement auditor must pass
def m05_settlement_auditor_pass(opp: ArbOpportunity) -> tuple[bool, str]:
    if opp.settlement_match_score < 0.45:
        return False, f"M05_SETTLEMENT_BLOCK: score={opp.settlement_match_score}, flags={opp.settlement_flags}"
    return True, ""

# M06 — Net edge threshold
def m06_net_edge_threshold(opp: ArbOpportunity, min_edge: float) -> tuple[bool, str]:
    if opp.net_edge < min_edge:
        return False, f"M06_EDGE_TOO_LOW: net_edge={opp.net_edge} < min={min_edge}"
    return True, ""
```
