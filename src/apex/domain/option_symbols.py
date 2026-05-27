"""OCC-style option symbols for Alpaca US options REST (same format as industry convention)."""

from __future__ import annotations

from datetime import date


def format_occ_option_symbol(
    underlying: str,
    expiry: date,
    right: str,
    strike: float,
) -> str:
    """
    Build Alpaca-style option symbol, e.g. ``AAPL240119C00190000``.

    ``right`` is ``call`` / ``put`` / ``C`` / ``P`` (case-insensitive).
    Strike is encoded as eight digits = round(strike * 1000).
    """
    root = underlying.strip().upper()
    r = right.strip().upper()
    oc = "C" if r in ("C", "CALL") else "P"
    ymd = expiry.strftime("%y%m%d")
    strike_int = int(round(float(strike) * 1000))
    if strike_int < 0 or strike_int > 99_999_999:
        raise ValueError(f"strike out of OCC range after scaling: {strike}")
    return f"{root}{ymd}{oc}{strike_int:08d}"


def position_intent_for_opening_leg(side: str) -> str:
    """Map spread leg ``buy``/``sell`` to Alpaca ``*_to_open`` intents for new risk."""
    s = (side or "").strip().lower()
    return "buy_to_open" if s == "buy" else "sell_to_open"
