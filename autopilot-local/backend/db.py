from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Generator

from sqlmodel import Field, Session, SQLModel, create_engine

from config import get_settings


class Portfolio(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    description: str = ""
    category: str  # political | hedge-fund | thematic
    pilot_name: str = ""
    is_following: bool = Field(default=False)
    last_refreshed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Holding(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    portfolio_id: str = Field(foreign_key="portfolio.id", index=True)
    ticker: str
    weight: float = 0.0
    shares: float = 0.0
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Trade(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    portfolio_id: str = Field(foreign_key="portfolio.id", index=True)
    ticker: str
    side: str  # buy | sell
    qty: float
    price: float = 0.0
    alpaca_order_id: str = ""
    status: str = "pending"  # pending | filled | failed
    executed_at: datetime | None = None


class PerformanceSnapshot(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    portfolio_id: str = Field(foreign_key="portfolio.id", index=True)
    date: date
    value_usd: float
    return_pct: float = 0.0


class UserPosition(SQLModel, table=True):
    """Mirrored Alpaca positions tagged by source portfolio."""
    ticker: str = Field(primary_key=True)
    qty: float = 0.0
    avg_entry: float = 0.0
    current_price: float = 0.0
    unrealized_pl: float = 0.0
    portfolio_id: str = ""


class PolymarketPosition(SQLModel, table=True):
    """Polymarket paper trading positions synced from APEX engine."""
    id: int | None = Field(default=None, primary_key=True)
    market_id: str = Field(index=True)
    question: str = ""
    slug: str = ""
    side: str  # YES | NO
    entry_price: float = 0.0
    stake_usd: float = 0.0
    quantity: float = 1.0
    current_value: float = 0.0
    unrealized_pl: float = 0.0
    status: str = "open"  # open | resolved_yes | resolved_no | closed
    opened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None

    class Config:
        table_name = "polymarket_position"


class PolymarketTrade(SQLModel, table=True):
    """Polymarket trade history synced from APEX audit.db."""
    id: int | None = Field(default=None, primary_key=True)
    market_id: str = Field(index=True)
    question: str = ""
    side: str  # YES | NO
    stake_usd: float = 0.0
    entry_price: float = 0.0
    exit_price: float | None = None
    order_id: str = ""
    status: str = "filled"  # filled | cancelled | failed
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        table_name = "polymarket_trade"


class PolymarketSnapshot(SQLModel, table=True):
    """Daily Polymarket bankroll snapshot for equity curve."""
    id: int | None = Field(default=None, primary_key=True)
    date: date
    bankroll_usd: float = 10000.0
    buying_power_usd: float = 10000.0
    open_positions: int = 0
    daily_pl: float = 0.0
    daily_pl_pct: float = 0.0

    class Config:
        table_name = "polymarket_snapshot"


class RefreshLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    portfolio_id: str = ""
    job_name: str
    status: str
    message: str = ""
    ran_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        db_path = get_settings()["db_path"]
        _engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
    return _engine


def init_db() -> None:
    engine = get_engine()
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session


def get_session_sync() -> Session:
    return Session(get_engine())
