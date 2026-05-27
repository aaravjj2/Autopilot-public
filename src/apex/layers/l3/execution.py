from __future__ import annotations

from dataclasses import dataclass

import asyncio

from apex.core.config import Settings
from apex.core.logging import get_logger
from apex.core.retry import call_with_retries
from apex.domain.contracts import BrokerClient
from apex.domain.enums import EventType, Instrument
from apex.domain.errors import MalformedProposalError, RiskCheckFailedError
from apex.domain.models import AuditEvent, TradeProposal, ArbOpportunity, ArbThesis
from apex.integrations.broker import VenueRoutingBroker
from apex.integrations.kalshi_trading import kalshi_execution_venue
from apex.layers.l3.risk_checks import RiskCheckEngine
from apex.repositories.sqlite_store import SQLiteStore

LOGGER = get_logger(__name__)


def fast_fill_peek(fill_broker: BrokerClient, order_id: str, settings: Settings) -> tuple[bool, str]:
    """Quick peek at order status right after submit (catches fast fills).

    First tries Alpaca WebSocket trade updates for near-instant confirmation
    (P2.7), then falls back to REST polling via ``monitor_fill``.
    """
    from apex.core.retry import call_with_retries

    # Try WebSocket fill confirmation first (P2.7)
    try:
        from apex.integrations.alpaca_adapter import AlpacaStreamClient

        ws = AlpacaStreamClient()
        if ws.available:
            fill_msg = ws.wait_for_fill(order_id, timeout=10.0)
            ws.stop()
            if fill_msg:
                order_data = fill_msg.get("order", {}) or {}
                status = str(order_data.get("status", "")).lower()
                if status in {"filled", "partially_filled"}:
                    return True, f"filled:ws_{status}"
                if status in {"canceled", "cancelled", "expired", "rejected"}:
                    return False, f"ws_{status}"
    except Exception:
        pass

    try:
        early = fill_broker.get_order(order_id)
        early_status = str(early.get("status", "")).lower()
        if early_status in {"filled", "partially_filled"}:
            return True, f"filled:{early_status}"
        if early_status in {"canceled", "cancelled", "expired", "rejected", "failed"}:
            return False, early_status or "bad_terminal"
    except Exception:
        pass
    try:
        return call_with_retries(
            lambda: fill_broker.monitor_fill(order_id, timeout_seconds=300),
            max_attempts=settings.broker_monitor_fill_max_attempts,
            backoff_seconds=settings.broker_submit_backoff_sec,
            log_label=f"monitor_fill:{order_id}",
        )
    except Exception as exc:
        LOGGER.warning("fast_fill_peek: monitor_fill failed for %s: %s", order_id, exc)
        return False, str(exc)


@dataclass
class ExecutionService:
    broker: BrokerClient
    risk_engine: RiskCheckEngine
    store: SQLiteStore
    settings: Settings

    def execute(self, proposal: TradeProposal, correlations: dict[str, float] | None = None) -> str | None:
        if proposal is None:
            raise MalformedProposalError("TradeProposal is null")

        active_fn = getattr(self.broker, "active_broker", None)
        active = active_fn(proposal) if callable(active_fn) else self.broker
        account = active.get_account_snapshot()
        preview_ok, preview_reason = active.preview_order(proposal)
        if proposal.instrument == Instrument.POLYMARKET_EVENT:
            risk_results = self.risk_engine.run_polymarket_paper(
                proposal=proposal,
                account=account,
                preview_passed=preview_ok,
                preview_reason=preview_reason,
            )
        else:
            risk_results = self.risk_engine.run_all(
                proposal=proposal,
                account=account,
                correlated_symbols=correlations,
                preview_passed=preview_ok,
                preview_reason=preview_reason,
            )
        for result in risk_results:
            if not result.passed:
                self.store.append_event(
                    AuditEvent(
                        event_type=EventType.RISK_REJECTED,
                        symbol=proposal.symbol,
                        conviction=proposal.conviction_final,
                        risk_check=result.risk_id,
                        rejection_reason=result.reason,
                        raw_payload={"proposal": proposal.model_dump(mode="json"), "risk_action": result.action.value},
                    )
                )
                if result.risk_id == "R01":
                    self.store.append_event(
                        AuditEvent(
                            event_type=EventType.SYSTEM_ALERT,
                            symbol=proposal.symbol,
                            rejection_reason="CRITICAL_SECURITY_VIOLATION",
                            raw_payload={"reason": result.reason},
                        )
                    )
                raise RiskCheckFailedError(result.risk_id, result.reason)

        submit_broker = (
            self.broker if isinstance(self.broker, VenueRoutingBroker) else active
        )
        order_id = call_with_retries(
            lambda: submit_broker.submit_order(proposal),
            max_attempts=self.settings.broker_submit_max_attempts,
            backoff_seconds=self.settings.broker_submit_backoff_sec,
            log_label=f"submit_order:{proposal.symbol}",
        )
        self.store.append_event(
            AuditEvent(
                event_type=EventType.ORDER_SUBMITTED,
                symbol=proposal.symbol,
                order_id=order_id,
                conviction=proposal.conviction_final,
                pm_signal=proposal.direction.value,
                raw_payload={"proposal": proposal.model_dump(mode="json")},
            )
        )

        fill_broker = (
            self.broker if isinstance(self.broker, VenueRoutingBroker) else active
        )
        filled, fill_reason = fast_fill_peek(fill_broker, order_id, self.settings)
        if not filled:
            fill_broker.cancel_order(order_id)
            self.store.append_event(
                AuditEvent(
                    event_type=EventType.ORDER_CANCELLED,
                    symbol=proposal.symbol,
                    order_id=order_id,
                    rejection_reason=fill_reason,
                    raw_payload={"reason": fill_reason},
                )
            )
            return None

        fill_payload: dict = {"message": fill_reason}
        if proposal.instrument == Instrument.POLYMARKET_EVENT:
            fill_payload.update(
                {
                    "venue": "polymarket_paper",
                    "polymarket_market_id": proposal.polymarket_market_id,
                    "polymarket_outcome_side": proposal.polymarket_outcome_side,
                    "polymarket_stake_usd": proposal.polymarket_stake_usd,
                    "polymarket_question": proposal.symbol,
                    "entry_price": proposal.entry_price,
                }
            )
        self.store.append_event(
            AuditEvent(
                event_type=EventType.ORDER_FILLED,
                symbol=proposal.symbol,
                order_id=order_id,
                raw_payload=fill_payload,
            )
        )
        LOGGER.info("Order filled: %s for %s", order_id, proposal.symbol)
        return order_id

    def _compute_kelly_stake(self, opp: ArbOpportunity, thesis: ArbThesis | None) -> float:
        conf_str = thesis.confidence if thesis else "MEDIUM"
        conf_map = {"HIGH": 0.8, "MEDIUM": 0.5, "LOW": 0.2}
        conf_float = conf_map.get(conf_str, 0.5)
        
        edge = opp.net_edge
        if edge <= 0:
            return 10.0
        if edge >= 0.99:
            edge = 0.99
            
        kelly_fraction = (edge * conf_float) / (1.0 - edge)
        
        max_bankroll = self.settings.polymarket_paper_bankroll_usd
        max_stake = max_bankroll * 0.05
        
        stake = kelly_fraction * max_bankroll
        stake = max(10.0, min(stake, max_stake))
        
        LOGGER.info("Kelly sizing for %s: edge=%.3f conf=%.1f fraction=%.3f -> stake=$%.2f", 
                   opp.id, edge, conf_float, kelly_fraction, stake)
        return stake

    async def submit_arb_paper_orders(
        self,
        opp: ArbOpportunity,
        thesis: ArbThesis | None = None,
    ) -> tuple[str | None, str | None]:
        """
        Submit both arb legs atomically. If either leg fails, cancel the other.
        Returns (kalshi_order_id, poly_order_id) or (None, None) on failure.
        """
        stake_usd = self._compute_kelly_stake(opp, thesis)
        
        risk = self.risk_engine.run_arb_paper(opp, stake_usd)
        if not risk.all_passed:
            LOGGER.warning(
                "Arb risk check FAILED for %s: %s", opp.id, risk.rejection_reason
            )
            self.store.append_event(AuditEvent(
                event_type=EventType.ARB_RISK_FAILED,
                rejection_reason=risk.rejection_reason,
                raw_payload={"arb_id": opp.id, "checks": risk.failed},
            ))
            return None, None

        self.store.append_event(AuditEvent(
            event_type=EventType.ARB_RISK_PASSED,
            raw_payload={"arb_id": opp.id, "checks": risk.passed},
        ))

        from apex.execution.state_machine import ArbExecutionStateMachine

        sm = ArbExecutionStateMachine(opp.id)
        sm._fire("submit_leg1")

        submit_kalshi = getattr(self.broker, "submit_kalshi_paper", None)
        submit_poly = getattr(self.broker, "submit_polymarket_paper", None)
        if not callable(submit_kalshi) or not callable(submit_poly):
            LOGGER.error("Broker missing submit_kalshi_paper / submit_polymarket_paper for arb %s", opp.id)
            sm._fire("timeout")
            return None, None

        try:
            kalshi_order_id = await submit_kalshi(
                ticker=opp.kalshi_ticker,
                stake_usd=stake_usd,
                price=opp.kalshi_yes_ask,
            )
        except Exception as e:
            LOGGER.error("Kalshi paper leg failed for %s: %s", opp.id, e)
            sm._fire("timeout")
            return None, None

        sm.ctx.leg1_order_id = kalshi_order_id
        sm._fire("fill_leg1")
        sm._fire("route_dex")
        sm._fire("submit_leg2")
        LOGGER.info("Kalshi paper leg submitted: %s (%.3f YES)", kalshi_order_id, opp.kalshi_yes_ask)

        try:
            poly_order_id = await submit_poly(
                market_id=opp.poly_market_id,
                outcome="NO",
                stake_usd=stake_usd,
                price=opp.poly_no_ask,
            )
        except Exception as e:
            LOGGER.error("Poly paper leg failed for %s: %s — scratching leg1", opp.id, e)
            from apex.execution.scratch import submit_scratch_close

            submit_scratch_close(opp.kalshi_ticker)
            sm.scratch_leg1()
            self.store.append_event(AuditEvent(
                event_type=EventType.SYSTEM_ALERT,
                symbol=opp.id,
                rejection_reason="POLY_LEG_FAILED",
                raw_payload={"arb_id": opp.id, "error": str(e), "sm_state": sm.state},
            ))
            return None, None

        # Write both legs to SQLite
        try:
            self.store.save_arb_opportunities([opp])
        except Exception as e:
            LOGGER.warning("Failed to save arb opportunity to store: %s", e)

        loop = asyncio.get_running_loop()
        poly_filled, _ = await loop.run_in_executor(
            None, fast_fill_peek, self.broker, poly_order_id, self.settings
        )
        kalshi_broker = (
            getattr(self.broker, "kalshi_paper", None)
            if hasattr(self.broker, "kalshi_paper")
            else self.broker
        )
        kalshi_filled, _ = await loop.run_in_executor(
            None,
            (kalshi_broker or self.broker).monitor_fill,
            kalshi_order_id,
            30,
        )

        if poly_filled and not kalshi_filled:
            LOGGER.critical("LEG IMBALANCE: Kalshi leg failed after Poly leg %s filled.", poly_order_id)
            from apex.execution.scratch import submit_scratch_close
            from apex.observability.alerts import alert_leg_imbalance

            submit_scratch_close(opp.kalshi_ticker)
            sm.scratch_leg1()
            alert_leg_imbalance(opp.id, poly_order_id, kalshi_order_id)
            self.store.append_event(AuditEvent(
                event_type=EventType.SYSTEM_ALERT,
                symbol=opp.id,
                rejection_reason="LEG_IMBALANCE",
                raw_payload={
                    "poly_order_id": poly_order_id,
                    "kalshi_order_id": kalshi_order_id,
                    "sm_state": sm.state,
                },
            ))
            pm_symbol = f"PM:{opp.poly_market_id}|NO"
            try:
                if hasattr(self.broker, "close_symbol_position"):
                    self.broker.close_symbol_position(pm_symbol)
            except Exception as e:
                LOGGER.error("Failed to market-sell Polymarket leg %s: %s", pm_symbol, e)
            return None, None

        sm.ctx.leg2_tx_hash = poly_order_id
        sm._fire("fill_leg2")
        stake = stake_usd
        kalshi_venue = kalshi_execution_venue(self.settings)
        self.store.append_event(
            AuditEvent(
                event_type=EventType.ORDER_FILLED,
                symbol=opp.kalshi_ticker,
                order_id=kalshi_order_id,
                raw_payload={
                    "venue": kalshi_venue,
                    "arb_id": opp.id,
                    "kalshi_ticker": opp.kalshi_ticker,
                    "kalshi_order_id": kalshi_order_id,
                    "stake_usd": stake,
                    "entry_price": opp.kalshi_yes_ask,
                    "kalshi_yes_ask": opp.kalshi_yes_ask,
                    "question": opp.question,
                },
            )
        )
        self.store.append_event(
            AuditEvent(
                event_type=EventType.ORDER_FILLED,
                symbol=f"PM:{opp.poly_market_id}",
                order_id=poly_order_id,
                raw_payload={
                    "venue": "polymarket_paper",
                    "arb_id": opp.id,
                    "polymarket_market_id": opp.poly_market_id,
                    "polymarket_outcome_side": "NO",
                    "poly_order_id": poly_order_id,
                    "polymarket_stake_usd": stake,
                    "polymarket_question": opp.question,
                    "entry_price": opp.poly_no_ask,
                },
            )
        )
        self.store.append_event(
            AuditEvent(
                event_type=EventType.ARB_PAPER_SUBMITTED,
                symbol=opp.kalshi_ticker,
                order_id=kalshi_order_id,
                raw_payload={
                    "venue": kalshi_venue,
                    "arb_id": opp.id,
                    "kalshi_ticker": opp.kalshi_ticker,
                    "kalshi_order_id": kalshi_order_id,
                    "kalshi_stake_usd": stake,
                    "entry_price": opp.kalshi_yes_ask,
                    "question": opp.question,
                    "poly_order_id": poly_order_id,
                    "sm_state": sm.state,
                },
            )
        )
        LOGGER.info("Arb paper order complete: %s | %s state=%s", kalshi_order_id, poly_order_id, sm.state)
        return kalshi_order_id, poly_order_id

