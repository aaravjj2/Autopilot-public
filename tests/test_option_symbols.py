from __future__ import annotations

from datetime import date

from apex.domain.option_symbols import format_occ_option_symbol, position_intent_for_opening_leg


def test_occ_symbol_matches_alpaca_style_example() -> None:
    # Mirrors Alpaca docs style: AAPL240119C00190000
    occ = format_occ_option_symbol("AAPL", date(2024, 1, 19), "call", 190.0)
    assert occ == "AAPL240119C00190000"


def test_occ_put_strike_padding() -> None:
    occ = format_occ_option_symbol("SPY", date(2025, 1, 27), "put", 608.0)
    assert occ == "SPY250127P00608000"


def test_position_intent_mapping() -> None:
    assert position_intent_for_opening_leg("buy") == "buy_to_open"
    assert position_intent_for_opening_leg("sell") == "sell_to_open"
