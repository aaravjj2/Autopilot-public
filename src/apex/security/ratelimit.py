"""In-process sliding-window rate limiter.

Lightweight and dependency-free; suitable for a single-instance deployment
(Cloud Run min/max-instances=1). For horizontal scale this would move to Redis,
but the interface stays the same.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    def __init__(self, max_events: int, window_seconds: float) -> None:
        self.max_events = int(max_events)
        self.window = float(window_seconds)
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window
        with self._lock:
            bucket = self._buckets[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_events:
                return False
            bucket.append(now)
            return True

    def retry_after(self, key: str) -> float:
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(key)
            if not bucket:
                return 0.0
            return max(0.0, self.window - (now - bucket[0]))

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()
