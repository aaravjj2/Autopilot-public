from __future__ import annotations

import time
import uuid
import weakref
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from apex.core.context import reset_run_id, set_run_id
from apex.core.logging import get_logger
from apex.core.retry import is_transient_exception
from apex.domain.enums import EventType
from apex.domain.models import AuditEvent
from apex.scheduler.alerts import post_json_webhook

if TYPE_CHECKING:
    from apscheduler.schedulers.base import BaseScheduler
    from apex.services.engine import ApexEngine

LOGGER = get_logger(__name__)
ET = ZoneInfo("America/New_York")
# Track which schedulers have already registered jobs.
# Uses uuid4 + weakref.ref to avoid memory-address-reuse collisions from id().
_REGISTERED_SCHEDULER_IDS: dict[str, weakref.ref[object]] = {}

# (job_name, hour, minute, day_of_week) — day_of_week None = every day
SCHEDULE: list[tuple[str, int, int, int | None]] = [
    ("system_health_check", 5, 45, None),
    ("database_backup", 5, 50, None),
    ("overnight_news_digest", 6, 0, None),
    ("watchlist_refresh", 6, 30, None),
    ("polymarket_macro_snapshot", 6, 45, None),
    ("options_chain_snapshot", 7, 0, None),
    ("market_snapshot", 7, 15, None),
    ("opportunity_scoring", 7, 30, None),
    ("deep_research_triggers", 8, 0, None),
    ("agent_panel_run", 8, 30, None),
    ("pre_market_risk_check", 9, 15, None),
    ("loss_cut_scan", 9, 35, None),
    ("order_submission", 9, 31, None),
    ("polymarket_event_discovery", 9, 22, None),
    ("polymarket_paper_order_submission", 9, 37, None),
    ("arb_opportunity_scan", 9, 0, None),
    ("prediction_markets_agent_cycle", 9, 10, None),
    ("intraday_polymarket_check", 10, 0, None),
    ("intraday_exit_review", 10, 30, None),
    ("midday_review", 12, 0, None),
    ("exit_review_afternoon", 14, 0, None),
    ("whale_wallet_scan", 13, 0, None),
    ("pre_close_polymarket_scan", 15, 15, None),
    ("pre_close_exit_review", 15, 30, None),
    ("eod_flatten_positions", 15, 45, None),
    ("end_of_day_orders", 15, 50, None),
    ("fill_reconciliation", 16, 15, None),
    ("pl_attribution", 16, 30, None),
    ("trade_memory_update", 17, 0, None),
    ("brain_context_refresh", 17, 30, None),
    ("self_improvement_cycle", 17, 45, None),
    ("world_cup_discovery", 8, 0, None),
]


def idempotent_job(engine: ApexEngine, job_name: str, func: Callable[[], None]) -> None:
    run_date = datetime.now(ET).date().isoformat()
    if not engine.store.start_job(job_name, run_date):
        LOGGER.info("Skipping already successful job %s for %s", job_name, run_date)
        return

    run_id = f"{job_name}:{run_date}:{uuid.uuid4().hex[:10]}"
    token = set_run_id(run_id)
    status = "success"
    details = ""
    last_exc: BaseException | None = None
    max_attempts = max(1, min(20, int(engine.settings.scheduler_transient_max_attempts)))
    backoff = float(engine.settings.scheduler_transient_backoff_sec)

    try:
        for attempt in range(max_attempts):
            try:
                func()
                last_exc = None
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < max_attempts - 1 and is_transient_exception(exc):
                    LOGGER.warning(
                        "Transient failure on job %s (%s), attempt %s/%s — sleeping %.1fs",
                        job_name,
                        type(exc).__name__,
                        attempt + 1,
                        max_attempts,
                        backoff,
                    )
                    time.sleep(backoff)
                    continue
                break

        if last_exc is not None:
            status = "failed"
            details = str(last_exc)
            LOGGER.exception("Job %s failed for %s", job_name, run_date)
            try:
                engine.store.append_event(
                    AuditEvent(
                        event_type=EventType.SYSTEM_ALERT,
                        rejection_reason=f"job_failed:{job_name}",
                        raw_payload={
                            "phase": "scheduler",
                            "job_name": job_name,
                            "run_date": run_date,
                            "run_id": run_id,
                            "details": details,
                        },
                    )
                )
            except Exception:  # noqa: BLE001
                LOGGER.debug("Could not append job failure audit event", exc_info=True)

            hook = (engine.settings.apex_webhook_url or "").strip()
            if hook:
                post_json_webhook(
                    hook,
                    {
                        "event": "apex_job_failed",
                        "job_name": job_name,
                        "run_date": run_date,
                        "run_id": run_id,
                        "error": details,
                    },
                )
    finally:
        reset_run_id(token)
        engine.store.finish_job(job_name, run_date, status, details)


def register_jobs(scheduler: BaseScheduler, engine: ApexEngine) -> None:
    sched_id = str(uuid.uuid4())
    # Clean up stale weakrefs and check if this scheduler is already registered.
    stale = [k for k, v in list(_REGISTERED_SCHEDULER_IDS.items()) if v() is None]
    for k in stale:
        del _REGISTERED_SCHEDULER_IDS[k]
    if stale:
        LOGGER.debug("Cleaned %d stale scheduler weakrefs from registry", len(stale))

    # Check existing registrations.  We can't tell whether a new scheduler object
    # at the same id() is "the same" as a live one, so we only guard against
    # the pathological case of register_jobs being called twice on the same object.
    already = [k for k, v in _REGISTERED_SCHEDULER_IDS.items() if v() is scheduler]
    if already:
        LOGGER.debug(
            "APEX jobs already registered on scheduler id=%s (key=%s), skipping",
            id(scheduler),
            already[0],
        )
        return

    _REGISTERED_SCHEDULER_IDS[sched_id] = weakref.ref(scheduler)
    LOGGER.info(
        "Registering %d APEX scheduler jobs (sched_id=%s, id=%s)",
        len(SCHEDULE) + 4,
        sched_id,
        id(scheduler),
    )

    def _options_chain() -> None:
        engine.options_chain_snapshot(engine.todays_watchlist or engine.watchlist_refresh())

    def _market_snapshot() -> None:
        engine.market_snapshot(engine.todays_watchlist or engine.watchlist_refresh())

    def _opportunity_scoring() -> None:
        engine.opportunity_scoring(engine.todays_watchlist or engine.watchlist_refresh())

    def _agent_panel() -> None:
        wl = engine.todays_watchlist or engine.watchlist_refresh()
        if wl:
            engine.market_snapshot(wl)
            if not engine.todays_opportunities:
                engine.opportunity_scoring(wl)
        engine.agent_panel_run(engine.todays_opportunities)

    callbacks: dict[str, Callable[[], None]] = {
        "system_health_check": engine.system_health_check,
        "overnight_news_digest": engine.overnight_news_digest,
        "database_backup": engine.database_backup,
        "watchlist_refresh": engine.watchlist_refresh,
        "polymarket_macro_snapshot": engine.polymarket_macro_snapshot,
        "options_chain_snapshot": _options_chain,
        "market_snapshot": _market_snapshot,
        "opportunity_scoring": _opportunity_scoring,
        "deep_research_triggers": engine.deep_research_triggers,
        "agent_panel_run": _agent_panel,
        "pre_market_risk_check": engine.pre_market_risk_check,
        "order_submission": engine.order_submission,
        "polymarket_event_discovery": engine.polymarket_event_discovery,
        "polymarket_paper_order_submission": engine.polymarket_paper_order_submission,
        "arb_opportunity_scan": engine.arb_opportunity_scan,
        "prediction_markets_agent_cycle": engine.prediction_markets_agent_cycle,
        "intraday_polymarket_check": engine.intraday_polymarket_check,
        "intraday_exit_review": engine.intraday_exit_review,
        "loss_cut_scan": engine.loss_cut_scan,
        "midday_review": engine.midday_review,
        "exit_review_afternoon": engine.exit_review_afternoon,
        "whale_wallet_scan": engine.whale_wallet_scan,
        "pre_close_polymarket_scan": engine.pre_close_polymarket_scan,
        "pre_close_exit_review": engine.pre_close_exit_review,
        "eod_flatten_positions": engine.eod_flatten_all_positions,
        "end_of_day_orders": engine.end_of_day_orders,
        "fill_reconciliation": engine.fill_reconciliation,
        "pl_attribution": engine.pl_attribution,
        "trade_memory_update": engine.trade_memory_update,
        "brain_context_refresh": engine.brain_context_refresh,
        "self_improvement_cycle": engine.self_improvement_cycle,
        "world_cup_discovery": engine.world_cup_discovery,
    }

    scheduled = {name for name, *_ in SCHEDULE}
    if scheduled != set(callbacks):
        missing = sorted(scheduled - set(callbacks))
        extra = sorted(set(callbacks) - scheduled)
        raise ValueError(
            "SCHEDULE and callbacks must match exactly. "
            f"missing_callbacks={missing} extra_callbacks={extra}"
        )

    for name, hour, minute, day_of_week in SCHEDULE:
        if name == "loss_cut_scan":
            continue
        cb = callbacks[name]
        scheduler.add_job(
            lambda n=name, c=cb: idempotent_job(engine, n, c),
            "cron",
            day_of_week=day_of_week,
            hour=hour,
            minute=minute,
            timezone=ET,
            id=name,
            replace_existing=True,
        )

    # Intraday loss_cut_scan every 5 minutes during market hours (replaces daily 9:35 slot)
    scheduler.add_job(
        lambda: idempotent_job(engine, "loss_cut_scan", engine.loss_cut_scan),
        "cron",
        day_of_week="mon-fri",
        hour="9-15",
        minute="*/5",
        timezone=ET,
        id="loss_cut_scan",
        replace_existing=True,
    )

    # Arb scan every 3 minutes (not idempotent — must run repeatedly)
    scheduler.add_job(
        engine.arb_opportunity_scan,
        "cron",
        day_of_week="mon-fri",
        hour="9-16",
        minute="*/3",
        timezone=ET,
        id="arb_opportunity_scan_intraday",
        replace_existing=True,
    )

    # Unified Kalshi arb + Polymarket event agents every 5 minutes
    scheduler.add_job(
        engine.prediction_markets_agent_cycle,
        "cron",
        day_of_week="mon-fri",
        hour="9-16",
        minute="*/5",
        timezone=ET,
        id="prediction_markets_agent_cycle_intraday",
        replace_existing=True,
    )

    # World Cup agent cycle (full pipeline) every 15 minutes 8 AM - 11 PM
    scheduler.add_job(
        engine.world_cup_agent_cycle,
        "cron",
        day_of_week="mon-sun",
        hour="8-23",
        minute="*/15",
        timezone=ET,
        id="world_cup_agent_cycle_intraday",
        replace_existing=True,
    )
