from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sse_starlette.sse import EventSourceResponse

from alpaca_client import AlpacaClient
from data.performance import (
    benchmark_return,
    performance_series,
    period_return_pct,
    sharpe_ratio,
)
from db import (
    Holding,
    PolymarketPosition,
    PolymarketSnapshot,
    PolymarketTrade,
    Portfolio,
    Trade,
    UserPosition,
    get_session,
)
from pm_sync import sync_polymarket_from_apex
from portfolios import get_portfolio_spec
from scheduler import refresh_all_portfolios, refresh_portfolio
from sync import follow_portfolio, unfollow_portfolio

router = APIRouter(tags=["marketplace"])


def _portfolio_card(session: Session, p: Portfolio, period: str = "1M") -> dict[str, Any]:
    ret = period_return_pct(session, p.id, period)
    holdings = session.exec(select(Holding).where(Holding.portfolio_id == p.id)).all()
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "category": p.category,
        "pilot_name": p.pilot_name,
        "is_following": p.is_following,
        "return_pct": round(ret, 2),
        "aum_usd": 100_000.0,
        "holdings_count": len(holdings),
        "last_refreshed_at": p.last_refreshed_at.isoformat() if p.last_refreshed_at else None,
    }


@router.get("/api/positions")
def get_open_positions() -> list[dict[str, Any]]:
    from apex.integrations.hub import get_integration_hub

    hub = get_integration_hub()
    if not hub or not hub.has_alpaca():
        raise HTTPException(status_code=503, detail="Alpaca not configured")

    alp = hub.alpaca_direct
    positions = alp.get_positions()
    result = []
    for p in positions:
        sym = p.get("symbol", "")
        entry = float(p.get("avg_entry_price", 0) or 0)
        qty = float(p.get("qty", 0) or 0)
        current = float(p.get("current_price", 0) or 0)
        market_val = float(p.get("market_value", 0) or 0)
        unrealized_pl = float(p.get("unrealized_pl", 0) or 0)
        unrealized_plpc = float(p.get("unrealized_plpc", 0) or 0)
        cost_basis = float(p.get("cost_basis", 0) or 0)
        asset_class = p.get("asset_class", "us_equity")

        result.append(
            {
                "symbol": sym,
                "asset_class": asset_class,
                "side": "long" if qty >= 0 else "short",
                "qty": abs(qty),
                "avg_entry_price": entry,
                "current_price": current,
                "market_value": market_val,
                "cost_basis": cost_basis,
                "unrealized_pl": round(unrealized_pl, 2),
                "unrealized_pl_pct": round(unrealized_plpc * 100, 2),
                "pnl_pct": round(((current - entry) / entry * 100) if entry else 0, 2),
            }
        )
    return result


@router.get("/api/portfolios")
def list_portfolios(
    period: str = "1M",
    category: str | None = None,
    sort: str = "return",
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    rows = session.exec(select(Portfolio)).all()
    if category:
        rows = [p for p in rows if p.category == category]
    cards = [_portfolio_card(session, p, period) for p in rows]
    if sort == "return":
        cards.sort(key=lambda x: x["return_pct"], reverse=True)
    elif sort == "name":
        cards.sort(key=lambda x: x["name"])
    elif sort == "newest":
        cards.sort(key=lambda x: x.get("last_refreshed_at") or "", reverse=True)
    return cards


@router.get("/api/portfolios/{portfolio_id}")
def get_portfolio(
    portfolio_id: str,
    period: str = "1M",
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    p = session.get(Portfolio, portfolio_id)
    if not p:
        raise HTTPException(404, "Portfolio not found")
    holdings = session.exec(select(Holding).where(Holding.portfolio_id == portfolio_id)).all()
    alpaca = AlpacaClient()
    prices = alpaca.get_latest_prices([h.ticker for h in holdings])
    holdings_out = []
    for h in holdings:
        px = prices.get(h.ticker.upper(), 0.0)
        value = 100_000.0 * h.weight
        holdings_out.append(
            {
                "ticker": h.ticker,
                "weight": h.weight,
                "weight_pct": round(h.weight * 100, 2),
                "shares": h.shares,
                "price": px,
                "value_usd": round(value, 2),
            }
        )
    trades = sorted(
        session.exec(select(Trade).where(Trade.portfolio_id == portfolio_id)).all(),
        key=lambda t: t.executed_at or datetime.min,
        reverse=True,
    )[:25]
    return {
        **_portfolio_card(session, p, period),
        "holdings": holdings_out,
        "trades": [
            {
                "id": t.id,
                "ticker": t.ticker,
                "side": t.side,
                "qty": t.qty,
                "price": t.price,
                "status": t.status,
                "executed_at": t.executed_at.isoformat() if t.executed_at else None,
            }
            for t in trades
        ],
        "performance": performance_series(session, portfolio_id, period),
        "benchmark_return_pct": round(benchmark_return(period), 2),
        "sharpe_ratio": round(sharpe_ratio(portfolio_id, session), 2),
        "spec": get_portfolio_spec(portfolio_id),
    }


@router.post("/api/portfolios/{portfolio_id}/follow")
def follow(portfolio_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    result = follow_portfolio(session, portfolio_id)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "follow failed"))
    return result


@router.delete("/api/portfolios/{portfolio_id}/follow")
def unfollow(portfolio_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    result = unfollow_portfolio(session, portfolio_id)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "unfollow failed"))
    return result


@router.get("/api/dashboard")
def dashboard(session: Session = Depends(get_session)) -> dict[str, Any]:
    alpaca = AlpacaClient()
    ping = alpaca.ping()
    positions_raw = alpaca.get_positions() if alpaca.configured else []
    tickers = [str(p["symbol"]).upper() for p in positions_raw]
    prices = alpaca.get_latest_prices(tickers)
    positions = []
    total_unrealized = 0.0
    for p in positions_raw:
        sym = str(p["symbol"]).upper()
        qty = float(p.get("qty") or 0)
        entry = float(p.get("avg_entry_price") or 0)
        current = prices.get(sym, float(p.get("current_price") or 0))
        upl = (current - entry) * qty if entry else float(p.get("unrealized_pl") or 0)
        total_unrealized += upl
        tagged = session.get(UserPosition, sym)
        positions.append(
            {
                "ticker": sym,
                "qty": qty,
                "avg_entry": entry,
                "current_price": current,
                "unrealized_pl": round(upl, 2),
                "portfolio_id": tagged.portfolio_id if tagged else "",
            }
        )
    followed = session.exec(select(Portfolio).where(Portfolio.is_following == True)).all()  # noqa: E712
    followed_cards = []
    for p in followed:
        followed_cards.append(
            {
                **_portfolio_card(session, p, "1M"),
                "performance": performance_series(session, p.id, "1W"),
            }
        )
    trades = sorted(
        session.exec(select(Trade)).all(),
        key=lambda t: t.executed_at or datetime.min,
        reverse=True,
    )[:50]
    return {
        "account": {
            "equity": ping.get("equity", 0),
            "cash": ping.get("cash", 0),
            "buying_power": ping.get("buying_power", 0),
            "unrealized_pl": round(total_unrealized, 2),
        },
        "followed_portfolios": followed_cards,
        "positions": positions,
        "trades": [
            {
                "portfolio_id": t.portfolio_id,
                "ticker": t.ticker,
                "side": t.side,
                "qty": t.qty,
                "price": t.price,
                "status": t.status,
                "executed_at": t.executed_at.isoformat() if t.executed_at else None,
            }
            for t in trades
        ],
    }


async def _pnl_stream():
    alpaca = AlpacaClient()
    while True:
        payload: dict[str, Any] = {"positions": [], "timestamp": datetime.now(timezone.utc).isoformat()}
        if alpaca.configured:
            positions = alpaca.get_positions()
            tickers = [str(p["symbol"]).upper() for p in positions]
            prices = alpaca.get_latest_prices(tickers)
            for p in positions:
                sym = str(p["symbol"]).upper()
                qty = float(p.get("qty") or 0)
                entry = float(p.get("avg_entry_price") or 0)
                current = prices.get(sym, entry)
                payload["positions"].append(
                    {
                        "ticker": sym,
                        "qty": qty,
                        "current_price": current,
                        "unrealized_pl": round((current - entry) * qty, 2),
                    }
                )
            acc = alpaca.ping()
            payload["account"] = acc
        yield {"event": "pnl", "data": json.dumps(payload)}
        await asyncio.sleep(3)


@router.get("/api/stream/pnl")
async def stream_pnl():
    return EventSourceResponse(_pnl_stream())


@router.post("/api/refresh/all")
def refresh_all() -> dict[str, Any]:
    refresh_all_portfolios()
    return {"ok": True, "message": "refresh started"}


@router.post("/api/refresh/{portfolio_id}")
def refresh_one(portfolio_id: str) -> dict[str, Any]:
    refresh_portfolio(portfolio_id)
    return {"ok": True, "portfolio_id": portfolio_id}


@router.get("/api/polymarket/summary")
def polymarket_summary(session: Session = Depends(get_session)) -> dict[str, Any]:
    positions = session.exec(
        select(PolymarketPosition).where(PolymarketPosition.status == "open")
    ).all()

    total_staked = sum(p.stake_usd for p in positions)
    total_value = sum(p.current_value for p in positions)
    total_pl = sum(p.unrealized_pl for p in positions)

    latest_snapshot = session.exec(
        select(PolymarketSnapshot).order_by(PolymarketSnapshot.date.desc()).limit(1)
    ).first()

    bankroll = latest_snapshot.bankroll_usd if latest_snapshot else 10000.0
    buying_power = latest_snapshot.buying_power_usd if latest_snapshot else 10000.0

    return {
        "bankroll_usd": round(bankroll, 2),
        "buying_power_usd": round(buying_power, 2),
        "total_staked": round(total_staked, 2),
        "total_value": round(total_value, 2),
        "unrealized_pl": round(total_pl, 2),
        "open_positions": len(positions),
        "daily_pl": round(latest_snapshot.daily_pl, 2) if latest_snapshot else 0.0,
        "daily_pl_pct": round(latest_snapshot.daily_pl_pct, 4) if latest_snapshot else 0.0,
    }


@router.get("/api/polymarket/positions")
def polymarket_positions(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    positions = session.exec(
        select(PolymarketPosition).order_by(PolymarketPosition.opened_at.desc())
    ).all()

    return [
        {
            "id": p.id,
            "market_id": p.market_id,
            "question": p.question,
            "slug": p.slug,
            "side": p.side,
            "entry_price": p.entry_price,
            "stake_usd": p.stake_usd,
            "quantity": p.quantity,
            "current_value": p.current_value,
            "unrealized_pl": p.unrealized_pl,
            "status": p.status,
            "opened_at": p.opened_at.isoformat() if p.opened_at else None,
            "resolved_at": p.resolved_at.isoformat() if p.resolved_at else None,
        }
        for p in positions
    ]


@router.get("/api/polymarket/trades")
def polymarket_trades(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    trades = session.exec(
        select(PolymarketTrade).order_by(PolymarketTrade.executed_at.desc())
    ).all()

    return [
        {
            "id": t.id,
            "market_id": t.market_id,
            "question": t.question,
            "side": t.side,
            "stake_usd": t.stake_usd,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "order_id": t.order_id,
            "status": t.status,
            "executed_at": t.executed_at.isoformat() if t.executed_at else None,
        }
        for t in trades
    ]


@router.get("/api/polymarket/equity-curve")
def polymarket_equity_curve(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    snapshots = session.exec(
        select(PolymarketSnapshot).order_by(PolymarketSnapshot.date.asc())
    ).all()

    return [
        {
            "date": s.date.isoformat(),
            "bankroll_usd": s.bankroll_usd,
            "buying_power_usd": s.buying_power_usd,
            "daily_pl": s.daily_pl,
            "daily_pl_pct": s.daily_pl_pct,
        }
        for s in snapshots
    ]


@router.post("/api/polymarket/sync")
def polymarket_sync() -> dict[str, Any]:
    stats = sync_polymarket_from_apex()
    return {
        "ok": True,
        "synced": stats,
        "message": (
            f"Synced {stats['positions']} positions, {stats['trades']} trades, "
            f"{stats['snapshots']} snapshots"
        ),
    }
