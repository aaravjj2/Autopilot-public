from __future__ import annotations


class ApexError(Exception):
    """Base APEX exception."""


class MalformedProposalError(ApexError):
    """Raised when a trade proposal fails schema validation."""


class RiskCheckFailedError(ApexError):
    """Raised when any risk check fails."""

    def __init__(self, risk_id: str, reason: str) -> None:
        super().__init__(f"{risk_id}: {reason}")
        self.risk_id = risk_id
        self.reason = reason


class BrokerCircuitOpenError(ApexError):
    """Raised when broker circuit breaker is open (too many recent failures)."""

    def __init__(self, platform: str = "alpaca") -> None:
        super().__init__(f"Circuit breaker open for {platform}")
        self.platform = platform
