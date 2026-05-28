from __future__ import annotations
# BRIGHTDATA INTEGRATION — 2026-05-27 — arbitrage intelligence agent tests

from pathlib import Path

import pytest

from apex.agents.arb_intelligence_agent import ArbitrageIntelligenceAgent
from apex.core.config import Settings
from apex.domain.models import ArbOpportunity


def _opp(edge: float = 0.065, score: float = 0.9) -> ArbOpportunity:
    return ArbOpportunity(
        kalshi_ticker="CPI-TEST",
        poly_market_id="poly-1",
        question="Will CPI be above 3.0?",
        kalshi_title="Will CPI be above 3.0%?",
        poly_title="CPI above 3.0",
        kalshi_yes_ask=0.45,
        poly_no_ask=0.52,
        gross_spread=0.03,
        net_edge=edge,
        settlement_match_score=score,
        settlement_flags=[],
    )


class _Intel:
    def __init__(self, remaining: int = 30, risk_title: str = "stable outlook", source_found: bool = True):
        self.remaining = remaining
        self.risk_title = risk_title
        self.source_found = source_found
        self.calls = 0

    async def check_session_budget(self):
        return {"ok": self.remaining > 0, "calls_remaining": self.remaining, "calls_made": 0}

    async def search_breaking_news(self, query: str, n_results: int = 5):
        self.calls += 1
        if "consensus" in query:
            return [{"title": "Experts say yes likely", "url": "https://consensus.example", "snippet": "yes likely"}]
        return [{"title": self.risk_title, "url": "https://news.example", "snippet": self.risk_title}]

    async def get_settlement_source(self, *_args, **_kwargs):
        self.calls += 1
        if self.source_found:
            return {"found": True, "url": "https://www.bls.gov/release", "excerpt": "BLS confirms", "confidence": 0.9}
        return {"found": False, "url": "", "excerpt": "", "confidence": 0.0}


@pytest.mark.asyncio
async def test_buy_verdict_on_clean_opportunity(tmp_path: Path) -> None:
    agent = ArbitrageIntelligenceAgent(Settings(brightdata_api_key="x"), _Intel())
    agent.report_dir = tmp_path
    report = await agent.run(_opp())
    assert report["verdict"] == "BUY"
    assert report["confidence_score"] >= 80


@pytest.mark.asyncio
async def test_skip_on_high_news_risk(tmp_path: Path) -> None:
    agent = ArbitrageIntelligenceAgent(Settings(brightdata_api_key="x"), _Intel(risk_title="event postponed"))
    agent.report_dir = tmp_path
    report = await agent.run(_opp())
    assert report["verdict"] == "SKIP"


@pytest.mark.asyncio
async def test_wait_on_unverified_source(tmp_path: Path) -> None:
    agent = ArbitrageIntelligenceAgent(Settings(brightdata_api_key="x"), _Intel(source_found=False))
    agent.report_dir = tmp_path
    report = await agent.run(_opp())
    assert report["verdict"] == "WAIT"


@pytest.mark.asyncio
async def test_degraded_on_budget_exhaustion(tmp_path: Path) -> None:
    intel = _Intel(remaining=2)
    agent = ArbitrageIntelligenceAgent(Settings(brightdata_api_key="x"), intel)
    agent.report_dir = tmp_path
    report = await agent.run(_opp())
    assert report["verdict"] == "SKIP"
    assert report["confidence_score"] == 0
    assert intel.calls == 0


@pytest.mark.asyncio
async def test_report_written_to_disk(tmp_path: Path) -> None:
    agent = ArbitrageIntelligenceAgent(Settings(brightdata_api_key="x"), _Intel())
    agent.report_dir = tmp_path
    _ = await agent.run(_opp())
    files = list(tmp_path.glob("CPI-TEST_*.json"))
    assert files


@pytest.mark.asyncio
async def test_data_sources_in_report(tmp_path: Path) -> None:
    agent = ArbitrageIntelligenceAgent(Settings(brightdata_api_key="x"), _Intel())
    agent.report_dir = tmp_path
    report = await agent.run(_opp())
    assert isinstance(report["data_sources_used"], list)
    assert len(report["data_sources_used"]) > 0


@pytest.mark.asyncio
async def test_run_uses_title_when_question_missing(tmp_path: Path) -> None:
    opp = _opp()
    opp.question = ""
    opp.kalshi_title = "Will CPI be above 3.0%?"
    agent = ArbitrageIntelligenceAgent(Settings(brightdata_api_key="x"), _Intel())
    agent.report_dir = tmp_path
    report = await agent.run(opp)
    assert report["verdict"] in {"BUY", "WAIT", "SKIP"}
