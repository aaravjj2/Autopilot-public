from __future__ import annotations

from datetime import date

from apex.domain.enums import Instrument
from apex.layers.l2.agent_panel import _find_nearest_strike, _select_expiry_from_chain


def test_find_nearest_strike_returns_exact_match() -> None:
    assert _find_nearest_strike(150.0, [145.0, 150.0, 155.0]) == 150.0


def test_find_nearest_strike_falls_back_to_round_target_when_empty() -> None:
    result = _find_nearest_strike(164.29, [])
    assert result == 164.29


def test_find_nearest_strike_returns_closest() -> None:
    result = _find_nearest_strike(152.0, [145.0, 150.0, 155.0])
    assert result in (150.0, 155.0)


def test_select_expiry_returns_earnings_when_chain_is_none() -> None:
    earnings = date(2026, 6, 15)
    today = date.today()
    exp = _select_expiry_from_chain(Instrument.CALL, None, earnings)
    assert exp == earnings if 0 <= (earnings - today).days <= 45 else exp >= today


def test_select_expiry_returns_fallback_when_chain_empty() -> None:
    exp = _select_expiry_from_chain(Instrument.PUT, {"expirations": [], "calls": [], "puts": []}, None)
    assert exp >= date.today()


def test_select_expiry_fallsback_to_equity_when_chain_missing_option_type() -> None:
    """If the chain has expirations but no calls/puts for required leg, agent_panel
    logs a warning and falls back to EQUITY.  This test verifies the expiry selection
    still returns a valid date (not crashing)."""
    chain = {
        "expirations": [(date.today().replace(day=28)).isoformat()],
        "calls": [],
        "puts": [],
    }
    exp = _select_expiry_from_chain(Instrument.CALL, chain, None)
    assert exp is not None
