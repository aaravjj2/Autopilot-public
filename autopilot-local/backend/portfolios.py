from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from db import Holding, Portfolio, init_db, get_session_sync


PORTFOLIO_DEFINITIONS: list[dict[str, Any]] = [
    {
        "id": "pelosi-tracker",
        "name": "Pelosi Tracker",
        "description": "Mirrors recent congressional disclosure activity for Nancy Pelosi.",
        "category": "political",
        "pilot_name": "Nancy Pelosi",
        "seed_holdings": [("NVDA", 0.22), ("AAPL", 0.18), ("MSFT", 0.15), ("GOOGL", 0.12), ("AMZN", 0.10)],
    },
    {
        "id": "trump-portfolio",
        "name": "Trump Stock Portfolio",
        "description": "Tracks disclosed equity activity linked to Trump family filings.",
        "category": "political",
        "pilot_name": "Donald J. Trump",
        "seed_holdings": [("DJT", 0.35), ("LMT", 0.15), ("CAT", 0.12), ("XOM", 0.10), ("SPY", 0.08)],
    },
    {
        "id": "senate-buys",
        "name": "Senate Best Buys",
        "description": "Top bought tickers across Senate disclosures (90-day window).",
        "category": "political",
        "pilot_name": "U.S. Senate",
        "seed_holdings": [("MSFT", 0.20), ("NVDA", 0.18), ("JPM", 0.14), ("UNH", 0.12), ("LLY", 0.10)],
    },
    {
        "id": "simons-tracker",
        "name": "Jim Simons Tracker",
        "description": "Renaissance Technologies 13F-style basket (CIK 0001037389).",
        "category": "hedge-fund",
        "pilot_name": "Jim Simons",
        "cik": "0001037389",
        "seed_holdings": [("NVDA", 0.12), ("META", 0.10), ("AMZN", 0.09), ("GOOGL", 0.08), ("MSFT", 0.08)],
    },
    {
        "id": "burry-tracker",
        "name": "Burry Tracker",
        "description": "Scion Asset Management 13F-style basket (CIK 0001649339).",
        "category": "hedge-fund",
        "pilot_name": "Michael Burry",
        "cik": "0001649339",
        "seed_holdings": [("BABA", 0.25), ("JD", 0.15), ("GEO", 0.12), ("REAL", 0.10), ("EL", 0.08)],
    },
    {
        "id": "dalio-tracker",
        "name": "Dalio Tracker",
        "description": "Bridgewater Associates 13F-style basket (CIK 0001350694).",
        "category": "hedge-fund",
        "pilot_name": "Ray Dalio",
        "cik": "0001350694",
        "seed_holdings": [("SPY", 0.15), ("IVV", 0.12), ("IEMG", 0.10), ("GOOGL", 0.08), ("META", 0.07)],
    },
    {
        "id": "inverse-cramer",
        "name": "Inverse Cramer",
        "description": "Thematic inverse of high-profile CNBC buy calls (manually curated).",
        "category": "thematic",
        "pilot_name": "Inverse Cramer",
        "seed_holdings": [("SQQQ", 0.20), ("PSQ", 0.15), ("SDS", 0.12), ("SPXS", 0.10), ("SH", 0.08)],
    },
    {
        "id": "ai-basket",
        "name": "AI Picks",
        "description": "Top AI/ML-adjacent holdings aggregated from tracked 13F baskets.",
        "category": "thematic",
        "pilot_name": "APEX Thematic",
        "seed_holdings": [("NVDA", 0.28), ("MSFT", 0.18), ("AMD", 0.12), ("AVGO", 0.10), ("SMH", 0.08)],
    },
]


def _normalize_weights(holdings: list[tuple[str, float]]) -> list[tuple[str, float]]:
    total = sum(w for _, w in holdings) or 1.0
    return [(t.upper(), w / total) for t, w in holdings]


def seed_portfolios(session: Session) -> None:
    for spec in PORTFOLIO_DEFINITIONS:
        existing = session.get(Portfolio, spec["id"])
        if existing:
            continue
        session.add(
            Portfolio(
                id=spec["id"],
                name=spec["name"],
                description=spec["description"],
                category=spec["category"],
                pilot_name=spec["pilot_name"],
                is_following=False,
            )
        )
        for ticker, weight in _normalize_weights(spec["seed_holdings"]):
            session.add(
                Holding(
                    portfolio_id=spec["id"],
                    ticker=ticker,
                    weight=weight,
                    shares=0.0,
                )
            )
    session.commit()


def get_portfolio_spec(portfolio_id: str) -> dict[str, Any] | None:
    for spec in PORTFOLIO_DEFINITIONS:
        if spec["id"] == portfolio_id:
            return spec
    return None


def list_portfolio_ids() -> list[str]:
    return [p["id"] for p in PORTFOLIO_DEFINITIONS]


def ensure_seeded() -> None:
    init_db()
    with get_session_sync() as session:
        count = len(session.exec(select(Portfolio)).all())
        if count == 0:
            seed_portfolios(session)
        else:
            # backfill any new definitions
            seed_portfolios(session)


def update_holdings(
    session: Session, portfolio_id: str, holdings: list[tuple[str, float]]
) -> bool:
    """Replace holdings; return True if weights changed materially."""
    normalized = _normalize_weights(holdings)
    old = session.exec(
        select(Holding).where(Holding.portfolio_id == portfolio_id)
    ).all()
    old_map = {h.ticker: round(h.weight, 4) for h in old}
    new_map = {t: round(w, 4) for t, w in normalized}
    changed = old_map != new_map
    for h in old:
        session.delete(h)
    for ticker, weight in normalized:
        session.add(
            Holding(portfolio_id=portfolio_id, ticker=ticker, weight=weight, shares=0.0)
        )
    portfolio = session.get(Portfolio, portfolio_id)
    if portfolio:
        portfolio.last_refreshed_at = datetime.utcnow()
        portfolio.updated_at = datetime.utcnow()
    session.commit()
    return changed
