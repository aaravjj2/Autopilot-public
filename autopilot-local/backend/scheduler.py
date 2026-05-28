from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import select

from data.congress import refresh_political_portfolio
from data.performance import snapshot_all_portfolios, snapshot_portfolio_performance
from data.sec_13f import refresh_hedge_fund_portfolio
from db import Portfolio, RefreshLog, get_session_sync
from portfolios import list_portfolio_ids, update_holdings
from sync import rebalance_if_following

LOGGER = logging.getLogger(__name__)
ET = ZoneInfo("America/New_York")

_scheduler: BackgroundScheduler | None = None


def _log_refresh(portfolio_id: str, job: str, status: str, message: str = "") -> None:
    with get_session_sync() as session:
        session.add(
            RefreshLog(
                portfolio_id=portfolio_id,
                job_name=job,
                status=status,
                message=message[:500],
            )
        )
        session.commit()


def refresh_portfolio(portfolio_id: str) -> None:
    with get_session_sync() as session:
        portfolio = session.get(Portfolio, portfolio_id)
        if not portfolio:
            return
        new_holdings = None
        if portfolio.category == "political":
            new_holdings = refresh_political_portfolio(portfolio_id)
        elif portfolio.category == "hedge-fund":
            new_holdings = refresh_hedge_fund_portfolio(portfolio_id)
        if new_holdings:
            changed = update_holdings(session, portfolio_id, new_holdings)
            if changed:
                rebalance_if_following(session, portfolio_id, new_holdings)
            _log_refresh(portfolio_id, "refresh", "ok", f"holdings={len(new_holdings)}")
        else:
            _log_refresh(portfolio_id, "refresh", "skipped", "using seed holdings")
        snapshot_portfolio_performance(session, portfolio_id)


def refresh_all_political() -> None:
    with get_session_sync() as session:
        for p in session.exec(select(Portfolio).where(Portfolio.category == "political")).all():
            refresh_portfolio(p.id)


def refresh_all_hedge_funds() -> None:
    with get_session_sync() as session:
        for p in session.exec(
            select(Portfolio).where(Portfolio.category == "hedge-fund")
        ).all():
            refresh_portfolio(p.id)


def refresh_all_performance() -> None:
    with get_session_sync() as session:
        snapshot_all_portfolios(session)
    _log_refresh("", "performance_snapshot", "ok")


def refresh_all_portfolios() -> None:
    for pid in list_portfolio_ids():
        refresh_portfolio(pid)
    refresh_all_performance()


def _market_hours() -> bool:
    now = datetime.now(ET)
    if now.weekday() >= 5:
        return False
    return (now.hour > 9 or (now.hour == 9 and now.minute >= 30)) and now.hour < 16


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = BackgroundScheduler(timezone=ET)
    _scheduler.add_job(
        refresh_all_political,
        "cron",
        minute="*/30",
        hour="9-15",
        day_of_week="mon-fri",
        id="political_refresh",
    )
    _scheduler.add_job(
        refresh_all_hedge_funds,
        "cron",
        hour=6,
        minute=0,
        id="hedge_13f_refresh",
    )
    _scheduler.add_job(
        refresh_all_performance,
        "cron",
        hour=6,
        minute=15,
        id="performance_snapshot",
    )
    _scheduler.start()
    LOGGER.info("Autopilot Local scheduler started")
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
