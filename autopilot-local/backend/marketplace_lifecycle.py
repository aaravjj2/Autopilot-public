from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from sqlmodel import select

LOGGER = logging.getLogger(__name__)

_sqlite_worker_task: asyncio.Task | None = None


async def _sqlite_worker() -> None:
    from apex.core.config import get_settings
    from apex.repositories.sqlite_store import SQLiteStore

    from main import arb_write_queue

    settings = get_settings()
    store = SQLiteStore(settings.sqlite_path)
    LOGGER.info("Started marketplace SQLite background worker")
    while True:
        try:
            opps = await arb_write_queue.get()
            if opps is None:
                break
            await asyncio.to_thread(store.save_arb_opportunities, opps)
            arb_write_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            LOGGER.error("Marketplace SQLite worker error: %s", exc)


async def startup_marketplace(*, enable_arb_worker: bool = False) -> None:
    from apex.core.config import get_settings
    from apex.demo.seed_data import seed_demo_database
    from apex.repositories.sqlite_store import SQLiteStore
    from data.performance import snapshot_all_portfolios
    from db import PerformanceSnapshot, get_session_sync, init_db
    from portfolios import ensure_seeded
    from scheduler import start_scheduler

    global _sqlite_worker_task

    init_db()
    ensure_seeded()
    settings = get_settings()
    if settings.demo_mode:
        await asyncio.to_thread(seed_demo_database, SQLiteStore(settings.sqlite_path))
    with get_session_sync() as session:
        if not session.exec(select(PerformanceSnapshot)).first():
            snapshot_all_portfolios(session)
    start_scheduler()
    if enable_arb_worker:
        _sqlite_worker_task = asyncio.create_task(_sqlite_worker())


async def shutdown_marketplace() -> None:
    global _sqlite_worker_task

    from scheduler import stop_scheduler

    stop_scheduler()
    if _sqlite_worker_task:
        _sqlite_worker_task.cancel()
        _sqlite_worker_task = None


@asynccontextmanager
async def marketplace_lifespan(*, enable_arb_worker: bool = False):
    await startup_marketplace(enable_arb_worker=enable_arb_worker)
    try:
        yield
    finally:
        await shutdown_marketplace()
