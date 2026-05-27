import pytest

from agent import claude_client
from agent.decision_engine import make_decision
from agent.prompt_builder import build_prompt


def _ctx():
    return {
        "question": "Will Argentina beat France?",
        "platform": "kalshi",
        "implied_prob": 0.55,
        "volume": 5000,
        "time_to_close_hours": 12.0,
        "home_team": "Argentina",
        "away_team": "France",
        "home_wc_record": {"appearances": 10, "win_rate": 0.6, "best_finish": "Champion"},
        "away_wc_record": {"appearances": 10, "win_rate": 0.5, "best_finish": "Champion"},
        "home_recent_form": {"form_string": "WWDLW", "wins": 3, "draws": 1, "losses": 1},
        "away_recent_form": {"form_string": "WLDWW", "wins": 3, "draws": 1, "losses": 1},
        "home_stage_rates": {"qf_rate": 0.5, "sf_rate": 0.3, "win_rate": 0.2},
        "away_stage_rates": {"qf_rate": 0.5, "sf_rate": 0.3, "win_rate": 0.2},
        "home_news": "• x",
        "away_news": "• y",
        "home_injury_alerts_formatted": "",
        "away_injury_alerts_formatted": "",
        "h2h": {"meetings": 4, "team_a_wins": 2, "draws": 1, "team_b_wins": 1, "wc_meetings_only": []},
        "historical_edge": {"accuracy": 0.5, "avg_edge": 0.01},
        "bankroll": 1000,
        "max_stake": 50,
        "open_positions_count": 0,
    }


def test_prompt_builder_output():
    s, p = build_prompt(_ctx())
    assert "Argentina" in p and "Head-to-Head" in p and "implied probability" in p


def test_claude_client_parses_valid_json(monkeypatch):
    monkeypatch.setattr(claude_client, "_route", lambda: "shell")
    monkeypatch.setattr(claude_client, "_call_shell_brain", lambda s, p: '{"estimated_probability":0.6,"confidence":"high","action":"bet_yes","reasoning":"r","key_factors":["a","b","c"],"red_flags":[]}')
    out = claude_client.call_claude("p", "s")
    assert out["action"] == "bet_yes"


def test_claude_client_handles_markdown_fence(monkeypatch):
    monkeypatch.setattr(claude_client, "_route", lambda: "shell")
    monkeypatch.setattr(claude_client, "_call_shell_brain", lambda s, p: '```json\n{"estimated_probability":0.6,"confidence":"high","action":"bet_yes","reasoning":"r","key_factors":["a","b","c"],"red_flags":[]}\n```')
    out = claude_client.call_claude("p", "s")
    assert out["confidence"] == "high"


def test_claude_client_retries_on_bad_json(monkeypatch):
    monkeypatch.setattr(claude_client, "_route", lambda: "shell")
    monkeypatch.setattr(claude_client, "_call_shell_brain", lambda s, p: 'not-json')
    with pytest.raises(ValueError):
        claude_client.call_claude("p", "s")


def test_decision_engine_skips_low_edge():
    d = make_decision({"estimated_probability": 0.56, "action": "bet_yes", "reasoning": "", "key_factors": [], "red_flags": []}, _ctx())
    assert d["action"] == "skip"


def test_decision_engine_skips_illiquid():
    c = _ctx()
    c["volume"] = 50
    d = make_decision({"estimated_probability": 0.8, "action": "bet_yes", "reasoning": "", "key_factors": [], "red_flags": []}, c)
    assert d["action"] == "skip"


def test_decision_engine_stake_within_cap():
    d = make_decision({"estimated_probability": 0.8, "action": "bet_yes", "reasoning": "", "key_factors": [], "red_flags": []}, _ctx())
    assert d["stake"] <= _ctx()["max_stake"]


def test_decision_engine_no_negative_stake():
    d = make_decision({"estimated_probability": 0.2, "action": "bet_no", "reasoning": "", "key_factors": [], "red_flags": []}, _ctx())
    assert d["stake"] >= 0
