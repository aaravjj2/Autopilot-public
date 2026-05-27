from __future__ import annotations

class BrokerCircuitOpenError(Exception):
    """Raised when broker circuit breaker is open (too many recent failures)."""

    def __init__(self, platform: str = "alpaca") -> None:
        super().__init__(f"Circuit breaker open for {platform}")
        self.platform = platform
