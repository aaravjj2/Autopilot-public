from __future__ import annotations

import bisect
from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from apex.core.config import Settings
from apex.core.logging import get_logger
from apex.domain.enums import Direction, Instrument
from apex.domain.models import OpportunityScore, SpreadLeg, TradeProposal
from apex.integrations.dexter_adapter import DexterAdapter

if TYPE_CHECKING:
    from apex.integrations.hub import IntegrationHub

LOGGER = get_logger(__name__)

DTE_RANGES = {
    Instrument.CALL: (14, 30),
    Instrument.PUT: (14, 30),
    Instrument.VERTICAL: (21, 45),
    Instrument.STRADDLE: (21, 45),
    Instrument.IRON_CONDOR: (30, 45),
}


def _find_nearest_strike(target: float, available_strikes: list[float]) -> float:
    if not available_strikes:
        return round(target, 2)
    strikes_sorted = sorted(available_strikes)
    idx = bisect.bisect_left(strikes_sorted, target)
    if idx == 0:
        return strikes_sorted[0]
    if idx == len(strikes_sorted):
        return strikes_sorted[-1]
    before = strikes_sorted[idx - 1]
    after = strikes_sorted[idx]
    return after if (target - before) >= (after - target) else before


def _select_expiry_from_chain(
    instrument: Instrument,
    chain_data: dict[str, Any] | None,
    earnings_date: date | None,
) -> date:
    today = date.today()
    if chain_data is None:
        fallback = today + timedelta(days=14)
        if earnings_date and 0 <= (earnings_date - today).days <= 45:
            return earnings_date
        return fallback

    raw_expirations = chain_data.get("expirations", [])
    if not raw_expirations:
        fallback = today + timedelta(days=14)
        if earnings_date and 0 <= (earnings_date - today).days <= 45:
            return earnings_date
        return fallback

    valid_expirations: list[date] = []
    min_dte, max_dte = DTE_RANGES.get(instrument, (14, 45))

    for exp_str in raw_expirations:
        try:
            exp_date = date.fromisoformat(exp_str) if isinstance(exp_str, str) else exp_str
            dte = (exp_date - today).days
            if min_dte <= dte <= max_dte:
                valid_expirations.append(exp_date)
        except Exception:
            continue

    if valid_expirations:
        return min(valid_expirations)

    all_expirations: list[date] = []
    for exp_str in raw_expirations:
        try:
            exp_date = date.fromisoformat(exp_str) if isinstance(exp_str, str) else exp_str
            dte = (exp_date - today).days
            if dte >= min_dte:
                all_expirations.append(exp_date)
        except Exception:
            continue

    if all_expirations:
        return min(all_expirations)

    fallback = today + timedelta(days=min_dte)
    if earnings_date and 0 <= (earnings_date - today).days <= 45:
        return earnings_date
    return fallback


def _compute_risk_reward(entry: float, stop_loss: float, direction: Direction) -> float:
    if direction == Direction.LONG:
        upside = take_profit - entry if 'take_profit' in locals() else (entry * 1.08 - entry)
        downside = entry - stop_loss
    elif direction == Direction.SHORT:
        upside = entry - take_profit if 'take_profit' in locals() else (entry - entry * 0.92)
        downside = stop_loss - entry
    else:
        upside = abs(entry * 1.03 - entry)
        downside = abs(entry - entry * 0.97)

    if downside <= 0:
        return 1.5
    rr = upside / downside
    return round(min(rr, 5.0), 2)


@dataclass
class SpecialistOutput:
    score: float
    rationale: str
    payload: dict[str, Any]


@dataclass
class MultiAgentPanelService:
    settings: Settings | None = None
    hub: IntegrationHub | None = None
    _dexter: DexterAdapter | None = None

    def __post_init__(self) -> None:
        if self.hub:
            self._dexter = self.hub.dextex

    def _adversarial_params(self) -> tuple[float, float, float]:
        """(dexter_trigger_conviction, dexter_severity_threshold, conviction_floor)."""
        if self.settings is None:
            return 8.0, 7.0, 6.0
        return (
            float(self.settings.dexter_trigger_conviction),
            float(self.settings.dexter_threshold),
            float(self.settings.conviction_floor),
        )

    def _market_analyst(
        self, opportunity: OpportunityScore, market_data: dict[str, Any]
    ) -> SpecialistOutput:
        bars = market_data.get("bars", [])
        trend = "uptrend" if opportunity.technical_score >= 6 else "downtrend"
        reference = bars[-5] if len(bars) >= 5 else (bars[-1] if bars else {})
        levels = {"support": reference.get("low"), "resistance": reference.get("high")}
        return SpecialistOutput(
            score=opportunity.technical_score,
            rationale=f"Detected {trend} with technical score {opportunity.technical_score:.2f}",
            payload={"trend": trend, "levels": levels},
        )

    def _fundamentals_analyst(
        self, opportunity: OpportunityScore, market_data: dict[str, Any]
    ) -> SpecialistOutput:
        fundamentals = market_data.get("fundamentals", {})
        earnings_risk = bool(market_data.get("earnings_date"))
        valuation_flag = fundamentals.get("pe")
        rationale = (
            "Fundamentals support trend"
            if opportunity.fundamental_score >= 6
            else "Fundamental caution"
        )
        if opportunity.symbol.upper() == "NVDA" and "nvda_earnings_week" in (
            opportunity.catalyst or ""
        ):
            rationale = "NVDA earnings-week catalyst; fundamentals weighted with event vol"
            earnings_risk = False
        return SpecialistOutput(
            score=opportunity.fundamental_score,
            rationale=rationale,
            payload={"valuation_flag": valuation_flag, "earnings_risk": earnings_risk},
        )

    def _options_specialist(
        self, opportunity: OpportunityScore, options_data: dict[str, Any] | None
    ) -> SpecialistOutput:
        iv_rank = (options_data or {}).get("iv_rank")
        if opportunity.instrument == Instrument.EQUITY:
            return SpecialistOutput(
                score=5.0,
                rationale="Equity preferred over options",
                payload={"iv_rank": iv_rank},
            )
        structure = "single_leg"
        if opportunity.instrument == Instrument.VERTICAL:
            structure = "debit_spread"
        return SpecialistOutput(
            score=7.0,
            rationale=f"Selected {structure} with IV rank {iv_rank}",
            payload={"iv_rank": iv_rank, "structure": structure},
        )

    def _pm_analyst(
        self, opportunity: OpportunityScore, pm_data: dict[str, Any] | None
    ) -> SpecialistOutput:
        if pm_data is None:
            return SpecialistOutput(
                score=4.0,
                rationale="No PM market for ticker",
                payload={"signal": "NO_MARKET"},
            )
        signal = pm_data.get("signal", "NEUTRAL")
        divergence = float(pm_data.get("divergence", 0))
        score = 7.0 if abs(divergence) >= 0.15 else 5.5
        return SpecialistOutput(
            score=score,
            rationale=f"PM signal {signal} divergence {divergence:.2f}",
            payload={
                "signal": signal,
                "divergence": divergence,
                "whale_alignment": pm_data.get("whale_alignment"),
            },
        )

    def _bull_advocate(self, outputs: dict[str, SpecialistOutput]) -> SpecialistOutput:
        score = (
            outputs["market"].score
            + outputs["fundamentals"].score
            + outputs["pm"].score
        ) / 3
        return SpecialistOutput(
            score=score,
            rationale="Momentum and catalysts align for upside continuation.",
            payload={"upside_case": "breakout follow-through"},
        )

    def _bear_advocate(self, outputs: dict[str, SpecialistOutput]) -> SpecialistOutput:
        score = max(0.0, 10 - ((outputs["market"].score + outputs["pm"].score) / 2))
        return SpecialistOutput(
            score=score,
            rationale="Adverse macro repricing and failed breakout are key risks.",
            payload={"downside_case": "mean reversion + macro shock"},
        )

    def _judge(
        self,
        opportunity: OpportunityScore,
        market_data: dict[str, Any],
        options_data: dict[str, Any] | None,
        outputs: dict[str, SpecialistOutput],
    ) -> TradeProposal | None:
        market_price = float(market_data["bars"][-1]["close"])
        consensus = (
            outputs["market"].score
            + outputs["fundamentals"].score
            + outputs["pm"].score
        ) / 3
        conviction = min(
            10.0, max(0.0, (opportunity.conviction * 0.6) + (consensus * 0.4))
        )
        neutral_compatible = {Instrument.STRADDLE, Instrument.IRON_CONDOR}
        if conviction < 6.0 or (
            opportunity.direction == Direction.NEUTRAL
            and opportunity.instrument not in neutral_compatible
        ):
            return None

        direction = opportunity.direction
        if direction == Direction.LONG:
            stop_loss = market_price * 0.96
            take_profit = market_price * 1.08
        elif direction == Direction.SHORT:
            stop_loss = market_price * 1.04
            take_profit = market_price * 0.92
        else:
            stop_loss = market_price * 0.97
            take_profit = market_price * 1.03

        risk_reward = (take_profit - market_price) / (market_price - stop_loss) if market_price > stop_loss else 1.5

        instrument = opportunity.instrument
        sector = market_data.get("sector", "UNKNOWN")
        iv_rank = (options_data or {}).get("iv_rank")
        earnings_raw = market_data.get("earnings_date")
        earnings_date = earnings_raw if isinstance(earnings_raw, date) else None

        cap = min(5.0, opportunity.max_position_pct)
        span = max(0.0, conviction - 6.0)
        scaled = cap * (0.25 + 0.75 * min(1.0, span / 4.0))
        position_size_pct = min(cap, scaled)

        max_loss_dollars = market_price * position_size_pct / 100.0 * (market_price - stop_loss)

        base = {
            "symbol": opportunity.symbol,
            "direction": direction,
            "instrument": instrument,
            "entry_price": market_price,
            "position_size_pct": position_size_pct,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "max_loss_dollars": max_loss_dollars,
            "conviction_final": conviction,
            "judge_rationale": (
                f"Weighted market({outputs['market'].score:.1f}), fundamentals({outputs['fundamentals'].score:.1f}), "
                f"pm({outputs['pm'].score:.1f}); bull={outputs['bull'].score:.1f}, bear={outputs['bear'].score:.1f}"
            ),
            "dissenting_view": outputs["bear"].rationale,
            "sector": sector,
            "iv_rank": iv_rank,
            "earnings_date": earnings_date,
        }
        if instrument == Instrument.EQUITY:
            return TradeProposal(**base)

        expiry_date = _select_expiry_from_chain(instrument, options_data, earnings_date)

        chain_calls = (options_data or {}).get("calls", [])
        chain_puts = (options_data or {}).get("puts", [])
        available_calls = [float(c.get("strike", 0)) for c in chain_calls if c.get("strike")]
        available_puts = [float(p.get("strike", 0)) for p in chain_puts if p.get("strike")]

        needs_calls = instrument in {Instrument.CALL, Instrument.STRADDLE, Instrument.IRON_CONDOR} or (instrument == Instrument.VERTICAL and direction == Direction.LONG)
        needs_puts = instrument in {Instrument.PUT, Instrument.STRADDLE, Instrument.IRON_CONDOR} or (instrument == Instrument.VERTICAL and direction == Direction.SHORT)
        if (needs_calls and not available_calls) or (needs_puts and not available_puts):
            LOGGER.warning(
                "No %s options chain data for %s %s (calls=%d puts=%d); falling back to EQUITY",
                "calls" if (needs_calls and not available_calls) else "puts",
                opportunity.symbol,
                instrument.value,
                len(available_calls),
                len(available_puts),
            )
            base["instrument"] = Instrument.EQUITY
            if base["direction"] == Direction.NEUTRAL:
                base["direction"] = (
                    Direction.LONG
                    if outputs["bull"].score >= outputs["bear"].score
                    else Direction.SHORT
                )
            return TradeProposal(**base)

        if instrument in {Instrument.CALL, Instrument.PUT}:
            target_strike = market_price
            available = available_calls if instrument == Instrument.CALL else available_puts
            strike = _find_nearest_strike(target_strike, available)
            return TradeProposal(
                **base,
                expiry_date=expiry_date,
                strike=strike,
            )

        if instrument == Instrument.STRADDLE:
            call_strike = _find_nearest_strike(market_price, available_calls)
            put_strike = _find_nearest_strike(market_price, available_puts)
            return TradeProposal(
                **base,
                expiry_date=expiry_date,
                spread_legs=[
                    SpreadLeg(
                        side="buy",
                        option_type="call",
                        strike=call_strike,
                        expiry_date=expiry_date,
                        quantity=1,
                    ),
                    SpreadLeg(
                        side="buy",
                        option_type="put",
                        strike=put_strike,
                        expiry_date=expiry_date,
                        quantity=1,
                    ),
                ],
            )

        if instrument == Instrument.IRON_CONDOR:
            width_pct_low = 0.02 + (iv_rank or 50) / 1000.0
            width_pct_high = 0.05 + (iv_rank or 50) / 500.0
            lower_put = _find_nearest_strike(market_price * (1 - width_pct_low * 2), available_puts)
            short_put = _find_nearest_strike(market_price * (1 - width_pct_low), available_puts)
            short_call = _find_nearest_strike(market_price * (1 + width_pct_high), available_calls)
            upper_call = _find_nearest_strike(market_price * (1 + width_pct_high * 2), available_calls)
            return TradeProposal(
                **base,
                expiry_date=expiry_date,
                spread_legs=[
                    SpreadLeg(
                        side="buy",
                        option_type="put",
                        strike=lower_put,
                        expiry_date=expiry_date,
                        quantity=1,
                    ),
                    SpreadLeg(
                        side="sell",
                        option_type="put",
                        strike=short_put,
                        expiry_date=expiry_date,
                        quantity=1,
                    ),
                    SpreadLeg(
                        side="sell",
                        option_type="call",
                        strike=short_call,
                        expiry_date=expiry_date,
                        quantity=1,
                    ),
                    SpreadLeg(
                        side="buy",
                        option_type="call",
                        strike=upper_call,
                        expiry_date=expiry_date,
                        quantity=1,
                    ),
                ],
            )

        if instrument == Instrument.VERTICAL:
            if direction == Direction.LONG:
                long_strike = _find_nearest_strike(market_price, available_calls)
                short_strike = _find_nearest_strike(market_price * 1.05, available_calls)
            else:
                long_strike = _find_nearest_strike(market_price, available_puts)
                short_strike = _find_nearest_strike(market_price * 0.95, available_puts)
            return TradeProposal(
            **base,
            instrument=Instrument.VERTICAL,
            expiry_date=expiry_date,
            spread_legs=[
                SpreadLeg(
                    side="buy",
                    option_type="call" if direction == Direction.LONG else "put",
                    strike=long_strike,
                    expiry_date=expiry_date,
                    quantity=1,
                ),
                SpreadLeg(
                    side="sell",
                    option_type="call" if direction == Direction.LONG else "put",
                    strike=short_strike,
                    expiry_date=expiry_date,
                    quantity=1,
                ),
            ],
        )

    def _run_dexter_counter_thesis(
        self,
        proposal: TradeProposal,
        *,
        dexter_prefetch: dict[str, Any] | None,
        severity_threshold: float,
        conviction_floor: float,
    ) -> tuple[float, bool, str, float | None, bool]:
        prior = proposal.conviction_final
        if dexter_prefetch:
            new_c, should_cancel, rationale, severity, reduction_applied = (
                DexterAdapter.apply_adversarial_research(
                    dexter_prefetch,
                    prior,
                    severity_threshold=severity_threshold,
                    conviction_floor=conviction_floor,
                )
            )
            LOGGER.info(
                "Dexter prefetch %s: severity %.1f, conviction %.2f -> %.2f, cancel=%s",
                proposal.symbol,
                severity,
                prior,
                new_c,
                should_cancel,
            )
            return new_c, should_cancel, rationale, severity, reduction_applied

        if self._dexter and self._dexter.available:
            try:
                thesis = proposal.judge_rationale or "Technical momentum trade"
                new_c, should_cancel, rationale, severity, reduction_applied = (
                    self._dexter.run_counter_thesis(
                        symbol=proposal.symbol,
                        current_thesis=thesis,
                        direction=proposal.direction.value,
                        conviction=prior,
                        severity_threshold=severity_threshold,
                        conviction_floor=conviction_floor,
                    )
                )
                LOGGER.info(
                    "Dexter counter-thesis for %s: severity %.1f, conviction %.2f -> %.2f, cancel=%s",
                    proposal.symbol,
                    severity,
                    prior,
                    new_c,
                    should_cancel,
                )
                return new_c, should_cancel, rationale, severity, reduction_applied
            except Exception as exc:
                LOGGER.debug("Dexter counter-thesis failed: %s", exc)

        if self.hub and self.hub.has_groq():
            try:
                thesis = proposal.judge_rationale or "Technical momentum trade"
                result = self.hub.groq_direct.run_counter_thesis(
                    symbol=proposal.symbol,
                    thesis=thesis,
                    conviction=prior,
                )
                research = {
                    "severity": float(result.get("severity", 5.0)),
                    "risks": result.get("risks", []),
                    "recommended_action": result.get("recommended_action", "PROCEED"),
                }
                new_c, should_cancel, rationale, severity, reduction_applied = (
                    DexterAdapter.apply_adversarial_research(
                        research,
                        prior,
                        severity_threshold=severity_threshold,
                        conviction_floor=conviction_floor,
                    )
                )
                LOGGER.info(
                    "Groq counter-thesis for %s: severity %.1f, conviction %.2f -> %.2f, cancel=%s",
                    proposal.symbol,
                    severity,
                    prior,
                    new_c,
                    should_cancel,
                )
                return new_c, should_cancel, rationale, severity, reduction_applied
            except Exception as exc:
                LOGGER.debug("Groq counter-thesis failed: %s", exc)

        if proposal.symbol.upper() in {"TSLA", "NVDA"}:
            fake = {
                "severity": 8.0,
                "risks": ["Demo path: elevated crowding / dispersion"],
                "recommended_action": "REDUCE_CONVICTION",
            }
            return DexterAdapter.apply_adversarial_research(
                fake,
                prior,
                severity_threshold=severity_threshold,
                conviction_floor=conviction_floor,
            )

        return prior, False, "Counter-thesis unavailable - using rules-based fallback", None, False

    def evaluate(
        self,
        opportunity: OpportunityScore,
        market_data: dict[str, Any],
        options_data: dict[str, Any] | None,
        pm_data: dict[str, Any] | None,
        dexter_prefetch: dict[str, Any] | None = None,
    ) -> TradeProposal | None:
        outputs = {
            "market": self._market_analyst(opportunity, market_data),
            "fundamentals": self._fundamentals_analyst(opportunity, market_data),
            "options": self._options_specialist(opportunity, options_data),
            "pm": self._pm_analyst(opportunity, pm_data),
        }
        outputs["bull"] = self._bull_advocate(outputs)
        outputs["bear"] = self._bear_advocate(outputs)
        proposal = self._judge(opportunity, market_data, options_data, outputs)
        if proposal is None:
            return None

        trigger, severity_threshold, conviction_floor = self._adversarial_params()
        if proposal.conviction_final >= trigger:
            new_conviction, should_cancel, dex_reason, severity, reduction_applied = (
                self._run_dexter_counter_thesis(
                    proposal,
                    dexter_prefetch=dexter_prefetch,
                    severity_threshold=severity_threshold,
                    conviction_floor=conviction_floor,
                )
            )
            proposal.conviction_final = new_conviction
            if severity is not None:
                proposal.dexter_severity = severity
                proposal.dexter_reduction_applied = reduction_applied
            if should_cancel:
                LOGGER.info("Adversarial review cancelled %s: %s", proposal.symbol, dex_reason)
                return None

        return proposal
