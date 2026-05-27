"""Default equity/ETF candidate pool for daily watchlist refresh (non-defense, non-healthcare)."""

from __future__ import annotations

# Technology (NVDA also in _SEMI for sector emphasis)
_TECH = ["AAPL", "MSFT", "GOOGL", "META", "IBM", "CSCO", "SAP", "ORCL"]

# Financial services
_FINANCIAL = ["JPM", "BRK-B", "AXP", "V", "MA", "GS", "BLK"]

# Consumer staples
_STAPLES = ["PG", "KO", "PEP", "CL", "WMT", "COST", "HSY"]

# Telecommunications
_TELECOM = ["VZ", "T"]

# Energy & utilities
_ENERGY_UTIL = ["XOM", "CVX", "DUK", "AEP"]

# Industrials (non-defense)
_INDUSTRIAL = ["CAT", "MMM", "HON", "GE"]

# Consumer discretionary
_DISCRETIONARY = ["AMZN", "MCD", "NKE", "HD", "SBUX"]

# Real estate (REITs)
_REIT = ["PLD"]

# Materials & mining
_MATERIALS = ["GOLD", "LIN"]

# Semiconductors (equities + sector ETFs) — also merged via weekly_focus when enabled
_SEMI = [
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
    "SMH",
    "SOXX",
    "XSD",
]

# ETFs — broad market, sectors, and precious metals
_ETFS = [
    "SPY",
    "QQQ",
    "IWM",
    "DIA",
    "VTI",
    "GLD",
    "SLV",
    "GDX",
    "XLK",
    "XLF",
    "XLE",
    "XLI",
    "XLP",
    "XLY",
    "XLU",
    "XLB",
]

DEFAULT_WATCHLIST_CANDIDATES: list[str] = (
    _SEMI
    + _TECH
    + _FINANCIAL
    + _STAPLES
    + _TELECOM
    + _ENERGY_UTIL
    + _INDUSTRIAL
    + _DISCRETIONARY
    + _REIT
    + _MATERIALS
    + _ETFS
)
