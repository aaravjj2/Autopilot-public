from __future__ import annotations
# BRIGHTDATA INTEGRATION — 2026-05-27 — intelligence service tests

import pytest

from apex.core.config import Settings
from apex.integrations.brightdata_intelligence import BrightDataIntelligence


@pytest.mark.asyncio
async def test_search_returns_empty_on_exception(monkeypatch) -> None:
    intel = BrightDataIntelligence(Settings(brightdata_api_key="x"))

    async def _boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(intel, "_call_mcp_tool", _boom)
    out = await intel.search_breaking_news("cpi latest", 3)
    assert out == []


@pytest.mark.asyncio
async def test_scrape_truncates_at_8000_chars(monkeypatch) -> None:
    intel = BrightDataIntelligence(Settings(brightdata_api_key="x"))

    async def _ok(*_args, **_kwargs):
        return "a" * 10000

    monkeypatch.setattr(intel, "_call_mcp_tool", _ok)
    out = await intel.scrape_source_page("https://example.com/a")
    assert len(out) == 8000


@pytest.mark.asyncio
async def test_get_market_context_skips_for_imminent() -> None:
    intel = BrightDataIntelligence(Settings(brightdata_api_key="x"))
    ctx = await intel.get_market_context("title", "poly", horizon_hours=1)
    assert ctx["news"] == []
    assert ctx["risk_signals"] == []


@pytest.mark.asyncio
async def test_risk_signals_detected(monkeypatch) -> None:
    intel = BrightDataIntelligence(Settings(brightdata_api_key="x"))

    async def _fake_news(*_args, **_kwargs):
        return [{"title": "Match postponed", "url": "https://news", "snippet": "postponed due to weather"}]

    monkeypatch.setattr(intel, "search_breaking_news", _fake_news)
    ctx = await intel.get_market_context("x", "y", horizon_hours=6)
    assert "postponed" in ctx["risk_signals"]


@pytest.mark.asyncio
async def test_settlement_source_confidence_domain_match(monkeypatch) -> None:
    intel = BrightDataIntelligence(Settings(brightdata_api_key="x"))

    async def _news(*_args, **_kwargs):
        return [{"title": "BLS", "url": "https://www.bls.gov/news", "snippet": "CPI release"}]

    async def _scrape(*_args, **_kwargs):
        return "CPI came in at 3.1%"

    monkeypatch.setattr(intel, "search_breaking_news", _news)
    monkeypatch.setattr(intel, "scrape_source_page", _scrape)
    src = await intel.get_settlement_source("CPI release", ["bls"])
    assert src["confidence"] == 0.9


@pytest.mark.asyncio
async def test_settlement_source_prefers_authoritative_domain(monkeypatch) -> None:
    intel = BrightDataIntelligence(Settings(brightdata_api_key="x"))

    async def _news(*_args, **_kwargs):
        return [
            {"title": "Random blog", "url": "https://example.com/cpi", "snippet": "cpi summary"},
            {"title": "BLS release", "url": "https://www.bls.gov/news.release/cpi.htm", "snippet": "official"},
        ]

    async def _scrape(_url: str):
        return "authoritative text"

    monkeypatch.setattr(intel, "search_breaking_news", _news)
    monkeypatch.setattr(intel, "scrape_source_page", _scrape)
    src = await intel.get_settlement_source("CPI release", ["bls"])
    assert src["url"].startswith("https://www.bls.gov")
    assert src["confidence"] == 0.9


@pytest.mark.asyncio
async def test_check_session_budget_returns_false_at_limit() -> None:
    intel = BrightDataIntelligence(
        Settings(brightdata_api_key="x", brightdata_max_requests_per_run=50)
    )
    intel._request_count = 50
    # Avoid spawning a real MCP subprocess during unit tests.
    async def _stats(*_args, **_kwargs):
        return {"tools": {}}

    intel._call_mcp_tool = _stats  # type: ignore[method-assign]
    budget = await intel.check_session_budget()
    assert budget["ok"] is False


@pytest.mark.asyncio
async def test_settlement_source_falls_back_without_site_filter(monkeypatch) -> None:
    intel = BrightDataIntelligence(Settings(brightdata_api_key="x"))
    calls = {"n": 0}

    async def _news(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return []
        return [{"title": "BLS release", "url": "https://www.bls.gov/news.release/cpi.htm", "snippet": "official"}]

    async def _scrape(_url: str):
        return "official cpi excerpt"

    monkeypatch.setattr(intel, "search_breaking_news", _news)
    monkeypatch.setattr(intel, "scrape_source_page", _scrape)
    src = await intel.get_settlement_source("CPI release", ["bls"])
    assert calls["n"] == 2
    assert src["found"] is True
