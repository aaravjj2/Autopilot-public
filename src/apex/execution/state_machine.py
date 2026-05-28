"""Arb execution state machine (Week 7)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

LOGGER = logging.getLogger(__name__)

try:
    from transitions import Machine

    HAS_TRANSITIONS = True
except ImportError:
    HAS_TRANSITIONS = False
    Machine = None  # type: ignore


class ArbExecState(str, Enum):
    PREDICTIVE_ENTRY = "predictive_entry"
    LEG_1_PENDING = "leg_1_pending"
    LEG_1_FILLED = "leg_1_filled"
    ROUTE_TO_DEX = "route_to_dex"
    LEG_2_PENDING = "leg_2_pending"
    FULLY_HEDGED = "fully_hedged"
    MEV_ATTACK_DETECTED = "mev_attack_detected"
    TRADFI_HEDGE_TRIGGER = "tradfi_hedge_trigger"
    TRADFI_HEDGE_FILLED = "tradfi_hedge_filled"
    TIMEOUT_ABORT = "timeout_abort"


@dataclass
class ArbExecutionContext:
    arb_id: str
    state: str = ArbExecState.PREDICTIVE_ENTRY.value
    leg1_order_id: str | None = None
    leg2_tx_hash: str | None = None
    hedge_ticker: str = "SPY"
    history: list[dict[str, Any]] = field(default_factory=list)
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def log(self, event: str, **payload: Any) -> None:
        self.history.append(
            {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **payload}
        )
        self.updated_at = datetime.now(timezone.utc).isoformat()


def _build_machine(ctx: ArbExecutionContext):
    if not HAS_TRANSITIONS:
        return None
    states = [s.value for s in ArbExecState]
    transitions = [
        {"trigger": "submit_leg1", "source": "predictive_entry", "dest": "leg_1_pending"},
        {"trigger": "fill_leg1", "source": "leg_1_pending", "dest": "leg_1_filled"},
        {"trigger": "timeout", "source": "leg_1_pending", "dest": "timeout_abort"},
        {"trigger": "route_dex", "source": "leg_1_filled", "dest": "route_to_dex"},
        {"trigger": "submit_leg2", "source": "route_to_dex", "dest": "leg_2_pending"},
        {"trigger": "fill_leg2", "source": "leg_2_pending", "dest": "fully_hedged"},
        {"trigger": "mev_detected", "source": "leg_2_pending", "dest": "mev_attack_detected"},
        {
            "trigger": "hedge_tradfi",
            "source": "mev_attack_detected",
            "dest": "tradfi_hedge_trigger",
        },
        {
            "trigger": "fill_hedge",
            "source": "tradfi_hedge_trigger",
            "dest": "tradfi_hedge_filled",
        },
    ]
    return Machine(
        model=ctx,
        states=states,
        transitions=transitions,
        initial=ctx.state,
        model_attribute="state",
        ignore_invalid_triggers=False,
    )


class ArbExecutionStateMachine:
    """Dual-leg arb execution with fallback paths."""

    def __init__(self, arb_id: str):
        self.ctx = ArbExecutionContext(arb_id=arb_id)
        self._machine = _build_machine(self.ctx)

    @property
    def state(self) -> str:
        return self.ctx.state

    def _fire(self, trigger: str, **kwargs: Any) -> bool:
        if self._machine is None:
            return self._manual_transition(trigger, **kwargs)
        try:
            # Triggers are bound to the model (ctx), not the Machine instance
            getattr(self.ctx, trigger)(**kwargs)
            self.ctx.log(trigger, state=self.ctx.state)
            return True
        except Exception as exc:
            LOGGER.warning("SM trigger %s failed: %s", trigger, exc)
            return False

    def _manual_transition(self, trigger: str, **kwargs: Any) -> bool:
        mapping = {
            "submit_leg1": ArbExecState.LEG_1_PENDING,
            "fill_leg1": ArbExecState.LEG_1_FILLED,
            "timeout": ArbExecState.TIMEOUT_ABORT,
            "route_dex": ArbExecState.ROUTE_TO_DEX,
            "submit_leg2": ArbExecState.LEG_2_PENDING,
            "fill_leg2": ArbExecState.FULLY_HEDGED,
            "mev_detected": ArbExecState.MEV_ATTACK_DETECTED,
            "hedge_tradfi": ArbExecState.TRADFI_HEDGE_TRIGGER,
            "fill_hedge": ArbExecState.TRADFI_HEDGE_FILLED,
        }
        if trigger not in mapping:
            return False
        self.ctx.state = mapping[trigger].value
        self.ctx.log(trigger, state=self.ctx.state, **kwargs)
        return True

    def run_paper_flow(
        self,
        *,
        leg1_fill: Callable[[], str],
        leg2_fill: Callable[[], str],
        simulate_mev: bool = False,
    ) -> ArbExecutionContext:
        self._fire("submit_leg1")
        self.ctx.leg1_order_id = leg1_fill()
        self._fire("fill_leg1")
        self._fire("route_dex")
        self._fire("submit_leg2")
        if simulate_mev:
            self._fire("mev_detected")
            self._fire("hedge_tradfi")
            self._fire("fill_hedge")
            return self.ctx
        self.ctx.leg2_tx_hash = leg2_fill()
        self._fire("fill_leg2")
        return self.ctx

    def scratch_leg1(self) -> dict[str, Any]:
        """Auto-reversal (Week 7 Day 2)."""
        self.ctx.log("scratch_leg1", order_id=self.ctx.leg1_order_id)
        return {"status": "scratch_submitted", "order_id": self.ctx.leg1_order_id}
