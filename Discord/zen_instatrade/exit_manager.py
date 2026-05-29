import os
import sqlite3
from datetime import datetime, timedelta
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# Load env variables
with open('.env') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            key, val = line.strip().split('=', 1)
            os.environ[key.strip()] = val.strip()

API_KEY = os.getenv("ALPACA_PAPER_KEY")
SECRET_KEY = os.getenv("ALPACA_PAPER_SECRET")
trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)

DB_PATH = "trades.db"

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def check_and_exit_trades():
    """Monitor all open trades and exit based on target/stop loss/expiration"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get all open trades
    cursor.execute("SELECT * FROM trades WHERE status = 'open' ORDER BY placed_at")
    open_trades = cursor.fetchall()
    
    if not open_trades:
        print("📊 No open trades to monitor")
        return
    
    print(f"\n🔍 Monitoring {len(open_trades)} open trade(s)...")
    
    for trade in open_trades:
        try:
            # Get current position info
            positions = trading_client.get_all_positions()
            position = None
            for pos in positions:
                if pos.symbol == trade['symbol']:
                    position = pos
                    break
            
            if not position:
                print(f"⚠️  {trade['symbol']}: No active position found (may have been closed)")
                cursor.execute(
                    "UPDATE trades SET status = 'closed_manual' WHERE id = ?",
                    (trade['id'],)
                )
                conn.commit()
                continue
            
            current_price = float(position.current_price)
            entry_price = float(trade['entry_price'])
            current_value = current_price * 100  # Option contracts are 100 shares
            current_pl = current_value - (entry_price * 100)
            
            print(f"\n📈 {trade['symbol']} (Strike: ${trade['strike']})")
            print(f"   Entry: ${entry_price} | Current: ${current_price:.2f} | P&L: ${current_pl:.2f}")
            
            should_exit = False
            exit_reason = None
            
            # Check target (take profit)
            if trade['target'] and current_price >= trade['target']:
                should_exit = True
                exit_reason = "TARGET_HIT"
                print(f"   ✅ TARGET HIT: ${trade['target']}")
            
            # Check stop loss
            elif trade['stop_loss'] and current_price <= trade['stop_loss']:
                should_exit = True
                exit_reason = "STOP_LOSS"
                print(f"   ⛔ STOP LOSS HIT: ${trade['stop_loss']}")
            
            # Check if expiration is tomorrow or closer
            exp_date = datetime.strptime(trade['expiration'], "%m/%d/%Y")
            days_to_exp = (exp_date - datetime.now()).days
            if days_to_exp <= 1:
                should_exit = True
                exit_reason = "EXPIRATION_NEAR"
                print(f"   ⏰ EXPIRATION IN {days_to_exp} DAY(S)")
            
            # Execute exit if needed
            if should_exit:
                print(f"   🚪 EXITING: {exit_reason}")
                exit_order = sell_position(trade['symbol'])
                if exit_order:
                    cursor.execute(
                        "UPDATE trades SET status = 'closed', exit_price = ?, exit_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (current_price, trade['id'])
                    )
                    conn.commit()
                    print(f"   ✅ SOLD at ${current_price:.2f}")
        
        except Exception as e:
            print(f"   ❌ Error processing {trade['symbol']}: {e}")
    
    conn.close()

def sell_position(symbol: str, qty: int = 1):
    """Sell a position at market"""
    try:
        order_data = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY
        )
        order = trading_client.submit_order(order_data)
        print(f"   📤 Sell order placed for {symbol}")
        return order
    except Exception as e:
        print(f"   ❌ Failed to sell {symbol}: {e}")
        return None

def print_portfolio_summary():
    """Print summary of all trades"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Open trades
    cursor.execute("SELECT * FROM trades WHERE status = 'open'")
    open_trades = cursor.fetchall()
    
    # Closed trades
    cursor.execute("SELECT * FROM trades WHERE status IN ('closed', 'closed_manual')")
    closed_trades = cursor.fetchall()
    
    print("\n" + "="*70)
    print("📊 TRADE PORTFOLIO SUMMARY")
    print("="*70)
    
    if open_trades:
        print(f"\n🟢 OPEN TRADES ({len(open_trades)}):")
        for trade in open_trades:
            print(f"  • {trade['ticker']}: ${trade['strike']} {trade['type']} | Entry: ${trade['entry_price']} | Target: ${trade['target']} | Stop: ${trade['stop_loss']}")
    
    if closed_trades:
        print(f"\n⚫ CLOSED TRADES ({len(closed_trades)}):")
        for trade in closed_trades:
            if trade['exit_price']:
                pnl = (trade['exit_price'] - trade['entry_price']) * 100
                pnl_pct = ((trade['exit_price'] - trade['entry_price']) / trade['entry_price']) * 100
                print(f"  • {trade['ticker']}: ${trade['strike']} {trade['type']} | Entry: ${trade['entry_price']} | Exit: ${trade['exit_price']:.2f} | P&L: ${pnl:.2f} ({pnl_pct:+.1f}%)")
    
    print("="*70)
    conn.close()

if __name__ == "__main__":
    print("🤖 Starting Trade Exit Manager...")
    check_and_exit_trades()
    print_portfolio_summary()
