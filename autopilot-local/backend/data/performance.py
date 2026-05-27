from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import yfinance as yf
from sqlmodel import Session, select

from db import Holding, PerformanceSnapshot, Portfolio


def _nav_for_holdings(
    holdings: list[Holding], prices: dict[str, float], notional: float
) -> float:
    if not holdings:
        return notional
    nav = 0.0
    for h in holdings:
        px = prices.get(h.ticker.upper(), 0.0)
        if px <= 0:
            continue
        nav += notional * h.weight
    return nav if nav > 0 else notional


def snapshot_portfolio_performance(
    session: Session, portfolio_id: str, notional: float = 100_000.0
) -> PerformanceSnapshot:
    holdings = session.exec(
        select(Holding).where(Holding.portfolio_id == portfolio_id)
    ).all()
    tickers = [h.ticker for h in holdings] or ["SPY"]
    prices: dict[str, float] = {}
    for sym in tickers:
        try:
            hist = yf.Ticker(sym).history(period="5d")
            if not hist.empty:
                prices[sym.upper()] = float(hist["Close"].iloc[-1])
        except Exception:
            continue
    value = _nav_for_holdings(holdings, prices, notional)
    prior = session.exec(
        select(PerformanceSnapshot)
        .where(PerformanceSnapshot.portfolio_id == portfolio_id)
        .order_by(PerformanceSnapshot.date)
    ).all()
    inception = prior[0].value_usd if prior else value
    ret = ((value - inception) / inception * 100.0) if inception else 0.0
    snap = PerformanceSnapshot(
        portfolio_id=portfolio_id,
        date=date.today(),
        value_usd=value,
        return_pct=ret,
    )
    session.add(snap)
    session.commit()
    return snap


def snapshot_all_portfolios(session: Session, notional: float = 100_000.0) -> int:
    portfolios = session.exec(select(Portfolio)).all()
    count = 0
    for p in portfolios:
        snapshot_portfolio_performance(session, p.id, notional)
        count += 1
    return count


def period_return_pct(
    session: Session, portfolio_id: str, period: str
) -> float:
    days_map = {"1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365}
    days = days_map.get(period, 30)
    cutoff = date.today() - timedelta(days=days)
    snaps = session.exec(
        select(PerformanceSnapshot)
        .where(PerformanceSnapshot.portfolio_id == portfolio_id)
        .order_by(PerformanceSnapshot.date)
    ).all()
    if len(snaps) < 2:
        if snaps:
            return snaps[-1].return_pct
        return 0.0
    in_range = [s for s in snaps if s.date >= cutoff]
    if len(in_range) < 2:
        start = snaps[0]
        end = snaps[-1]
    else:
        start = in_range[0]
        end = in_range[-1]
    if start.value_usd <= 0:
        return 0.0
    return (end.value_usd - start.value_usd) / start.value_usd * 100.0


def benchmark_return(period: str) -> float:
    days_map = {"1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365}
    days = days_map.get(period, 30)
    try:
        hist = yf.Ticker("SPY").history(period=f"{days + 5}d")
        if len(hist) < 2:
            return 0.0
        start = float(hist["Close"].iloc[0])
        end = float(hist["Close"].iloc[-1])
        return (end - start) / start * 100.0
    except Exception:
        return 0.0


def sharpe_ratio(portfolio_id: str, session: Session) -> float:
    snaps = session.exec(
        select(PerformanceSnapshot)
        .where(PerformanceSnapshot.portfolio_id == portfolio_id)
        .order_by(PerformanceSnapshot.date)
    ).all()
    if len(snaps) < 5:
        return 0.0
    values = [s.value_usd for s in snaps]
    rets = [
        (values[i] - values[i - 1]) / values[i - 1]
        for i in range(1, len(values))
        if values[i - 1] > 0
    ]
    if not rets:
        return 0.0
    import statistics

    mean = statistics.mean(rets) * 252
    std = statistics.pstdev(rets) * (252**0.5) if len(rets) > 1 else 1.0
    if std <= 0:
        return 0.0
    return (mean - 0.05) / std


def performance_series(
    session: Session, portfolio_id: str, period: str
) -> list[dict[str, Any]]:
    days_map = {"1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365}
    days = days_map.get(period, 30)
    cutoff = date.today() - timedelta(days=days)
    snaps = session.exec(
        select(PerformanceSnapshot)
        .where(PerformanceSnapshot.portfolio_id == portfolio_id)
        .order_by(PerformanceSnapshot.date)
    ).all()
    filtered = [s for s in snaps if s.date >= cutoff] or snaps
    return [
        {"date": s.date.isoformat(), "value": s.value_usd, "return_pct": s.return_pct}
        for s in filtered
    ]
