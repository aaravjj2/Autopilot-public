# 🤖 Zen AI Trading Bot - Auto-Exit System

## Overview

This system automatically executes trades from Zen AI Bullseye signals and manages exits using intelligent stop-loss and take-profit triggers.

## Components

### 1. **main.py** - Discord Bot
- Listens to `#🐂-ai-bullseye` Discord channel
- Detects "Bullseye Trade Idea" signals
- Parses: Ticker, Strike, Expiration, Call/Put, Buy/Sell
- Executes **market orders** for BUY signals only
- Logs all trades to `trades.db`

### 2. **exit_manager.py** - Trade Monitor
- Monitors all open positions
- Checks exit conditions every 5 minutes:
  - **Take Profit**: When price reaches target
  - **Stop Loss**: When price hits stop loss
  - **Expiration**: Automatically exits on expiration day
- Automatically sells positions when triggered
- Updates trade status and exit price

### 3. **scheduler.py** - Automated Runner
- Runs `exit_manager.py` every 5 minutes
- Prints portfolio summary every 30 minutes
- Keeps system monitoring 24/7

## Installation

```bash
pip install -r requirements.txt
```

## Running the System

### Option 1: All Components (Recommended)

```bash
# Terminal 1: Discord Bot (listens for signals)
python main.py

# Terminal 2: Trade Scheduler (monitors exits)
python scheduler.py
```

### Option 2: Manual Monitoring

```bash
# One-time check
python exit_manager.py
```

## Database Schema

All trades are stored in `trades.db` (SQLite):

```sql
CREATE TABLE trades (
    id TEXT PRIMARY KEY,              -- Order ID from Alpaca
    symbol TEXT NOT NULL,              -- OCC symbol (e.g., AG260618C00022000)
    ticker TEXT NOT NULL,              -- Stock ticker (e.g., AG)
    strike REAL NOT NULL,              -- Strike price (e.g., 22.0)
    expiration TEXT NOT NULL,          -- Expiration date (e.g., 6/18/2026)
    type TEXT NOT NULL,                -- CALL or PUT
    entry_price REAL NOT NULL,         -- Entry premium (e.g., 0.90)
    target REAL,                       -- Take profit target
    stop_loss REAL,                    -- Stop loss level
    status TEXT DEFAULT 'open',        -- open, closed, closed_manual
    placed_at DATETIME,                -- When trade was placed
    exit_price REAL,                   -- Exit premium (when sold)
    exit_at DATETIME                   -- When trade was closed
);
```

## Example Flow

### Entry
```
1. Discord Bot detects: "AG CALL, Strike $22, Expiration 6/18, Target $21.50, Stop $0.45"
2. Executes BUY order at market price ($0.90)
3. Logs to trades.db: {id, symbol, ticker, strike, expiration, target, stop_loss}
4. Status: OPEN
```

### Monitoring
```
Every 5 minutes:
- Fetch current position price
- Check: Is price >= $21.50 (target)? → YES → SELL
- Check: Is price <= $0.45 (stop)? → NO
- Check: Is expiration <= 1 day away? → NO
- Result: EXIT → SELL at market
```

### Exit
```
Status: CLOSED
Exit Price: $21.50
P&L: ($21.50 - $0.90) × 100 = $2,060 profit
```

## Configuration

Edit these in `exit_manager.py` if needed:

```python
# Check frequency
schedule.every(5).minutes.do(run_exit_check)  # Change to 1, 10, etc.

# Market hours (currently runs 24/7)
# Add time filters in run_exit_check() if needed
```

## Monitoring Commands

### Check Current Trades
```bash
python exit_manager.py
```

### View Database
```bash
sqlite3 trades.db "SELECT * FROM trades WHERE status='open';"
```

### Follow Bot Logs
```bash
tail -f /tmp/zen_bot.log
```

### Follow Scheduler Logs
```bash
tail -f /tmp/scheduler.log
```

## Status Codes

- **open**: Position is active, monitoring for exits
- **closed**: Position exited automatically (target/stop/expiration)
- **closed_manual**: Position was manually closed or no longer exists

## Safety Features

✅ **Stop Loss Protection**: Automatically exits at stop loss level
✅ **Take Profit**: Scales out at target price
✅ **Expiration Management**: Closes positions on or before expiration
✅ **Position Tracking**: All trades logged to database
✅ **Real-time Monitoring**: Checks every 5 minutes
✅ **Error Handling**: Catches and logs all exceptions

## Example Portfolio Output

```
======================================================================
📊 TRADE PORTFOLIO SUMMARY
======================================================================

🟢 OPEN TRADES (2):
  • AG: $22.0 CALL | Entry: $0.9 | Target: $21.5 | Stop: $0.45
  • NVDA: $235.0 CALL | Entry: $2.50 | Target: $285 | Stop: $1.25

⚫ CLOSED TRADES (5):
  • XLE: $60.0 CALL | Entry: $1.20 | Exit: $2.15 | P&L: $95.00 (+79.2%)
  • META: $620.0 CALL | Entry: $3.50 | Exit: $1.75 | P&L: -$175.00 (-50.0%)
  • TLT: $85.0 CALL | Entry: $0.95 | Exit: $1.90 | P&L: $95.00 (+100.0%)
======================================================================
```

## Troubleshooting

### "asset not found" error
- OCC symbol format is wrong
- Check strike price is valid
- Verify expiration date is valid

### Scheduler not running
```bash
ps aux | grep scheduler.py
jobs
```

### Database locked
```bash
# Reset database
rm trades.db
python exit_manager.py  # Recreates it
```

### No positions found
- Check Alpaca account has capital
- Verify orders filled (check Alpaca dashboard)
- Confirm symbol is correct

## Next Steps

- [ ] Add email alerts on trade exits
- [ ] Add Discord notifications for exits
- [ ] Implement profit/loss alerts
- [ ] Add portfolio value tracking
- [ ] Create web dashboard

---

**Bot Status**: Ready to trade! 🚀
