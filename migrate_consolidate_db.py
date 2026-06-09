#!/usr/bin/env python3
"""Database consolidation script - merges discord_trades.db and signal_quality.db into audit.db"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("migrate_db")


def migrate_database(audit_db_path: str = "data/audit.db") -> None:
    """Consolidate all SQLite databases into audit.db with data preservation."""
    audit_path = Path(audit_db_path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Connect to main audit database
    audit_conn = sqlite3.connect(audit_path)
    audit_cursor = audit_conn.cursor()
    
    # Enable WAL mode and foreign keys
    audit_cursor.execute("PRAGMA journal_mode=WAL")
    audit_cursor.execute("PRAGMA foreign_keys=ON")
    
    # Initialize schema (same as sqlite_store.py)
    audit_cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            event_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            symbol TEXT,
            agent TEXT,
            conviction REAL,
            risk_check TEXT,
            rejection_reason TEXT,
            order_id TEXT,
            pl_realized REAL,
            pm_signal TEXT,
            raw_payload TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS trade_attribution (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            closed_at TEXT NOT NULL,
            technical_correct INTEGER NOT NULL,
            fundamental_correct INTEGER NOT NULL,
            pm_correct INTEGER NOT NULL,
            dexter_helpful INTEGER NOT NULL,
            pl_realized REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS trade_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            closed_at TEXT NOT NULL,
            thesis TEXT NOT NULL,
            outcome TEXT NOT NULL,
            conviction REAL NOT NULL,
            payload TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS gate_results (
            gate_id TEXT NOT NULL,
            checked_at TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT NOT NULL,
            PRIMARY KEY (gate_id, checked_at)
        );

        CREATE TABLE IF NOT EXISTS job_runs (
            job_name TEXT NOT NULL,
            run_date TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL,
            details TEXT,
            PRIMARY KEY (job_name, run_date)
        );

        CREATE TABLE IF NOT EXISTS discord_trades (
            id TEXT PRIMARY KEY,
            message_id TEXT,
            symbol TEXT NOT NULL,
            ticker TEXT NOT NULL,
            strike REAL NOT NULL,
            expiration TEXT NOT NULL,
            type TEXT NOT NULL,
            entry_price REAL,
            target REAL,
            stop_loss REAL,
            status TEXT DEFAULT 'open',
            placed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            exit_price REAL,
            exit_at DATETIME,
            source TEXT DEFAULT 'discord_bullseye',
            conviction REAL,
            risk_score REAL,
            contracts INTEGER DEFAULT 1,
            brain_approved INTEGER DEFAULT 0,
            brain_reason TEXT
        );

        CREATE TABLE IF NOT EXISTS signal_tracking (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            symbol TEXT NOT NULL,
            instrument TEXT,
            conviction REAL,
            direction TEXT,
            entry_price REAL,
            entry_time TEXT,
            exit_price REAL,
            exit_time TEXT,
            pnl REAL,
            pnl_pct REAL,
            status TEXT DEFAULT 'open',
            metadata TEXT
        );

        CREATE TABLE IF NOT EXISTS equity_curve (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            equity REAL NOT NULL,
            cash REAL DEFAULT 0,
            positions_value REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS completed_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            instrument TEXT NOT NULL DEFAULT 'EQUITY',
            source TEXT NOT NULL DEFAULT 'unknown',
            entry_price REAL NOT NULL,
            exit_price REAL NOT NULL,
            quantity REAL NOT NULL,
            pnl REAL NOT NULL,
            pnl_pct REAL NOT NULL,
            entry_time TEXT NOT NULL,
            exit_time TEXT NOT NULL,
            holding_period_hours REAL,
            order_id TEXT,
            metadata TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_audit_symbol ON audit_log(symbol);
        CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log(event_type);
        CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_discord_status ON discord_trades(status);
        CREATE INDEX IF NOT EXISTS idx_discord_ticker ON discord_trades(ticker);
        CREATE INDEX IF NOT EXISTS idx_signal_source ON signal_tracking(source);
        CREATE INDEX IF NOT EXISTS idx_signal_status ON signal_tracking(status);
        CREATE INDEX IF NOT EXISTS idx_equity_timestamp ON equity_curve(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_completed_symbol ON completed_trades(symbol);
        CREATE INDEX IF NOT EXISTS idx_completed_source ON completed_trades(source);
        """
    )
    audit_conn.commit()
    
    # Migrate discord_trades.db
    discord_db = Path("data/discord_trades.db")
    if discord_db.exists():
        logger.info("📦 Migrating %s...", discord_db)
        discord_conn = sqlite3.connect(discord_db)
        discord_conn.row_factory = sqlite3.Row
        discord_cursor = discord_conn.cursor()
        
        try:
            discord_cursor.execute("SELECT * FROM discord_trades")
            rows = discord_cursor.fetchall()
            
            migrated = 0
            for row in rows:
                try:
                    audit_cursor.execute(
                        """
                        INSERT OR REPLACE INTO discord_trades
                        (id, message_id, symbol, ticker, strike, expiration, type, entry_price,
                         target, stop_loss, status, placed_at, exit_price, exit_at, source,
                         conviction, risk_score, contracts, brain_approved, brain_reason)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            row["id"],
                            row["message_id"] if "message_id" in row.keys() else None,
                            row["symbol"],
                            row["ticker"],
                            row["strike"],
                            row["expiration"],
                            row["type"],
                            row["entry_price"] if "entry_price" in row.keys() else None,
                            row["target"] if "target" in row.keys() else None,
                            row["stop_loss"] if "stop_loss" in row.keys() else None,
                            row["status"] if "status" in row.keys() else "open",
                            row["placed_at"] if "placed_at" in row.keys() else None,
                            row["exit_price"] if "exit_price" in row.keys() else None,
                            row["exit_at"] if "exit_at" in row.keys() else None,
                            row["source"] if "source" in row.keys() else "discord_bullseye",
                            row["conviction"] if "conviction" in row.keys() else None,
                            row["risk_score"] if "risk_score" in row.keys() else None,
                            row["contracts"] if "contracts" in row.keys() else 1,
                            row["brain_approved"] if "brain_approved" in row.keys() else 0,
                            row["brain_reason"] if "brain_reason" in row.keys() else "",
                        ),
                    )
                    migrated += 1
                except Exception as e:
                    logger.warning("⚠️  Failed to migrate discord trade %s: %s", row["id"], e)
            
            audit_conn.commit()
            logger.info("✅ Migrated %d Discord trades", migrated)
        except Exception as e:
            logger.error("❌ Failed to migrate discord_trades: %s", e)
        finally:
            discord_conn.close()
    else:
        logger.info("ℹ️  %s not found, skipping", discord_db)
    
    # Migrate signal_quality.db
    signal_db = Path("data/signal_quality.db")
    if signal_db.exists():
        logger.info("📦 Migrating %s...", signal_db)
        signal_conn = sqlite3.connect(signal_db)
        signal_conn.row_factory = sqlite3.Row
        signal_cursor = signal_conn.cursor()
        
        try:
            signal_cursor.execute("SELECT * FROM signal_tracking")
            rows = signal_cursor.fetchall()
            
            migrated = 0
            for row in rows:
                try:
                    audit_cursor.execute(
                        """
                        INSERT OR REPLACE INTO signal_tracking
                        (id, source, symbol, instrument, conviction, direction, entry_price,
                         entry_time, exit_price, exit_time, pnl, pnl_pct, status, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            row["id"],
                            row["source"],
                            row["symbol"],
                            row["instrument"] if "instrument" in row.keys() else None,
                            row["conviction"] if "conviction" in row.keys() else None,
                            row["direction"] if "direction" in row.keys() else None,
                            row["entry_price"] if "entry_price" in row.keys() else None,
                            row["entry_time"] if "entry_time" in row.keys() else None,
                            row["exit_price"] if "exit_price" in row.keys() else None,
                            row["exit_time"] if "exit_time" in row.keys() else None,
                            row["pnl"] if "pnl" in row.keys() else None,
                            row["pnl_pct"] if "pnl_pct" in row.keys() else None,
                            row["status"] if "status" in row.keys() else "open",
                            row["metadata"] if "metadata" in row.keys() else None,
                        ),
                    )
                    migrated += 1
                except Exception as e:
                    logger.warning("⚠️  Failed to migrate signal %s: %s", row["id"], e)
            
            audit_conn.commit()
            logger.info("✅ Migrated %d signals", migrated)
        except Exception as e:
            logger.error("❌ Failed to migrate signal_quality: %s", e)
        finally:
            signal_conn.close()
    else:
        logger.info("ℹ️  %s not found, skipping", signal_db)
    
    # Verify migration
    logger.info("📊 Migration Summary:\n")
    for table in ["audit_log", "discord_trades", "signal_tracking", "equity_curve", "completed_trades"]:
        try:
            count = audit_cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            logger.info("  %s: %d rows", table, count)
        except Exception:
            logger.info("  %s: 0 rows", table)
    
    audit_conn.close()
    logger.info("✅ Database consolidation complete!\n")

if __name__ == "__main__":
    migrate_database()
