from __future__ import annotations


from apex.core.config import Settings
from apex.domain.enums import Direction, PMSignal
from apex.layers.l1.brain import FinanceBrainService


def make_settings(**overrides) -> Settings:
    data = {
        "ALPACA_API_KEY": "x",
        "ALPACA_SECRET_KEY": "y",
        "ALPACA_PAPER_TRADE": True,
        "ALPACA_BASE_URL": "https://paper-api.alpaca.markets",
    }
    data.update(overrides)
    return Settings(**data)


def make_bars(closes: list[float]) -> list[dict]:
    return [{"close": c, "high": c * 1.02, "low": c * 0.98, "volume": 1000000} for c in closes]


def make_fundamentals(**kwargs) -> dict:
    defaults = {
        "revenue_growth": None,
        "pe": None,
        "ev_to_ebitda": None,
        "free_cash_flow_yield": None,
        "gross_margin": None,
        "debt_to_equity": None,
        "earnings_surprise_pct": None,
        "analyst_recommendation": None,
        "analyst_recommendation_trend": None,
    }
    defaults.update(kwargs)
    return defaults


class MockPMClient:
    def __init__(self, signal: PMSignal = PMSignal.NEUTRAL, divergence: float = 0.0):
        self._signal = signal
        self._divergence = divergence

    def get_ticker_signal(self, symbol: str):
        return {"signal": self._signal.value, "divergence": self._divergence}


def test_trend_score_bullish():
    settings = make_settings()
    pm_client = MockPMClient()
    brain = FinanceBrainService(settings, pm_client)

    bars = make_bars([100, 102, 104, 106, 108, 107, 109, 111, 113, 115] * 3)
    score = brain._trend_score(bars)

    assert score >= 6.0, f"Expected bullish score >= 6.0, got {score}"


def test_trend_score_bearish():
    settings = make_settings()
    pm_client = MockPMClient()
    brain = FinanceBrainService(settings, pm_client)

    bars = make_bars([115, 113, 111, 109, 107, 105, 103, 101, 99, 97] * 3)
    score = brain._trend_score(bars)

    assert score <= 4.5, f"Expected bearish score <= 4.5, got {score}"


def test_trend_score_neutral():
    settings = make_settings()
    pm_client = MockPMClient()
    brain = FinanceBrainService(settings, pm_client)

    bars = make_bars([100, 101, 100, 101, 100, 101, 100, 101, 100, 101] * 3)
    score = brain._trend_score(bars)

    assert 4.0 <= score <= 6.0, f"Expected neutral score between 4.0-6.0, got {score}"


def test_fundamental_score_strong_buy():
    settings = make_settings()
    pm_client = MockPMClient()
    brain = FinanceBrainService(settings, pm_client)

    fundamentals = make_fundamentals(
        revenue_growth=0.25,
        pe=12,
        ev_to_ebitda=8,
        free_cash_flow_yield=0.08,
        gross_margin=0.6,
        debt_to_equity=0.3,
        earnings_surprise_pct=0.15,
        analyst_recommendation="buy",
        analyst_recommendation_trend="up",
    )
    score = brain._fundamental_score(fundamentals)

    assert score >= 8.0, f"Expected strong fundamentals >= 8.0, got {score}"


def test_fundamental_score_weak():
    settings = make_settings()
    pm_client = MockPMClient()
    brain = FinanceBrainService(settings, pm_client)

    fundamentals = make_fundamentals(
        revenue_growth=-0.15,
        pe=60,
        ev_to_ebitda=30,
        free_cash_flow_yield=-0.05,
        gross_margin=0.15,
        debt_to_equity=2.5,
        earnings_surprise_pct=-0.15,
        analyst_recommendation="sell",
        analyst_recommendation_trend="down",
    )
    score = brain._fundamental_score(fundamentals)

    assert score <= 3.0, f"Expected weak fundamentals <= 3.0, got {score}"


def test_conviction_pm_divergence_capped():
    settings = make_settings()
    pm_client = MockPMClient(signal=PMSignal.BULLISH, divergence=0.8)
    brain = FinanceBrainService(settings, pm_client)

    bars = make_bars([100] * 30)
    fundamentals = make_fundamentals()

    score = brain.score_symbol(
        "TEST",
        market_snapshot={"bars": bars, "fundamentals": fundamentals, "sector": "Tech"},
    )

    max_divergence_contrib = 0.5 * 1.0
    max_technical_contrib = 7.5 * 0.45
    max_fundamental_contrib = 10.0 * 0.35

    max_possible = max_technical_contrib + max_fundamental_contrib + max_divergence_contrib
    assert score.conviction <= max_possible + 0.1, f"Conviction {score.conviction} exceeds max possible {max_possible}"


def test_conviction_respects_floor():
    settings = make_settings()
    pm_client = MockPMClient(signal=PMSignal.NEUTRAL, divergence=0.0)
    brain = FinanceBrainService(settings, pm_client)

    bars = make_bars([100] * 30)
    fundamentals = make_fundamentals(revenue_growth=0, pe=20)

    score = brain.score_symbol(
        "TEST",
        market_snapshot={"bars": bars, "fundamentals": fundamentals, "sector": "Tech"},
    )

    assert score.conviction >= 0.0, f"Conviction {score.conviction} below floor"
    assert score.conviction <= 10.0, f"Conviction {score.conviction} above ceiling"


def test_direction_bullish():
    settings = make_settings()
    pm_client = MockPMClient(signal=PMSignal.BULLISH, divergence=0.3)
    brain = FinanceBrainService(settings, pm_client)

    bars = make_bars([100, 102, 104, 106, 108, 110, 112, 114, 116, 118] * 3)
    fundamentals = make_fundamentals(revenue_growth=0.2, pe=15)

    score = brain.score_symbol(
        "TEST",
        market_snapshot={"bars": bars, "fundamentals": fundamentals, "sector": "Tech"},
    )

    assert score.direction == Direction.LONG, f"Expected LONG, got {score.direction}"


def test_direction_bearish():
    settings = make_settings()
    pm_client = MockPMClient(signal=PMSignal.BEARISH, divergence=-0.3)
    brain = FinanceBrainService(settings, pm_client)

    bars = make_bars([120, 115, 110, 105, 100, 98, 96, 94, 92, 90] * 3)
    fundamentals = make_fundamentals(revenue_growth=-0.15, pe=50)

    score = brain.score_symbol(
        "TEST",
        market_snapshot={"bars": bars, "fundamentals": fundamentals, "sector": "Tech"},
    )

    assert score.direction in {Direction.SHORT, Direction.NEUTRAL}, f"Expected SHORT/NEUTRAL, got {score.direction}"


def test_risk_reward_computed():
    settings = make_settings()
    pm_client = MockPMClient()
    brain = FinanceBrainService(settings, pm_client)

    bars = make_bars([100] * 30)
    fundamentals = make_fundamentals()

    score = brain.score_symbol(
        "TEST",
        market_snapshot={"bars": bars, "fundamentals": fundamentals, "sector": "Tech"},
    )

    expected_rr = (100 * 1.08 - 100) / (100 - 100 * 0.96)
    assert abs(score.risk_reward - expected_rr) < 0.1, f"Expected R:R ~{expected_rr}, got {score.risk_reward}"