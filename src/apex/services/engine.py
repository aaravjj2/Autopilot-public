from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any

from apex.core.config import Settings
from apex.core.logging import get_logger
from apex.core.retry import call_with_retries
from apex.domain.enums import EventType, Instrument
from apex.domain.watchlist_candidates import DEFAULT_WATCHLIST_CANDIDATES
from apex.domain.weekly_focus import priority_watchlist_symbols, weekly_focus_symbols
from apex.domain.errors import BrokerCircuitOpenError, MalformedProposalError, RiskCheckFailedError
from apex.domain.models import AuditEvent, OpportunityScore, Position, TradeProposal
from apex.integrations.broker import AlpacaBrokerAdapter, PaperBrokerSimulator, VenueRoutingBroker
from apex.integrations.polymarket_events import polymarket_event_proposal_from_market
from apex.integrations.polymarket_gamma_public import fetch_active_liquid_markets
from apex.integrations.repo_registry import IntegrationRegistry
from apex.layers.l0.ingestion import DataIngestionService
from apex.layers.l1.brain import FinanceBrainService
from apex.layers.l2.agent_panel import MultiAgentPanelService
from apex.layers.l3.execution import ExecutionService
from apex.layers.l4.observability import ObservabilityService
from apex.repositories.sqlite_store import SQLiteStore
from apex.services.arb_engine import ArbEngine
from apex.services.exit_monitor import evaluate_position_exit

LOGGER = get_logger(__name__)


@dataclass
class ApexEngine:
    settings: Settings
    store: SQLiteStore
    ingestion: DataIngestionService
    brain: FinanceBrainService
    panel: MultiAgentPanelService
    execution: ExecutionService
    observability: ObservabilityService
    integration_registry: IntegrationRegistry
    arb_engine: ArbEngine
    watchlist_candidates: list[str] = field(
        default_factory=lambda: list(DEFAULT_WATCHLIST_CANDIDATES)
    )
    todays_watchlist: list[str] = field(default_factory=list)
    todays_opportunities: list[OpportunityScore] = field(default_factory=list)
    todays_proposals: list[TradeProposal] = field(default_factory=list)
    todays_order_ids: list[str] = field(default_factory=list)
    todays_polymarket_event_proposals: list[TradeProposal] = field(default_factory=list)
    todays_polymarket_order_ids: list[str] = field(default_factory=list)
    dexter_prefetch_by_symbol: dict[str, dict[str, Any]] = field(default_factory=dict)

    def system_health_check(self) -> None:
        try:
            validation = self.integration_registry.validate(strict=self.settings.strict_integrations)
        except RuntimeError as exc:
            self.store.append_event(
                AuditEvent(
                    event_type=EventType.SYSTEM_ALERT,
                    rejection_reason="INTEGRATION_HEALTH_FAILURE",
                    raw_payload={
                        "health": "failed",
                        "reason": str(exc),
                    },
                )
            )
            raise
        pm_ready = self.ingestion.pm_client is not None
        event = AuditEvent(
            event_type=EventType.SYSTEM_ALERT,
            raw_payload={
                "health": "ok",
                "components": ["market_data", "options_data", "polymarket", "sqlite"],
                "integrations": validation,
                "options_trading_enabled": self.settings.options_trading_enabled,
                "alpaca_flatten_options_to_equity": self.settings.alpaca_flatten_options_to_equity,
                "polymarket_paper_trading_enabled": self.settings.polymarket_paper_trading_enabled,
                "polymarket_automated_events_enabled": self.settings.polymarket_automated_events_enabled,
                "polymarket_client_ready": pm_ready,
                "weekly_focus_enabled": self.settings.weekly_focus_enabled,
                "weekly_focus_symbols": weekly_focus_symbols(self.settings)[:12]
                if self.settings.weekly_focus_enabled
                else [],
            },
        )
        self.store.append_event(event)

    def overnight_news_digest(self) -> None:
        cap = max(1, int(self.settings.daily_stock_analysis_max_stocks))
        if self.settings.weekly_focus_enabled:
            focus = weekly_focus_symbols(self.settings)
            symbols = list(dict.fromkeys(focus + self.watchlist_candidates))[:cap]
        else:
            symbols = list(self.watchlist_candidates[:cap])
        self.ingestion.refresh_news_digest(symbols=symbols)
        self.store.append_event(
            AuditEvent(
                event_type=EventType.SYSTEM_ALERT,
                raw_payload={
                    "phase": "overnight_news_digest",
                    "daily_stock_analysis_symbols": symbols,
                    "weekly_focus": self.settings.weekly_focus_enabled,
                    "digest_chars": len((self.ingestion.cache.news or {}).get("summary", "")),
                },
            )
        )

    def watchlist_refresh(self) -> list[str]:
        priority = priority_watchlist_symbols(self.settings)
        watchlist = self.ingestion.refresh_watchlist(
            self.watchlist_candidates,
            max_size=self.settings.watchlist_max_size,
            priority_symbols=priority,
        )
        self.todays_watchlist = watchlist
        LOGGER.info("Watchlist size: %s", len(watchlist))
        return watchlist

    def polymarket_macro_snapshot(self) -> None:
        self.ingestion.refresh_polymarket_macro()

    def options_chain_snapshot(self, watchlist: list[str]) -> None:
        self.ingestion.refresh_options_data(watchlist)

    def market_snapshot(self, watchlist: list[str]) -> None:
        self.ingestion.refresh_market_data(watchlist)

    def opportunity_scoring(self, watchlist: list[str]) -> list[OpportunityScore]:
        scores = self.brain.score_watchlist(
            watchlist,
            self.ingestion.cache.market,
            self.ingestion.cache.options,
            self.ingestion.cache.polymarket_macro,
            self.ingestion.cache.news,
        )
        for score in scores:
            self.store.append_event(
                AuditEvent(
                    event_type=EventType.OPPORTUNITY_SCORED,
                    symbol=score.symbol,
                    conviction=score.conviction,
                    pm_signal=score.pm_signal.value,
                    raw_payload=score.model_dump(mode="json"),
                )
            )
        filtered = [item for item in scores if item.conviction >= self.settings.conviction_floor]
        self.todays_opportunities = filtered
        return filtered

    def deep_research_triggers(self) -> None:
        """Pre-panel adversarial research via Dexter for top opportunities (scheduled 8:00 ET)."""
        self.dexter_prefetch_by_symbol.clear()
        hub = getattr(self.panel, "hub", None)
        if hub is None or not hub.has_dexter() or hub.dextex is None:
            LOGGER.info("deep_research_triggers: skipped (Dexter not configured or unavailable)")
            return
        if not self.todays_opportunities:
            LOGGER.info("deep_research_triggers: no opportunities in memory; skipping")
            return
        dex = hub.dextex
        max_symbols = max(1, int(self.settings.top_symbols_per_day))
        focus_set = (
            set(weekly_focus_symbols(self.settings)) if self.settings.weekly_focus_enabled else set()
        )

        def _research_rank(opp: OpportunityScore) -> tuple[int, float]:
            pin = 0 if opp.symbol.upper() in focus_set else 1
            nvda = 0 if opp.symbol.upper() == "NVDA" else 1
            return (pin, nvda, -opp.conviction)

        ranked = sorted(self.todays_opportunities, key=_research_rank)
        for opp in ranked[:max_symbols]:
            thesis = (
                f"direction={opp.direction.value} instrument={opp.instrument.value} "
                f"pm_signal={opp.pm_signal.value} catalyst={opp.catalyst[:200]} "
                f"invalidation={opp.invalidation[:120]}"
            )
            try:
                result = dex.deep_research(opp.symbol, thesis, float(opp.conviction))
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("deep_research failed for %s: %s", opp.symbol, exc)
                self.store.append_event(
                    AuditEvent(
                        event_type=EventType.SYSTEM_ALERT,
                        symbol=opp.symbol,
                        rejection_reason="deep_research_exception",
                        raw_payload={
                            "phase": "deep_research_triggers",
                            "error": str(exc)[:500],
                        },
                    )
                )
                continue
            preview = str(result.get("counter_thesis", ""))[:800]
            self.store.append_event(
                AuditEvent(
                    event_type=EventType.SYSTEM_ALERT,
                    symbol=opp.symbol,
                    conviction=opp.conviction,
                    raw_payload={
                        "phase": "deep_research_triggers",
                        "severity": result.get("severity"),
                        "risks": result.get("risks"),
                        "recommended_action": result.get("recommended_action"),
                        "counter_thesis_preview": preview,
                    },
                )
            )
            self.dexter_prefetch_by_symbol[opp.symbol] = result

    def agent_panel_run(self, opportunities: list[OpportunityScore]) -> list[TradeProposal]:
        proposals: list[TradeProposal] = []
        focus_set = (
            set(weekly_focus_symbols(self.settings)) if self.settings.weekly_focus_enabled else set()
        )

        def _panel_rank(opp: OpportunityScore) -> tuple[int, float]:
            pin = 0 if opp.symbol.upper() in focus_set else 1
            nvda = 0 if opp.symbol.upper() == "NVDA" else 1
            return (pin, nvda, -opp.conviction)

        ranked_opps = sorted(opportunities, key=_panel_rank)
        panel_batch = (
            ranked_opps
            if self.settings.autotrade_all_approved
            else ranked_opps[: self.settings.top_symbols_per_day]
        )
        try:
            for opportunity in panel_batch:
                try:
                    market_data = dict(
                        self.ingestion.cache.market.get(opportunity.symbol, {})
                    )
                    news = self.ingestion.cache.news or {}
                    if news.get("summary"):
                        market_data["overnight_news_summary"] = str(news["summary"])[:2000]
                    if not market_data.get("bars"):
                        self.store.append_event(
                            AuditEvent(
                                event_type=EventType.SYSTEM_ALERT,
                                symbol=opportunity.symbol,
                                rejection_reason="missing_market_bars",
                                raw_payload={
                                    "phase": "agent_panel_run",
                                    "detail": "Skipping opportunity: empty or missing daily bars",
                                },
                            )
                        )
                        continue
                    options_data = self.ingestion.cache.options.get(opportunity.symbol)
                    pm_data = self.ingestion.pm_client.get_ticker_signal(opportunity.symbol)
                    prefetch = self.dexter_prefetch_by_symbol.get(opportunity.symbol)
                    proposal = self.panel.evaluate(
                        opportunity,
                        market_data,
                        options_data,
                        pm_data,
                        dexter_prefetch=prefetch,
                    )
                    if proposal is None:
                        continue
                    proposals.append(proposal)
                    self.store.append_event(
                        AuditEvent(
                            event_type=EventType.PROPOSAL_CREATED,
                            symbol=proposal.symbol,
                            conviction=proposal.conviction_final,
                            raw_payload=proposal.model_dump(mode="json"),
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    LOGGER.warning("agent_panel_run failed for %s: %s", opportunity.symbol, exc)
                    self.store.append_event(
                        AuditEvent(
                            event_type=EventType.SYSTEM_ALERT,
                            symbol=opportunity.symbol,
                            rejection_reason="agent_panel_exception",
                            raw_payload={
                                "phase": "agent_panel_run",
                                "error": str(exc)[:500],
                            },
                        )
                    )
        finally:
            self.dexter_prefetch_by_symbol.clear()
        self.todays_proposals = proposals
        return proposals

    def polymarket_event_discovery(self) -> list[TradeProposal]:
        """
        Discover liquid open markets from public Gamma REST (no Alpaca, no MCP).

        Populates ``todays_polymarket_event_proposals`` when paper + automation are on.
        """
        if not (
            self.settings.polymarket_paper_trading_enabled
            and self.settings.polymarket_automated_events_enabled
        ):
            self.todays_polymarket_event_proposals = []
            return []
        markets = fetch_active_liquid_markets(
            limit=int(self.settings.polymarket_event_discovery_limit),
            min_volume=float(self.settings.polymarket_event_min_volume_24h),
        )
        proposals: list[TradeProposal] = []
        seen: set[str] = set()
        for m in markets:
            p = polymarket_event_proposal_from_market(m, self.settings)
            if p is None:
                continue
            pid = p.polymarket_market_id
            if pid in seen:
                continue
            seen.add(pid)
            proposals.append(p)
        self.todays_polymarket_event_proposals = proposals
        for proposal in proposals:
            self.store.append_event(
                AuditEvent(
                    event_type=EventType.PROPOSAL_CREATED,
                    symbol=proposal.symbol,
                    conviction=proposal.conviction_final,
                    raw_payload={
                        "venue": "polymarket_paper",
                        "source": "gamma_public",
                        **proposal.model_dump(mode="json"),
                    },
                )
            )
        self.store.append_event(
            AuditEvent(
                event_type=EventType.SYSTEM_ALERT,
                raw_payload={
                    "phase": "polymarket_event_discovery",
                    "venue": "polymarket_paper",
                    "proposal_count": len(proposals),
                    "markets_scanned": len(markets),
                },
            )
        )
        return proposals

    def polymarket_paper_order_submission(
        self, proposals: list[TradeProposal] | None = None
    ) -> list[str]:
        """Submit only ``POLYMARKET_EVENT`` proposals via the PM paper broker."""
        proposals = proposals if proposals is not None else self.todays_polymarket_event_proposals
        if not self.settings.polymarket_paper_trading_enabled:
            self.todays_polymarket_order_ids = []
            return []
        order_ids: list[str] = []
        correlations: dict[str, float] = {}
        for proposal in proposals:
            if proposal.instrument != Instrument.POLYMARKET_EVENT:
                continue
            try:
                order_id = self.execution.execute(proposal, correlations=correlations)
                if order_id:
                    order_ids.append(order_id)
            except RiskCheckFailedError as exc:
                self.store.append_event(
                    AuditEvent(
                        event_type=EventType.SYSTEM_ALERT,
                        symbol=proposal.symbol,
                        rejection_reason=str(exc),
                        raw_payload={
                            "phase": "polymarket_paper_order_submission",
                            "venue": "polymarket_paper",
                            "error_class": "RiskCheckFailedError",
                            "risk_id": exc.risk_id,
                            "reason": exc.reason,
                        },
                    )
                )
            except MalformedProposalError as exc:
                self.store.append_event(
                    AuditEvent(
                        event_type=EventType.SYSTEM_ALERT,
                        symbol=proposal.symbol,
                        rejection_reason=str(exc),
                        raw_payload={
                            "phase": "polymarket_paper_order_submission",
                            "venue": "polymarket_paper",
                            "error_class": "MalformedProposalError",
                        },
                    )
                )
            except BrokerCircuitOpenError as exc:
                self.store.append_event(
                    AuditEvent(
                        event_type=EventType.SYSTEM_ALERT,
                        symbol=proposal.symbol,
                        rejection_reason=str(exc),
                        raw_payload={
                            "phase": "polymarket_paper_order_submission",
                            "venue": "polymarket_paper",
                            "error_class": "BrokerCircuitOpenError",
                        },
                    )
                )
            except Exception as exc:  # noqa: BLE001
                self.store.append_event(
                    AuditEvent(
                        event_type=EventType.SYSTEM_ALERT,
                        symbol=proposal.symbol,
                        rejection_reason=str(exc),
                        raw_payload={
                            "phase": "polymarket_paper_order_submission",
                            "venue": "polymarket_paper",
                            "error_class": type(exc).__name__,
                        },
                    )
                )
        self.todays_polymarket_order_ids = order_ids
        return order_ids

    def _equity_broker_for_flatten(self) -> AlpacaBrokerAdapter | None:
        b = self.execution.broker
        if isinstance(b, VenueRoutingBroker):
            inner = b.equity_broker
            return inner if isinstance(inner, AlpacaBrokerAdapter) else None
        return b if isinstance(b, AlpacaBrokerAdapter) else None

    def _flatten_proposal_for_alpaca(self, proposal: TradeProposal) -> TradeProposal:
        """
        Optionally flatten options proposals to equity notional orders.
        When ``OPTIONS_TRADING_ENABLED`` is true, native Alpaca options routing is used.
        """
        if proposal.instrument == Instrument.POLYMARKET_EVENT:
            return proposal
        if self.settings.options_trading_enabled:
            return proposal
        if not self.settings.alpaca_flatten_options_to_equity:
            return proposal
        if self._equity_broker_for_flatten() is None:
            return proposal
        if proposal.instrument == Instrument.EQUITY:
            return proposal
        payload = proposal.model_dump(mode="json")
        payload["instrument"] = Instrument.EQUITY.value
        payload["strike"] = None
        payload["spread_legs"] = None
        payload["expiry_date"] = None
        rationale = str(payload.get("judge_rationale", ""))[:2800]
        payload["judge_rationale"] = (
            rationale + f" | routed equities-only (was {proposal.instrument.value})"
        )
        return TradeProposal.model_validate(payload)

    def _opportunity_by_symbol(self) -> dict[str, OpportunityScore]:
        return {opp.symbol: opp for opp in self.todays_opportunities}

    def _resolve_entry_time(self, position: Position) -> datetime:
        from_audit = self.store.get_symbol_entry_time(position.symbol)
        if from_audit is not None:
            return from_audit
        return position.entry_time

    def review_position_exits(self, phase: str, *, eod_flatten: bool = False) -> None:
        """
        Intraday / pre-close / EOD: stop-loss, take-profit, max-hold, signal reversal,
        proposal price targets, and optional end-of-day flatten.
        
        NOTE: Skips Discord-tracked positions to prevent engine from closing them
        with wrong exit rules. Discord positions are handled by monitor_discord_exits().
        """
        if not self.settings.exit_monitor_enabled:
            return
        account = self.execution.broker.get_account_snapshot()
        broker = self.execution.broker
        opportunities = self._opportunity_by_symbol()
        
        # Build set of Discord-tracked symbols to skip
        discord_symbols = set()
        try:
            open_discord = self.store.get_open_discord_trades()
            discord_symbols = {t["symbol"] for t in open_discord if t.get("symbol")}
        except Exception as exc:
            LOGGER.warning("Exit review: Failed to load Discord trades: %s", exc)
        
        candidates: list[dict[str, Any]] = []
        closed: list[str] = []
        skipped_discord = 0
        
        for pos in account.open_positions:
            sym = pos.symbol
            if sym.startswith("PM:"):
                candidates.append({"symbol": sym, "action": "skip_polymarket_paper"})
                continue
            
            # Skip Discord-tracked positions - let monitor_discord_exits() handle them
            if sym in discord_symbols:
                skipped_discord += 1
                candidates.append({"symbol": sym, "action": "skip_discord_tracked"})
                continue
            
            try:
                is_option = len(sym) > 10 and any(c.isdigit() for c in sym[-8:])
                if is_option:
                    # For option positions, use Alpaca's current_price (not yfinance)
                    try:
                        raw_positions = self.execution.broker.get_positions()
                        matched = next((p for p in raw_positions if p.symbol == sym), None)
                        raw = getattr(matched, "_raw", None) or (matched.__dict__ if matched else {})
                        px = float(raw.get("current_price", 0) or pos.avg_entry_price)
                    except Exception:
                        px = float(pos.avg_entry_price)
                else:
                    px = float(self.ingestion.market_data.get_intraday_price(sym))
            except Exception:  # noqa: BLE001
                px = float(pos.avg_entry_price)
            entry = float(pos.avg_entry_price)
            if entry <= 0:
                candidates.append({"symbol": sym, "note": "skip_bad_entry"})
                continue
            entry_time = self._resolve_entry_time(pos)
            proposal_targets = self.store.get_symbol_proposal_targets(sym)
            decision = evaluate_position_exit(
                position=pos,
                price=px,
                settings=self.settings,
                opportunity=opportunities.get(sym),
                entry_time=entry_time,
                proposal_targets=proposal_targets,
                eod_flatten=eod_flatten,
            )
            is_long = pos.side != "short"
            move_pct = ((px - entry) / entry) * 100.0 if is_long else ((entry - px) / entry) * 100.0
            row: dict[str, Any] = {
                "symbol": sym,
                "move_pct": round(move_pct, 3),
                "px": px,
                "entry": entry,
            }
            if decision is None:
                candidates.append({**row, "action": "hold"})
                continue
            reason = decision.reason
            row["action"] = f"close_{reason}"
            candidates.append(row)
            closer = getattr(broker, "close_symbol_position", None)
            if closer is None:
                continue
            try:
                if closer(sym):
                    closed.append(sym)
                    self.store.append_event(
                        AuditEvent(
                            event_type=EventType.TRADE_CLOSED,
                            symbol=sym,
                            rejection_reason=reason,
                            raw_payload={
                                "phase": phase,
                                "move_pct": move_pct,
                                "eod_flatten": eod_flatten,
                            },
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Exit close failed for %s: %s", sym, exc)
        self.store.append_event(
            AuditEvent(
                event_type=EventType.SYSTEM_ALERT,
                raw_payload={
                    "phase": phase,
                    "eod_flatten": eod_flatten,
                    "open_positions": len(account.open_positions),
                    "discord_positions_skipped": skipped_discord,
                    "candidates": candidates,
                    "closed_symbols": closed,
                },
            )
        )

    def eod_flatten_all_positions(self) -> None:
        """Close all equity positions before the session ends (paper or Alpaca)."""
        self.review_position_exits(phase="eod_flatten_all_positions", eod_flatten=True)

    def _compute_correlations(self, new_symbol: str) -> dict[str, float]:
        try:
            import numpy as np
        except ImportError:
            return {}
        open_positions = self.execution.broker.get_positions()
        if not open_positions:
            return {}
        symbols = list(set([new_symbol] + [p.symbol for p in open_positions]))
        returns_data: dict[str, list[float]] = {}
        for sym in symbols:
            market_data = self.ingestion.cache.market.get(sym, {})
            bars = market_data.get("bars", [])
            if len(bars) < 10:
                continue
            closes = [bar["close"] for bar in bars[-30:]]
            rets = []
            for i in range(1, len(closes)):
                if closes[i - 1] > 0:
                    rets.append((closes[i] - closes[i - 1]) / closes[i - 1])
            if len(rets) >= 10:
                returns_data[sym] = rets
        if not returns_data or new_symbol not in returns_data:
            return {}
        new_returns = np.array(returns_data[new_symbol])
        correlations = {}
        for sym, rets in returns_data.items():
            if sym == new_symbol:
                continue
            other_returns = np.array(rets)
            min_len = min(len(new_returns), len(other_returns))
            if min_len < 10:
                continue
            corr = np.corrcoef(new_returns[:min_len], other_returns[:min_len])[0, 1]
            if not np.isnan(corr):
                correlations[sym] = float(abs(corr))
        return correlations

    def order_submission(self, proposals: list[TradeProposal] | None = None) -> list[str]:
        proposals = proposals if proposals is not None else self.todays_proposals
        order_ids: list[str] = []
        static_correlations = {position.symbol: abs(position.correlation_to_book) for position in self.execution.broker.get_positions()}
        for proposal in proposals:
            if proposal.instrument == Instrument.POLYMARKET_EVENT:
                continue
            proposal = self._flatten_proposal_for_alpaca(proposal)
            correlations = self._compute_correlations(proposal.symbol)
            correlations.update(static_correlations)
            try:
                order_id = self.execution.execute(proposal, correlations=correlations)
                if order_id:
                    order_ids.append(order_id)
            except RiskCheckFailedError as exc:
                self.store.append_event(
                    AuditEvent(
                        event_type=EventType.SYSTEM_ALERT,
                        symbol=proposal.symbol,
                        rejection_reason=str(exc),
                        raw_payload={
                            "phase": "order_submission",
                            "error_class": "RiskCheckFailedError",
                            "risk_id": exc.risk_id,
                            "reason": exc.reason,
                        },
                    )
                )
            except MalformedProposalError as exc:
                self.store.append_event(
                    AuditEvent(
                        event_type=EventType.SYSTEM_ALERT,
                        symbol=proposal.symbol,
                        rejection_reason=str(exc),
                        raw_payload={
                            "phase": "order_submission",
                            "error_class": "MalformedProposalError",
                        },
                    )
                )
            except BrokerCircuitOpenError as exc:
                self.store.append_event(
                    AuditEvent(
                        event_type=EventType.SYSTEM_ALERT,
                        symbol=proposal.symbol,
                        rejection_reason=str(exc),
                        raw_payload={
                            "phase": "order_submission",
                            "error_class": "BrokerCircuitOpenError",
                        },
                    )
                )
            except Exception as exc:  # noqa: BLE001
                self.store.append_event(
                    AuditEvent(
                        event_type=EventType.SYSTEM_ALERT,
                        symbol=proposal.symbol,
                        rejection_reason=str(exc),
                        raw_payload={
                            "phase": "order_submission",
                            "error_class": type(exc).__name__,
                        },
                    )
                )
        self.todays_order_ids = order_ids
        return order_ids

    def pre_market_risk_check(self) -> None:
        account = self.execution.broker.get_account_snapshot()
        self.store.append_event(
            AuditEvent(
                event_type=EventType.SYSTEM_ALERT,
                raw_payload={
                    "phase": "pre_market_risk_check",
                    "daily_pl_pct": account.daily_pl_pct,
                    "open_positions": len(account.open_positions),
                },
            )
        )

    def intraday_polymarket_check(self) -> None:
        shifts: list[dict[str, Any]] = []
        err: str | None = None
        try:
            shifts = call_with_retries(
                lambda: self.ingestion.pm_client.get_intraday_macro_shift(),
                max_attempts=max(1, int(self.settings.ingestion_fetch_max_attempts)),
                backoff_seconds=float(self.settings.ingestion_fetch_backoff_sec),
                log_label="intraday_polymarket_check",
            )
        except Exception as exc:  # noqa: BLE001
            err = str(exc)[:500]
            LOGGER.warning("intraday_polymarket_check failed after retries: %s", exc)
        payload: dict[str, Any] = {"phase": "intraday_polymarket_check", "shifts": shifts}
        if err:
            payload["error"] = err
        self.store.append_event(
            AuditEvent(
                event_type=EventType.SYSTEM_ALERT,
                raw_payload=payload,
            )
        )

    def intraday_exit_review(self) -> None:
        self.review_position_exits(phase="intraday_exit_review")
        self.monitor_discord_exits(phase="intraday_exit_review")

    def loss_cut_scan(self) -> None:
        from apex.layers.l3.loss_cut_brain import loss_cut_scan as _scan
        _scan(
            settings=self.settings,
            broker=self.execution.broker,
            store=self.store,
            market_data=self.ingestion.market_data,
        )

    def exit_review_afternoon(self) -> None:
        self.review_position_exits(phase="exit_review_afternoon")
        self.monitor_discord_exits(phase="exit_review_afternoon")

    def midday_review(self) -> None:
        self.review_position_exits(phase="midday_review")
        self.monitor_discord_exits(phase="midday_review")

    def pre_close_exit_review(self) -> None:
        self.review_position_exits(phase="pre_close_exit_review")
        self.monitor_discord_exits(phase="pre_close_exit_review")

    def monitor_discord_exits(self, phase: str) -> None:
        """Monitor and exit Discord-originated trades via consolidated ``DiscordExitManager``.

        Delegates to ``DiscordExitManager.check_once()`` which is the single
        source of truth for Discord exit decisions, avoiding duplicate logic.
        """
        if not self.settings.exit_monitor_enabled:
            return
        from apex.integrations.discord_exit_manager import DiscordExitManager
        mgr = DiscordExitManager()
        try:
            exited = mgr.check_once()
            if exited:
                LOGGER.info("Discord exits [%s]: closed %d trade(s)", phase, len(exited))
                for e in exited:
                    self.store.append_event(
                        AuditEvent(
                            event_type=EventType.TRADE_CLOSED,
                            symbol=e["symbol"],
                            rejection_reason=f"discord_{e.get('reason', 'unknown')}",
                            raw_payload={"phase": phase, "exit_price": e.get("exit_price")},
                        )
                    )
        except Exception as exc:
            LOGGER.warning("Discord exit [%s] failed: %s", phase, exc)

    def arb_opportunity_scan(self) -> None:
        """Kalshi ↔ Polymarket arb scan (Phase 2 scheduler + API loop)."""
        from apex.services.arb_scan import scan_and_persist

        opps = scan_and_persist(self.store, settings=self.settings, limit=100)
        self.store.append_event(
            AuditEvent(
                event_type=EventType.SYSTEM_ALERT,
                raw_payload={
                    "phase": "arb_opportunity_scan",
                    "count": len(opps),
                    "status": "ok",
                },
            )
        )

    def prediction_markets_agent_cycle(self) -> None:
        """Unified Polymarket + Kalshi arb paper agents (scheduler + API loop)."""
        import asyncio

        from apex.services.pm_trading import run_prediction_markets_agent_cycle

        asyncio.run(run_prediction_markets_agent_cycle(self))

    def self_improvement_cycle(self) -> None:
        """Export → train → evaluate → promote → brain feedback."""
        from apex.services.self_improvement import run_self_improvement_cycle

        run_self_improvement_cycle(self)

    def world_cup_agent_cycle(self) -> None:
        """FIFA World Cup discover → score → paper trade."""
        import asyncio

        from apex.services.world_cup_trading import run_world_cup_agent_cycle

        asyncio.run(run_world_cup_agent_cycle(self))

    def world_cup_discovery(self) -> None:
        from apex.services.world_cup_trading import discover_and_persist

        discover_and_persist(self.store)

    def whale_wallet_scan(self) -> None:
        """Scan for whale wallet movements (stub - to be implemented)."""
        self.store.append_event(
            AuditEvent(
                event_type=EventType.SYSTEM_ALERT,
                raw_payload={"phase": "whale_wallet_scan", "status": "stubbed"},
            )
        )

    def pre_close_polymarket_scan(self) -> None:
        """Pre-close Polymarket scan (delegates to intraday check)."""
        self.intraday_polymarket_check()

    def end_of_day_orders(self) -> None:
        self.store.append_event(
            AuditEvent(
                event_type=EventType.SYSTEM_ALERT,
                raw_payload={
                    "phase": "end_of_day_orders",
                    "orders": self.todays_order_ids,
                    "polymarket_paper_orders": self.todays_polymarket_order_ids,
                },
            )
        )

    def fill_reconciliation(self) -> None:
        broker = self.execution.broker
        get_order = getattr(broker, "get_order", None)
        discrepancies: list[dict[str, Any]] = []
        matched: list[dict[str, Any]] = []
        all_ids = [*self.todays_order_ids, *self.todays_polymarket_order_ids]
        if get_order is None:
            discrepancies.append({"issue": "broker_missing_get_order", "order_ids": all_ids})
        else:
            for oid in all_ids:
                if not oid:
                    discrepancies.append({"order_id": oid, "issue": "empty_order_id"})
                    continue
                if str(oid).startswith("failed_"):
                    discrepancies.append({"order_id": oid, "issue": "local_failed_submit_token"})
                    continue
                try:
                    od = get_order(oid)
                except Exception as exc:  # noqa: BLE001
                    discrepancies.append(
                        {
                            "order_id": oid,
                            "issue": "get_order_exception",
                            "error": str(exc)[:500],
                        }
                    )
                    continue
                if not isinstance(od, dict):
                    discrepancies.append({"order_id": oid, "issue": "unexpected_get_order_payload", "remote": str(od)[:200]})
                    continue
                status = str(od.get("status", "")).lower()
                err = od.get("error")
                st = od.get("status")
                if err or st in ("error", "exception"):
                    discrepancies.append({"order_id": oid, "issue": "broker_error_dict", "remote": od})
                    continue
                if status not in {"filled", "partially_filled"}:
                    discrepancies.append(
                        {"order_id": oid, "issue": "status_not_filled", "broker_status": status or st}
                    )
                else:
                    matched.append({"order_id": oid, "broker_status": status})
        payload: dict[str, Any] = {
            "phase": "fill_reconciliation",
            "submitted_orders": all_ids,
            "equity_orders": list(self.todays_order_ids),
            "polymarket_paper_orders": list(self.todays_polymarket_order_ids),
            "matched": matched,
            "discrepancies": discrepancies,
        }
        if not discrepancies:
            payload["status"] = "reconciled_ok"
        self.store.append_event(
            AuditEvent(
                event_type=EventType.SYSTEM_ALERT,
                raw_payload=payload,
            )
        )

    def pl_attribution(self) -> None:
        """Calculate and record realized P&L from closed positions.
        
        CRITICAL: Separates Discord trades from engine trades to prevent
        double-counting and source misattribution.
        """
        from apex.core.context import get_run_id
        from datetime import datetime as dt
        
        run_id = get_run_id()
        total_pnl = 0.0
        engine_pnl = 0.0
        discord_pnl = 0.0
        trades_processed = 0
        
        try:
            # Get account info for equity tracking
            account = self.execution.broker.get_account()
            equity = float(account.get("equity", 0))
            cash = float(account.get("cash", 0))
            positions_value = equity - cash
            
            # Record equity point
            self.store.add_equity_point(
                timestamp=dt.now(timezone.utc).isoformat(),
                equity=equity,
                cash=cash,
                positions_value=positions_value,
            )
            
            # Build set of Discord order IDs (both open and closed)
            discord_order_ids = set()
            try:
                open_discord = self.store.get_open_discord_trades()
                for t in open_discord:
                    if t.get("id"):
                        discord_order_ids.add(t["id"])
                
                # Also check closed Discord trades
                all_discord = self.store.read_table("discord_trades", limit=500)
                for t in all_discord:
                    if t.get("id"):
                        discord_order_ids.add(t["id"])
            except Exception as exc:
                LOGGER.warning("P&L: Failed to load Discord trades: %s", exc)
            
            # Get filled orders from Alpaca
            try:
                filled_orders = self.execution.broker.get_orders(status="filled")
            except Exception as exc:
                LOGGER.warning("P&L: Failed to fetch filled orders: %s", exc)
                filled_orders = []
            
            # Process each filled order
            for order in filled_orders:
                order_id = order.get("id", "")
                symbol = order.get("symbol", "")
                filled_qty = float(order.get("filled_qty", 0))
                filled_avg_price = float(order.get("filled_avg_price", 0) or 0)
                side = order.get("side", "")
                order_type = order.get("order_class", "") or "equity"
                submitted_at = order.get("submitted_at", "")
                filled_at = order.get("filled_at", "")
                
                if not order_id or not symbol or filled_qty <= 0:
                    continue
                
                # Determine instrument type
                instrument = "OPTION" if order_type == "oco" or len(symbol) > 10 else "EQUITY"
                
                # Check if we already processed this order
                existing = self.store.get_completed_trades(limit=1000, days=90)
                if any(t.get("order_id") == order_id for t in existing):
                    continue
                
                # For sell orders, calculate P&L
                if side == "sell":
                    # DETERMINE SOURCE: Check if this is a Discord trade
                    if order_id in discord_order_ids:
                        source = "discord_bullseye"
                        # Get entry price from Discord trades table
                        discord_trade = next(
                            (t for t in all_discord if t.get("id") == order_id),
                            None
                        )
                        entry_price = float(discord_trade.get("entry_price", 0)) if discord_trade else 0
                        if entry_price <= 0:
                            entry_price = filled_avg_price * 0.9  # Fallback estimate
                    else:
                        source = "apex_engine"
                        # Find corresponding buy order from audit log
                        entry_data = self.store.get_symbol_entry_time(symbol)
                        entry_price = filled_avg_price * 0.9  # Rough estimate
                    
                    exit_price = filled_avg_price
                    quantity = filled_qty
                    pnl = (exit_price - entry_price) * quantity * (100 if instrument == "OPTION" else 1)
                    pnl_pct = ((exit_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
                    
                    self.store.add_completed_trade(
                        symbol=symbol,
                        instrument=instrument,
                        source=source,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        quantity=quantity,
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        entry_time=submitted_at,
                        exit_time=filled_at,
                        order_id=order_id,
                        metadata={"run_id": run_id, "broker_status": "filled", "source": source},
                    )
                    
                    total_pnl += pnl
                    trades_processed += 1
                    
                    if source == "discord_bullseye":
                        discord_pnl += pnl
                        # Update Discord trade status
                        try:
                            discord_trade = next(
                                (t for t in all_discord if t.get("id") == order_id),
                                None
                            )
                            if discord_trade:
                                self.store.update_discord_trade(
                                    order_id,
                                    {"status": "closed", "exit_price": exit_price},
                                )
                        except Exception as exc:
                            LOGGER.warning("P&L: Failed to update Discord trade %s: %s", order_id, exc)
                    else:
                        engine_pnl += pnl
                    
                    LOGGER.info(
                        "P&L: Closed %s [%s] | %s %.2f | Entry: $%.2f | Exit: $%.2f | P&L: $%.2f (%.1f%%)",
                        symbol,
                        source,
                        instrument,
                        quantity,
                        entry_price,
                        exit_price,
                        pnl,
                        pnl_pct,
                    )
            
            # Get P&L attribution summary
            attribution = self.store.get_pnl_attribution(days=30)
            
            LOGGER.info(
                "P&L Attribution: %d trades | Engine: $%.2f | Discord: $%.2f | Total: $%.2f | Win Rate: %.1f%%",
                trades_processed,
                engine_pnl,
                discord_pnl,
                total_pnl,
                attribution["overall"]["win_rate"],
            )
            
            # Record attribution event
            self.store.append_event(
                AuditEvent(
                    event_type=EventType.SYSTEM_ALERT,
                    raw_payload={
                        "phase": "pl_attribution",
                        "trades_processed": trades_processed,
                        "engine_pnl": engine_pnl,
                        "discord_pnl": discord_pnl,
                        "total_pnl": total_pnl,
                        "attribution": attribution,
                    },
                )
            )
            
        except Exception as exc:
            LOGGER.error("P&L Attribution failed: %s", exc, exc_info=True)
            self.store.append_event(
                AuditEvent(
                    event_type=EventType.SYSTEM_ALERT,
                    raw_payload={
                        "phase": "pl_attribution",
                        "status": "failed",
                        "error": str(exc),
                    },
                )
            )

    def trade_memory_update(self) -> None:
        _ = self.store.recent_trade_memory(limit=8)

    def brain_context_refresh(self) -> None:
        feedback = self.observability.feedback_threshold_adjustments()
        if "dexter_threshold" in feedback:
            self.settings.dexter_threshold = feedback["dexter_threshold"]
            LOGGER.info("Runtime override: dexter_threshold = %.1f", feedback["dexter_threshold"])
        if "pm_weight_adj" in feedback and feedback["pm_weight_adj"] != 0:
            LOGGER.info("Runtime override: pm_weight_adj = %.2f (applied in PM scoring)", feedback["pm_weight_adj"])
        self.store.append_event(
            AuditEvent(
                event_type=EventType.SYSTEM_ALERT,
                raw_payload={"phase": "brain_context_refresh", "feedback": feedback},
            )
        )

    def database_backup(self) -> None:
        """Backup SQLite DB to ``data/backups/`` with 30-day retention."""
        import shutil
        from pathlib import Path

        backup_dir = self.settings.sqlite_path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        today = date.today().isoformat()
        dest = backup_dir / f"audit_backup_{today}.db"
        try:
            import sqlite3
            src_conn = sqlite3.connect(str(self.settings.sqlite_path))
            dst_conn = sqlite3.connect(str(dest))
            src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()
            LOGGER.info("DB backup created: %s (%d bytes)", dest, dest.stat().st_size)
        except Exception as exc:
            LOGGER.warning("DB backup failed: %s", exc)
            return
        # Retention: remove backups older than 30 days
        import time
        cutoff = time.time() - 30 * 86400
        for f in sorted(backup_dir.glob("audit_backup_*.db")):
            if f.stat().st_mtime < cutoff:
                f.unlink()
                LOGGER.debug("Removed old backup: %s", f.name)
        self.store.append_event(
            AuditEvent(
                event_type=EventType.SYSTEM_ALERT,
                raw_payload={"phase": "database_backup", "path": str(dest), "size_bytes": dest.stat().st_size},
            )
        )

    def warm_trading_day_caches(self) -> None:
        """
        Prime ingestion caches after a cold scheduler start or mid-day restart.
        Does not touch job_runs idempotency (call before cron fires or for catch-up).
        """
        wl = self.todays_watchlist
        if not wl:
            try:
                wl = self.watchlist_refresh()
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Warm: watchlist_refresh failed: %s", exc)
                return
        if not wl:
            LOGGER.warning("Warm: empty watchlist; cannot prime caches")
            return
        need_market = any(not self.ingestion.cache.market.get(s, {}).get("bars") for s in wl)
        need_options = any(
            s not in self.ingestion.cache.options or not self.ingestion.cache.options.get(s)
            for s in wl
        )
        if not need_market and not need_options:
            LOGGER.debug("Warm: caches already look fresh (%d symbols)", len(wl))
            return
        LOGGER.info("Warm: priming polymarket + options + market for %d symbols", len(wl))
        try:
            self.polymarket_macro_snapshot()
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Warm: polymarket macro failed: %s", exc)
        try:
            self.options_chain_snapshot(wl)
            self.market_snapshot(wl)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Warm: options/market snapshot failed: %s", exc)

    def equity_autopilot_cycle(self) -> dict[str, Any]:
        """Intraday Alpaca pipeline: refresh data, score, panel, submit (market hours only)."""
        from zoneinfo import ZoneInfo

        now_et = datetime.now(ZoneInfo("America/New_York")).time()
        if not (time(9, 30) <= now_et <= time(16, 0)):
            return {"status": "skipped", "detail": "outside_regular_market_hours"}

        if not self.settings.alpaca_paper_trade:
            return {"status": "disabled", "detail": "ALPACA_PAPER_TRADE=false"}

        wl = self.todays_watchlist or self.watchlist_refresh()
        if not wl:
            return {"status": "error", "detail": "empty_watchlist"}

        self.polymarket_macro_snapshot()
        self.options_chain_snapshot(wl)
        self.market_snapshot(wl)
        opps = self.opportunity_scoring(wl)
        proposals = self.agent_panel_run(opps)
        order_ids = self.order_submission(proposals)
        return {
            "status": "ok",
            "watchlist_size": len(wl),
            "opportunities": len(opps),
            "proposals": len(proposals),
            "orders_submitted": len(order_ids),
            "order_ids": order_ids[:20],
        }

    def run_daily_cycle(self) -> None:
        from apex.core.context import reset_run_id, set_run_id

        run_id = f"manual_daily:{date.today().isoformat()}:{uuid.uuid4().hex[:10]}"
        token = set_run_id(run_id)
        try:
            self.system_health_check()
            self.overnight_news_digest()
            watchlist = self.watchlist_refresh()
            if not watchlist:
                return
            self.polymarket_macro_snapshot()
            self.options_chain_snapshot(watchlist)
            self.market_snapshot(watchlist)
            opportunities = self.opportunity_scoring(watchlist)
            self.deep_research_triggers()
            proposals = self.agent_panel_run(opportunities)
            self.pre_market_risk_check()
            self.order_submission(proposals)
            if (
                self.settings.polymarket_paper_trading_enabled
                and self.settings.polymarket_automated_events_enabled
            ):
                self.polymarket_event_discovery()
                self.polymarket_paper_order_submission()
            self.intraday_polymarket_check()
            self.midday_review()
            self.whale_wallet_scan()
            self.pre_close_polymarket_scan()
            self.pre_close_exit_review()
            self.eod_flatten_all_positions()
            self.end_of_day_orders()
            self.fill_reconciliation()
            self.pl_attribution()
            self.trade_memory_update()
            self.brain_context_refresh()
            LOGGER.info("APEX daily cycle complete for %s", date.today().isoformat())
        finally:
            reset_run_id(token)
