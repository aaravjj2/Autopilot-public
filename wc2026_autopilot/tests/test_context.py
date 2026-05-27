from context.assembler import assemble_context


def mock_market():
    return {
        "question": "Will Argentina beat France?",
        "platform": "kalshi",
        "market_id": "X",
        "implied_prob": 0.55,
        "volume": 5000,
        "open_interest": 10000,
        "closes_at": "2026-07-01T12:00:00Z",
    }


def test_assemble_context_shape():
    required_keys = [
        "question",
        "platform",
        "implied_prob",
        "home_team",
        "away_team",
        "h2h",
        "bankroll",
        "max_stake",
    ]
    ctx = assemble_context(mock_market(), bankroll=1000, open_positions=[])
    for key in required_keys:
        assert key in ctx


def test_max_stake_cap():
    ctx = assemble_context(mock_market(), bankroll=1000, open_positions=[])
    assert ctx["max_stake"] <= 50


def test_context_handles_unknown_teams():
    m = mock_market()
    m["question"] = "Will TeamFoo beat TeamBar?"
    ctx = assemble_context(m, bankroll=1000, open_positions=[])
    assert "home_wc_record" in ctx
