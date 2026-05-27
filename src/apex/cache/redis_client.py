"""Redis connection helper with in-memory fallback for dev/tests."""

from __future__ import annotations

import logging
from typing import Any, Optional

LOGGER = logging.getLogger(__name__)

_redis_client: Any = None
_memory_fallback: dict[str, dict[str, str]] = {}


def get_redis(redis_url: Optional[str] = None):
    """Return a redis client or None if unavailable."""
    global _redis_client
    if redis_url == "":
        return None
    if _redis_client is not None and redis_url is None:
        return _redis_client

    url = redis_url
    if url is None:
        try:
            from apex.core.config import get_settings

            url = getattr(get_settings(), "redis_url", "") or ""
        except Exception:
            url = ""

    if not url:
        return None

    try:
        import redis

        _redis_client = redis.from_url(url, decode_responses=True)
        _redis_client.ping()
        LOGGER.info("Redis connected: %s", url.split("@")[-1])
        return _redis_client
    except Exception as exc:
        LOGGER.warning("Redis unavailable (%s); using in-memory fallback", exc)
        return None


def memory_hset(key: str, mapping: dict[str, str]) -> None:
    bucket = _memory_fallback.setdefault(key, {})
    bucket.update(mapping)


def memory_hgetall(key: str) -> dict[str, str]:
    return dict(_memory_fallback.get(key, {}))


def reset_redis_for_tests() -> None:
    global _redis_client
    _redis_client = None
    _memory_fallback.clear()
