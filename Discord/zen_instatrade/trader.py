import os
from datetime import datetime
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import sqlite3

# Initialize Paper Trading Client
API_KEY = os.getenv("ALPACA_PAPER_KEY")
SECRET_KEY = os.getenv("ALPACA_PAPER_SECRET")
trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)

DB_PATH = "trades.db"

def init_db():
    """Initialize trades database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trades (
        id TEXT PRIMARY KEY,
        symbol TEXT NOT NULL,
        ticker TEXT NOT NULL,
        strike REAL NOT NULL,
        expiration TEXT NOT NULL,
        type TEXT NOT NULL,
        entry_price REAL NOT NULL,
        target REAL,
        stop_loss REAL,
        status TEXT DEFAULT 'open',
        placed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        exit_price REAL,
        exit_at DATETIME
    )
    ''')
    conn.commit()
    conn.close()

def generate_occ_symbol(ticker: str, expiration_str: str, option_type: str, strike: float) -> str:
    """Formats Discord data into the required OCC options symbol.
    
    OCC Format: TICKER + YYMMDD + C/P + STRIKEPRICE
    Note: Alpaca API uses the compact format without the left-padding spaces
    """
    # New Format: "5/15/2026"
    date_obj = datetime.strptime(expiration_str, "%m/%d/%Y")
    date_formatted = date_obj.strftime("%y%m%d")
    
    opt_type = 'C' if option_type.upper() == 'CALL' else 'P'
    # Strike: 8 digits, 3 decimal places (e.g. 60.0 -> 00060000)
    strike_formatted = str(int(strike * 1000)).zfill(8)
    
    # Compact format: TICKER + YYMMDD + C/P + STRIKE (no spaces)
    occ_symbol = f"{ticker}{date_formatted}{opt_type}{strike_formatted}"
    return occ_symbol

def execute_paper_trade(parsed_data: dict, qty: int = 1, entry_price: float = None, target: float = None, stop_loss: float = None):
    """Fires a MARKET order to Alpaca and logs to database."""
    try:
        occ_symbol = generate_occ_symbol(
            parsed_data["ticker"], 
            parsed_data["expiration"], 
            parsed_data["type"], 
            parsed_data["strike"]
        )
        
        # Swapped to a Market Order since the alert has no limit price
        order_data = MarketOrderRequest(
            symbol=occ_symbol,
            qty=qty,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY
        )
        
        order = trading_client.submit_order(order_data)
        print(f"✅ Market Order Executed: {occ_symbol}")
        
        # Log trade to database
        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT OR REPLACE INTO trades 
        (id, symbol, ticker, strike, expiration, type, entry_price, target, stop_loss, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order.id,
            occ_symbol,
            parsed_data["ticker"],
            parsed_data["strike"],
            parsed_data["expiration"],
            parsed_data["type"],
            entry_price,
            target,
            stop_loss,
            'open'
        ))
        conn.commit()
        conn.close()
        print(f"   📊 Trade logged to database (ID: {order.id})")
        
        return order
        
    except Exception as e:
        print(f"❌ Failed to execute trade: {e}")
