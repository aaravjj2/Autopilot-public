from __future__ import annotations

import signal
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler

from apex.core.logging import get_logger
from apex.scheduler.jobs import register_jobs
from apex.services.engine import ApexEngine

LOGGER = get_logger(__name__)

ET = ZoneInfo("America/New_York")


def _catch_up_morning_pipeline(engine: ApexEngine) -> None:
    """If scheduler started after the morning pipeline window, run it once immediately.

    The cron scheduler only fires jobs at their next *future* scheduled time, so if
    autopilot starts at 10:00 ET the 9:31 ``order_submission`` window is already
    gone.  This catch-up runs the critical morning sequence once so the system
    doesn't sit idle until the next calendar day.
    """
    now = datetime.now(ET)

    # Only catch up if order_submission (9:31) has already passed today
    if now.hour < 9 or (now.hour == 9 and now.minute < 31):
        return
    if now.hour >= 16:
        return  # too late in the day; let the afternoon/exit jobs fire normally

    # Skip if the jobs already ran (e.g. scheduler restarted mid-day)
    try:
        already_ran = engine.store.start_job("catch_up_pipeline", now.date().isoformat())
        if not already_ran:
            LOGGER.info("Catch-up: morning pipeline already completed today")
            return
    except Exception:
        pass

    LOGGER.info(
        "Scheduler started at %02d:%02d ET — morning pipeline window closed. "
        "Running catch-up...",
        now.hour, now.minute,
    )

    # 1. Ensure watchlist is loaded
    wl = engine.todays_watchlist
    if not wl:
        try:
            wl = engine.watchlist_refresh()
        except Exception as exc:
            LOGGER.warning("Catch-up: watchlist_refresh failed: %s", exc)
            return
    if not wl:
        LOGGER.warning("Catch-up: empty watchlist, nothing to do")
        return

    # 2. Opportunity scoring
    opps = engine.todays_opportunities
    if not opps:
        try:
            opps = engine.opportunity_scoring(wl)
        except Exception as exc:
            LOGGER.warning("Catch-up: opportunity_scoring failed: %s", exc)
            return

    # 3. Agent panel (generates proposals)
    proposals: list[Any] = []
    try:
        proposals = engine.agent_panel_run(opps)
    except Exception as exc:
        LOGGER.warning("Catch-up: agent_panel_run failed: %s", exc)

    # 4. Pre-market risk check (clears stale flags)
    try:
        engine.pre_market_risk_check()
    except Exception as exc:
        LOGGER.warning("Catch-up: pre_market_risk_check failed: %s", exc)

    # 5. Order submission
    try:
        engine.order_submission(proposals)
    except Exception as exc:
        LOGGER.warning("Catch-up: order_submission failed: %s", exc)

    # Mark catch-up complete in job_runs so it doesn't re-run on restart
    try:
        engine.store.finish_job("catch_up_pipeline", now.date().isoformat(), "success", "")
    except Exception:
        pass

    LOGGER.info("Morning pipeline catch-up complete for %s", now.date().isoformat())


def _interrupt_from_signal(signum: int, _frame: object | None) -> None:
    LOGGER.info("Received signal %s; stopping autopilot", signum)
    raise KeyboardInterrupt()


def run_scheduler(engine: ApexEngine, *, bootstrap: bool = True) -> None:
    """
    Blocking APScheduler loop (US/Eastern). One failed job no longer tears down
    the process; SIGINT/SIGTERM raise KeyboardInterrupt for graceful shutdown.
    """
    scheduler = BlockingScheduler(
        executors={"default": ThreadPoolExecutor(5)},
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 7200,
        },
        timezone="America/New_York",
    )
    register_jobs(scheduler, engine)

    if bootstrap:
        try:
            engine.warm_trading_day_caches()
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Startup bootstrap skipped: %s", exc)
        _catch_up_morning_pipeline(engine)

    try:
        signal.signal(signal.SIGINT, _interrupt_from_signal)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _interrupt_from_signal)
    except ValueError:
        pass

    LOGGER.info("APEX autopilot scheduler running (Ctrl+C or SIGTERM to exit)")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        LOGGER.info("Scheduler stop requested")
    finally:
        try:
            scheduler.shutdown(wait=False)
        except Exception as exc:  # noqa: BLE001
            LOGGER.debug("Scheduler shutdown: %s", exc)
