import json
from unittest.mock import MagicMock, patch

import pytest

from ingestion import espn_scraper, market_fetcher, news_fetcher, worldcup_history
from ingestion.wc2026_fixtures import fetch_and_insert_fixtures


@pytest.mark.live
def test_download_fjelstul_dataset():
    csvs = worldcup_history.download_fjelstul_csvs()
    matches = worldcup_history.parse_matches_csv(csvs["matches.csv"])
    assert len(matches) >= 800


@pytest.mark.live
def test_kaggle_results_dataset():
    text = worldcup_history.download_international_results()
    assert text.count("\n") >= 40000


def test_fixtures_2026_exactly_104_rows(db):
    count = db.execute("SELECT COUNT(*) FROM fixtures_2026").fetchone()[0]
    assert count == 104


def test_fixtures_group_stage_count(db):
    count = db.execute("SELECT COUNT(*) FROM fixtures_2026 WHERE stage='group'").fetchone()[0]
    assert count == 72


def test_fixtures_knockout_count(db):
    count = db.execute("SELECT COUNT(*) FROM fixtures_2026 WHERE stage != 'group'").fetchone()[0]
    assert count == 32


def test_fixtures_all_12_groups_present(db):
    rows = db.execute("SELECT DISTINCT group_name FROM fixtures_2026 WHERE stage='group'").fetchall()
    names = {r[0] for r in rows}
    assert names == set("ABCDEFGHIJKL")


def test_fixtures_known_group_teams(db):
    rows = db.execute(
        "SELECT * FROM fixtures_2026 WHERE home_team='Argentina' OR away_team='Argentina'"
    ).fetchall()
    assert len(rows) == 3


def test_fixtures_waterfall_uses_synthetic_when_all_urls_404(monkeypatch, empty_db):
    import requests

    def fake_get(*a, **k):
        r = MagicMock()
        r.status_code = 404
        r.ok = False
        r.text = ""
        r.raise_for_status.side_effect = requests.HTTPError("404")
        return r

    monkeypatch.setattr(requests, "get", fake_get)
    empty_db.execute("DELETE FROM fixtures_2026")
    fetch_and_insert_fixtures(empty_db)
    count = empty_db.execute("SELECT COUNT(*) FROM fixtures_2026").fetchone()[0]
    assert count == 104


ESPN_SCOREBOARD_FIXTURE = {
    "events": [
        {
            "id": "evt_001",
            "date": "2026-07-19T19:00Z",
            "competitions": [
                {
                    "competitors": [
                        {"homeAway": "home", "team": {"displayName": "Argentina"}, "score": "0"},
                        {"homeAway": "away", "team": {"displayName": "France"}, "score": "0"},
                    ],
                    "status": {"type": {"description": "Scheduled"}},
                }
            ],
        }
    ]
}

ESPN_NEWS_FIXTURE = {
    "articles": [
        {
            "headline": "Mbappe fitness update ahead of WC",
            "description": "France winger...",
            "published": "2026-06-10T12:00Z",
            "links": {"web": {"href": "https://espn.com/1"}},
        }
    ]
}


def test_espn_scraper_scoreboard_mock(monkeypatch):
    import config as _cfg
    _cfg.clear_cache()
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = ESPN_SCOREBOARD_FIXTURE
        out = espn_scraper.fetch_scoreboard()
        assert len(out) == 1
        assert out[0].home_team == "Argentina"


def test_espn_scraper_news_mock():
    import config as _cfg
    _cfg.clear_cache()
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = ESPN_NEWS_FIXTURE
        out = espn_scraper.fetch_news()
        assert len(out) == 1
        assert "Mbappe" in out[0].title


def test_espn_scraper_falls_back_to_cache_on_500(monkeypatch):
    import config as _cfg
    _cfg.clear_cache()
    espn_scraper._DISK_CACHE["scoreboard"] = ESPN_SCOREBOARD_FIXTURE
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 500
        out = espn_scraper.fetch_scoreboard()
        assert len(out) == 1


def test_espn_scraper_cache_ttl(monkeypatch):
    import config as _cfg
    _cfg.clear_cache()
    call_count = {"n": 0}

    def mock_get(*args, **kwargs):
        call_count["n"] += 1
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = ESPN_SCOREBOARD_FIXTURE
        return r

    with patch("requests.get", side_effect=mock_get):
        out1 = espn_scraper.fetch_scoreboard()
        out2 = espn_scraper.fetch_scoreboard()
        assert out1 and out2
        assert call_count["n"] == 1


MOCK_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Google News</title>
  <item><title>Argentina injury concern ahead of Group J opener</title><link>https://news.google.com/1</link></item>
  <item><title>Argentina injury concern ahead of Group J opener</title><link>https://news.google.com/1</link></item>
</channel></rss>"""

def test_news_fetcher_parses_rss(monkeypatch):
    news_fetcher._ARTICLE_CACHE.clear()
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = MOCK_RSS
        mock_get.return_value.raise_for_status.return_value = None
        out = news_fetcher.fetch_team_news("Argentina")
        assert out
        assert "Argentina" in out[0]["title"]


def test_news_fetcher_empty_feed(monkeypatch):
    news_fetcher._ARTICLE_CACHE.clear()
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b'<?xml version=\"1.0\"?><rss version=\"2.0\"><channel></channel></rss>'
        mock_get.return_value.raise_for_status.return_value = None
        out = news_fetcher.fetch_team_news("Argentina")
        assert isinstance(out, list)


MOCK_KALSHI_RESPONSE = {
    "markets": [
        {
            "ticker": "FIFAWC-ARG-WIN",
            "title": "Will Argentina win the 2026 FIFA World Cup?",
            "yes_bid": 0.27,
            "yes_ask": 0.29,
            "volume": 48200,
            "open_interest": 12000,
            "close_time": "2026-07-19T23:59:00Z",
            "series_ticker": "FIFAWC",
        }
    ]
}

MOCK_POLYMARKET_RESPONSE = [
    {
        "question": "Will Brazil reach the FIFA 2026 semifinals?",
        "outcomePrices": ["0.61", "0.39"],
        "volume": 12400.0,
        "endDate": "2026-07-18T00:00:00Z",
        "active": True,
        "id": "pm1",
    }
]


def test_kalshi_wc_filter_hits_on_world_cup_keyword():
    assert market_fetcher.is_wc_market({"title": "Will Argentina win the World Cup?", "ticker": "ARG-WC"})


def test_kalshi_wc_filter_misses_unrelated():
    assert not market_fetcher.is_wc_market({"title": "Will the Fed cut rates in July?", "ticker": "FED-JULY"})


def test_polymarket_wc_filter_hits_on_question():
    assert market_fetcher.is_polymarket_wc({"question": "Will Brazil reach the FIFA 2026 semifinals?"})


def test_market_fetcher_kalshi_parsing_multi_strategy():
    call_count = {"n": 0}

    def mock_get(url, params=None, timeout=20, **kwargs):
        call_count["n"] += 1
        r = MagicMock()
        r.status_code = 200
        # First strategy: empty
        if params and params.get("series_ticker") == "FIFAWC":
            r.json.return_value = {"markets": []}
        # Second: search World Cup yields one
        elif params and "World Cup" in str(params.get("search", "")):
            r.json.return_value = MOCK_KALSHI_RESPONSE
        else:
            r.json.return_value = {"markets": []}
        return r

    with patch("requests.get", side_effect=mock_get):
        out = market_fetcher.fetch_kalshi_markets(limit=10)
        assert call_count["n"] > 1
        assert len(out) == 1
        assert out[0].platform == "kalshi"


def test_market_fetcher_polymarket_parsing_list_shape():
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = MOCK_POLYMARKET_RESPONSE
        out = market_fetcher.fetch_polymarket_markets(limit=10)
        assert len(out) == 1
        assert out[0].platform == "polymarket"


def test_market_fetcher_polymarket_parsing_dict_shape():
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"data": MOCK_POLYMARKET_RESPONSE}
        out = market_fetcher.fetch_polymarket_markets(limit=10)
        assert len(out) == 1
