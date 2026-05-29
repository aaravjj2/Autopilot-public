from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from apex.core.logging import get_logger

LOGGER = get_logger(__name__)
T = TypeVar("T")


def is_transient_exception(exc: BaseException) -> bool:
    """HTTP / network blips worth retrying (scheduler, ingestion, etc.)."""

    try:
        import requests

        transient_requests = (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
        )
        if isinstance(exc, transient_requests):
            return True
    except ImportError:
        pass
    return isinstance(exc, (TimeoutError, BrokenPipeError, ConnectionResetError, OSError))


def call_with_retries(
    fn: Callable[[], T],
    *,
    max_attempts: int,
    backoff_seconds: float = 2.0,
    log_label: str = "",
) -> T:
    """Run ``fn`` up to ``max_attempts`` times; retry only on transient errors."""

    attempts = max(1, min(int(max_attempts), 20))
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            if attempt < attempts - 1 and is_transient_exception(exc):
                LOGGER.warning(
                    "Transient error%s (attempt %s/%s): %s — retrying in %.1fs",
                    f" [{log_label}]" if log_label else "",
                    attempt + 1,
                    attempts,
                    exc,
                    backoff_seconds,
                )
                time.sleep(max(0.0, float(backoff_seconds)))
                continue
            raise
