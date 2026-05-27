"""In-process TTL caches for hot API paths."""

from __future__ import annotations

import time
from typing import Any, Callable, TypeVar

T = TypeVar("T")

_CACHE: dict[str, tuple[float, Any]] = {}


def cached(key: str, ttl_sec: float, factory: Callable[[], T]) -> T:
    now = time.monotonic()
    hit = _CACHE.get(key)
    if hit is not None and now - hit[0] < ttl_sec:
        return hit[1]  # type: ignore[return-value]
    value = factory()
    _CACHE[key] = (now, value)
    return value


def invalidate(key: str) -> None:
    _CACHE.pop(key, None)
