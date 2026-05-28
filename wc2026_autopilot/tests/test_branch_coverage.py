from __future__ import annotations

from unittest.mock import MagicMock, patch


import config
from agent import claude_client
from ingestion import espn_scraper, market_fetcher, football_data_org
from ingestion.wc2026_fixtures import fetch_and_insert_fixtures
from ingestion import worldcup_history


def test_claude_extract_json_from_fence():
    txt = "```json\n{\"estimated_probability\":0.5,\"confidence\":\"low\",\"action\":\"skip\",\"reasoning\":\"r\",\"key_factors\":[\"a\",\"b\",\"c\"],\"red_flags\":[]}\n```"
    out = claude_client._extract_json(txt)
    assert out["action"] == "skip"


def test_claude_openai_compat_called(monkeypatch):
    # Cover groq branch without real network
    monkeypatch.setenv("WC_LLM_BRAIN", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setattr(
        claude_client,
        "_call_openai_compat",
        lambda base_url, api_key, model, system, prompt: '{"estimated_probability":0.6,"confidence":"medium","action":"skip","reasoning":"r","key_factors":["a","b","c"],"red_flags":[]}',
    )
    out = claude_client.call_claude("p", "s")
    assert out["estimated_probability"] == 0.6


def test_config_db_path_and_connection(monkeypatch, tmp_path):
    monkeypatch.setenv("WC_DB_PATH", str(tmp_path / "x.sqlite"))
    p = config.db_path()
    assert p.name.endswith(".sqlite")
    conn = config.get_db_connection(p)
    conn.execute("SELECT 1")
    conn.close()


def test_config_download_bytes_caches(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DATA_RAW", tmp_path)

    class R:
        status_code = 200
        content = b"abc"

        def raise_for_status(self):
            return None

    calls = {"n": 0}

    def fake_get(*a, **k):
        calls["n"] += 1
        return R()

    monkeypatch.setattr("requests.get", fake_get)
    b1 = config.download_bytes("https://example.com/a", dest_name="a.bin")
    b2 = config.download_bytes("https://example.com/a", dest_name="a.bin")
    assert b1 == b2 == b"abc"
    assert calls["n"] == 1


def test_fetch_and_insert_fixtures_success_from_openfootball(monkeypatch, empty_db):
    # Force the first waterfall source to succeed
    sample = """
Group A
2026-06-11 Mexico vs South Africa @ Stadium, City
Round of 16
2026-07-09 TBD vs TBD
""".strip()

    monkeypatch.setattr("ingestion.wc2026_fixtures.download_text", lambda url, dest_name=None, timeout=60.0: sample)
    n = fetch_and_insert_fixtures(empty_db)
    assert n == 104  # still enforced to 104 via synthetic fill if too few


def test_market_fetcher_fetch_all_wc_markets_combines(monkeypatch):
    monkeypatch.setattr(market_fetcher, "fetch_kalshi_markets", lambda *a, **k: [market_fetcher.Market("kalshi","1","q",0.5,1,1,"")])
    monkeypatch.setattr(market_fetcher, "fetch_polymarket_markets", lambda *a, **k: [market_fetcher.Market("polymarket","2","q",0.5,1,1,"")])
    out = market_fetcher.fetch_all_wc_markets()
    assert len(out) == 2


def test_market_fetcher_kalshi_handles_exception(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("no")

    monkeypatch.setattr("requests.get", boom)
    out = market_fetcher.fetch_kalshi_markets(limit=5)
    assert out == []


def test_polymarket_handles_weird_shape(monkeypatch):
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = "not-a-list"
        out = market_fetcher.fetch_polymarket_markets(limit=5)
        assert out == []


def test_espn_standings_and_team_mock(monkeypatch):
    import config as _cfg
    _cfg.clear_cache()

    def fake_get(url, timeout=15):
        r = MagicMock()
        r.status_code = 200
        if "standings" in url:
            r.json.return_value = {"children": [{"name": "Group A", "standings": {}}]}
        else:
            r.json.return_value = {"id": "1", "name": "Argentina"}
        return r

    with patch("requests.get", side_effect=fake_get):
        s = espn_scraper.fetch_standings()
        assert s.groups and s.groups[0]["name"] == "Group A"
        t = espn_scraper.fetch_team("1")
        assert t.get("name") == "Argentina"


def test_football_data_org_429_retry(monkeypatch):
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "k")

    calls = {"n": 0}

    def fake_get(url, headers=None, timeout=20):
        calls["n"] += 1
        r = MagicMock()
        if calls["n"] == 1:
            r.status_code = 429
            r.raise_for_status.side_effect = Exception("429")
            r.json.return_value = {}
        else:
            r.status_code = 200
            r.raise_for_status.return_value = None
            r.json.return_value = {"teams": [{"id": 1}]}
        return r

    with patch("requests.get", side_effect=fake_get):
        teams = football_data_org.fetch_wc_teams()
        assert teams and teams[0]["id"] == 1


def test_worldcup_history_insert_paths(empty_db):
    # Exercise insert functions without network
    matches = worldcup_history.parse_matches_csv(
        "tournament_name,stage_name,match_date,home_team_name,away_team_name,home_team_score,away_team_score\n"
        "1930 FIFA Men's World Cup,group stage,1930-07-13,Argentina,Brazil,1,0\n"
    )
    assert matches and matches[0].tournament_year == 1930
    n = worldcup_history.insert_wc_matches(empty_db, matches)
    assert n == 1
    intl_csv = "date,home_team,away_team,home_score,away_score,tournament,neutral\n2020-01-01,Argentina,Brazil,1,1,Friendly,TRUE\n"
    n2 = worldcup_history.insert_international_results(empty_db, intl_csv)
    assert n2 == 1
