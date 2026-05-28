"""World Cup Elo model and discovery."""

from __future__ import annotations

from unittest.mock import patch


from apex.core.config import get_settings
from apex.ml.world_cup_model import (
    MODEL_VERSION,
    MODEL_VERSION_POISSON,
    apply_scores,
    score_contract,
    score_contract_poisson,
)
from apex.integrations.world_cup_markets import discover_world_cup_markets, _is_fifa_text


def test_is_fifa_text():
    assert _is_fifa_text("Will Brazil win the 2026 FIFA World Cup?")
    assert not _is_fifa_text("S&P 500 above 6000")


def test_elo_match_winner_favors_stronger_team():
    row = {
        "question": "Will Brazil beat Argentina?",
        "market_yes_ask": 0.45,
        "contract_type": "match_winner",
    }
    sc = score_contract(row)
    assert sc.fair_prob > 0.5
    assert sc.contract_type == "match_winner"


def test_score_contract_poisson_match_winner():
    row = {
        "question": "Will Brazil beat Argentina?",
        "market_yes_ask": 0.45,
        "contract_type": "match_winner",
    }
    sc = score_contract_poisson(row)
    assert sc is not None
    assert sc.model_version == MODEL_VERSION_POISSON
    assert sc.contract_type == "match_winner"
    weaker = score_contract_poisson(
        {
            "question": "Will Argentina beat Brazil?",
            "market_yes_ask": 0.45,
            "contract_type": "match_winner",
        }
    )
    assert weaker is not None
    assert sc.fair_prob > weaker.fair_prob


def test_score_contract_poisson_flag_uses_poisson(monkeypatch, tmp_path):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "poisson.db"))
    monkeypatch.setenv("WORLD_CUP_USE_POISSON", "true")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.world_cup_use_poisson is True

    row = {
        "question": "Will Brazil beat Argentina?",
        "market_yes_ask": 0.45,
        "contract_type": "match_winner",
    }
    sc = score_contract(row, settings)
    assert sc.model_version == MODEL_VERSION_POISSON

    monkeypatch.setenv("WORLD_CUP_USE_POISSON", "false")
    get_settings.cache_clear()
    sc_elo = score_contract(row, get_settings())
    assert sc_elo.model_version == MODEL_VERSION


def test_apply_scores_passes_model_version(monkeypatch, tmp_path):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "mv.db"))
    monkeypatch.setenv("WORLD_CUP_USE_POISSON", "true")
    get_settings.cache_clear()

    rows = [
        {
            "id": "p",
            "question": "Will Brazil beat Argentina?",
            "market_yes_ask": 0.45,
            "contract_type": "match_winner",
            "net_edge": 0.02,
        },
    ]
    out = apply_scores(rows)
    assert out[0]["model_version"] == MODEL_VERSION_POISSON


def test_apply_scores_sorts_by_final_score():
    rows = [
        {"id": "a", "question": "FIFA test", "market_yes_ask": 0.3, "net_edge": 0.01},
        {"id": "b", "question": "FIFA test 2", "market_yes_ask": 0.7, "net_edge": 0.08},
    ]
    out = apply_scores(rows)
    assert "final_score" in out[0]
    assert out[0]["final_score"] >= out[-1]["final_score"]


def test_discover_disabled(monkeypatch, tmp_path):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "a.db"))
    monkeypatch.setenv("WORLD_CUP_ENABLED", "false")
    from apex.core.config import get_settings

    get_settings.cache_clear()
    assert discover_world_cup_markets() == []


def test_discover_kalshi_mock(monkeypatch, tmp_path):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "a.db"))
    monkeypatch.setenv("WORLD_CUP_ENABLED", "true")
    from apex.core.config import get_settings

    get_settings.cache_clear()

    with patch(
        "apex.integrations.world_cup_markets.discover_kalshi_world_cup",
        return_value=[],
    ), patch(
        "apex.integrations.world_cup_markets.discover_polymarket_world_cup",
        return_value=[],
    ):
        assert discover_world_cup_markets() == []
