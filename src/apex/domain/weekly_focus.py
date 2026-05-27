"""Weekly thematic focus: semiconductors, SMH/SOXX, and NVDA earnings (May 2026)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apex.core.config import Settings

# Chip designers, equipment, memory, foundry ADRs
_SEMICONDUCTOR_EQUITIES = [
    "NVDA",
    "AMD",
    "AVGO",
    "QCOM",
    "MU",
    "AMAT",
    "LRCX",
    "KLAC",
    "INTC",
    "MRVL",
    "ON",
    "TXN",
    "ASML",
    "TSM",
]

_SEMICONDUCTOR_ETFS = ["SMH", "SOXX", "XSD"]

DEFAULT_WEEKLY_FOCUS_SYMBOLS: list[str] = _SEMICONDUCTOR_EQUITIES + _SEMICONDUCTOR_ETFS

# NVIDIA Q1 FY27 results — conference call May 20, 2026 (US/Eastern week focus)
DEFAULT_NVDA_EARNINGS_DATE = date(2026, 5, 20)

NVDA_EARNINGS_SPOTLIGHT = "NVDA"


def parse_symbol_csv(raw: str) -> list[str]:
    return [part.strip().upper() for part in raw.split(",") if part.strip()]


def weekly_focus_symbols(settings: Settings) -> list[str]:
    if not settings.weekly_focus_enabled:
        return []
    if settings.weekly_focus_symbols.strip():
        return parse_symbol_csv(settings.weekly_focus_symbols)
    return list(DEFAULT_WEEKLY_FOCUS_SYMBOLS)


def weekly_focus_earnings_symbols(settings: Settings) -> list[str]:
    if not settings.weekly_focus_earnings_symbols.strip():
        return [NVDA_EARNINGS_SPOTLIGHT]
    return parse_symbol_csv(settings.weekly_focus_earnings_symbols)


def nvda_earnings_date(settings: Settings) -> date | None:
    if settings.nvda_earnings_date is not None:
        return settings.nvda_earnings_date
    return DEFAULT_NVDA_EARNINGS_DATE if settings.weekly_focus_enabled else None


def is_within_earnings_window(
    symbol: str,
    settings: Settings,
    *,
    as_of: date | None = None,
    market_earnings: date | None = None,
) -> bool:
    if symbol not in weekly_focus_earnings_symbols(settings):
        return False
    today = as_of or date.today()
    window = max(0, int(settings.nvda_earnings_window_days))
    target = market_earnings
    if symbol == NVDA_EARNINGS_SPOTLIGHT:
        target = nvda_earnings_date(settings) or target
    if target is None:
        return False
    return today - timedelta(days=window) <= target <= today + timedelta(days=window)


def merge_watchlist_candidates(
    base: list[str],
    focus: list[str],
) -> list[str]:
    """Focus symbols first, then remaining base candidates (deduped, order preserved)."""
    seen: set[str] = set()
    merged: list[str] = []
    for symbol in focus + base:
        key = symbol.upper()
        if key in seen:
            continue
        seen.add(key)
        merged.append(key)
    return merged


def build_effective_watchlist_candidates(
    base: list[str],
    settings: Settings,
) -> list[str]:
    focus = weekly_focus_symbols(settings)
    if not focus:
        return list(base)
    return merge_watchlist_candidates(base, focus)


def priority_watchlist_symbols(settings: Settings) -> list[str]:
    """Symbols pinned at the front of daily watchlist refresh."""
    if not settings.weekly_focus_enabled:
        return []
    focus = weekly_focus_symbols(settings)
    # NVDA first when earnings focus is on
    if NVDA_EARNINGS_SPOTLIGHT in focus:
        ordered = [NVDA_EARNINGS_SPOTLIGHT] + [s for s in focus if s != NVDA_EARNINGS_SPOTLIGHT]
        return ordered
    return focus
