import discord
import os
import re
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Import the trader module
from trader import execute_paper_trade

# NEW Channel ID for #🐂-ai-bullseye
TARGET_CHANNEL_ID = 1410785669780869201

class ZenTradingBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    async def on_ready(self):
        print(f'🚀 Logged on to Discord as {self.user}!')
        print(f'🎧 Listening for AI Bullseye alerts in channel {TARGET_CHANNEL_ID}...')
        
        # Try to fetch recent messages from the channel on startup
        try:
            channel = self.get_channel(TARGET_CHANNEL_ID)
            if channel:
                print(f"📡 Fetching recent messages from #{channel.name}...")
                async for message in channel.history(limit=10):
                    await self.process_message(message)
        except Exception as e:
            print(f"⚠️ Could not fetch message history: {e}")

    async def on_message(self, message):
        """Handle new messages"""
        await self.process_message(message)
    
    async def on_message_edit(self, before, after):
        """Handle edited messages"""
        print(f"[EDIT] {after.author}: {after.content[:50] if after.content else '[embed]'}")
        await self.process_message(after)
    
    async def process_message(self, message):
        """Process a message for trading signals"""
        # 1. Target the specific AI Bullseye channel
        if message.channel.id != TARGET_CHANNEL_ID:
            return
        
        # DEBUG: Log all messages in the channel
        print(f"\n📬 [{message.id}] From {message.author}: {message.content[:80] if message.content else '[embed only]'}")
        if message.embeds:
            print(f"   📊 Embeds: {len(message.embeds)}")
            for i, embed in enumerate(message.embeds):
                print(f"      Embed {i}: title='{embed.title}', desc_len={len(embed.description or '')}, fields={len(embed.fields)}")
        
        # 2. Extract text from the message OR the embed
        full_text = message.content if message.content else ""
        if message.embeds:
            for embed in message.embeds:
                if embed.title: 
                    full_text += " " + embed.title
                if embed.description: 
                    full_text += " " + embed.description
                for field in embed.fields:
                    full_text += f" {field.name} {field.value}"
        
        if full_text:
            print(f"   Full text: {full_text[:150]}")
        
        # 3. Check if it's a valid trade idea (multiple possible triggers)
        if "Bullseye Trade Idea" in full_text or "bullseye" in full_text.lower():
            print(f"\n🚨 New Bullseye Signal Detected!")
            
            # 4. Clean and parse
            signal_data = self.parse_signal(full_text)
            
            if signal_data:
                print(f"📊 Parsed Data: {signal_data}")
                execute_paper_trade(signal_data)
            else:
                print(f"❌ Failed to parse signal data from message")
                    
    def parse_signal(self, text):
        """Strips markdown and uses Regex to extract the Bullseye variables."""
        clean_text = text.replace('*', '').replace('`', '').replace('\n', ' ')
        
        try:
            ticker = re.search(r'Symbol\s+([A-Z]+)', clean_text).group(1)
            strike = float(re.search(r'Strike\s+([\d\.]+)', clean_text).group(1))
            # Grabs date format like 5/15/2026
            expiration = re.search(r'Expiration\s+(\d{1,2}/\d{1,2}/\d{4})', clean_text).group(1)
            option_type = re.search(r'Call/Put\s+(Call|Put)', clean_text, re.IGNORECASE).group(1).upper()
            action = re.search(r'Buy/Sell\s+(Buy|Sell)', clean_text, re.IGNORECASE).group(1).upper()
            
            # Safety check: Only execute BUY alerts to open positions
            if action != "BUY":
                print("⚠️ Signal is a SELL. Ignoring entry.")
                return None
                
            return {
                "ticker": ticker,
                "type": option_type,
                "strike": strike,
                "expiration": expiration
            }
        except (AttributeError, TypeError) as e:
            print(f"⚠️ Failed to parse regex from message. Error: {e}")
            return None

# Run the bot (NO INTENTS)
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_USER_TOKEN")
    client = ZenTradingBot()
    client.run(TOKEN)
