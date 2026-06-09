from __future__ import annotations

import pytest
from datetime import date, timedelta

from apex.core.config import Settings
from apex.domain.enums import Direction, Instrument
from apex.domain.models import AccountSnapshot, Position, SpreadLeg, TradeProposal
from apex.layers.l3.risk_checks import RiskCheckEngine


def make_settings(**overrides) -> Settings:
    data = {
        "ALPACA_API_KEY": "x",
        "ALPACA_SECRET_KEY": "y",
        "ALPACA_PAPER_TRADE": True,
        "ALPACA_BASE_URL": "https://paper-api.alpaca.markets",
    }
    data.update(overrides)
    return Settings(**data)


def make_account(daily_pl_pct: float = 0.0, positions: list[Position] | None = None) -> AccountSnapshot:
    return AccountSnapshot(
        equity=100000.0,
        buying_power=100000.0,
        daily_pl_pct=daily_pl_pct,
        open_positions=positions or [],
    )


def make_proposal(**overrides) -> TradeProposal:
    payload = {
        "symbol": "AAPL",
        "direction": Direction.LONG,
        "instrument": Instrument.EQUITY,
        "entry_price": 200.0,
        "position_size_pct": 3.0,
        "stop_loss": 190.0,
        "take_profit": 220.0,
        "max_loss_dollars": 1000.0,
        "conviction_final": 7.0,
        "judge_rationale": "test",
        "dissenting_view": "test",
        "sector": "Technology",
    }
    payload.update(overrides)
    return TradeProposal(**payload)


@pytest.mark.smoke
def test_r01_rejects_live_endpoint() -> None:
    settings = make_settings(ALPACA_PAPER_TRADE=False, ALPACA_BASE_URL="https://api.alpaca.markets")
    engine = RiskCheckEngine(settings)
    result = engine._r01_paper_account()
    assert result.passed is False
    assert result.risk_id == "R01"


def test_r05_daily_loss_halts() -> None:
    settings = make_settings(DAILY_LOSS_LIMIT_PCT=3.0)
    engine = RiskCheckEngine(settings)
    result = engine._r05_daily_loss_limit(make_account(daily_pl_pct=-3.5))
    assert result.passed is False
    assert result.risk_id == "R05"


def test_r09_earnings_blackout_rejects_near_event() -> None:
    settings = make_settings(EARNINGS_BLACKOUT_DAYS=2)
    engine = RiskCheckEngine(settings)
    proposal = make_proposal(earnings_date=date.today() + timedelta(days=1))
    result = engine._r09_earnings_blackout(proposal)
    assert result.passed is False
    assert result.risk_id == "R09"


def test_r10_long_option_requires_low_iv_rank() -> None:
    settings = make_settings(IV_RANK_LONG_THRESHOLD=50)
    engine = RiskCheckEngine(settings)
    proposal = make_proposal(
        instrument=Instrument.CALL,
        expiry_date=date.today() + timedelta(days=14),
        strike=200.0,
        iv_rank=75.0,
    )
    result = engine._r10_iv_rank_filter(proposal)
    assert result.passed is False
    assert result.risk_id == "R10"


def test_r15_auto_disables_flatten_when_options_enabled() -> None:
    settings = make_settings(
        OPTIONS_TRADING_ENABLED=True,
        ALPACA_FLATTEN_OPTIONS_TO_EQUITY=True,
    )
    assert settings.alpaca_flatten_options_to_equity is False
    engine = RiskCheckEngine(settings)
    exp = date.today() + timedelta(days=14)
    proposal = make_proposal(
        instrument=Instrument.VERTICAL,
        expiry_date=exp,
        spread_legs=[
            SpreadLeg(
                side="buy",
                option_type="call",
                strike=200.0,
                expiry_date=exp,
                quantity=1,
            )
        ],
    )
    result = engine._r15_options_trading_policy(proposal)
    assert result.passed is True


def test_r12_requires_dexter_reduction_when_severity_high() -> None:
    settings = make_settings(DEXTER_THRESHOLD=7.0)
    engine = RiskCheckEngine(settings)
    proposal = make_proposal(dexter_severity=8.0, dexter_reduction_applied=False)
    result = engine._r12_dexter_override(proposal)
    assert result.passed is False
    assert result.risk_id == "R12"


def test_m08(monkeypatch) -> None:
    from apex.domain.models import ArbOpportunity
    settings = make_settings(
        ALPACA_PAPER_TRADE=True,
        POLYMARKET_PAPER_TRADING_ENABLED=True,
        ARB_MIN_NET_EDGE=0.01,
        KALSHI_MIN_VOLUME_24H=1000.0,
        ARB_PAPER_RELAX_ORDERBOOK=False,
    )
    engine = RiskCheckEngine(settings)
    
    opp = ArbOpportunity(
        kalshi_ticker="KXTEST",
        poly_market_id="PTEST",
        question="Test Question",
        kalshi_title="Test Kalshi Title",
        poly_title="Test Poly Title",
        gross_spread=0.06,
        net_edge=0.05,
        volume_kalshi=2000.0,
        volume_poly=2000.0,
        kalshi_yes_ask=0.5,
        poly_no_ask=0.45,
        settlement_match_score=0.9,
        settlement_flags=[],
    )
    
    def mock_fetch(ticker):
        return {
            "yes": [[0.30, 100]],
            "no": [[0.50, 100]]
        }
    monkeypatch.setattr("apex.layers.l3.risk_checks.fetch_kalshi_orderbook", mock_fetch)
    monkeypatch.setattr("apex.cache.orderbook_l2.read_orderbook", lambda *a, **k: {})
    
    class MockResponse:
        def raise_for_status(self): pass
        def json(self): return {"asks": [{"price": "0.45", "size": "1000"}]}
    monkeypatch.setattr("requests.get", lambda url, timeout: MockResponse())
    
    res = engine.run_arb_paper(opp)
    assert "M08" in res.failed
    assert "M08_SPREAD_WIDTH: 0.2000 > 0.15" in res.rejection_reason


def test_run_arb_paper_rejects_missing_ids() -> None:
    from apex.domain.models import ArbOpportunity

    settings = make_settings(ALPACA_PAPER_TRADE=True, POLYMARKET_PAPER_TRADING_ENABLED=True)
    engine = RiskCheckEngine(settings)
    opp = ArbOpportunity(
        kalshi_ticker="",
        poly_market_id="",
        question="Q",
        kalshi_title="Q",
        poly_title="Q",
        gross_spread=0.06,
        net_edge=0.05,
        volume_kalshi=2000.0,
        volume_poly=2000.0,
        kalshi_yes_ask=0.5,
        poly_no_ask=0.45,
        settlement_match_score=0.9,
        settlement_flags=[],
    )
    res = engine.run_arb_paper(opp)
    assert res.all_passed is False
    assert res.rejection_reason.startswith("M00_INVALID_OPP")

