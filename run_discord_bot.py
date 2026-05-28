#!/usr/bin/env python3
"""APEX Discord Bot Launcher - Starts the Discord Bullseye listener"""
import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Discord-specific paths
DISCORD_DIR = Path(__file__).resolve().parent / "Discord" / "zen_instatrade"

# Load Discord-specific keys first (isolated from main keys.env)
discord_keys = DISCORD_DIR / "keys.env"
if discord_keys.exists():
    load_dotenv(discord_keys, override=True)
    print(f"Loaded Discord keys from: {discord_keys}")

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from apex.integrations.discord_bot import get_discord_integration  # noqa: E402
from apex.integrations.discord_exit_manager import get_discord_exit_manager  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/tmp/apex-discord.log"),
    ]
)

logger = logging.getLogger("apex-discord")

async def main():
    # Load main .env for APEX engine config (but Discord keys already loaded)
    load_dotenv(Path(__file__).resolve().parent / ".env")
    
    token = os.getenv("DISCORD_USER_TOKEN")
    if not token:
        logger.error("DISCORD_USER_TOKEN not set - cannot start Discord bot")
        sys.exit(1)
    
    logger.info("Starting APEX Discord Integration...")
    logger.info(f"Discord keys loaded from: {discord_keys}")
    
    # Start exit manager monitoring loop
    exit_manager = get_discord_exit_manager()
    
    async def run_exit_manager():
        await exit_manager.run_monitoring_loop()
    
    # Start Discord bot
    bot = get_discord_integration()
    if bot:
        logger.info("Launching Discord bot...")
        
        # Run both the bot and exit manager concurrently
        await asyncio.gather(
            bot.start(),
            run_exit_manager(),
            return_exceptions=True,
        )
    else:
        logger.error("Failed to initialize Discord bot")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Discord bot stopped by user")
    except Exception as e:
        logger.error(f"Discord bot crashed: {e}", exc_info=True)
        sys.exit(1)
