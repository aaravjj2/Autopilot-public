"""APEX Discord Integration - Bullseye Signal Listener with Brain"""
from __future__ import annotations

import os
import re
import logging
from datetime import datetime
from typing import Any
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Channel ID for #🐂-ai-bullseye
TARGET_CHANNEL_ID = 1410785669780869201

class DiscordSignalParser:
    """Parses Bullseye Trade Idea signals from Discord messages."""
    
    @staticmethod
    def parse_signal(text: str) -> dict[str, Any] | None:
        """Extract trading signal from Discord message text."""
        clean_text = text.replace('*', '').replace('`', '').replace('\n', ' ')
        
        try:
            ticker = re.search(r'Symbol\s+([A-Z]+)', clean_text).group(1)
            strike = float(re.search(r'Strike\s+([\d\.]+)', clean_text).group(1))
            expiration = re.search(r'Expiration\s+(\d{1,2}/\d{1,2}/\d{4})', clean_text).group(1)
            option_type = re.search(r'Call/Put\s+(Call|Put)', clean_text, re.IGNORECASE).group(1).upper()
            action = re.search(r'Buy/Sell\s+(Buy|Sell)', clean_text, re.IGNORECASE).group(1).upper()
            
            if action != "BUY":
                logger.info(f"Ignoring SELL signal for {ticker}")
                return None
            
            return {
                "ticker": ticker,
                "type": option_type,
                "strike": strike,
                "expiration": expiration,
                "source": "discord_bullseye",
            }
        except (AttributeError, TypeError) as e:
            logger.warning(f"Failed to parse Discord signal: {e}")
            return None
    
    @staticmethod
    def extract_text_from_message(content: str, embeds: list[dict] | None = None) -> str:
        """Combine message content and embed text for parsing."""
        full_text = content or ""
        if embeds:
            for embed in embeds:
                if embed.get("title"):
                    full_text += " " + embed["title"]
                if embed.get("description"):
                    full_text += " " + embed["description"]
                for field in embed.get("fields", []):
                    full_text += f" {field.get('name', '')} {field.get('value', '')}"
        return full_text


class DiscordTradeStore:
    """Wrapper around consolidated SQLiteStore for Discord-originated trades."""
    
    def __init__(self, db_path: str | Path = "data/audit.db"):
        from apex.repositories.sqlite_store import SQLiteStore
        self.store = SQLiteStore(Path(db_path))
    
    def add_trade(self, trade: dict[str, Any]) -> bool:
        """Add a Discord trade to the consolidated database."""
        return self.store.add_discord_trade({
            "id": trade["order_id"],
            "message_id": trade.get("message_id"),
            "symbol": trade["symbol"],
            "ticker": trade["ticker"],
            "strike": trade["strike"],
            "expiration": trade["expiration"],
            "type": trade["type"],
            "entry_price": trade.get("entry_price"),
            "target": trade.get("target"),
            "stop_loss": trade.get("stop_loss"),
            "status": "open",
            "conviction": trade.get("conviction", 8.0),
            "risk_score": trade.get("risk_score", 50),
            "contracts": trade.get("contracts", 1),
            "brain_approved": trade.get("brain_approved", False),
            "brain_reason": trade.get("brain_reason", ""),
        })
    
    def update_trade(self, order_id: str, updates: dict[str, Any]) -> bool:
        """Update a Discord trade."""
        return self.store.update_discord_trade(order_id, updates)
    
    def get_open_trades(self) -> list[dict]:
        """Get all open Discord trades."""
        return self.store.get_open_discord_trades()
    
    def get_portfolio_stats(self) -> dict[str, Any]:
        """Get Discord trade portfolio stats."""
        return self.store.get_discord_trade_stats()
    
    def get_all_trades(self, limit: int = 50) -> list[dict]:
        """Get recent Discord trades."""
        return self.store.read_table("discord_trades", limit=limit)
    
    def get_trade_stats(self) -> dict:
        """Get Discord trade portfolio stats."""
        return self.store.get_discord_trade_stats()


class DiscordBullseyeBot:
    """Discord bot with BRAIN - validates and executes trades intelligently."""
    
    def __init__(self, token: str | None = None, channel_id: int = TARGET_CHANNEL_ID):
        self.token = token or os.getenv("DISCORD_USER_TOKEN")
        self.channel_id = channel_id
        self.parser = DiscordSignalParser()
        self.store = DiscordTradeStore()
        self._client = None
        
        # Import brain
        from apex.integrations.discord_brain import get_discord_brain
        self.brain = get_discord_brain()
    
    async def start(self):
        """Start the Discord bot."""
        try:
            import discord
        except ImportError:
            logger.error("discord.py-self not installed. Run: pip install discord.py-self")
            return
        
        class ZenTradingBot(discord.Client):
            def __init__(bot_self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                bot_self.parent = self
            
            async def on_ready(bot_self):
                logger.info(f"🤖 Discord bot logged in as {bot_self.user}")
                logger.info(f"🎯 Listening for Bullseye alerts in channel {self.channel_id}")
                logger.info("🧠 Brain active - evaluating signals before execution")
                
                try:
                    channel = bot_self.get_channel(self.channel_id)
                    if channel:
                        logger.info(f"📡 Fetching recent messages from #{channel.name}...")
                        try:
                            async for message in channel.history(limit=10):
                                await bot_self.process_message(message)
                        except TypeError as te:
                            if "'>' not supported" in str(te):
                                logger.warning("Message history fetch failed (discord.py-self compatibility issue) - will process new messages only")
                            else:
                                raise
                except Exception as e:
                    logger.warning(f"Could not fetch message history: {e}")
            
            async def on_message(bot_self, message):
                await bot_self.process_message(message)
            
            async def on_message_edit(bot_self, before, after):
                await bot_self.process_message(after)
            
            async def process_message(bot_self, message):
                if message.channel.id != self.channel_id:
                    return
                
                logger.debug(f"[{message.id}] From {message.author}: {message.content[:80] if message.content else '[embed]'}")
                
                full_text = self.parser.extract_text_from_message(
                    message.content,
                    [{"title": e.title, "description": e.description, "fields": [{"name": f.name, "value": f.value} for f in e.fields]} for e in message.embeds] if message.embeds else None
                )
                
                if "Bullseye Trade Idea" in full_text or "bullseye" in full_text.lower():
                    logger.info("🚨 New Bullseye Signal Detected!")
                    
                    signal_data = self.parser.parse_signal(full_text)
                    if signal_data:
                        signal_data["message_id"] = str(message.id)
                        signal_data["author"] = str(message.author)
                        await self.on_signal_received(signal_data)
                    else:
                        logger.warning("❌ Failed to parse signal data")
        
        self._client = ZenTradingBot()
        await self._client.start(self.token)
    
    async def on_signal_received(self, signal: dict[str, Any]):
        """Handle a new Bullseye signal - BRAIN evaluates before execution."""
        logger.info(f"🧠 Processing Discord signal: {signal}")
        
        try:
            # Get current portfolio state for risk assessment
            portfolio_state = await self._get_portfolio_state()
            
            # BRAIN evaluates the signal
            evaluation = await self.brain.evaluate_signal(signal, portfolio_state)
            
            logger.info(f"🧠 Brain verdict: {evaluation['verdict']} - {evaluation['reason']}")
            
            if evaluation["verdict"] == "approve":
                await self._execute_approved_trade(signal, evaluation)
            else:
                await self._log_rejected_signal(signal, evaluation)
        except Exception as e:
            logger.error(f"❌ Brain evaluation failed: {e}", exc_info=True)
    
    async def _get_portfolio_state(self) -> dict:
        """Get current portfolio state for risk assessment."""
        try:
            from apex.integrations.alpaca_adapter import AlpacaDirectIntegration
            alpaca = AlpacaDirectIntegration()
            
            account = alpaca.get_account()
            positions = alpaca.get_positions()
            
            return {
                "equity": float(account.get("equity", 100000)),
                "buying_power": float(account.get("buying_power", 0)),
                "positions": positions,
                "trades_today": 0,  # Would track from database
                "sectors": {},  # Would calculate from positions
            }
        except Exception as e:
            logger.warning(f"Failed to get portfolio state: {e}")
            return {"equity": 100000.0, "buying_power": 0.0, "positions": [], "trades_today": 0, "sectors": {}}
    
    async def _execute_approved_trade(self, signal: dict, evaluation: dict):
        """Execute a trade that the brain has approved."""
        ticker = signal["ticker"]
        strike = signal["strike"]
        expiration = signal["expiration"]
        option_type = signal["type"]
        contracts = evaluation.get("position_size", 1)
        stop_loss = evaluation.get("stop_loss")
        take_profit = evaluation.get("take_profit")
        conviction = evaluation.get("conviction", 8.0)
        
        # Generate OCC symbol
        from apex.integrations.discord_bot import generate_occ_symbol
        occ_symbol = generate_occ_symbol(ticker, expiration, option_type, strike)
        
        logger.info(f"📤 Executing trade: {contracts}x {occ_symbol} (conviction: {conviction:.1f})")
        
        try:
            from apex.integrations.alpaca_adapter import AlpacaDirectIntegration
            from apex.repositories.sqlite_store import SQLiteStore
            from apex.domain.enums import EventType, AuditEvent
            from apex.core.config import get_settings
            
            alpaca = AlpacaDirectIntegration()
            
            # Place market order
            result = alpaca.place_single_option_market_order(
                occ_symbol=occ_symbol,
                qty=contracts,
                side="buy",
            )
            
            if "error" not in result:
                order_id = result.get("id", f"discord-{signal.get('message_id', 'unknown')}")
                
                # Get actual fill price from order result
                actual_entry = result.get("filled_avg_price") or evaluation.get("estimated_entry")
                if actual_entry:
                    actual_entry = float(actual_entry)
                
                # Log trade to store
                self.store.add_trade({
                    "order_id": order_id,
                    "message_id": signal.get("message_id"),
                    "symbol": occ_symbol,
                    "ticker": ticker,
                    "strike": strike,
                    "expiration": expiration,
                    "type": option_type,
                    "entry_price": actual_entry,
                    "target": take_profit,
                    "stop_loss": stop_loss,
                    "conviction": conviction,
                    "risk_score": evaluation.get("risk_score", 50),
                    "contracts": contracts,
                    "brain_approved": True,
                    "brain_reason": evaluation.get("reason", ""),
                })
                
                # Record audit event for engine visibility
                try:
                    settings = get_settings()
                    audit_store = SQLiteStore(settings.sqlite_path)
                    audit_store.append_event(
                        AuditEvent(
                            event_type=EventType.ORDER_SUBMITTED,
                            symbol=occ_symbol,
                            agent="discord_brain",
                            conviction=conviction,
                            order_id=order_id,
                            raw_payload={
                                "source": "discord_bullseye",
                                "ticker": ticker,
                                "strike": strike,
                                "expiration": expiration,
                                "type": option_type,
                                "contracts": contracts,
                                "entry_price": actual_entry,
                                "stop_loss": stop_loss,
                                "take_profit": take_profit,
                                "message_id": signal.get("message_id"),
                                "brain_verdict": "approve",
                                "brain_reason": evaluation.get("reason", ""),
                            },
                        )
                    )
                except Exception as audit_exc:
                    logger.warning(f"Failed to record audit event: {audit_exc}")
                
                logger.info(f"✅ Trade executed: {order_id} | {contracts}x {occ_symbol}")
                logger.info(f"   Entry: ${actual_entry} | Stop Loss: ${stop_loss} | Take Profit: ${take_profit}")
                
                # Record in brain for learning
                self.brain.record_trade_outcome(order_id, 0, 0)
                
            else:
                logger.error(f"❌ Trade execution failed: {result['error']}")
                
        except Exception as e:
            logger.error(f"❌ Trade execution error: {e}")
    
    async def _log_rejected_signal(self, signal: dict, evaluation: dict):
        """Log a signal that the brain rejected."""
        ticker = signal.get("ticker", "unknown")
        reason = evaluation.get("reason", "Unknown")
        
        logger.info(f"❌ Signal rejected for {ticker}: {reason}")
        
        # Still log to store for tracking (but not executed)
        from apex.integrations.discord_bot import generate_occ_symbol
        occ_symbol = generate_occ_symbol(
            signal["ticker"],
            signal["expiration"],
            signal["type"],
            signal["strike"],
        )
        
        self.store.add_trade({
            "order_id": f"rejected-{signal.get('message_id', 'unknown')}",
            "message_id": signal.get("message_id"),
            "symbol": occ_symbol,
            "ticker": ticker,
            "strike": signal["strike"],
            "expiration": signal["expiration"],
            "type": signal["type"],
            "entry_price": None,
            "target": None,
            "stop_loss": None,
            "conviction": evaluation.get("conviction", 0),
            "risk_score": evaluation.get("risk_score", 100),
            "contracts": 0,
            "brain_approved": False,
            "brain_reason": reason,
        })


def generate_occ_symbol(ticker: str, expiration_str: str, option_type: str, strike: float) -> str:
    """Generate OCC option symbol.

    Deprecated: use ``apex.domain.option_symbols.format_occ_option_symbol`` instead.
    """
    from apex.domain.option_symbols import format_occ_option_symbol
    expiry = datetime.strptime(expiration_str, "%m/%d/%Y").date()
    return format_occ_option_symbol(ticker, expiry, option_type, strike)


def get_discord_integration():
    """Get singleton Discord integration instance."""
    load_dotenv()
    token = os.getenv("DISCORD_USER_TOKEN")
    if not token:
        logger.warning("DISCORD_USER_TOKEN not set - Discord integration disabled")
        return None
    return DiscordBullseyeBot(token=token)
