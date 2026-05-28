from unittest.mock import patch


from ingestion import market_fetcher
from ingestion.wc2026_fixtures import _build_synthetic_104, _parse_jfjelstul_matches_json, parse_fixture_text


def test_fixture_synthetic_shape():
    rows = _build_synthetic_104()
    assert len(rows) == 104
    assert sum(1 for r in rows if r.stage == "group") == 72


def test_fixture_parse_alt_dsl_line():
    text = "Argentina  1-0  France  @ Stadium, City"
    rows = parse_fixture_text(text)
    assert rows and rows[0].home_team == "Argentina"


def test_fixture_parse_jfjelstul_json_minimal():
    payload = '[{"tournament_year":2026,"home_team_name":"Argentina","away_team_name":"France","match_date":"2026-07-19"}]'
    out = _parse_jfjelstul_matches_json(payload)
    assert len(out) == 1
    assert out[0].home_team == "Argentina"


def test_snapshot_markets_inserts_rows(empty_db):
    m = market_fetcher.Market(
        platform="kalshi",
        market_id="X",
        question="Will Argentina win the World Cup?",
        implied_prob=0.5,
        volume=1000,
        open_interest=10,
        closes_at="2026-07-19T00:00:00Z",
    )
    n = market_fetcher.snapshot_markets(empty_db, [m])
    assert n == 1
    c = empty_db.execute("SELECT COUNT(*) FROM market_snapshots").fetchone()[0]
    assert c == 1


def test_fetch_kalshi_explicit_series_ticker_branch():
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "markets": [
                {
                    "ticker": "SOCCER-X",
                    "title": "FIFA World Cup 2026 winner",
                    "yes_bid": 0.4,
                    "yes_ask": 0.5,
                    "volume": 1,
                    "open_interest": 1,
                    "close_time": "2026-07-19T00:00:00Z",
                }
            ]
        }
        out = market_fetcher.fetch_kalshi_markets(series_ticker="SOCCER", limit=1)
        assert out and out[0].market_id == "SOCCER-X"


def test_polymarket_handles_non_wc_returns_empty():
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [{"question": "Fed rates", "outcomePrices": ["0.5", "0.5"], "id": "1"}]
        out = market_fetcher.fetch_polymarket_markets(limit=10)
        assert out == []
