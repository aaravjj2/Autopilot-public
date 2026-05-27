from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from statistics import mean
from typing import TYPE_CHECKING, Any

from apex.core.config import Settings
from apex.core.logging import get_logger
from apex.domain.contracts import PredictionMarketClient
from apex.domain.enums import Direction, Instrument, PMSignal
from apex.domain.models import OpportunityScore
from apex.integrations.hub import IntegrationHub
from apex.domain.weekly_focus import (
    is_within_earnings_window,
    weekly_focus_symbols,
)
from apex.integrations.news_regime_adapters import KronosAdapter

if TYPE_CHECKING:
    from apex.integrations.tradingagents_adapter import TradingAgentsAdapter

LOGGER = get_logger(__name__)


@dataclass
class FinanceBrainService:
    settings: Settings
    pm_client: PredictionMarketClient
    hub: IntegrationHub | None = None
    kronos: KronosAdapter | None = None
    store: Any = None
    _trading_agents: Any = None

    def __post_init__(self) -> None:
        if self.hub:
            self._trading_agents = self.hub.trading_agents

    def _get_trade_memory(self, symbol: str) -> list[dict]:
        if self.store is None:
            return []
        try:
            return self.store.symbol_trade_memory(symbol, limit=3)
        except Exception:
            return []

    def _trend_score(self, bars: list[dict[str, Any]]) -> float:
        if len(bars) < 20:
            return 5.0

        closes = [bar["close"] for bar in bars[-30:]]
        volumes = [bar.get("volume", 0) for bar in bars[-30:]]

        if len(closes) < 10:
            return 5.0

        fast = mean(closes[-5:])
        slow = mean(closes[-20:])
        sma_score = 7.5 if fast > slow else 3.5 if fast < slow else 5.0

        returns = []
        for i in range(1, len(closes)):
            if closes[i - 1] > 0:
                returns.append((closes[i] - closes[i - 1]) / closes[i - 1])

        rsi = 50.0
        if len(returns) >= 14:
            gains = [r for r in returns[-14:] if r > 0]
            losses = [-r for r in returns[-14:] if r < 0]
            avg_gain = sum(gains) / 14 if gains else 0.0
            avg_loss = sum(losses) / 14 if losses else 0.0
            rs = avg_gain / (avg_loss + 1e-9)
            rsi = 100 - (100 / (1 + rs))
        rsi_score = min(10.0, max(0.0, rsi / 10))

        if len(closes) >= 26:
            ema12 = sum(closes[-12:]) / 12
            ema26 = sum(closes[-26:]) / 26
            macd = ema12 - ema26
            macd_hist = macd / (ema26 + 1e-9)
            macd_score = 7.5 if macd > 0 else 3.5 if macd < 0 else 5.0
        else:
            macd_score = 5.0

        avg_volume = sum(volumes) / len(volumes) if volumes else 1
        recent_volume = volumes[-1] if volumes else 0
        volume_score = 7.5 if recent_volume > avg_volume * 1.2 else 3.5 if recent_volume < avg_volume * 0.8 else 5.0

        atr = 0.0
        if len(bars) >= 14:
            trs = []
            for bar in bars[-14:]:
                high = bar.get("high", bar["close"])
                low = bar.get("low", bar["close"])
                prev_close = bar.get("close", bar["close"])
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                trs.append(tr)
            atr = sum(trs) / 14
        price = closes[-1]
        atr_pct = (atr / price) * 100 if price > 0 else 0
        volatility_score = min(10.0, max(0.0, 5.0 + (1.0 / (atr_pct + 0.1))))

        final_score = (sma_score * 0.25) + (rsi_score * 0.25) + (macd_score * 0.20) + (volume_score * 0.15) + (volatility_score * 0.15)
        return round(min(10.0, max(0.0, final_score)), 2)

    def _fundamental_score(self, fundamentals: dict[str, Any]) -> float:
        score = 5.0

        growth = fundamentals.get("revenue_growth")
        if isinstance(growth, (int, float)):
            if growth > 0.2:
                score += 1.5
            elif growth > 0:
                score += 0.75
            elif growth < -0.1:
                score -= 1.0

        pe = fundamentals.get("pe")
        if isinstance(pe, (int, float)) and pe > 0:
            if pe < 15:
                score += 1.0
            elif pe < 25:
                score += 0.5
            elif pe > 50:
                score -= 0.5

        ev_ebitda = fundamentals.get("ev_to_ebitda")
        if isinstance(ev_ebitda, (int, float)) and ev_ebitda > 0:
            if ev_ebitda < 10:
                score += 0.75
            elif ev_ebitda > 25:
                score -= 0.5

        fcf_yield = fundamentals.get("free_cash_flow_yield")
        if isinstance(fcf_yield, (int, float)):
            if fcf_yield > 0.05:
                score += 0.75
            elif fcf_yield > 0:
                score += 0.25
            elif fcf_yield < -0.02:
                score -= 0.5

        gross_margin = fundamentals.get("gross_margin")
        if isinstance(gross_margin, (int, float)):
            if gross_margin > 0.5:
                score += 0.5
            elif gross_margin < 0.2:
                score -= 0.5

        debt_equity = fundamentals.get("debt_to_equity")
        if isinstance(debt_equity, (int, float)):
            if debt_equity < 0.5:
                score += 0.5
            elif debt_equity > 2.0:
                score -= 0.5

        earnings_surprise = fundamentals.get("earnings_surprise_pct")
        if isinstance(earnings_surprise, (int, float)):
            if earnings_surprise > 0.1:
                score += 0.75
            elif earnings_surprise < -0.1:
                score -= 0.5

        rec = str(fundamentals.get("analyst_recommendation", "")).lower()
        rec_trend = str(fundamentals.get("analyst_recommendation_trend", "")).lower()
        if rec in {"buy", "strong_buy"}:
            score += 1.0
            if rec_trend == "up":
                score += 0.5
        if rec in {"sell", "strong_sell"}:
            score -= 1.0
            if rec_trend == "down":
                score -= 0.5

        return min(10.0, max(0.0, score))

    def _pm_score(self, symbol: str) -> tuple[PMSignal, float]:
        signal = self.pm_client.get_ticker_signal(symbol)
        if not signal:
            return PMSignal.NO_MARKET, 0.0
        divergence = float(signal.get("divergence", 0.0))
        raw_signal = str(signal.get("signal", "NEUTRAL")).upper()
        if raw_signal == "BULLISH":
            return PMSignal.BULLISH, divergence
        if raw_signal == "BEARISH":
            return PMSignal.BEARISH, divergence
        return PMSignal.NEUTRAL, divergence

    def _trading_agents_score(
        self, symbol: str, market_data: dict[str, Any]
    ) -> float | None:
        if self.hub and self.hub.has_groq():
            try:
                result = self.hub.groq_direct.analyze(symbol, market_data)
                if "confidence" in result:
                    LOGGER.info(
                        "Groq confidence %.2f for %s", result["confidence"], symbol
                    )
                    return result["confidence"]
            except Exception as exc:
                LOGGER.debug("Groq analysis failed for %s: %s", symbol, exc)

        if self._trading_agents and self._trading_agents.available:
            try:
                result = self._trading_agents.analyze(symbol)
                if "confidence" in result:
                    return result["confidence"]
            except Exception as exc:
                LOGGER.debug("TradingAgents analysis failed for %s: %s", symbol, exc)
        return None

    def _weekly_focus_nudge(
        self,
        symbol: str,
        market_snapshot: dict[str, Any],
    ) -> tuple[float, str]:
        if not self.settings.weekly_focus_enabled:
            return 0.0, ""
        focus = set(weekly_focus_symbols(self.settings))
        notes: list[str] = []
        nudge = 0.0
        if symbol.upper() in focus:
            nudge += float(self.settings.weekly_focus_conviction_boost)
            notes.append("semi_focus")
        earnings_raw = market_snapshot.get("earnings_date")
        market_earnings = earnings_raw if isinstance(earnings_raw, date) else None
        if is_within_earnings_window(
            symbol.upper(),
            self.settings,
            market_earnings=market_earnings,
        ):
            nudge += float(self.settings.nvda_earnings_conviction_boost)
            notes.append("nvda_earnings_week")
        return min(1.2, nudge), "|".join(notes)

    def _news_conviction_nudge(self, news_snapshot: dict[str, Any] | None) -> float:
        """Small conviction delta from overnight digest (daily_stock_analysis regime)."""
        if not news_snapshot:
            return 0.0
        for segment in news_snapshot.get("sources", []):
            if segment.get("source") != "daily_stock_analysis":
                continue
            report = segment.get("report") or {}
            regime = str(report.get("regime", "")).lower()
            if regime == "risk_on":
                return 0.12
            if regime == "risk_off":
                return -0.12
        summary = str(news_snapshot.get("summary", "")).lower()
        if "risk-on" in summary or "bullish" in summary:
            return 0.08
        if "risk-off" in summary or "bearish" in summary:
            return -0.08
        return 0.0

    def _macro_conviction_nudge(self, macro: list[dict[str, Any]] | None) -> float:
        """Blend Polymarket macro basket into a small conviction delta (±0.25)."""
        if not macro:
            return 0.0
        probs: list[float] = []
        for row in macro[:12]:
            try:
                p = float(row.get("probability", 0.5))
            except (TypeError, ValueError):
                p = 0.5
            probs.append(max(0.0, min(1.0, p)))
        if not probs:
            return 0.0
        avg = sum(probs) / len(probs)
        return max(-0.25, min(0.25, (avg - 0.5) * 0.9))

    def score_symbol(
        self,
        symbol: str,
        market_snapshot: dict[str, Any],
        options_snapshot: dict[str, Any] | None = None,
        macro_snapshot: list[dict[str, Any]] | None = None,
        news_snapshot: dict[str, Any] | None = None,
    ) -> OpportunityScore:
        bars = market_snapshot["bars"]
        fundamentals = market_snapshot["fundamentals"]
        sector = market_snapshot["sector"]
        iv_rank = (options_snapshot or {}).get("iv_rank")

        trade_memory = self._get_trade_memory(symbol)
        recent_losses = sum(1 for t in trade_memory if t.get("outcome") == "loss")
        if recent_losses >= 2:
            LOGGER.info("Recent trade history for %s: %d consecutive losses", symbol, recent_losses)

        now = datetime.now(tz=timezone.utc)
        cached_at_str = market_snapshot.get("_cached_at")
        if cached_at_str:
            try:
                cached_at = datetime.fromisoformat(cached_at_str) if isinstance(cached_at_str, str) else cached_at_str
                data_age_seconds = (now - cached_at).total_seconds()
                if data_age_seconds > 600:
                    LOGGER.warning("Stale data for %s: %.1f seconds old", symbol, data_age_seconds)
            except Exception:
                pass

        ta_confidence = self._trading_agents_score(symbol, market_snapshot)

        technical = self._trend_score(bars)
        fundamental = self._fundamental_score(fundamentals)
        pm_signal, divergence = self._pm_score(symbol)

        if ta_confidence is not None:
            confidence_blend = (technical + ta_confidence) / 2
            technical = confidence_blend
            LOGGER.info(
                "TradingAgents confidence %.2f blended into technical score for %s",
                ta_confidence,
                symbol,
            )

        pm_weight_adj = getattr(self.settings, "pm_weight_adj", 0.0)
        divergence_contribution = min(0.5, abs(divergence)) * (1.0 + pm_weight_adj)
        conviction = (technical * 0.45) + (fundamental * 0.35) + divergence_contribution
        conviction = min(10.0, max(0.0, conviction))

        regime_info: dict[str, Any] = {}
        if self.kronos is not None:
            regime_info = self.kronos.get_regime_classification(symbols=["SPY"])
        regime = str(regime_info.get("regime", "unknown"))
        regime_mult = 1.0
        if regime == "low_vol_bull":
            regime_mult = 1.06
        elif regime == "high_vol_bear":
            regime_mult = 0.88
        elif regime == "high_vol_bull":
            regime_mult = 0.94
        elif regime == "low_vol_bear":
            regime_mult = 0.92
        elif regime == "range_bound":
            regime_mult = 0.98
        conviction = min(10.0, max(0.0, conviction * regime_mult))
        if regime_info:
            LOGGER.info("Kronos regime %s (mult=%.3f) applied for %s", regime, regime_mult, symbol)

        macro_nudge = self._macro_conviction_nudge(macro_snapshot)
        news_nudge = self._news_conviction_nudge(news_snapshot)
        focus_nudge, focus_note = self._weekly_focus_nudge(symbol, market_snapshot)
        conviction = min(10.0, max(0.0, conviction + macro_nudge + news_nudge + focus_nudge))
        if macro_nudge and macro_snapshot:
            LOGGER.debug(
                "Polymarket macro nudge %+.3f for %s (%d macro rows)",
                macro_nudge,
                symbol,
                len(macro_snapshot),
            )
        if news_nudge and news_snapshot:
            LOGGER.debug("Overnight news nudge %+.3f for %s", news_nudge, symbol)
        if focus_nudge:
            LOGGER.info("Weekly focus nudge %+.3f for %s (%s)", focus_nudge, symbol, focus_note)

        direction = Direction.NEUTRAL
        if technical >= 6 and pm_signal in {
            PMSignal.BULLISH,
            PMSignal.NO_MARKET,
            PMSignal.NEUTRAL,
        }:
            direction = Direction.LONG
        elif technical <= 4 and pm_signal in {
            PMSignal.BEARISH,
            PMSignal.NO_MARKET,
            PMSignal.NEUTRAL,
        }:
            direction = Direction.SHORT

        instrument = Instrument.EQUITY
        if (
            direction == Direction.NEUTRAL
            and isinstance(iv_rank, (int, float))
            and iv_rank >= 60
            and conviction >= 6.0
        ):
            instrument = Instrument.IRON_CONDOR
        elif (
            abs(divergence) >= 0.35
            and isinstance(iv_rank, (int, float))
            and iv_rank < 50
            and conviction >= 6.5
        ):
            instrument = Instrument.STRADDLE
        elif isinstance(iv_rank, (int, float)) and iv_rank >= 55 and conviction >= 6.5:
            instrument = Instrument.VERTICAL
        elif conviction >= 7.5 and direction == Direction.LONG:
            instrument = Instrument.CALL
        elif conviction >= 7.5 and direction == Direction.SHORT:
            instrument = Instrument.PUT

        bars = market_snapshot["bars"]
        market_price = float(bars[-1]["close"]) if bars else 100.0
        if direction == Direction.LONG:
            rr = (market_price * 1.08 - market_price) / (market_price - market_price * 0.96)
        elif direction == Direction.SHORT:
            rr = (market_price - market_price * 0.92) / (market_price * 1.04 - market_price)
        else:
            rr = (market_price * 1.03 - market_price) / (market_price - market_price * 0.97)
        risk_reward = round(min(rr, 5.0), 2)

        return OpportunityScore(
            symbol=symbol,
            direction=direction,
            instrument=instrument,
            conviction=conviction,
            technical_score=technical,
            fundamental_score=fundamental,
            pm_signal=pm_signal,
            pm_divergence=max(-1.0, min(1.0, divergence)),
            catalyst=(
                f"Regime/technical alignment in {sector}"
                + (
                    f" | PM_macro={macro_nudge:+.2f}"
                    if macro_snapshot and abs(macro_nudge) > 1e-6
                    else ""
                )
                + (f" | news={news_nudge:+.2f}" if abs(news_nudge) > 1e-6 else "")
                + (f" | {focus_note}" if focus_note else "")
                + (f" | recent_losses={recent_losses}" if recent_losses > 0 else "")
            ),
            risk_reward=risk_reward,
            options_structure=(
                {
                    "strategy": "single_leg",
                    "note": "replace with chain-aware leg selection",
                }
                if instrument
                in {
                    Instrument.CALL,
                    Instrument.PUT,
                    Instrument.VERTICAL,
                    Instrument.STRADDLE,
                    Instrument.IRON_CONDOR,
                }
                else None
            ),
            max_position_pct=min(self.settings.max_position_size_pct, 5.0),
            invalidation="Break of prior 5-day support/resistance",
        )

    def score_watchlist(
        self,
        watchlist: list[str],
        market_cache: dict[str, dict[str, Any]],
        options_cache: dict[str, dict[str, Any]] | None = None,
        macro_snapshot: list[dict[str, Any]] | None = None,
        news_snapshot: dict[str, Any] | None = None,
    ) -> list[OpportunityScore]:
        scores: list[OpportunityScore] = []
        for symbol in watchlist:
            snapshot = market_cache.get(symbol)
            if not snapshot:
                continue
            try:
                score = self.score_symbol(
                    symbol,
                    snapshot,
                    (options_cache or {}).get(symbol),
                    macro_snapshot,
                    news_snapshot,
                )
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Opportunity scoring skipped %s: %s", symbol, exc)
                continue
            scores.append(score)
        return sorted(scores, key=lambda item: item.conviction, reverse=True)
