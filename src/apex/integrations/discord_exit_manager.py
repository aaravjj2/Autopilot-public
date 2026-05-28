"""APEX Discord Exit Manager - Monitors and exits Discord-originated trades"""
from __future__ import annotations

import time
import logging
import asyncio
from datetime import datetime, timezone
from typing import Any

from apex.integrations.discord_bot import DiscordTradeStore
from apex.integrations.alpaca_adapter import AlpacaDirectIntegration
from apex.layers.l3.loss_cut_brain import _loss_threshold, _unrealized_pnl_pct

logger = logging.getLogger(__name__)


class DiscordExitManager:
    """Monitors Discord-originated trades and exits based on target/stop-loss/expiration."""

    def __init__(self):
        self.store = DiscordTradeStore()
        self.alpaca = AlpacaDirectIntegration()
        self.check_interval = 300  # 5 minutes
        self.last_scan_summary: dict = {}

    def check_once(self) -> list[dict]:
        """Synchronous entry point — called by the engine scheduler.

        Returns list of exits triggered in this scan.
        """
        import asyncio
        return asyncio.run(self.check_and_exit_trades())

    async def run_monitoring_loop(self):
        """Continuously monitor and exit trades."""
        logger.info("Discord Exit Manager started - checking every 5 minutes")
        while True:
            try:
                exited = await self.check_and_exit_trades()
                await self.print_portfolio_summary()
                if exited:
                    logger.info("Exit manager closed %d trade(s): %s", len(exited), exited)
            except Exception as e:
                logger.error(f"Exit manager check failed: {e}")
            await asyncio.sleep(self.check_interval)

    async def check_and_exit_trades(self) -> list[dict]:
        """Monitor all open trades and exit based on conditions."""
        open_trades = self.store.get_open_trades()
        
        if not open_trades:
            logger.debug("No open Discord trades to monitor")
            return []
        
        logger.info(f"Monitoring {len(open_trades)} open Discord trade(s)...")
        exited = []
        now_sec = time.time()
        alpaca_positions = self.alpaca.get_positions()
        position_map = {p.get("symbol", ""): p for p in alpaca_positions}
        
        for trade in open_trades:
            try:
                occ_symbol = trade["symbol"]
                position = position_map.get(occ_symbol)
                
                if not position:
                    logger.warning(f"{occ_symbol}: No active position found")
                    self.store.update_trade(trade["id"], {"status": "closed_manual"})
                    continue
                
                current_price = float(position.get("current_price", 0))
                entry_price = float(trade.get("entry_price") or 0)
                if entry_price <= 0:
                    entry_price = float(position.get("avg_entry_price", 0))
                
                contracts = float(position.get("qty", trade.get("contracts", 1)))
                current_value = current_price * 100 * contracts
                entry_value = entry_price * 100 * contracts if entry_price else 0
                current_pl = current_value - entry_value if entry_value else 0
                pl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
                
                logger.info(
                    f"{occ_symbol} | Entry: ${entry_price:.2f} | Current: ${current_price:.2f} | P&L: ${current_pl:.2f} ({pl_pct:+.1f}%)"
                )
                
                should_exit = False
                exit_reason = None
                
                # Check target (take profit)
                if trade.get("target") and entry_price > 0:
                    target = float(trade["target"])
                    if current_price >= target:
                        should_exit = True
                        exit_reason = "TARGET_HIT"
                        logger.info(f"  TARGET HIT: ${target:.2f}")
                
                # Check explicit stop loss
                if not should_exit and trade.get("stop_loss") and entry_price > 0:
                    stop_loss = float(trade["stop_loss"])
                    if current_price <= stop_loss:
                        should_exit = True
                        exit_reason = "STOP_LOSS"
                        logger.info(f"  STOP LOSS HIT: ${stop_loss:.2f}")
                
                # Loss cut brain: progressive threshold using Alpaca's unrealized_plpc
                if not should_exit:
                    opened_epoch = _parse_opened_at(position)
                    held = (now_sec - opened_epoch) / 60.0
                    brain_pl = _unrealized_pnl_pct(position)
                    threshold = _loss_threshold(position, held)
                    if brain_pl <= -threshold:
                        should_exit = True
                        exit_reason = f"LOSS_CUT_BRAIN_{abs(threshold):.0f}PCT"
                        logger.info(
                            f"  LOSS CUT BRAIN: P&L={brain_pl:.1f}% threshold={-threshold:.0f}% held={held:.0f}min"
                        )
                
                # Check expiration
                if not should_exit:
                    try:
                        exp_date = datetime.strptime(trade["expiration"], "%m/%d/%Y")
                        days_to_exp = (exp_date - datetime.now()).days
                        if days_to_exp <= 1:
                            should_exit = True
                            exit_reason = "EXPIRATION_NEAR"
                            logger.info(f"  EXPIRATION IN {days_to_exp} DAY(S)")
                    except (ValueError, TypeError):
                        pass
                
                # Execute exit if needed
                if should_exit:
                    logger.info(f"  EXITING: {exit_reason}")
                    is_option = position.get("asset_class") == "us_option"
                    result = await self._sell_position(occ_symbol, qty=contracts, is_option=is_option)
                    if result:
                        self.store.update_trade(trade["id"], {
                            "status": "closed",
                            "exit_price": current_price,
                            "exit_at": datetime.now(tz=timezone.utc).isoformat(),
                        })
                        exited.append({
                            "trade_id": trade["id"],
                            "symbol": occ_symbol,
                            "exit_price": current_price,
                            "reason": exit_reason,
                        })
            
            except Exception as e:
                logger.error(f"Error processing {trade.get('symbol')}: {e}")

        self.last_scan_summary = {
            "scanned_at": datetime.now(tz=timezone.utc).isoformat(),
            "open_trades": len(open_trades),
            "exited": len(exited),
        }
        return exited
    
    async def _sell_position(self, symbol: str, qty: int = 1, is_option: bool = True) -> dict | None:
        """Sell a position at market (handles both option and equity symbols)."""
        try:
            if is_option:
                result = self.alpaca.place_single_option_market_order(
                    occ_symbol=symbol,
                    qty=qty,
                    side="sell",
                )
            else:
                result = self.alpaca.place_order(
                    symbol=symbol,
                    qty=qty,
                    side="sell",
                    order_type="market",
                )
            if "error" not in result:
                logger.info(f"Sell order placed for {symbol}")
                return result
            else:
                logger.error(f"Failed to sell {symbol}: {result['error']}")
                return None
        except Exception as e:
            logger.error(f"Failed to sell {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to sell {symbol}: {e}")
            return None
    
    async def print_portfolio_summary(self) -> dict:
        """Get summary of all Discord trades."""
        stats = self.store.get_trade_stats()
        all_trades = self.store.get_all_trades(limit=20)
        
        open_count = stats.get("open", stats.get("open_trades", 0))
        closed_count = stats.get("closed", stats.get("closed_trades", 0))
        avg_pnl = stats.get("avg_pnl", 0)
        
        logger.info(f"Discord Portfolio: {open_count} open, {closed_count} closed, Avg P&L: ${avg_pnl:.2f}")
        
        return {
            **stats,
            "recent_trades": all_trades[:10],
        }


def get_discord_exit_manager() -> DiscordExitManager:
    """Get singleton Discord exit manager instance."""
    return DiscordExitManager()


def _parse_opened_at(position: dict[str, Any]) -> float:
    """Extract position open time as epoch seconds from Alpaca position dict.

    Falls back to ``now`` if unavailable (default threshold applies).
    """
    raw = position.get("opened_at") or position.get("created_at")
    if raw:
        try:
            if isinstance(raw, (int, float)):
                return float(raw)
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
        except (ValueError, TypeError, AttributeError):
            pass
    return time.time()
