from __future__ import annotations

# BRIGHTDATA INTEGRATION — 2026-05-27 — arbitrage intelligence agent

import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apex.core.config import Settings
from apex.core.logging import get_logger
from apex.domain.models import ArbOpportunity
from apex.integrations.brightdata_intelligence import BrightDataIntelligence

LOGGER = get_logger(__name__)


class ArbitrageIntelligenceAgent:
    def __init__(self, settings: Settings, intelligence: BrightDataIntelligence):
        self.settings = settings
        self.intelligence = intelligence
        self.report_dir = Path("data/intelligence_reports").resolve()
        self.report_dir.mkdir(parents=True, exist_ok=True)

    async def run(self, opp: ArbOpportunity) -> dict[str, Any]:
        budget_before = await self.intelligence.check_session_budget()
        if not budget_before.get("ok", False) or int(budget_before.get("calls_remaining", 0)) < 10:
            report = self._base_report(opp)
            report.update(
                {
                    "verdict": "SKIP",
                    "confidence_score": 0,
                    "rationale": "Budget exhausted; intelligence calls skipped.",
                    "data_sources_used": [],
                }
            )
            self._write_report(report)
            return report

        base_query = (opp.question or opp.kalshi_title or opp.poly_title or opp.kalshi_ticker).strip()
        q_news = f"{base_query} latest news site:reuters.com OR site:bloomberg.com OR site:ft.com"
        q_consensus = f"{base_query} prediction expert consensus"
        q_source_keywords = self._source_keywords_for_opp(opp)
        news_task = self.intelligence.search_breaking_news(q_news, n_results=5)
        source_task = self.intelligence.get_settlement_source(opp.question, q_source_keywords)
        consensus_task = self.intelligence.search_breaking_news(q_consensus, n_results=5)
        try:
            news, source, consensus = await asyncio.wait_for(
                asyncio.gather(
                    news_task,
                    source_task,
                    consensus_task,
                    return_exceptions=True,
                ),
                timeout=20,
            )
        except TimeoutError:
            news, source, consensus = [], {"found": False, "url": "", "excerpt": "", "confidence": 0.0}, []
        if isinstance(news, Exception):
            news = []
        if isinstance(source, Exception):
            source = {"found": False, "url": "", "excerpt": "", "confidence": 0.0}
        if isinstance(consensus, Exception):
            consensus = []

        risk_signals = self._extract_risk_signals(news)
        risk_level = "HIGH" if len(risk_signals) >= 2 else ("MEDIUM" if risk_signals else "LOW")
        settlement_verified = bool(source.get("found")) and float(source.get("confidence", 0)) >= 0.7
        expert_direction = self._infer_consensus_direction(consensus)

        verdict = "SKIP"
        if (
            risk_level == "LOW"
            and settlement_verified
            and expert_direction != self._opposite_arb_direction(opp)
            and opp.net_edge > 0.04
        ):
            verdict = "BUY"
        elif risk_level == "LOW" and not settlement_verified and opp.net_edge > 0.04:
            verdict = "WAIT"

        confidence = 50
        if settlement_verified:
            confidence += 20
        if expert_direction == self._arb_direction(opp):
            confidence += 15
        if risk_level == "HIGH":
            confidence -= 20
        elif risk_level == "MEDIUM":
            confidence -= 10
        if opp.net_edge > 0.06:
            confidence += 15
        if opp.settlement_match_score > 0.85:
            confidence += 10
        confidence = max(0, min(100, confidence))

        sources_used = []
        for item in [*news, *consensus]:
            url = str(item.get("url", "")).strip()
            if url:
                sources_used.append(url)
        source_url = str(source.get("url", "")).strip()
        if source_url:
            sources_used.append(source_url)

        report = self._base_report(opp)
        unique_sources = sorted(set(sources_used))[:20]
        report.update(
            {
                "news_risk_level": risk_level,
                "settlement_source_verified": settlement_verified,
                "expert_consensus_direction": expert_direction,
                "data_sources_used": unique_sources,
                "verdict": verdict,
                "confidence_score": confidence,
                "rationale": (
                    f"risk={risk_level}, settlement_verified={settlement_verified}, "
                    f"consensus={expert_direction}, edge={opp.net_edge:.3f}"
                ),
            }
        )
        report["session_stats_before"] = budget_before
        report["session_stats_after"] = await self.intelligence.check_session_budget()
        self._write_report(report)
        return report

    def _base_report(self, opp: ArbOpportunity) -> dict[str, Any]:
        return {
            "ticker": opp.kalshi_ticker,
            "arb_id": opp.id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _write_report(self, report: dict[str, Any]) -> None:
        ticker = str(report.get("ticker", "unknown")).replace("/", "_")
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = self.report_dir / f"{ticker}_{ts}.json"
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    def _source_keywords_for_opp(self, opp: ArbOpportunity) -> list[str]:
        text = f"{opp.kalshi_title} {opp.poly_title}".lower()
        if "cpi" in text:
            return ["bls"]
        if "fomc" in text or "fed" in text:
            return ["federalreserve"]
        if "bitcoin" in text or "crypto" in text:
            return ["coingecko"]
        return [opp.kalshi_ticker]

    def _extract_risk_signals(self, rows: list[dict[str, Any]]) -> list[str]:
        blob = " ".join(f"{r.get('title','')} {r.get('snippet','')}" for r in rows).lower()
        signals = []
        for kw in ("postponed", "delayed", "cancelled", "investigation", "breaking", "injunction"):
            if kw in blob:
                signals.append(kw)
        return signals

    def _infer_consensus_direction(self, rows: list[dict[str, Any]]) -> str:
        blob = " ".join(f"{r.get('title','')} {r.get('snippet','')}" for r in rows).lower()
        yes_hits = sum(1 for w in ("yes", "above", "increase", "rise", "likely") if w in blob)
        no_hits = sum(1 for w in ("no", "below", "decrease", "fall", "unlikely") if w in blob)
        if yes_hits > no_hits:
            return "YES_FAVORED"
        if no_hits > yes_hits:
            return "NO_FAVORED"
        return "UNCLEAR"

    def _arb_direction(self, opp: ArbOpportunity) -> str:
        return "YES_FAVORED" if opp.kalshi_yes_ask <= opp.poly_no_ask else "NO_FAVORED"

    def _opposite_arb_direction(self, opp: ArbOpportunity) -> str:
        return "NO_FAVORED" if self._arb_direction(opp) == "YES_FAVORED" else "YES_FAVORED"
