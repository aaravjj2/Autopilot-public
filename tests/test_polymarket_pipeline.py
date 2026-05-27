from __future__ import annotations

from pathlib import Path

import pytest

from apex.core.config import Settings
from apex.domain.enums import Instrument
from apex.integrations.polymarket_events import polymarket_event_proposal_from_market
from apex.integrations.polymarket_gamma_public import infer_yes_won, training_row_from_market


def test_polymarket_event_proposal_underdog_yes(tmp_path: Path) -> None:
    settings = Settings(
        ALPACA_API_KEY="paper",
        ALPACA_SECRET_KEY="paper",
        ALPACA_PAPER_TRADE=True,
        ALPACA_BASE_URL="https://paper-api.alpaca.markets",
        SQLITE_PATH=tmp_path / "audit.db",
        CHROMADB_PATH=tmp_path / "chroma",
        POLYMARKET_PAPER_TRADING_ENABLED=True,
        POLYMARKET_EVENT_MIN_VOLUME_24H=10_000.0,
        POLYMARKET_EVENT_MIN_EDGE=0.05,
        POLYMARKET_PAPER_DEFAULT_STAKE_USD=40.0,
        POLYMARKET_PAPER_MAX_ORDER_USD=100.0,
    )
    market = {
        "id": "mkt_unit_1",
        "slug": "unit-test-market",
        "question": "Will unit test pass?",
        "volume": 250_000.0,
        "outcomePrices": '["0.22", "0.78"]',
    }
    p = polymarket_event_proposal_from_market(market, settings)
    assert p is not None
    assert p.instrument == Instrument.POLYMARKET_EVENT
    assert p.polymarket_outcome_side == "YES"
    assert p.polymarket_stake_usd == 40.0
    assert p.polymarket_market_id == "mkt_unit_1"


def test_infer_yes_won_from_terminal_prices() -> None:
    m = {"outcomePrices": '["1", "0"]', "id": "x"}
    assert infer_yes_won(m) is True
    m2 = {"outcomePrices": '["0.02", "0.98"]', "id": "y"}
    assert infer_yes_won(m2) is False


def test_training_row_shape() -> None:
    row = training_row_from_market(
        {
            "id": "z",
            "question": "Q?",
            "volume": 123.0,
            "closed": True,
            "outcomePrices": '["1", "0"]',
        }
    )
    assert row["market_id"] == "z"
    assert row["yes_won"] is True


def test_export_jsonl_append(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from apex.services import polymarket_training_export as exp

    def _fake_closed(**_kwargs: object) -> list[dict]:
        return [
            {
                "id": "closed-1",
                "question": "Resolved?",
                "volume": 500.0,
                "closed": True,
                "outcomePrices": '["1", "0"]',
            }
        ]

    monkeypatch.setattr(exp, "fetch_closed_markets_for_training", _fake_closed)
    out = tmp_path / "train.jsonl"
    n = exp.export_resolved_markets_to_jsonl(out, limit=3)
    assert n == 1
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert "closed-1" in lines[0]
