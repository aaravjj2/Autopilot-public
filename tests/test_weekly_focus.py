from __future__ import annotations

from datetime import date, timedelta

import pytest

from apex.core.config import Settings
from apex.domain.weekly_focus import (
    build_effective_watchlist_candidates,
    is_within_earnings_window,
    merge_watchlist_candidates,
    priority_watchlist_symbols,
    weekly_focus_symbols,
)
from apex.domain.watchlist_candidates import DEFAULT_WATCHLIST_CANDIDATES
from apex.layers.l1.brain import FinanceBrainService
from apex.domain.enums import Direction, Instrument
from apex.domain.models import TradeProposal
from apex.layers.l3.risk_checks import RiskCheckEngine


def _settings(**overrides) -> Settings:
    base = {
        "ALPACA_API_KEY": "x",
        "ALPACA_SECRET_KEY": "y",
        "ALPACA_PAPER_TRADE": True,
        "ALPACA_BASE_URL": "https://paper-api.alpaca.markets",
    }
    base.update(overrides)
    return Settings(**base)


def _proposal(**overrides) -> TradeProposal:
    payload = {
        "symbol": "NVDA",
        "direction": Direction.LONG,
        "instrument": Instrument.EQUITY,
        "entry_price": 100.0,
        "position_size_pct": 2.0,
        "stop_loss": 95.0,
        "take_profit": 110.0,
        "max_loss_dollars": 500.0,
        "conviction_final": 7.0,
        "judge_rationale": "test",
        "dissenting_view": "none",
    }
    payload.update(overrides)
    return TradeProposal(**payload)


def test_merge_puts_focus_first() -> None:
    merged = merge_watchlist_candidates(["AAPL", "MSFT"], ["NVDA", "SMH", "AAPL"])
    assert merged[:3] == ["NVDA", "SMH", "AAPL"]
    assert "MSFT" in merged


def test_nvda_earnings_window() -> None:
    settings = Settings(weekly_focus_enabled=True, nvda_earnings_date=date(2026, 5, 20))
    assert is_within_earnings_window("NVDA", settings, as_of=date(2026, 5, 18))
    assert not is_within_earnings_window("AAPL", settings, as_of=date(2026, 5, 18))


def test_default_focus_includes_smh_and_nvda() -> None:
    settings = Settings(weekly_focus_enabled=True)
    focus = weekly_focus_symbols(settings)
    assert "NVDA" in focus
    assert "SMH" in focus
    assert "SOXX" in focus


def test_priority_nvda_first() -> None:
    settings = Settings(weekly_focus_enabled=True)
    assert priority_watchlist_symbols(settings)[0] == "NVDA"


def test_brain_weekly_focus_nudge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NVDA_EARNINGS_WINDOW_DAYS", "14")
    settings = Settings(
        weekly_focus_enabled=True,
        weekly_focus_conviction_boost=0.35,
        nvda_earnings_conviction_boost=0.45,
        nvda_earnings_date=date(2026, 5, 20),
        nvda_earnings_window_days=14,
    )
    brain = FinanceBrainService(settings, pm_client=None)  # type: ignore[arg-type]
    nudge, note = brain._weekly_focus_nudge(
        "NVDA",
        {"earnings_date": date(2026, 5, 20)},
    )
    assert nudge >= 0.7
    assert "semi_focus" in note
    assert "nvda_earnings_week" in note


def test_r09_relaxed_for_nvda_focus() -> None:
    settings = _settings(
        WEEKLY_FOCUS_RELAX_EARNINGS_BLACKOUT=True,
        WEEKLY_FOCUS_EARNINGS_SYMBOLS="NVDA",
    )
    engine = RiskCheckEngine(settings)
    proposal = _proposal(earnings_date=date.today() + timedelta(days=1))
    result = engine._r09_earnings_blackout(proposal)
    assert result.passed


def test_effective_watchlist_has_semi_at_front() -> None:
    settings = Settings(weekly_focus_enabled=True)
    merged = build_effective_watchlist_candidates(DEFAULT_WATCHLIST_CANDIDATES, settings)
    assert merged[0] == "NVDA"
    assert "SMH" in merged[:20]
