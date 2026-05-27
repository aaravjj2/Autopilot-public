from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from apex.core.config import Settings
from apex.core.logging import get_logger
from apex.domain.enums import Instrument, RiskAction
from apex.domain.models import AccountSnapshot, RiskResult, TradeProposal, ArbOpportunity
import requests
from apex.integrations.kalshi_adapter import fetch_orderbook as fetch_kalshi_orderbook

LOGGER = get_logger(__name__)

_KALSHI_OB_CACHE: dict[str, tuple[float, dict]] = {}
_KALSHI_OB_LOCK = threading.Lock()
_KALSHI_OB_TTL_SEC = 20.0


def _cached_kalshi_orderbook(ticker: str) -> dict:
    import time

    now = time.monotonic()
    with _KALSHI_OB_LOCK:
        hit = _KALSHI_OB_CACHE.get(ticker)
        if hit is not None and now - hit[0] < _KALSHI_OB_TTL_SEC:
            return hit[1]
    ob = fetch_kalshi_orderbook(ticker)
    with _KALSHI_OB_LOCK:
        _KALSHI_OB_CACHE[ticker] = (now, ob)
    return ob


def _poly_ob_from_l2_cache(cached: dict) -> dict:
    """Normalize Redis L2 book (asks or yes/no ladders) for M07 depth walk."""
    if cached.get("asks"):
        return cached
    asks: list[dict[str, str]] = []
    for row in cached.get("no", []) or []:
        try:
            p, qty = float(row[0]), float(row[1])
            asks.append({"price": str(p), "size": str(qty)})
        except (TypeError, ValueError, IndexError):
            continue
    if asks:
        return {"asks": asks, "bids": cached.get("bids", [])}
    raise ValueError("cache miss")

class ArbRiskCheckResult:
    def __init__(self):
        self.passed: list[str] = []
        self.failed: list[str] = []
        self.rejection_reason: str | None = None

    @property
    def all_passed(self) -> bool:
        return not self.failed



@dataclass
class RiskCheckEngine:
    settings: Settings

    def run_all(
        self,
        proposal: TradeProposal,
        account: AccountSnapshot,
        correlated_symbols: dict[str, float] | None = None,
        preview_passed: bool = True,
        preview_reason: str = "preview_ok",
        stop_on_fail: bool = True,
    ) -> list[RiskResult]:
        correlations = correlated_symbols or {}
        results: list[RiskResult] = []

        checks = [
            self._r01_paper_account,
            self._r02_market_hours,
            lambda: self._r03_max_position_size(proposal),
            lambda: self._r04_sector_concentration(proposal, account),
            lambda: self._r05_daily_loss_limit(account),
            lambda: self._r06_max_open_positions(account),
            lambda: self._r07_options_max_loss(proposal, account),
            lambda: self._r08_correlation(proposal, correlations),
            lambda: self._r09_earnings_blackout(proposal),
            lambda: self._r10_iv_rank_filter(proposal),
            lambda: self._r11_conviction_floor(proposal),
            lambda: self._r12_dexter_override(proposal),
            lambda: self._r13_duplicate_position(proposal, account),
            lambda: self._r15_options_trading_policy(proposal),
            lambda: self._r14_alpaca_preview(preview_passed, preview_reason),
        ]
        for check in checks:
            result = check()
            results.append(result)
            if stop_on_fail and not result.passed:
                break
        return results

    def run_arb_paper(self, opp: ArbOpportunity, stake_usd: float = 50.0) -> ArbRiskCheckResult:
        """
        Run the full M01–M08 arb risk stack.
        Returns ArbRiskCheckResult. If any check fails, stops early.
        All checks are paper-only — no real money path exists.
        """
        result = ArbRiskCheckResult()
        
        _kalshi_ob_cache: dict | None = None
        
        def get_kalshi_ob() -> dict:
            nonlocal _kalshi_ob_cache
            if _kalshi_ob_cache is None:
                from apex.cache.orderbook_l2 import read_orderbook

                cached = read_orderbook("KALSHI", opp.kalshi_ticker, redis_url=self.settings.redis_url)
                if cached and (cached.get("yes") or cached.get("no")):
                    _kalshi_ob_cache = cached
                else:
                    _kalshi_ob_cache = _cached_kalshi_orderbook(opp.kalshi_ticker)
            return _kalshi_ob_cache

        def m01_paper_only() -> tuple[bool, str]:
            if not self.settings.alpaca_paper_trade:
                return False, "M01_PAPER_REQUIRED: ALPACA_PAPER_TRADE must be True for arb"
            if not self.settings.polymarket_paper_trading_enabled:
                return False, "M01_PAPER_REQUIRED: POLYMARKET_PAPER_TRADING_ENABLED must be True for arb"
            return True, ""

        def m02_min_edge() -> tuple[bool, str]:
            if opp.net_edge < self.settings.arb_min_net_edge:
                return False, f"M02_EDGE_BELOW_FLOOR: {opp.net_edge:.4f} < {self.settings.arb_min_net_edge}"
            return True, ""

        def m03_volume_check() -> tuple[bool, str]:
            min_vol = self.settings.kalshi_min_volume_24h
            if opp.volume_kalshi < min_vol:
                return False, f"M03_KALSHI_LOW_VOLUME: {opp.volume_kalshi:,.0f} < {min_vol:,.0f}"
            if opp.volume_poly < min_vol:
                return False, f"M03_POLY_LOW_VOLUME: {opp.volume_poly:,.0f} < {min_vol:,.0f}"
            return True, ""

        def m04_price_sanity() -> tuple[bool, str]:
            if not (0.01 <= opp.kalshi_yes_ask <= 0.99):
                return False, f"M04_KALSHI_PRICE_INVALID: {opp.kalshi_yes_ask}"
            if not (0.01 <= opp.poly_no_ask <= 0.99):
                return False, f"M04_POLY_PRICE_INVALID: {opp.poly_no_ask}"
            return True, ""

        def m05_settlement_pass() -> tuple[bool, str]:
            if opp.settlement_match_score < 0.45:
                return False, (
                    f"M05_SETTLEMENT_BLOCKED: score={opp.settlement_match_score:.2f} "
                    f"flags={opp.settlement_flags}"
                )
            return True, ""

        def m06_daily_arb_limit() -> tuple[bool, str]:
            from apex.repositories.sqlite_store import SQLiteStore

            store = SQLiteStore(self.settings.sqlite_path)
            realized = store.get_today_arb_pnl()
            event_loss = store.get_today_arb_event_loss_usd()
            daily_loss = abs(min(0.0, realized)) + event_loss
            cap = float(self.settings.arb_max_daily_loss_usd)
            if self.settings.arb_paper_relax_orderbook and self.settings.demo_mode:
                cap = max(cap, 2500.0)
            if daily_loss >= cap:
                return (
                    False,
                    f"M06_DAILY_ARB_LIMIT: loss ${daily_loss:.2f} >= cap ${cap:.2f}",
                )
            return True, ""

        def m07_liquidity_depth() -> tuple[bool, str]:
            try:
                kalshi_ob = get_kalshi_ob()

                try:
                    from apex.cache.orderbook_l2 import read_orderbook

                    poly_cached = read_orderbook(
                        "POLY", opp.poly_market_id, redis_url=self.settings.redis_url
                    )
                    if poly_cached and (poly_cached.get("asks") or poly_cached.get("yes")):
                        poly_ob = _poly_ob_from_l2_cache(poly_cached)
                    else:
                        raise ValueError("cache miss")
                except Exception:
                    poly_resp = requests.get(
                        f"https://clob.polymarket.com/book?token_id={opp.poly_market_id}",
                        timeout=8,
                    )
                    poly_resp.raise_for_status()
                    poly_ob = poly_resp.json()
            except Exception as e:
                LOGGER.warning("M07_ORDERBOOK_UNAVAILABLE: %s", e)
                if self.settings.arb_paper_relax_orderbook:
                    return True, f"M07_SKIPPED_PAPER:{e}"
                return False, f"M07_ORDERBOOK_UNAVAILABLE: {e}"

            no_bids = kalshi_ob.get("no", [])
            no_bids = sorted(no_bids, key=lambda x: x[0], reverse=True)
            
            k_filled_qty = 0.0
            k_filled_value = 0.0
            target_stake = stake_usd
            
            for bid in no_bids:
                p, qty = bid
                ask_p = 1.0 - p
                available_val = qty * ask_p
                needed_val = target_stake - k_filled_value
                
                if available_val >= needed_val:
                    k_filled_qty += needed_val / ask_p
                    k_filled_value += needed_val
                    break
                else:
                    k_filled_qty += qty
                    k_filled_value += available_val
            
            if k_filled_value < target_stake:
                return False, "M07_SLIPPAGE_EXCEEDED: Kalshi liquidity insufficient"
                
            k_vwap = k_filled_value / k_filled_qty if k_filled_qty > 0 else 0.0
            k_slippage = abs(k_vwap - opp.kalshi_yes_ask)
            LOGGER.debug("M07 Kalshi slippage estimate: %.4f", k_slippage)
            if k_slippage > 0.005:
                return False, f"M07_SLIPPAGE_EXCEEDED: Kalshi VWAP {k_vwap:.4f} > ask {opp.kalshi_yes_ask:.4f} + 0.005"
            
            p_asks = poly_ob.get("asks", [])
            p_asks = sorted(p_asks, key=lambda x: float(x.get("price", 1.0)))
            
            p_filled_qty = 0.0
            p_filled_value = 0.0
            for ask in p_asks:
                p = float(ask.get("price", 1.0))
                sz = float(ask.get("size", 0.0))
                available_val = sz * p
                needed_val = target_stake - p_filled_value
                
                if available_val >= needed_val:
                    p_filled_qty += needed_val / p
                    p_filled_value += needed_val
                    break
                else:
                    p_filled_qty += sz
                    p_filled_value += available_val
            
            if p_filled_value < target_stake:
                return False, "M07_SLIPPAGE_EXCEEDED: Poly liquidity insufficient"
                
            p_vwap = p_filled_value / p_filled_qty if p_filled_qty > 0 else 0.0
            p_slippage = abs(p_vwap - opp.poly_no_ask)
            LOGGER.debug("M07 Poly slippage estimate: %.4f", p_slippage)
            if p_slippage > 0.005:
                return False, f"M07_SLIPPAGE_EXCEEDED: Poly VWAP {p_vwap:.4f} > ask {opp.poly_no_ask:.4f} + 0.005"
                
            return True, ""

        def m08_spread_width() -> tuple[bool, str]:
            try:
                ob = get_kalshi_ob()
                yes_bids = ob.get("yes", []) or []
                no_bids = ob.get("no", []) or []
                if not yes_bids and not no_bids:
                    if self.settings.arb_paper_relax_orderbook:
                        return True, "M08_SKIPPED_PAPER:no_orderbook"
                    return False, "M08_SPREAD_UNAVAILABLE: empty orderbook"
                best_bid_no = max((b[0] for b in no_bids), default=0.0)
                best_bid_yes = max((b[0] for b in yes_bids), default=0.0)
                spread = (1.0 - best_bid_no) - best_bid_yes

                LOGGER.debug("Kalshi spread for %s is %.4f", opp.kalshi_ticker, spread)
                if spread > 0.15:
                    if self.settings.arb_paper_relax_orderbook:
                        return True, f"M08_SKIPPED_PAPER:wide_spread:{spread:.4f}"
                    return False, f"M08_SPREAD_WIDTH: {spread:.4f} > 0.15"
                return True, ""
            except Exception as e:
                LOGGER.warning("M08_SPREAD_UNAVAILABLE: %s", e)
                if self.settings.arb_paper_relax_orderbook:
                    return True, f"M08_SKIPPED_PAPER:{e}"
                return False, f"M08_SPREAD_UNAVAILABLE: {e}"

        def m09_kelly_cftc() -> tuple[bool, str]:
            """Week 6: fractional Kelly + CFTC $250k contract cap."""
            from apex.risk.metrics_service import get_cftc_tracker
            from apex.risk.kelly import kelly_from_edge
            from apex.risk.vix_client import get_vix

            vix = get_vix()
            conf = float(getattr(opp, "ai_confidence_score", 0) or 0.7)
            kr = kelly_from_edge(
                float(opp.net_edge),
                ai_confidence=conf,
                alpha=float(getattr(self.settings, "kelly_alpha", 0.25)),
                vix=vix,
                lambda_dampener=float(getattr(self.settings, "kelly_lambda", 0.02)),
            )
            min_kelly = 0.001 if self.settings.arb_paper_relax_orderbook else 0.005
            if kr.dampened_fraction < min_kelly:
                if self.settings.arb_paper_relax_orderbook:
                    return True, f"M09_SKIPPED_PAPER:kelly:{kr.dampened_fraction:.4f}"
                return False, f"M09_KELLY_TOO_SMALL: {kr.dampened_fraction:.4f}"
            tracker = get_cftc_tracker()
            tracker.limit_usd = float(
                getattr(self.settings, "cftc_contract_limit_usd", 250_000.0)
            )
            exp = tracker.check(opp.kalshi_ticker, stake_usd)
            if exp.breached:
                return (
                    False,
                    f"M09_CFTC_LIMIT: ${exp.notional_usd:,.0f} > ${exp.limit_usd:,.0f}",
                )
            try:
                from apex.repositories.cftc_persistence import flush_exposure
                from apex.repositories.sqlite_store import SQLiteStore

                _store = SQLiteStore(self.settings.sqlite_path)
                current_notional = tracker.exposures.get(opp.kalshi_ticker, 0.0) + stake_usd
                flush_exposure(_store, opp.kalshi_ticker, current_notional)
            except Exception:
                pass
            return True, ""

        checks = [
            ("M01", m01_paper_only),
            ("M02", m02_min_edge),
            ("M03", m03_volume_check),
            ("M04", m04_price_sanity),
            ("M05", m05_settlement_pass),
            ("M06", m06_daily_arb_limit),
            ("M07", m07_liquidity_depth),
            ("M08", m08_spread_width),
            ("M09", m09_kelly_cftc),
        ]

        for name, check_fn in checks:
            passed, reason = check_fn()
            if passed:
                result.passed.append(name)
            else:
                result.failed.append(name)
                result.rejection_reason = reason
                break  # fail-fast

        return result

    def run_polymarket_paper(
        self,
        proposal: TradeProposal,
        account: AccountSnapshot,
        preview_passed: bool = True,
        preview_reason: str = "preview_ok",
        stop_on_fail: bool = True,
    ) -> list[RiskResult]:
        """Risk path for ``Instrument.POLYMARKET_EVENT`` (paper bankroll only)."""
        results: list[RiskResult] = []
        checks = [
            self._m01_polymarket_paper_enabled,
            lambda: self._m02_pm_max_order(proposal),
            lambda: self._m03_pm_buying_power(proposal, account),
            lambda: self._m04_pm_max_open_positions(proposal, account),
            lambda: self._r11_conviction_floor(proposal),
            lambda: self._r14_alpaca_preview(preview_passed, preview_reason),
        ]
        for check in checks:
            result = check()
            results.append(result)
            if stop_on_fail and not result.passed:
                break
        return results

    def _m01_polymarket_paper_enabled(self) -> RiskResult:
        ok = bool(self.settings.polymarket_paper_trading_enabled)
        return RiskResult(
            risk_id="M01",
            passed=ok,
            reason="polymarket paper enabled" if ok else "POLYMARKET_PAPER_TRADING_ENABLED is false",
            action=RiskAction.HARD_BLOCK,
        )

    def _m02_pm_max_order(self, proposal: TradeProposal) -> RiskResult:
        stake = float(proposal.polymarket_stake_usd)
        mx = float(self.settings.polymarket_paper_max_order_usd)
        passed = stake <= mx + 1e-9
        return RiskResult(
            risk_id="M02",
            passed=passed,
            reason="stake within polymarket max order" if passed else "stake exceeds POLYMARKET_PAPER_MAX_ORDER_USD",
            action=RiskAction.CANCEL,
        )

    def _m03_pm_buying_power(self, proposal: TradeProposal, account: AccountSnapshot) -> RiskResult:
        stake = float(proposal.polymarket_stake_usd)
        passed = stake <= account.buying_power + 1e-6
        return RiskResult(
            risk_id="M03",
            passed=passed,
            reason="PM buying power sufficient" if passed else "insufficient Polymarket paper buying power",
            action=RiskAction.CANCEL,
        )

    def _m04_pm_max_open_positions(self, proposal: TradeProposal, account: AccountSnapshot) -> RiskResult:
        key = f"PM:{proposal.polymarket_market_id}|{proposal.polymarket_outcome_side}"
        has = any(p.symbol == key for p in account.open_positions)
        cap = int(self.settings.polymarket_paper_max_open_positions)
        passed = has or len(account.open_positions) < cap
        return RiskResult(
            risk_id="M04",
            passed=passed,
            reason="PM open position slots ok" if passed else "POLYMARKET_PAPER_MAX_OPEN_POSITIONS reached",
            action=RiskAction.CANCEL,
        )

    def _r01_paper_account(self) -> RiskResult:
        is_paper_url = "paper" in self.settings.alpaca_base_url.lower()
        passed = bool(self.settings.alpaca_paper_trade and is_paper_url)
        return RiskResult(
            risk_id="R01",
            passed=passed,
            reason="paper account verified" if passed else "live endpoint/key detected",
            action=RiskAction.HARD_BLOCK,
        )

    def _r02_market_hours(self) -> RiskResult:
        now_et = datetime.now(ZoneInfo("America/New_York")).time()
        start = time(9, 30)
        end = time(16, 0)
        passed = start <= now_et <= end
        return RiskResult(
            risk_id="R02",
            passed=passed,
            reason="within regular hours" if passed else "outside regular market hours",
            action=RiskAction.DEFER,
        )

    def _r03_max_position_size(self, proposal: TradeProposal) -> RiskResult:
        passed = proposal.position_size_pct <= self.settings.max_position_size_pct
        return RiskResult(
            risk_id="R03",
            passed=passed,
            reason="position size within threshold" if passed else "position size exceeds threshold",
            action=RiskAction.RESIZE,
        )

    def _r04_sector_concentration(self, proposal: TradeProposal, account: AccountSnapshot) -> RiskResult:
        total = sum(pos.market_value for pos in account.open_positions) + 1e-9
        sector_value = sum(
            pos.market_value for pos in account.open_positions if pos.sector == proposal.sector
        )
        projected_pct = ((sector_value + (account.equity * proposal.position_size_pct / 100.0)) / (total + account.equity)) * 100
        passed = projected_pct <= self.settings.max_sector_pct
        return RiskResult(
            risk_id="R04",
            passed=passed,
            reason="sector concentration healthy" if passed else "sector overweight",
            action=RiskAction.CANCEL,
        )

    def _r05_daily_loss_limit(self, account: AccountSnapshot) -> RiskResult:
        passed = account.daily_pl_pct >= -abs(self.settings.daily_loss_limit_pct)
        return RiskResult(
            risk_id="R05",
            passed=passed,
            reason="daily loss within threshold" if passed else "daily loss limit exceeded",
            action=RiskAction.HARD_BLOCK,
        )

    def _r06_max_open_positions(self, account: AccountSnapshot) -> RiskResult:
        passed = len(account.open_positions) < self.settings.max_open_positions
        return RiskResult(
            risk_id="R06",
            passed=passed,
            reason="open positions below max" if passed else "max open positions reached",
            action=RiskAction.CANCEL,
        )

    def _r07_options_max_loss(self, proposal: TradeProposal, account: AccountSnapshot) -> RiskResult:
        if proposal.instrument in (Instrument.EQUITY, Instrument.POLYMARKET_EVENT):
            return RiskResult("R07", True, "not an options-only check", RiskAction.CANCEL)
        max_allowed = account.equity * (self.settings.options_max_loss_pct / 100.0)
        passed = proposal.max_loss_dollars <= max_allowed
        return RiskResult(
            risk_id="R07",
            passed=passed,
            reason="options max loss bounded" if passed else "options max loss exceeds threshold",
            action=RiskAction.CANCEL,
        )

    def _r08_correlation(self, proposal: TradeProposal, correlations: dict[str, float]) -> RiskResult:
        corr = abs(correlations.get(proposal.symbol, 0.0))
        passed = corr <= 0.75
        return RiskResult(
            risk_id="R08",
            passed=passed,
            reason="correlation below threshold" if passed else f"high correlation {corr:.2f}",
            action=RiskAction.CANCEL,
        )

    def _r09_earnings_blackout(self, proposal: TradeProposal) -> RiskResult:
        if self.settings.weekly_focus_relax_earnings_blackout:
            from apex.domain.weekly_focus import weekly_focus_earnings_symbols

            if proposal.symbol.upper() in weekly_focus_earnings_symbols(self.settings):
                return RiskResult(
                    "R09",
                    True,
                    "weekly focus earnings play (blackout relaxed)",
                    RiskAction.CANCEL,
                )
        earnings = proposal.earnings_date
        if earnings is None:
            return RiskResult("R09", True, "no earnings event nearby", RiskAction.CANCEL)
        today = date.today()
        window = timedelta(days=self.settings.earnings_blackout_days)
        passed = not (today - window <= earnings <= today + window)
        return RiskResult(
            risk_id="R09",
            passed=passed,
            reason="outside earnings blackout" if passed else "earnings blackout",
            action=RiskAction.CANCEL,
        )

    def _r10_iv_rank_filter(self, proposal: TradeProposal) -> RiskResult:
        if proposal.instrument == Instrument.EQUITY:
            return RiskResult("R10", True, "equity trade", RiskAction.CANCEL)
        if proposal.iv_rank is None:
            return RiskResult("R10", False, "missing IV rank", RiskAction.CANCEL)
        long_options = proposal.instrument in {Instrument.CALL, Instrument.PUT, Instrument.STRADDLE}
        if long_options and proposal.iv_rank >= self.settings.iv_rank_long_threshold:
            return RiskResult("R10", False, "IV rank too high for long options", RiskAction.CANCEL)
        if not long_options and proposal.iv_rank <= self.settings.iv_rank_short_threshold:
            return RiskResult("R10", False, "IV rank too low for short premium", RiskAction.CANCEL)
        return RiskResult("R10", True, "IV rank filter passed", RiskAction.CANCEL)

    def _r11_conviction_floor(self, proposal: TradeProposal) -> RiskResult:
        passed = proposal.conviction_final >= self.settings.conviction_floor
        return RiskResult(
            risk_id="R11",
            passed=passed,
            reason="conviction above floor" if passed else "conviction below floor",
            action=RiskAction.CANCEL,
        )

    def _r12_dexter_override(self, proposal: TradeProposal) -> RiskResult:
        severity = proposal.dexter_severity
        if severity is None:
            return RiskResult("R12", True, "dexter not triggered", RiskAction.CANCEL)
        if severity > self.settings.dexter_threshold and not proposal.dexter_reduction_applied:
            return RiskResult("R12", False, "dexter reduction missing", RiskAction.CANCEL)
        return RiskResult("R12", True, "dexter override verified", RiskAction.CANCEL)

    def _r13_duplicate_position(self, proposal: TradeProposal, account: AccountSnapshot) -> RiskResult:
        duplicate = any(pos.symbol == proposal.symbol for pos in account.open_positions)
        passed = not duplicate
        return RiskResult(
            risk_id="R13",
            passed=passed,
            reason="no duplicate position" if passed else "duplicate symbol already open",
            action=RiskAction.CANCEL,
        )

    def _r14_alpaca_preview(self, passed: bool, reason: str) -> RiskResult:
        return RiskResult(
            risk_id="R14",
            passed=passed,
            reason=reason if reason else "preview rejected",
            action=RiskAction.CANCEL,
        )

    def _r15_options_trading_policy(self, proposal: TradeProposal) -> RiskResult:
        """Enforce OPTIONS_TRADING_ENABLED and block silent equity flatten at submit time."""
        if proposal.instrument == Instrument.POLYMARKET_EVENT:
            return RiskResult("R15", True, "polymarket event", RiskAction.CANCEL)
        is_option_structure = proposal.instrument != Instrument.EQUITY
        if not self.settings.options_trading_enabled:
            if is_option_structure:
                return RiskResult(
                    risk_id="R15",
                    passed=False,
                    reason="OPTIONS_TRADING_ENABLED is false",
                    action=RiskAction.CANCEL,
                )
            return RiskResult("R15", True, "equity-only mode", RiskAction.CANCEL)
        if self.settings.alpaca_flatten_options_to_equity and is_option_structure:
            return RiskResult(
                risk_id="R15",
                passed=False,
                reason="options enabled but ALPACA_FLATTEN_OPTIONS_TO_EQUITY is true",
                action=RiskAction.HARD_BLOCK,
            )
        if not is_option_structure:
            return RiskResult("R15", True, "equity proposal", RiskAction.CANCEL)
        if proposal.instrument in {
            Instrument.CALL,
            Instrument.PUT,
        } and (proposal.strike is None or proposal.expiry_date is None):
            return RiskResult(
                risk_id="R15",
                passed=False,
                reason="options proposal missing strike or expiry",
                action=RiskAction.CANCEL,
            )
        if proposal.instrument in {
            Instrument.VERTICAL,
            Instrument.STRADDLE,
            Instrument.IRON_CONDOR,
        } and not proposal.spread_legs:
            return RiskResult(
                risk_id="R15",
                passed=False,
                reason="spread options proposal missing spread_legs",
                action=RiskAction.CANCEL,
            )
        return RiskResult("R15", True, "options trading policy passed", RiskAction.CANCEL)
