from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone, timezone, timezone
from pathlib import Path
from typing import Any, Iterator

from apex.core.context import get_run_id
from apex.domain.enums import EventType
from apex.domain.models import AgentSignalAttribution, AuditEvent


class SQLiteStore:
    def __init__(self, db_path: Path):
        self._db_path = Path(db_path).expanduser().resolve()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            # Enable WAL mode for better concurrent access
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            
            conn.executescript(
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

                -- Consolidated from discord_trades.db
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

                -- Consolidated from signal_quality.db
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

                -- Equity curve for performance tracking
                CREATE TABLE IF NOT EXISTS equity_curve (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    equity REAL NOT NULL,
                    cash REAL DEFAULT 0,
                    positions_value REAL DEFAULT 0
                );

                -- Completed trades for P&L attribution
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

                CREATE TABLE IF NOT EXISTS world_cup_opportunities (
                    id TEXT PRIMARY KEY,
                    venue TEXT NOT NULL,
                    ticker_or_market_id TEXT,
                    kalshi_ticker TEXT,
                    poly_market_id TEXT,
                    question TEXT NOT NULL,
                    contract_type TEXT,
                    team_a TEXT,
                    team_b TEXT,
                    kickoff_ts TEXT,
                    market_yes_ask REAL,
                    volume_24h REAL,
                    fair_prob REAL,
                    model_edge REAL,
                    net_edge REAL,
                    final_score REAL,
                    detected_at TEXT
                );

                CREATE TABLE IF NOT EXISTS arb_opportunities (
                    id TEXT PRIMARY KEY,
                    kalshi_ticker TEXT NOT NULL,
                    poly_market_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    kalshi_title TEXT NOT NULL,
                    poly_title TEXT NOT NULL,
                    kalshi_yes_ask REAL NOT NULL,
                    poly_no_ask REAL NOT NULL,
                    gross_spread REAL NOT NULL,
                    net_edge REAL NOT NULL,
                    settlement_match_score REAL NOT NULL,
                    settlement_flags TEXT NOT NULL,
                    volume_kalshi REAL,
                    volume_poly REAL,
                    category TEXT,
                    kelly_fraction REAL,
                    detected_at TEXT,
                    resolution_ts TEXT,
                    outcome TEXT,
                    pnl REAL,
                    thesis_settlement_verdict TEXT
                );
                """
            )
            
            for col_sql in (
                "ALTER TABLE arb_opportunities ADD COLUMN thesis_settlement_verdict TEXT;",
                "ALTER TABLE arb_opportunities ADD COLUMN vwap_edge REAL DEFAULT 0;",
            ):
                try:
                    conn.execute(col_sql)
                except sqlite3.OperationalError:
                    pass
            
            # Create indexes for common queries
            conn.executescript(
                """
                CREATE INDEX IF NOT EXISTS idx_audit_symbol ON audit_log(symbol);
                CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log(event_type);
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_audit_run_id ON audit_log(json_extract(raw_payload, '$.run_id'));
                
                CREATE INDEX IF NOT EXISTS idx_discord_status ON discord_trades(status);
                CREATE INDEX IF NOT EXISTS idx_discord_ticker ON discord_trades(ticker);
                CREATE INDEX IF NOT EXISTS idx_discord_placed_at ON discord_trades(placed_at DESC);
                
                CREATE INDEX IF NOT EXISTS idx_signal_source ON signal_tracking(source);
                CREATE INDEX IF NOT EXISTS idx_signal_status ON signal_tracking(status);
                CREATE INDEX IF NOT EXISTS idx_signal_symbol ON signal_tracking(symbol);
                
                CREATE INDEX IF NOT EXISTS idx_equity_timestamp ON equity_curve(timestamp DESC);
                
                CREATE INDEX IF NOT EXISTS idx_completed_symbol ON completed_trades(symbol);
                CREATE INDEX IF NOT EXISTS idx_completed_source ON completed_trades(source);
                CREATE INDEX IF NOT EXISTS idx_completed_exit_time ON completed_trades(exit_time DESC);

                CREATE INDEX IF NOT EXISTS idx_arb_detected_at ON arb_opportunities(detected_at DESC);
                CREATE INDEX IF NOT EXISTS idx_arb_edge ON arb_opportunities(net_edge DESC);
                CREATE INDEX IF NOT EXISTS idx_arb_kalshi ON arb_opportunities(kalshi_ticker);
                CREATE INDEX IF NOT EXISTS idx_wc_edge ON world_cup_opportunities(model_edge DESC);
                """
            )

    def append_event(self, event: AuditEvent) -> None:
        payload = dict(event.raw_payload)
        rid = get_run_id()
        if rid:
            payload.setdefault("run_id", rid)
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO audit_log (
                    event_id, timestamp, event_type, symbol, agent, conviction, risk_check,
                    rejection_reason, order_id, pl_realized, pm_signal, raw_payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.timestamp.replace(tzinfo=timezone.utc).isoformat(),
                    event.event_type.value,
                    event.symbol,
                    event.agent,
                    event.conviction,
                    event.risk_check,
                    event.rejection_reason,
                    event.order_id,
                    event.pl_realized,
                    event.pm_signal,
                    json.dumps(payload),
                ),
            )

    def append_attribution(self, item: AgentSignalAttribution) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO trade_attribution (
                    symbol, closed_at, technical_correct, fundamental_correct, pm_correct,
                    dexter_helpful, pl_realized
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.symbol,
                    item.closed_at.isoformat(),
                    int(item.technical_correct),
                    int(item.fundamental_correct),
                    int(item.pm_correct),
                    int(item.dexter_helpful),
                    item.pl_realized,
                ),
            )

    def append_trade_memory(
        self,
        symbol: str,
        thesis: str,
        outcome: str,
        conviction: float,
        payload: dict,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO trade_memory (symbol, closed_at, thesis, outcome, conviction, payload)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol,
                    datetime.now(tz=timezone.utc).isoformat(),
                    thesis,
                    outcome,
                    conviction,
                    json.dumps(payload),
                ),
            )

    def recent_trade_memory(self, limit: int = 8) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT symbol, closed_at, thesis, outcome, conviction, payload
                FROM trade_memory
                ORDER BY closed_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "symbol": row["symbol"],
                "closed_at": row["closed_at"],
                "thesis": row["thesis"],
                "outcome": row["outcome"],
                "conviction": row["conviction"],
                "payload": json.loads(row["payload"]),
            }
            for row in rows
        ]

    def symbol_trade_memory(self, symbol: str, limit: int = 3) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT symbol, closed_at, thesis, outcome, conviction, payload
                FROM trade_memory
                WHERE symbol = ?
                ORDER BY closed_at DESC
                LIMIT ?
                """,
                (symbol.upper(), limit),
            ).fetchall()
        return [
            {
                "symbol": row["symbol"],
                "closed_at": row["closed_at"],
                "thesis": row["thesis"],
                "outcome": row["outcome"],
                "conviction": row["conviction"],
                "payload": json.loads(row["payload"]),
            }
            for row in rows
        ]

    def upsert_gate_result(self, gate_id: str, status: str, details: dict) -> None:
        checked_at = datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO gate_results (gate_id, checked_at, status, details)
                VALUES (?, ?, ?, ?)
                """,
                (gate_id, checked_at, status, json.dumps(details)),
            )
        self.append_event(
            AuditEvent(
                event_type=EventType.GATE_RESULT,
                raw_payload={
                    "gate_id": gate_id,
                    "status": status,
                    "details": details,
                    "checked_at": checked_at,
                },
            )
        )

    def start_job(self, job_name: str, run_date: str) -> bool:
        with self._conn() as conn:
            existing = conn.execute(
                "SELECT status FROM job_runs WHERE job_name=? AND run_date=?",
                (job_name, run_date),
            ).fetchone()
            if existing and existing["status"] == "success":
                return False
            conn.execute(
                """
                INSERT OR REPLACE INTO job_runs (
                    job_name, run_date, started_at, finished_at, status, details
                ) VALUES (?, ?, ?, NULL, 'running', NULL)
                """,
                (job_name, run_date, datetime.now(tz=timezone.utc).isoformat()),
            )
            return True

    def finish_job(self, job_name: str, run_date: str, status: str, details: str = "") -> None:
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE job_runs
                SET finished_at=?, status=?, details=?
                WHERE job_name=? AND run_date=?
                """,
                (datetime.now(tz=timezone.utc).isoformat(), status, details, job_name, run_date),
            )

    # Whitelist of allowed table names for read_table()
    _ALLOWED_TABLES = frozenset({
        "audit_log",
        "trade_attribution",
        "trade_memory",
        "gate_results",
        "job_runs",
        "discord_trades",
        "signal_tracking",
        "equity_curve",
        "completed_trades",
        "arb_opportunities",
        "world_cup_opportunities",
    })

    def append_arb_opportunity(self, arb_id: str, arb: Any) -> None:
        """Deprecated: use save_arb_opportunities instead."""
        pass

    def save_arb_opportunities(self, opps: list[Any]) -> None:
        """Bulk upsert arb opportunities."""
        if not opps:
            return
            
        with self._conn() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO arb_opportunities (
                    id, kalshi_ticker, poly_market_id, question,
                    kalshi_title, poly_title, kalshi_yes_ask, poly_no_ask,
                    gross_spread, net_edge, settlement_match_score,
                    settlement_flags, volume_kalshi, volume_poly, category,
                    kelly_fraction, detected_at, resolution_ts, outcome, pnl,
                    thesis_settlement_verdict, vwap_edge
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        o.id, o.kalshi_ticker, o.poly_market_id, o.question,
                        o.kalshi_title, o.poly_title, o.kalshi_yes_ask, o.poly_no_ask,
                        o.gross_spread, o.net_edge, o.settlement_match_score,
                        json.dumps(o.settlement_flags), o.volume_kalshi, o.volume_poly,
                        o.category, getattr(o, "kelly_fraction", 0.0), 
                        o.detection_ts.isoformat() if o.detection_ts else None,
                        o.resolution_ts.isoformat() if o.resolution_ts else None,
                        o.outcome, o.pnl, getattr(o, "thesis_settlement_verdict", None),
                        float(getattr(o, "vwap_edge", 0.0) or 0.0),
                    )
                    for o in opps
                ]
            )

    def save_world_cup_opportunities(self, rows: list[dict]) -> None:
        if not rows:
            return
        now = datetime.now(tz=timezone.utc).isoformat()
        with self._conn() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO world_cup_opportunities (
                    id, venue, ticker_or_market_id, kalshi_ticker, poly_market_id,
                    question, contract_type, team_a, team_b, kickoff_ts,
                    market_yes_ask, volume_24h, fair_prob, model_edge, net_edge,
                    final_score, detected_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        str(r.get("id") or r.get("pair_id") or ""),
                        str(r.get("venue") or ""),
                        str(r.get("ticker_or_market_id") or ""),
                        str(r.get("kalshi_ticker") or ""),
                        str(r.get("poly_market_id") or ""),
                        str(r.get("question") or ""),
                        str(r.get("contract_type") or "other"),
                        str(r.get("team_a") or ""),
                        str(r.get("team_b") or ""),
                        str(r.get("kickoff_ts") or ""),
                        float(r.get("market_yes_ask") or 0.5),
                        float(r.get("volume_24h") or 0),
                        float(r.get("fair_prob") or 0),
                        float(r.get("model_edge") or 0),
                        float(r.get("net_edge") or 0),
                        float(r.get("final_score") or 0),
                        str(r.get("detected_at") or now),
                    )
                    for r in rows
                    if r.get("id") or r.get("pair_id")
                ],
            )

    def list_world_cup_opportunities(self, limit: int = 100) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT * FROM world_cup_opportunities
                   ORDER BY final_score DESC, model_edge DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_today_arb_pnl(self) -> float:
        """Sum P&L from arb opportunities detected today (M06)."""
        today = datetime.now(tz=timezone.utc).date().isoformat()
        with self._conn() as conn:
            try:
                row = conn.execute(
                    """
                    SELECT COALESCE(SUM(pnl), 0) AS total
                    FROM arb_opportunities
                    WHERE date(detected_at) = date(?)
                      AND pnl IS NOT NULL
                    """,
                    (today,),
                ).fetchone()
            except sqlite3.OperationalError:
                return 0.0
        return float(row["total"]) if row else 0.0

    def get_today_arb_event_loss_usd(self) -> float:
        """Estimate daily arb loss from risk failures and closed paper legs (not generic alerts)."""
        import json

        today = datetime.now(tz=timezone.utc).date().isoformat()
        loss = 0.0
        try:
            rows = self.read_table("audit_log", limit=500)
        except Exception:
            return 0.0
        for row in rows:
            ts = str(row.get("timestamp", ""))[:10]
            if ts != today:
                continue
            et = str(row.get("event_type") or "")
            if et == "ARB_RISK_FAILED":
                loss += 25.0
                continue
            if et == "ORDER_FILLED":
                payload = row.get("raw_payload")
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except json.JSONDecodeError:
                        payload = {}
                if isinstance(payload, dict) and payload.get("arb_id"):
                    pl = float(row.get("pl_realized") or payload.get("pnl") or 0)
                    if pl < 0:
                        loss += abs(pl)
        return loss

    def get_failed_thesis_examples(self, limit: int = 5) -> list[Any]:
        from apex.domain.models import ArbOpportunity
        with self._conn() as conn:
            try:
                rows = conn.execute(
                    """SELECT * FROM arb_opportunities
                       WHERE outcome = 'LOSS' AND thesis_settlement_verdict = 'SAFE'
                       ORDER BY detected_at DESC
                       LIMIT ?""",
                    (limit,)
                ).fetchall()
            except sqlite3.OperationalError:
                return []
            
        result = []
        for row in rows:
            row_dict = dict(row)
            opp = ArbOpportunity(
                id=row_dict["id"],
                kalshi_ticker=row_dict["kalshi_ticker"],
                poly_market_id=row_dict["poly_market_id"],
                question=row_dict["question"],
                kalshi_title=row_dict["kalshi_title"],
                poly_title=row_dict["poly_title"],
                kalshi_yes_ask=row_dict["kalshi_yes_ask"],
                poly_no_ask=row_dict["poly_no_ask"],
                gross_spread=row_dict["gross_spread"],
                net_edge=row_dict["net_edge"],
                settlement_match_score=row_dict["settlement_match_score"],
                settlement_flags=json.loads(row_dict["settlement_flags"] or "[]"),
                detection_ts=datetime.fromisoformat(row_dict["detected_at"]) if row_dict["detected_at"] else datetime.now(timezone.utc),
                resolution_ts=datetime.fromisoformat(row_dict["resolution_ts"]) if row_dict.get("resolution_ts") else None,
                outcome=row_dict.get("outcome"),
                pnl=row_dict.get("pnl"),
                volume_kalshi=row_dict.get("volume_kalshi", 0.0),
                volume_poly=row_dict.get("volume_poly", 0.0),
                category=row_dict.get("category", "UNKNOWN")
            )
            setattr(opp, "thesis_settlement_verdict", row_dict.get("thesis_settlement_verdict"))
            result.append(opp)
        return result

    def read_table(self, table: str, limit: int = 200) -> list[dict]:
        if table not in self._ALLOWED_TABLES:
            raise ValueError(f"Table '{table}' not allowed. Must be one of: {sorted(self._ALLOWED_TABLES)}")
        with self._conn() as conn:
            rows = conn.execute(f"SELECT * FROM {table} ORDER BY ROWID DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

    def list_arb_opportunities(self, limit: int = 100) -> list[dict]:
        from apex.services.arb_row_utils import normalize_arb_rows

        return normalize_arb_rows(self.read_table("arb_opportunities", limit=limit))

    def list_active_arb_opportunities(self, limit: int = 100) -> list[dict]:
        from apex.services.arb_row_utils import normalize_arb_rows
        safe_limit = max(1, min(int(limit), 1000))

        with self._conn() as conn:
            rows = conn.execute(
                """SELECT * FROM arb_opportunities
                   WHERE outcome IS NULL OR TRIM(COALESCE(outcome, '')) = ''
                   ORDER BY net_edge DESC, detected_at DESC
                   LIMIT ?""",
                (safe_limit,),
            ).fetchall()
        return normalize_arb_rows([dict(r) for r in rows])

    def get_arb_opportunity(self, arb_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM arb_opportunities WHERE id = ?",
                (arb_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_resolved_arb_opportunities(self, limit: int = 100) -> list[Any]:
        from apex.domain.models import ArbOpportunity
        with self._conn() as conn:
            try:
                rows = conn.execute(
                    """SELECT * FROM arb_opportunities
                       WHERE outcome IS NOT NULL
                       ORDER BY detected_at ASC
                       LIMIT ?""",
                    (limit,)
                ).fetchall()
            except sqlite3.OperationalError:
                return []
            
        result = []
        for row in rows:
            row_dict = dict(row)
            opp = ArbOpportunity(
                id=row_dict["id"],
                kalshi_ticker=row_dict["kalshi_ticker"],
                poly_market_id=row_dict["poly_market_id"],
                question=row_dict["question"],
                kalshi_title=row_dict["kalshi_title"],
                poly_title=row_dict["poly_title"],
                kalshi_yes_ask=row_dict["kalshi_yes_ask"],
                poly_no_ask=row_dict["poly_no_ask"],
                gross_spread=row_dict["gross_spread"],
                net_edge=row_dict["net_edge"],
                settlement_match_score=row_dict["settlement_match_score"],
                settlement_flags=json.loads(row_dict["settlement_flags"] or "[]"),
                detection_ts=datetime.fromisoformat(row_dict["detected_at"]) if row_dict["detected_at"] else datetime.now(timezone.utc),
                resolution_ts=datetime.fromisoformat(row_dict["resolution_ts"]) if row_dict.get("resolution_ts") else None,
                outcome=row_dict.get("outcome"),
                pnl=row_dict.get("pnl"),
                volume_kalshi=row_dict.get("volume_kalshi", 0.0),
                volume_poly=row_dict.get("volume_poly", 0.0),
                category=row_dict.get("category", "UNKNOWN")
            )
            result.append(opp)
        return result

    def list_audit_events(self, limit: int = 300) -> list[dict]:
        """Audit rows newest-first with parsed JSON payload for UI."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        out: list[dict] = []
        for row in rows:
            d = dict(row)
            raw = d.get("raw_payload")
            if isinstance(raw, str):
                try:
                    d["payload_json"] = json.loads(raw)
                except Exception:
                    d["payload_json"] = {}
            else:
                d["payload_json"] = {}
            out.append(d)
        return out

    def list_job_runs(self, limit: int = 150) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM job_runs
                ORDER BY datetime(COALESCE(finished_at, started_at)) DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def audit_event_counts(self) -> dict[str, int]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT event_type, COUNT(*) AS c
                FROM audit_log
                GROUP BY event_type
                """
            ).fetchall()
        return {str(r["event_type"]): int(r["c"]) for r in rows}

    def job_runs_for_date(self, run_date: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM job_runs WHERE run_date = ? ORDER BY job_name",
                (run_date,),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_audit_events_for_run_id(self, run_id: str, limit: int = 200) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM audit_log
                WHERE json_extract(raw_payload, '$.run_id') = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (run_id, limit),
            ).fetchall()
        out: list[dict] = []
        for row in rows:
            d = dict(row)
            raw = d.get("raw_payload")
            if isinstance(raw, str):
                try:
                    d["payload_json"] = json.loads(raw)
                except Exception:
                    d["payload_json"] = {}
            else:
                d["payload_json"] = {}
            out.append(d)
        return out

    def get_symbol_entry_time(self, symbol: str) -> datetime | None:
        """Best-effort open time from audit (ORDER_FILLED, then ORDER_SUBMITTED)."""
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT timestamp FROM audit_log
                WHERE symbol = ? AND event_type IN ('ORDER_FILLED', 'ORDER_SUBMITTED')
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (symbol,),
            ).fetchone()
        if not row:
            return None
        try:
            return datetime.fromisoformat(str(row["timestamp"]))
        except ValueError:
            return None

    def get_symbol_proposal_targets(self, symbol: str) -> dict[str, Any] | None:
        """Stop/take-profit from the latest proposal audit row for a symbol."""
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT raw_payload FROM audit_log
                WHERE symbol = ? AND event_type IN ('PROPOSAL_CREATED', 'ORDER_SUBMITTED')
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (symbol,),
            ).fetchone()
        if not row:
            return None
        try:
            payload = json.loads(row["raw_payload"])
        except (json.JSONDecodeError, TypeError):
            return None
        proposal = payload.get("proposal")
        if not isinstance(proposal, dict):
            return None
        return {
            "stop_loss": proposal.get("stop_loss"),
            "take_profit": proposal.get("take_profit"),
            "direction": proposal.get("direction"),
        }

    # ========================================================================
    # Discord Trades (consolidated from discord_trades.db)
    # ========================================================================

    def add_discord_trade(self, trade: dict[str, Any]) -> bool:
        """Add a Discord-originated trade."""
        with self._conn() as conn:
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO discord_trades
                    (id, message_id, symbol, ticker, strike, expiration, type, entry_price,
                     target, stop_loss, status, conviction, risk_score, contracts, brain_approved, brain_reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trade["id"],
                        trade.get("message_id"),
                        trade["symbol"],
                        trade["ticker"],
                        trade["strike"],
                        trade["expiration"],
                        trade["type"],
                        trade.get("entry_price"),
                        trade.get("target"),
                        trade.get("stop_loss"),
                        trade.get("status", "open"),
                        trade.get("conviction"),
                        trade.get("risk_score"),
                        trade.get("contracts", 1),
                        1 if trade.get("brain_approved") else 0,
                        trade.get("brain_reason", ""),
                    ),
                )
                return True
            except Exception:
                return False

    def update_discord_trade(self, trade_id: str, updates: dict[str, Any]) -> bool:
        """Update a Discord trade with sanitized column names."""
        allowed_columns = frozenset({
            "status", "exit_price", "exit_at", "entry_price", "target",
            "stop_loss", "conviction", "risk_score", "contracts",
        })
        sanitized = {k: v for k, v in updates.items() if k in allowed_columns}
        if not sanitized:
            return False
        set_clause = ", ".join(f"{k} = ?" for k in sanitized.keys())
        values = list(sanitized.values()) + [trade_id]
        with self._conn() as conn:
            try:
                conn.execute(f"UPDATE discord_trades SET {set_clause} WHERE id = ?", values)
                return True
            except Exception:
                return False

    def get_open_discord_trades(self) -> list[dict]:
        """Get all open Discord trades."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM discord_trades WHERE status = 'open' ORDER BY placed_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_discord_trade_stats(self) -> dict[str, Any]:
        """Get portfolio stats from Discord trades."""
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open_count,
                    SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed_count,
                    AVG(CASE WHEN status = 'closed' AND exit_price IS NOT NULL AND entry_price IS NOT NULL
                        THEN (exit_price - entry_price) * contracts * 100 ELSE NULL END) as avg_pnl
                FROM discord_trades
                """
            ).fetchone()
        return {
            "total": row["total"],
            "open": row["open_count"],
            "closed": row["closed_count"],
            "avg_pnl": row["avg_pnl"] or 0,
        }

    # ========================================================================
    # Signal Tracking (consolidated from signal_quality.db)
    # ========================================================================

    def record_signal(self, signal: dict[str, Any]) -> bool:
        """Record a new signal for tracking."""
        with self._conn() as conn:
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO signal_tracking
                    (id, source, symbol, instrument, conviction, direction, entry_price, entry_time, status, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        signal.get("id", f"sig-{datetime.now(timezone.utc).isoformat()}"),
                        signal.get("source", "unknown"),
                        signal.get("symbol", ""),
                        signal.get("instrument", "EQUITY"),
                        signal.get("conviction", 5.0),
                        signal.get("direction", "LONG"),
                        signal.get("entry_price"),
                        signal.get("entry_time", datetime.now(timezone.utc).isoformat()),
                        "open",
                        json.dumps(signal.get("metadata", {})),
                    ),
                )
                return True
            except Exception:
                return False

    def close_signal(self, signal_id: str, exit_price: float, pnl: float = 0, pnl_pct: float = 0) -> bool:
        """Mark a signal as closed with P&L."""
        with self._conn() as conn:
            try:
                conn.execute(
                    """
                    UPDATE signal_tracking
                    SET exit_price = ?, exit_time = ?, pnl = ?, pnl_pct = ?, status = 'closed'
                    WHERE id = ?
                    """,
                    (exit_price, datetime.now(timezone.utc).isoformat(), pnl, pnl_pct, signal_id),
                )
                return True
            except Exception:
                return False

    def get_source_stats(self) -> dict[str, dict]:
        """Get performance stats by signal source."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT source,
                       COUNT(*) as total,
                       SUM(CASE WHEN status = 'closed' AND pnl > 0 THEN 1 ELSE 0 END) as wins,
                       SUM(CASE WHEN status = 'closed' AND pnl < 0 THEN 1 ELSE 0 END) as losses,
                       AVG(CASE WHEN status = 'closed' THEN pnl ELSE NULL END) as avg_pnl,
                       SUM(CASE WHEN status = 'closed' THEN pnl ELSE 0 END) as total_pnl
                FROM signal_tracking
                GROUP BY source
                """
            ).fetchall()
        result = {}
        for row in rows:
            total = row["total"]
            wins = row["wins"] or 0
            losses = row["losses"] or 0
            closed = wins + losses
            result[row["source"]] = {
                "total_signals": total,
                "closed_signals": closed,
                "win_rate": wins / closed * 100 if closed > 0 else 0,
                "avg_pnl": row["avg_pnl"] or 0,
                "total_pnl": row["total_pnl"] or 0,
            }
        return result

    def get_conviction_accuracy(self) -> list[dict]:
        """Get win rate by conviction level."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    CASE
                        WHEN conviction < 4 THEN '0-4'
                        WHEN conviction < 6 THEN '4-6'
                        WHEN conviction < 8 THEN '6-8'
                        ELSE '8-10'
                    END as conviction_bucket,
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'closed' AND pnl > 0 THEN 1 ELSE 0 END) as wins,
                    AVG(CASE WHEN status = 'closed' THEN pnl ELSE NULL END) as avg_pnl
                FROM signal_tracking
                WHERE status = 'closed'
                GROUP BY conviction_bucket
                ORDER BY conviction_bucket
                """
            ).fetchall()
        return [
            {
                "conviction_range": row[0],
                "total": row[1],
                "wins": row[2],
                "win_rate": row[2] / row[1] * 100 if row[1] > 0 else 0,
                "avg_pnl": row[3] or 0,
            }
            for row in rows
        ]

    # ========================================================================
    # Equity Curve & P&L Attribution
    # ========================================================================

    def add_equity_point(self, timestamp: str, equity: float, cash: float = 0, positions_value: float = 0) -> None:
        """Add an equity curve data point."""
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO equity_curve (timestamp, equity, cash, positions_value)
                VALUES (?, ?, ?, ?)
                """,
                (timestamp, equity, cash, positions_value),
            )

    def get_equity_curve(self, days: int = 30) -> list[dict]:
        """Get equity curve data for the specified number of days."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT timestamp, equity, cash, positions_value
                FROM equity_curve
                WHERE timestamp >= datetime('now', ?)
                ORDER BY timestamp ASC
                """,
                (f"-{days} days",),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_completed_trade(
        self,
        symbol: str,
        instrument: str,
        source: str,
        entry_price: float,
        exit_price: float,
        quantity: float,
        pnl: float,
        pnl_pct: float,
        entry_time: str,
        exit_time: str,
        order_id: str = "",
        metadata: dict | None = None,
    ) -> None:
        """Record a completed trade for P&L attribution."""
        holding_period = None
        try:
            entry_dt = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
            exit_dt = datetime.fromisoformat(exit_time.replace("Z", "+00:00"))
            holding_period = (exit_dt - entry_dt).total_seconds() / 3600
        except (ValueError, AttributeError):
            pass

        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO completed_trades
                (symbol, instrument, source, entry_price, exit_price, quantity,
                 pnl, pnl_pct, entry_time, exit_time, holding_period_hours, order_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol,
                    instrument,
                    source,
                    entry_price,
                    exit_price,
                    quantity,
                    pnl,
                    pnl_pct,
                    entry_time,
                    exit_time,
                    holding_period,
                    order_id,
                    json.dumps(metadata or {}),
                ),
            )

    def get_completed_trades(self, limit: int = 100, days: int = 30) -> list[dict]:
        """Get completed trades for P&L attribution."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM completed_trades
                WHERE exit_time >= datetime('now', ?)
                ORDER BY exit_time DESC
                LIMIT ?
                """,
                (f"-{days} days", limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_pnl_attribution(self, days: int = 30) -> dict[str, Any]:
        """Calculate P&L attribution by source, symbol, and instrument."""
        with self._conn() as conn:
            # Overall stats
            overall = conn.execute(
                """
                SELECT
                    COUNT(*) as total_trades,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
                    MAX(pnl) as largest_win,
                    MIN(pnl) as largest_loss,
                    AVG(holding_period_hours) as avg_holding_hours
                FROM completed_trades
                WHERE exit_time >= datetime('now', ?)
                """,
                (f"-{days} days",),
            ).fetchone()

            # By source
            by_source = conn.execute(
                """
                SELECT source,
                       COUNT(*) as trades,
                       SUM(pnl) as total_pnl,
                       AVG(pnl) as avg_pnl,
                       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate
                FROM completed_trades
                WHERE exit_time >= datetime('now', ?)
                GROUP BY source
                ORDER BY total_pnl DESC
                """,
                (f"-{days} days",),
            ).fetchall()

            # By symbol
            by_symbol = conn.execute(
                """
                SELECT symbol,
                       COUNT(*) as trades,
                       SUM(pnl) as total_pnl,
                       AVG(pnl) as avg_pnl
                FROM completed_trades
                WHERE exit_time >= datetime('now', ?)
                GROUP BY symbol
                ORDER BY total_pnl DESC
                LIMIT 20
                """,
                (f"-{days} days",),
            ).fetchall()

            # By instrument
            by_instrument = conn.execute(
                """
                SELECT instrument,
                       COUNT(*) as trades,
                       SUM(pnl) as total_pnl,
                       AVG(pnl) as avg_pnl
                FROM completed_trades
                WHERE exit_time >= datetime('now', ?)
                GROUP BY instrument
                ORDER BY total_pnl DESC
                """,
                (f"-{days} days",),
            ).fetchall()

        wins = overall["wins"] or 0
        losses = overall["losses"] or 0
        closed = wins + losses

        return {
            "period_days": days,
            "overall": {
                "total_trades": overall["total_trades"],
                "total_pnl": overall["total_pnl"] or 0,
                "avg_pnl": overall["avg_pnl"] or 0,
                "win_rate": wins / closed * 100 if closed > 0 else 0,
                "largest_win": overall["largest_win"] or 0,
                "largest_loss": overall["largest_loss"] or 0,
                "avg_holding_hours": overall["avg_holding_hours"] or 0,
            },
            "by_source": [
                {"source": r["source"], "trades": r["trades"], "total_pnl": r["total_pnl"] or 0,
                 "avg_pnl": r["avg_pnl"] or 0, "win_rate": r["win_rate"] or 0}
                for r in by_source
            ],
            "by_symbol": [
                {"symbol": r["symbol"], "trades": r["trades"], "total_pnl": r["total_pnl"] or 0,
                 "avg_pnl": r["avg_pnl"] or 0}
                for r in by_symbol
            ],
            "by_instrument": [
                {"instrument": r["instrument"], "trades": r["trades"], "total_pnl": r["total_pnl"] or 0,
                 "avg_pnl": r["avg_pnl"] or 0}
                for r in by_instrument
            ],
        }

    def get_pm_positions(self) -> list[dict]:
        """Return open Polymarket paper positions from audit events."""
        with self._conn() as conn:
            orders = conn.execute(
                """
                SELECT symbol, raw_payload, created_at
                FROM audit_events
                WHERE event_type = 'ORDER_SUBMITTED'
                  AND symbol LIKE 'PM:%'
                  AND symbol NOT IN (
                      SELECT symbol FROM completed_trades WHERE source = 'polymarket'
                  )
                ORDER BY created_at DESC
                LIMIT 50
                """,
            ).fetchall()
            completed = conn.execute(
                "SELECT symbol, pnl FROM completed_trades WHERE source = 'polymarket'",
            ).fetchall()
        closed_symbols = {r["symbol"] for r in completed}
        result = []
        for r in orders:
            sym = r["symbol"]
            if sym in closed_symbols:
                continue
            payload = r["raw_payload"]
            if isinstance(payload, str):
                import json
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            proposal = payload.get("proposal", {}) if isinstance(payload, dict) else {}
            result.append({
                "symbol": sym,
                "entry_price": float(proposal.get("entry_price", 0) or 0),
                "direction": proposal.get("direction", "LONG"),
                "created_at": r["created_at"],
            })
        return result
