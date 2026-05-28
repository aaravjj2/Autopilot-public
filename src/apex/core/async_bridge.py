from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable
from typing import TypeVar

T = TypeVar("T")


def run_sync(coro: Awaitable[T]) -> T:
    """Run a coroutine from sync code, even if an event loop is already running.

    If called inside an active event loop thread, execute the coroutine in a
    dedicated thread with its own loop to avoid ``asyncio.run`` runtime errors.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, T] = {}
    error: dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as exc:  # pragma: no cover - re-raised in caller thread
            error["exc"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    if "exc" in error:
        raise error["exc"]
    return result["value"]

