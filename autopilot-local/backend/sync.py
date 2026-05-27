from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from alpaca_client import AlpacaClient
from config import get_settings
from db import Holding, Portfolio, Trade, UserPosition
from portfolios import get_portfolio_spec


def _account_value(alpaca: AlpacaClient) -> float:
    acc = alpaca.get_account()
    return float(acc.get("equity") or acc.get("portfolio_value") or 0)


def _alpaca_position_map(alpaca: AlpacaClient) -> dict[str, float]:
    return {
        str(p["symbol"]).upper(): float(p.get("qty") or 0)
        for p in alpaca.get_positions()
    }


def follow_portfolio(session: Session, portfolio_id: str) -> dict[str, Any]:
    alpaca = AlpacaClient()
    if not alpaca.configured:
        return {"ok": False, "error": "Alpaca not configured"}
    portfolio = session.get(Portfolio, portfolio_id)
    if not portfolio:
        return {"ok": False, "error": "portfolio not found"}
    holdings = session.exec(
        select(Holding).where(Holding.portfolio_id == portfolio_id)
    ).all()
    if not holdings:
        return {"ok": False, "error": "no holdings"}
    allocation = float(get_settings()["paper_allocation_usd"])
    account_val = _account_value(alpaca)
    deploy = min(allocation, account_val * 0.95) if account_val > 0 else allocation
    tickers = [h.ticker for h in holdings]
    prices = alpaca.get_latest_prices(tickers)
    existing = _alpaca_position_map(alpaca)
    orders: list[dict[str, Any]] = []
    for h in holdings:
        px = prices.get(h.ticker.upper(), 0.0)
        if px <= 0:
            continue
        target_shares = math.floor((h.weight * deploy) / px)
        if target_shares <= 0:
            continue
        current = existing.get(h.ticker.upper(), 0.0)
        delta = target_shares - current
        if delta <= 0:
            continue
        result = alpaca.place_market_order(h.ticker, delta, "buy")
        order_id = str(result.get("id") or "")
        if order_id:
            filled = alpaca.wait_for_order(order_id, timeout_sec=30.0)
            fill_px = float(filled.get("filled_avg_price") or px)
            qty = float(filled.get("filled_qty") or delta)
            session.add(
                Trade(
                    portfolio_id=portfolio_id,
                    ticker=h.ticker.upper(),
                    side="buy",
                    qty=qty,
                    price=fill_px,
                    alpaca_order_id=order_id,
                    status=str(filled.get("status") or "filled"),
                    executed_at=datetime.utcnow(),
                )
            )
            session.add(
                UserPosition(
                    ticker=h.ticker.upper(),
                    qty=qty,
                    avg_entry=fill_px,
                    current_price=fill_px,
                    portfolio_id=portfolio_id,
                )
            )
            orders.append({"ticker": h.ticker, "qty": qty, "side": "buy"})
    portfolio.is_following = True
    portfolio.updated_at = datetime.utcnow()
    session.commit()
    return {"ok": True, "orders": orders}


def unfollow_portfolio(session: Session, portfolio_id: str) -> dict[str, Any]:
    alpaca = AlpacaClient()
    if not alpaca.configured:
        return {"ok": False, "error": "Alpaca not configured"}
    portfolio = session.get(Portfolio, portfolio_id)
    if not portfolio:
        return {"ok": False, "error": "portfolio not found"}
    tagged = session.exec(
        select(UserPosition).where(UserPosition.portfolio_id == portfolio_id)
    ).all()
    closed: list[str] = []
    for pos in tagged:
        result = alpaca.close_position(pos.ticker)
        if result.get("status") == "closed" or not result.get("error"):
            session.add(
                Trade(
                    portfolio_id=portfolio_id,
                    ticker=pos.ticker,
                    side="sell",
                    qty=pos.qty,
                    price=pos.current_price,
                    status="filled",
                    executed_at=datetime.utcnow(),
                )
            )
            session.delete(pos)
            closed.append(pos.ticker)
    portfolio.is_following = False
    portfolio.updated_at = datetime.utcnow()
    session.commit()
    return {"ok": True, "closed": closed}


def rebalance_if_following(
    session: Session, portfolio_id: str, new_holdings: list[tuple[str, float]]
) -> dict[str, Any]:
    portfolio = session.get(Portfolio, portfolio_id)
    if not portfolio or not portfolio.is_following:
        return {"ok": True, "skipped": True}
    from portfolios import update_holdings

    update_holdings(session, portfolio_id, new_holdings)
    # Simplified rebalance: unfollow then follow
    unfollow_portfolio(session, portfolio_id)
    return follow_portfolio(session, portfolio_id)
