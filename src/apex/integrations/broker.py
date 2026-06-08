from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from apex.core.config import Settings
from apex.core.logging import get_logger
from apex.core.retry import call_with_retries
from apex.domain.enums import Direction, Instrument
from apex.domain.errors import BrokerCircuitOpenError, MalformedProposalError
from apex.domain.models import AccountSnapshot, Position, TradeProposal
from apex.integrations.alpaca_adapter import AlpacaDirectIntegration

LOGGER = get_logger(__name__)


def _try_validate_occ_for_any_expiry(
    alpaca: AlpacaDirectIntegration,
    underlying: str,
    preferred_expiry: str,
    occ_symbols: list[str],
    max_shift_days: int = 14,
) -> str | None:
    """When OCC symbols are invalid for the preferred expiry, try nearby ones.

    Returns the expiry date string (ISO format) that makes all OCC symbols
    valid, or ``None`` if none of the tried expiries work.
    """
    from datetime import date, timedelta

    pref = date.fromisoformat(preferred_expiry)
    valid = alpaca.get_valid_occ_symbols(underlying, preferred_expiry)
    if valid:
        invalid = [s for s in occ_symbols if s.upper() not in valid]
        if not invalid:
            return preferred_expiry

    LOGGER.info(
        "Expiry fallback: %s has %d invalid OCC symbols out of %d; scanning ±%d days",
        preferred_expiry, len(invalid), len(occ_symbols), max_shift_days,
    )

    candidates: list[tuple[int, str]] = []
    for offset_days in range(1, max_shift_days + 1):
        for delta in (offset_days, -offset_days):
            cand = pref + timedelta(days=delta)
            cand_str = cand.isoformat()
            c_valid = alpaca.get_valid_occ_symbols(underlying, cand_str)
            if c_valid:
                all_ok = all(s.upper() in c_valid for s in occ_symbols)
                if all_ok:
                    candidates.append((abs(delta), cand_str))
    candidates.sort(key=lambda x: x[0])
    if candidates:
        best = candidates[0][1]
        LOGGER.info("Expiry fallback resolved: %s → %s", preferred_expiry, best)
        return best
    LOGGER.warning("Expiry fallback exhausted: no valid expiry within ±%d days", max_shift_days)
    return None


def _parse_alpaca_entry_time(row: dict[str, Any]) -> datetime:
    """Parse an Alpaca position row's entry timestamp into a UTC-aware datetime.

    Tries the common Alpaca timestamp field names in order.  Falls back to
    the current UTC time if no parseable field is found.
    """
    for key in ("created_at", "createdAt", "opened_at"):
        raw = row.get(key)
        if not raw:
            continue
        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError as exc:
            LOGGER.debug("_parse_alpaca_entry_time: could not parse %r for key %r: %s", raw, key, exc)
    LOGGER.debug("_parse_alpaca_entry_time: no timestamp field found; using datetime.now(tz=timezone.utc)")
    return datetime.now(tz=timezone.utc)


def _position_from_alpaca_row(row: dict[str, Any]) -> Position:
    qty = float(row.get("qty", 0) or 0)
    mv = float(row.get("market_value", 0) or 0)
    avg = float(row.get("avg_entry_price", 0) or 0)
    sym = str(row.get("symbol", "UNKNOWN"))
    side_raw = str(row.get("side", "long")).lower()
    side = "short" if side_raw == "short" else "long"
    return Position(
        symbol=sym,
        qty=qty,
        market_value=mv,
        sector="UNKNOWN",
        avg_entry_price=avg,
        side=side,
        correlation_to_book=0.1,
        entry_time=_parse_alpaca_entry_time(row),
    )


def _options_risk_budget(proposal: TradeProposal, account: AccountSnapshot) -> float:
    if proposal.max_loss_dollars and proposal.max_loss_dollars > 0:
        return float(proposal.max_loss_dollars)
    return account.equity * (proposal.position_size_pct / 100.0)


@dataclass
class PaperBrokerSimulator:
    settings: Settings
    equity: float = field(init=False)
    buying_power: float = field(init=False)
    positions: dict[str, Position] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.equity = float(self.settings.initial_account_equity)
        self.buying_power = float(self.settings.initial_account_equity)

    def get_account_snapshot(self) -> AccountSnapshot:
        market_value = sum(position.market_value for position in self.positions.values())
        daily_pl_pct = 0.0
        return AccountSnapshot(
            equity=self.equity + market_value,
            buying_power=self.buying_power,
            daily_pl_pct=daily_pl_pct,
            open_positions=list(self.positions.values()),
        )

    def get_positions(self) -> list[Position]:
        return list(self.positions.values())

    def preview_order(self, proposal: TradeProposal) -> tuple[bool, str]:
        if proposal.instrument == Instrument.POLYMARKET_EVENT:
            return False, "polymarket_use_venue_routing_broker"
        account = self.get_account_snapshot()
        if proposal.instrument != Instrument.EQUITY:
            est = _options_risk_budget(proposal, account)
            if est > account.buying_power:
                return False, "Insufficient buying power"
            return True, "paper_options_preview_ok"
        estimated_cost = account.equity * (proposal.position_size_pct / 100.0)
        if estimated_cost > account.buying_power:
            return False, "Insufficient buying power"
        return True, "preview_ok"

    def submit_order(self, proposal: TradeProposal) -> str:
        if proposal.instrument == Instrument.POLYMARKET_EVENT:
            return f"failed_{uuid4()}"
        order_id = str(uuid4())
        account = self.get_account_snapshot()
        if proposal.instrument != Instrument.EQUITY:
            est = max(1.0, _options_risk_budget(proposal, account))
            self.buying_power -= est
            return order_id
        notional = account.equity * (proposal.position_size_pct / 100.0)
        qty = max(notional / proposal.entry_price, 1.0)
        side = "long" if proposal.direction.value == "LONG" else "short"
        self.positions[proposal.symbol] = Position(
            symbol=proposal.symbol,
            qty=qty,
            market_value=notional,
            sector=proposal.sector,
            avg_entry_price=proposal.entry_price,
            side=side,
            correlation_to_book=0.1,
            entry_time=datetime.now(tz=timezone.utc),
        )
        self.buying_power -= notional
        return order_id

    def monitor_fill(self, order_id: str, timeout_seconds: int = 300) -> tuple[bool, str]:
        _ = timeout_seconds
        return True, f"filled:{order_id}"

    def cancel_order(self, order_id: str) -> None:
        _ = order_id

    def get_order(self, order_id: str) -> dict[str, Any]:
        if order_id.startswith("failed_"):
            return {"id": order_id, "status": "failed", "error": "simulated_submit_failure"}
        return {"id": order_id, "status": "filled"}

    def get_orders(self, status: str = "open") -> list[dict[str, Any]]:
        return []

    def close_symbol_position(self, symbol: str) -> bool:
        """Remove simulated position and restore notional buying power."""
        pos = self.positions.pop(symbol, None)
        if pos is None:
            return False
        self.buying_power += pos.market_value
        return True


@dataclass
class AlpacaBrokerAdapter:
    """
    Alpaca REST routing: equities by notional, and native US options (single-leg and
    multi-leg ``mleg``) when ``ALPACA_FLATTEN_OPTIONS_TO_EQUITY`` is disabled in settings.
    """

    alpaca: AlpacaDirectIntegration
    settings: Settings
    _fail_streak: int = field(default=0, init=False, repr=False)
    _circuit_open_until: float = field(default=0.0, init=False, repr=False)

    def _record_broker_failure(self) -> None:
        th = self.settings.broker_circuit_failure_threshold
        if th <= 0:
            return
        self._fail_streak += 1
        if self._fail_streak >= th:
            self._circuit_open_until = time.monotonic() + float(self.settings.broker_circuit_cooldown_sec)
            LOGGER.error(
                "Alpaca broker circuit OPEN for %.0fs after %d consecutive submit failures",
                float(self.settings.broker_circuit_cooldown_sec),
                self._fail_streak,
            )

    def _reset_circuit(self) -> None:
        self._fail_streak = 0
        self._circuit_open_until = 0.0

    def get_account_snapshot(self) -> AccountSnapshot:
        raw = self.alpaca.get_account()
        if raw.get("status") in {"error", "exception"}:
            LOGGER.warning("Alpaca account fetch failed: %s", raw)
            equity = float(self.settings.initial_account_equity)
            return AccountSnapshot(
                equity=equity,
                buying_power=equity,
                daily_pl_pct=0.0,
                open_positions=self.get_positions(),
            )
        equity = float(raw.get("equity", 0) or 0)
        bp = float(raw.get("buying_power", equity) or equity)
        last_equity = float(raw.get("last_equity", equity) or equity)
        daily_pl_pct = ((equity - last_equity) / last_equity * 100.0) if last_equity else 0.0
        return AccountSnapshot(
            equity=equity,
            buying_power=bp,
            daily_pl_pct=daily_pl_pct,
            open_positions=self.get_positions(),
        )

    def get_positions(self) -> list[Position]:
        rows = self.alpaca.get_positions()
        if not rows:
            return []
        return [_position_from_alpaca_row(r) for r in rows if isinstance(r, dict)]

    def preview_order(self, proposal: TradeProposal) -> tuple[bool, str]:
        if proposal.instrument == Instrument.POLYMARKET_EVENT:
            return False, "polymarket_not_supported_on_alpaca_adapter"
        account = self.get_account_snapshot()
        if proposal.instrument == Instrument.EQUITY:
            est = account.equity * (proposal.position_size_pct / 100.0)
            if est > account.buying_power:
                return False, "Insufficient buying power"
            if est < 1.0:
                return False, "Notional below minimum"
            return True, "preview_ok"
        if proposal.instrument in {
            Instrument.CALL,
            Instrument.PUT,
            Instrument.VERTICAL,
            Instrument.STRADDLE,
            Instrument.IRON_CONDOR,
        }:
            est = _options_risk_budget(proposal, account)
            if est > account.buying_power:
                return False, "Insufficient buying power for option strategy budget"
            if est < 1.0:
                return False, "Option risk budget below minimum"
            try:
                self._validate_option_proposal_for_alpaca(proposal)
            except ValueError as exc:
                return False, str(exc)
            return True, "preview_options_ok"
        return False, f"Alpaca adapter: unsupported instrument {proposal.instrument}"

    def _validate_option_proposal_for_alpaca(self, proposal: TradeProposal) -> None:
        from apex.domain.option_symbols import format_occ_option_symbol

        if proposal.spread_legs and len(proposal.spread_legs) >= 2:
            for leg in proposal.spread_legs:
                format_occ_option_symbol(
                    proposal.symbol,
                    leg.expiry_date,
                    leg.option_type,
                    float(leg.strike),
                )
            return
        if proposal.instrument in (Instrument.CALL, Instrument.PUT):
            if proposal.expiry_date is None or proposal.strike is None:
                raise ValueError("CALL/PUT requires expiry_date and strike")
            format_occ_option_symbol(
                proposal.symbol,
                proposal.expiry_date,
                "call" if proposal.instrument == Instrument.CALL else "put",
                float(proposal.strike),
            )
            return
        raise ValueError("Unsupported option proposal for Alpaca")

    def _submit_alpaca_options_order(self, proposal: TradeProposal) -> dict[str, Any]:
        from apex.domain.option_symbols import format_occ_option_symbol, position_intent_for_opening_leg

        # Check options buying power before proceeding
        try:
            acct_raw = self.alpaca.get_account()
            options_bp = float(acct_raw.get("options_buying_power", 0) or 0)
            est_cost = _options_risk_budget(proposal, self.get_account_snapshot())
            if options_bp > 0 and est_cost > options_bp:
                LOGGER.error(
                    "Insufficient options buying power: need $%.2f, have $%.2f",
                    est_cost, options_bp,
                )
                return {"error": "insufficient_options_buying_power", "status": "failed"}
        except Exception as exc:
            LOGGER.debug("Options BP check skipped: %s", exc)

        if proposal.spread_legs and len(proposal.spread_legs) >= 2:
            legs_fmt: list[dict[str, str]] = []
            occ_symbols: list[str] = []
            for leg in proposal.spread_legs:
                occ = format_occ_option_symbol(
                    proposal.symbol,
                    leg.expiry_date,
                    leg.option_type,
                    float(leg.strike),
                )
                occ_symbols.append(occ)
                legs_fmt.append(
                    {
                        "symbol": occ,
                        "side": leg.side.lower(),
                        "position_intent": position_intent_for_opening_leg(leg.side),
                        "ratio_qty": str(max(1, int(leg.quantity))),
                    }
                )

            expiry_str = proposal.spread_legs[0].expiry_date.isoformat()
            better_expiry = _try_validate_occ_for_any_expiry(
                self.alpaca, proposal.symbol, expiry_str, occ_symbols,
            )
            if better_expiry is None:
                LOGGER.error(
                    "Invalid OCC symbols for %s expiry %s; no fallback found",
                    proposal.symbol, expiry_str,
                )
                return {"error": f"no valid option symbols for {proposal.symbol}", "status": "failed"}
            if better_expiry != expiry_str:
                # Regenerate OCC symbols with the new expiry
                occ_symbols.clear()
                legs_fmt.clear()
                for leg in proposal.spread_legs:
                    occ = format_occ_option_symbol(
                        proposal.symbol,
                        date.fromisoformat(better_expiry),
                        leg.option_type,
                        float(leg.strike),
                    )
                    occ_symbols.append(occ)
                    legs_fmt.append(
                        {
                            "symbol": occ,
                            "side": leg.side.lower(),
                            "position_intent": position_intent_for_opening_leg(leg.side),
                            "ratio_qty": str(max(1, int(leg.quantity))),
                        }
                    )

            return self.alpaca.place_multileg_option_order(legs_fmt, order_type="market")
        if proposal.instrument in (Instrument.CALL, Instrument.PUT):
            if proposal.expiry_date is None or proposal.strike is None:
                return {"error": "missing expiry or strike", "status": "failed"}
            right = "call" if proposal.instrument == Instrument.CALL else "put"
            occ = format_occ_option_symbol(
                proposal.symbol,
                proposal.expiry_date,
                right,
                float(proposal.strike),
            )
            expiry_str = proposal.expiry_date.isoformat()
            better_expiry = _try_validate_occ_for_any_expiry(
                self.alpaca, proposal.symbol, expiry_str, [occ],
            )
            if better_expiry is None:
                return {"error": f"non-existent option symbol: {occ}", "status": "failed"}
            if better_expiry != expiry_str:
                occ = format_occ_option_symbol(
                    proposal.symbol,
                    date.fromisoformat(better_expiry),
                    right,
                    float(proposal.strike),
                )
            side = "buy" if proposal.direction.value == "LONG" else "sell"
            return self.alpaca.place_single_option_market_order(occ, qty=1, side=side)
        return {"error": f"unsupported instrument {proposal.instrument}", "status": "failed"}

    def submit_order(self, proposal: TradeProposal) -> str:
        if proposal.instrument == Instrument.POLYMARKET_EVENT:
            return f"failed_{uuid4()}"
        th = self.settings.broker_circuit_failure_threshold
        if th > 0 and time.monotonic() < self._circuit_open_until:
            raise BrokerCircuitOpenError("broker circuit cooldown active")

        account = self.get_account_snapshot()
        try:
            if proposal.instrument == Instrument.EQUITY:
                notional = max(1.0, account.equity * (proposal.position_size_pct / 100.0))
                direction = proposal.direction.value
                if direction == "NEUTRAL":
                    body = {"error": "neutral_equity_not_supported", "status": "failed"}
                elif direction == "LONG":
                    body = self.alpaca.place_notional_market_order(
                        proposal.symbol, notional, side="buy"
                    )
                else:
                    price = max(float(proposal.entry_price or 1.0), 1.0)
                    qty = max(1, int(notional / price))
                    body = self.alpaca.place_order(
                        proposal.symbol, qty, side="sell", order_type="market"
                    )
            else:
                body = self._submit_alpaca_options_order(proposal)
        except Exception:
            self._record_broker_failure()
            raise

        oid = str(body.get("id", ""))
        if oid and "error" not in body:
            self._reset_circuit()
            return oid
        LOGGER.error("Alpaca order failed: %s", body)
        self._record_broker_failure()
        return f"failed_{uuid4()}"

    def monitor_fill(self, order_id: str, timeout_seconds: int = 300) -> tuple[bool, str]:
        if order_id.startswith("failed_"):
            return False, "submit_failed"
        deadline = time.monotonic() + timeout_seconds
        terminal_ok = {"filled", "partially_filled"}
        terminal_bad = {"canceled", "cancelled", "expired", "rejected", "failed"}
        back = min(1.0, max(0.1, float(self.settings.broker_submit_backoff_sec)))
        while time.monotonic() < deadline:
            try:
                od = call_with_retries(
                    lambda: self.alpaca.get_order(order_id),
                    max_attempts=max(1, int(self.settings.broker_get_order_max_attempts)),
                    backoff_seconds=back,
                    log_label=f"get_order:{order_id}",
                )
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Alpaca get_order failed after retries: %s", exc)
                time.sleep(2.0)
                continue
            status = str(od.get("status", "")).lower()
            if status in terminal_ok:
                self._reset_circuit()
                return True, f"filled:{status}"
            if status in terminal_bad:
                return False, status or "bad_terminal"
            time.sleep(2.0)
        return False, "timeout"

    def cancel_order(self, order_id: str) -> None:
        self.alpaca.cancel_order(order_id)

    def get_order(self, order_id: str) -> dict[str, Any]:
        return self.alpaca.get_order(order_id)

    def get_orders(self, status: str = "open") -> list[dict[str, Any]]:
        return self.alpaca.get_orders(status=status)

    def close_symbol_position(self, symbol: str) -> bool:
        """Market-liquidate an equity position via Alpaca (paper or live)."""
        body = self.alpaca.close_stock_position(symbol)
        return "error" not in body and body.get("http_status") is None


def _pm_position_key(proposal: TradeProposal) -> str:
    return f"PM:{proposal.polymarket_market_id}|{proposal.polymarket_outcome_side}"


@dataclass
class PaperPolymarketBroker:
    """Simulated Polymarket bankroll and positions (no on-chain orders)."""

    settings: Settings
    bankroll: float = field(init=False)
    buying_power: float = field(init=False)
    positions: dict[str, Position] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.bankroll = float(self.settings.polymarket_paper_bankroll_usd)
        self.buying_power = self.bankroll

    def get_account_snapshot(self) -> AccountSnapshot:
        return AccountSnapshot(
            equity=self.bankroll,
            buying_power=self.buying_power,
            daily_pl_pct=0.0,
            open_positions=list(self.positions.values()),
        )

    def get_positions(self) -> list[Position]:
        return list(self.positions.values())

    def preview_order(self, proposal: TradeProposal) -> tuple[bool, str]:
        if proposal.instrument != Instrument.POLYMARKET_EVENT:
            return False, "not_a_polymarket_event_proposal"
        stake = float(proposal.polymarket_stake_usd)
        if stake > float(self.settings.polymarket_paper_max_order_usd):
            return False, "stake_exceeds_polymarket_paper_max_order_usd"
        if stake > self.buying_power + 1e-9:
            return False, "insufficient_polymarket_paper_buying_power"
        cap = int(self.settings.polymarket_paper_max_open_positions)
        key = _pm_position_key(proposal)
        if len(self.positions) >= cap and key not in self.positions:
            return False, "polymarket_paper_max_open_positions"
        return True, "polymarket_paper_preview_ok"

    def submit_order(self, proposal: TradeProposal) -> str:
        if proposal.instrument != Instrument.POLYMARKET_EVENT:
            return f"failed_{uuid4()}"
        order_id = str(uuid4())
        key = _pm_position_key(proposal)
        stake = float(proposal.polymarket_stake_usd)
        self.buying_power -= stake
        if key in self.positions:
            old = self.positions[key]
            self.positions[key] = Position(
                symbol=key,
                qty=old.qty + 1.0,
                market_value=old.market_value + stake,
                sector="POLYMARKET",
                avg_entry_price=float(proposal.entry_price),
                side="long",
                correlation_to_book=0.05,
                entry_time=old.entry_time,
            )
        else:
            self.positions[key] = Position(
                symbol=key,
                qty=1.0,
                market_value=stake,
                sector="POLYMARKET",
                avg_entry_price=float(proposal.entry_price),
                side="long",
                correlation_to_book=0.05,
                entry_time=datetime.now(tz=timezone.utc),
            )
        return order_id

    def monitor_fill(self, order_id: str, timeout_seconds: int = 300) -> tuple[bool, str]:
        _ = timeout_seconds
        return True, f"filled:{order_id}"

    def cancel_order(self, order_id: str) -> None:
        _ = order_id

    def get_order(self, order_id: str) -> dict[str, Any]:
        if order_id.startswith("failed_"):
            return {"id": order_id, "status": "failed", "error": "simulated_submit_failure"}
        return {"id": order_id, "status": "filled"}

    def close_symbol_position(self, symbol: str) -> bool:
        pos = self.positions.pop(symbol, None)
        if pos is None:
            return False
        self.buying_power += pos.market_value
        return True


def _kalshi_position_key(ticker: str, side: str = "YES") -> str:
    return f"KALSHI:{ticker}|{side.upper()}"


@dataclass
class PaperKalshiBroker:
    """Simulated Kalshi event positions (paper-only; no live Kalshi orders)."""

    settings: Settings
    bankroll: float = field(init=False)
    buying_power: float = field(init=False)
    positions: dict[str, Position] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.bankroll = float(self.settings.kalshi_paper_bankroll_usd)
        self.buying_power = self.bankroll

    def get_positions(self) -> list[Position]:
        return list(self.positions.values())

    def submit_yes_leg(
        self,
        ticker: str,
        stake_usd: float,
        price: float,
    ) -> str:
        order_id = f"KALSHI_PAPER_{uuid4().hex[:12]}"
        key = _kalshi_position_key(ticker, "YES")
        self.buying_power = max(0.0, self.buying_power - stake_usd)
        if key in self.positions:
            old = self.positions[key]
            self.positions[key] = Position(
                symbol=key,
                qty=old.qty + 1.0,
                market_value=old.market_value + stake_usd,
                sector="KALSHI",
                avg_entry_price=price,
                side="long",
                correlation_to_book=0.05,
                entry_time=old.entry_time,
            )
        else:
            self.positions[key] = Position(
                symbol=key,
                qty=1.0,
                market_value=stake_usd,
                sector="KALSHI",
                avg_entry_price=price,
                side="long",
                correlation_to_book=0.05,
                entry_time=datetime.now(tz=timezone.utc),
            )
        LOGGER.info("Kalshi paper YES leg %s @ %.3f stake $%.2f", ticker, price, stake_usd)
        return order_id

    def monitor_fill(self, order_id: str, timeout_seconds: int = 300) -> tuple[bool, str]:
        _ = timeout_seconds
        if order_id.startswith("failed_"):
            return False, "simulated_submit_failure"
        return True, f"filled:{order_id}"

    def cancel_order(self, order_id: str) -> None:
        _ = order_id

    def get_order(self, order_id: str) -> dict[str, Any]:
        if order_id.startswith("failed_"):
            return {"id": order_id, "status": "failed"}
        return {"id": order_id, "status": "filled"}

    def close_symbol_position(self, symbol: str) -> bool:
        pos = self.positions.pop(symbol, None)
        if pos is None:
            return False
        self.buying_power += pos.market_value
        return True


@dataclass
class VenueRoutingBroker:
    """
    Routes execution: equities/options to ``equity_broker`` (Tradier, Alpaca, or Paper),
    ``Instrument.POLYMARKET_EVENT`` to optional ``polymarket_paper``.
    """

    equity_broker: AlpacaBrokerAdapter | PaperBrokerSimulator
    polymarket_paper: PaperPolymarketBroker | None
    settings: Settings
    kalshi_paper: PaperKalshiBroker | None = None
    _order_venue: dict[str, str] = field(default_factory=dict)

    def active_broker(self, proposal: TradeProposal) -> Any:
        if proposal.instrument == Instrument.POLYMARKET_EVENT:
            if not self.settings.polymarket_paper_trading_enabled or self.polymarket_paper is None:
                raise MalformedProposalError(
                    "Polymarket paper trading disabled; set POLYMARKET_PAPER_TRADING_ENABLED=1"
                )
            return self.polymarket_paper
        return self.equity_broker

    def get_account_snapshot(self) -> AccountSnapshot:
        return self.equity_broker.get_account_snapshot()

    def preview_order(self, proposal: TradeProposal) -> tuple[bool, str]:
        return self.active_broker(proposal).preview_order(proposal)

    def submit_order(self, proposal: TradeProposal) -> str:
        if proposal.instrument == Instrument.POLYMARKET_EVENT:
            if self.polymarket_paper is None:
                return f"failed_{uuid4()}"
            oid = self.polymarket_paper.submit_order(proposal)
            self._order_venue[oid] = "pm"
            return oid
        oid = self.equity_broker.submit_order(proposal)
        self._order_venue[oid] = "eq"
        return oid

    def monitor_fill(self, order_id: str, timeout_seconds: int = 300) -> tuple[bool, str]:
        venue = self._order_venue.get(order_id)
        if venue == "pm" and self.polymarket_paper is not None:
            return self.polymarket_paper.monitor_fill(order_id, timeout_seconds)
        if venue == "kalshi" and self.kalshi_paper is not None:
            return self.kalshi_paper.monitor_fill(order_id, timeout_seconds)
        return self.equity_broker.monitor_fill(order_id, timeout_seconds)

    def cancel_order(self, order_id: str) -> None:
        if self._order_venue.get(order_id) == "pm" and self.polymarket_paper is not None:
            self.polymarket_paper.cancel_order(order_id)
            return
        self.equity_broker.cancel_order(order_id)

    def get_order(self, order_id: str) -> dict[str, Any]:
        if self._order_venue.get(order_id) == "pm" and self.polymarket_paper is not None:
            return self.polymarket_paper.get_order(order_id)
        return self.equity_broker.get_order(order_id)

    def get_orders(self, status: str = "open") -> list[dict[str, Any]]:
        return self.equity_broker.get_orders(status=status)

    def get_positions(self) -> list[Position]:
        out = list(self.equity_broker.get_positions())
        if self.polymarket_paper is not None:
            out.extend(self.polymarket_paper.get_positions())
        if self.kalshi_paper is not None:
            out.extend(self.kalshi_paper.get_positions())
        return out

    async def submit_polymarket_paper(
        self,
        market_id: str,
        outcome: str,
        stake_usd: float,
        price: float,
    ) -> str:
        if not self.settings.polymarket_paper_trading_enabled or self.polymarket_paper is None:
            raise MalformedProposalError(
                "Polymarket paper trading disabled; set POLYMARKET_PAPER_TRADING_ENABLED=1"
            )
        proposal = TradeProposal(
            symbol=f"PM:{market_id}",
            direction=Direction.LONG,
            instrument=Instrument.POLYMARKET_EVENT,
            entry_price=float(price),
            position_size_pct=1.0,
            stop_loss=max(0.01, float(price) - 0.05),
            take_profit=min(0.99, float(price) + 0.1),
            max_loss_dollars=float(stake_usd),
            conviction_final=5.0,
            judge_rationale="arb_paper_poly_leg",
            dissenting_view="",
            polymarket_market_id=str(market_id),
            polymarket_outcome_side=str(outcome).upper(),
            polymarket_stake_usd=float(stake_usd),
        )
        ok, reason = self.polymarket_paper.preview_order(proposal)
        if not ok:
            raise MalformedProposalError(f"polymarket_paper_preview_failed:{reason}")
        oid = self.polymarket_paper.submit_order(proposal)
        self._order_venue[oid] = "pm"
        return oid

    async def submit_kalshi_paper(
        self,
        ticker: str,
        stake_usd: float,
        price: float,
    ) -> str:
        if self.kalshi_paper is None:
            raise MalformedProposalError("Kalshi paper broker not configured")
        oid = self.kalshi_paper.submit_yes_leg(ticker, float(stake_usd), float(price))
        self._order_venue[oid] = "kalshi"
        return oid

    def close_symbol_position(self, symbol: str) -> bool:
        if symbol.startswith("PM:") and self.polymarket_paper is not None:
            return self.polymarket_paper.close_symbol_position(symbol)
        if symbol.startswith("KALSHI:") and self.kalshi_paper is not None:
            return self.kalshi_paper.close_symbol_position(symbol)
        closer = getattr(self.equity_broker, "close_symbol_position", None)
        return bool(closer and closer(symbol))
