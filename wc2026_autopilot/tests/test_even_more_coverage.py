from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import config
from agent import claude_client
from context import assembler
from ingestion import market_fetcher, news_fetcher, football_data_org, worldcup_history


def _json_decision():
    return '{"estimated_probability":0.52,"confidence":"low","action":"skip","reasoning":"r","key_factors":["a","b","c"],"red_flags":[]}'


def test_claude_gemini_openrouter_ollama_branches(monkeypatch):
    for brain in ("gemini", "openrouter", "ollama"):
        monkeypatch.setenv("WC_LLM_BRAIN", brain)
        monkeypatch.setenv("GEMINI_API_KEY", "k")
        monkeypatch.setenv("OPENROUTER_KEY", "k")
        monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
        monkeypatch.setattr(claude_client, "_call_openai_compat", lambda *a, **k: _json_decision())
        out = claude_client.call_claude("p", "s")
        assert out["action"] == "skip"


def test_claude_anthropic_branch(monkeypatch):
    monkeypatch.setenv("WC_LLM_BRAIN", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")

    class FakeAnthropic:
        def __init__(self):
            pass

        class messages:
            @staticmethod
            def create(**kwargs):
                c = SimpleNamespace(text=_json_decision())
                return SimpleNamespace(content=[c])

    fake_mod = SimpleNamespace(Anthropic=FakeAnthropic)
    sys.modules["anthropic"] = fake_mod
    out = claude_client.call_claude("p", "s")
    assert out["confidence"] == "low"


def test_claude_shell_brain_failure(monkeypatch):
    monkeypatch.setenv("WC_LLM_BRAIN", "shell")
    monkeypatch.setenv("WC_SHELL_BRAIN_CMD", "false")
    with pytest.raises(ValueError):
        claude_client.call_claude("p", "s")


def test_market_normalization_paths():
    # last_price fallback
    m = {
        "ticker": "X",
        "title": "FIFA World Cup",
        "yes_bid": 0,
        "yes_ask": 0,
        "last_price": 30,
        "volume": 1,
        "open_interest": 1,
        "close_time": "",
    }
    nm = market_fetcher._normalize_kalshi_market(m)
    assert 0.0 < nm.implied_prob < 1.0

    # polymarket missing id returns None
    pm = {"question": "Will Brazil win the FIFA 2026 World Cup?", "outcomePrices": ["0.6", "0.4"]}
    assert market_fetcher._normalize_polymarket_market(pm) is None


def test_market_fetcher_polymarket_status_not_200(monkeypatch):
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 500
        out = market_fetcher.fetch_polymarket_markets(limit=5)
        assert out == []


def test_news_fetcher_request_exception(monkeypatch):
    news_fetcher._ARTICLE_CACHE.clear()
    config.clear_cache()

    def boom(*a, **k):
        raise RuntimeError("no")

    monkeypatch.setattr("requests.get", boom)
    out = news_fetcher.fetch_team_news("Argentina-X")
    assert out == []


def test_news_fetcher_match_news_combines(monkeypatch):
    news_fetcher._ARTICLE_CACHE.clear()
    monkeypatch.setattr(news_fetcher, "_fetch_rss", lambda q: [{"title": q, "url": q, "source": "s", "published_at": ""}])
    out = news_fetcher.fetch_match_news("Argentina", "France")
    assert any("Argentina" in a["title"] for a in out)


def test_context_hours_until_parse_error():
    assert assembler.hours_until("not-a-time") == 999.0


def test_context_to_json_roundtrip():
    ctx = {"a": 1}
    assert assembler.context_to_json(ctx) == '{"a": 1}'


def test_football_data_org_token_bucket_consumes():
    b = football_data_org.TokenBucket(rate_per_min=10)
    before = b.tokens
    b.consume()
    assert b.tokens <= before


def test_football_data_org_standings_shape(monkeypatch):
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "k")

    def fake_get(url, headers=None, timeout=20):
        r = MagicMock()
        r.status_code = 200
        r.raise_for_status.return_value = None
        r.json.return_value = {"standings": []}
        return r

    with patch("requests.get", side_effect=fake_get):
        out = football_data_org.fetch_wc_standings()
        assert isinstance(out, dict)


def test_worldcup_history_download_fallback(monkeypatch):
    calls = {"n": 0}

    def fake_download(url, dest_name=None, timeout=60.0):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("fail")
        return "date,home_team,away_team,home_score,away_score,tournament,neutral\n2020-01-01,A,B,0,0,Friendly,TRUE\n"

    monkeypatch.setattr(worldcup_history, "download_text", fake_download)
    txt = worldcup_history.download_international_results()
    assert "2020-01-01" in txt


def test_claude_extract_json_loose_object():
    txt = "prefix {\"a\": 1} suffix"
    assert claude_client._extract_json(txt)["a"] == 1


def test_kalshi_market_fetch_none(monkeypatch):
    # Cover fetch_kalshi_market None path
    monkeypatch.setattr(market_fetcher, "_kalshi_get", lambda *a, **k: {})
    assert market_fetcher.fetch_kalshi_market("NOPE") is None


def test_kalshi_market_fetch_parses(monkeypatch):
    monkeypatch.setattr(
        market_fetcher,
        "_kalshi_get",
        lambda *a, **k: {"market": {"title": "World Cup", "yes_bid": 10, "yes_ask": 20, "volume": 1, "open_interest": 1, "close_time": ""}},
    )
    m = market_fetcher.fetch_kalshi_market("TICK")
    assert m and m.platform == "kalshi"
