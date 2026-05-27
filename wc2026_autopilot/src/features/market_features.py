"""Market parsing, edge, Kelly sizing."""

from __future__ import annotations

import os
import re
from difflib import get_close_matches
from typing import Any

WC2026_TEAMS = [
    "Argentina",
    "Brazil",
    "France",
    "Germany",
    "Spain",
    "England",
    "Portugal",
    "Netherlands",
    "Belgium",
    "USA",
    "Mexico",
    "Canada",
    "Japan",
    "South Korea",
    "Morocco",
    "Senegal",
    "Croatia",
    "Uruguay",
    "Colombia",
    "Italy",
    "Switzerland",
    "Denmark",
    "Australia",
    "Ecuador",
    "Iran",
    "Saudi Arabia",
    "Qatar",
    "Ghana",
    "Cameroon",
    "Tunisia",
    "Poland",
    "Serbia",
    "Wales",
    "Costa Rica",
    "Paraguay",
    "Chile",
    "Peru",
    "Nigeria",
    "Egypt",
    "Algeria",
]

TEAM_ALIASES = {
    "u.s.": "USA",
    "united states": "USA",
    "korea republic": "South Korea",
    "korea": "South Korea",
}


def _normalize_team(name: str) -> str | None:
    n = name.strip()
    low = n.lower()
    if low in TEAM_ALIASES:
        return TEAM_ALIASES[low]
    for t in WC2026_TEAMS:
        if t.lower() in low or low in t.lower():
            return t
    match = get_close_matches(n, WC2026_TEAMS, n=1, cutoff=0.6)
    return match[0] if match else n or None


def parse_market_teams(question: str) -> tuple[str | None, str | None]:
    q = question or ""
    patterns = [
        r"(?P<a>.+?)\s+(?:beat|defeat|win vs|vs\.?|versus)\s+(?P<b>.+?)(?:\?|$)",
        r"Will\s+(?P<a>.+?)\s+win",
    ]
    for pat in patterns:
        m = re.search(pat, q, re.I)
        if m:
            a = _normalize_team(m.group("a").replace("Will ", "").strip())
            b = _normalize_team(m.group("b").strip()) if "b" in m.groupdict() and m.group("b") else None
            if "win the" in q.lower() and " vs " not in q.lower():
                return a, None
            return a, b
    # Championship style
    m = re.search(r"Will\s+(.+?)\s+win", q, re.I)
    if m:
        return _normalize_team(m.group(1).strip()), None
    return None, None


def compute_edge(agent_prob: float, market_implied_prob: float) -> float:
    return float(agent_prob) - float(market_implied_prob)


def kelly_fraction(edge: float, odds: float = 1.0, agent_prob: float | None = None) -> float:
    if edge <= 0:
        return 0.0
    p = agent_prob if agent_prob is not None else min(0.99, max(0.01, 0.5 + edge))
    q = 1.0 - p
    b = max(0.01, float(odds))
    f = (b * p - q) / b
    cap = float(os.getenv("MAX_KELLY_FRACTION", "0.05"))
    return max(0.0, min(f, cap))


def is_liquid_enough(market: dict[str, Any], min_volume: float | None = None) -> bool:
    threshold = min_volume
    if threshold is None:
        threshold = float(os.getenv("MIN_MARKET_VOLUME", "1000"))
    vol = float(market.get("volume") or 0)
    return vol >= threshold
