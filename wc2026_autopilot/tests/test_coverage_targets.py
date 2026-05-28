from unittest.mock import MagicMock, patch


import config
from agent import claude_client
from ingestion import football_data_org


def test_config_download_text_caches(tmp_path, monkeypatch):
    # Force DATA_RAW to a tmp directory for this test
    monkeypatch.setattr(config, "DATA_RAW", tmp_path)

    calls = {"n": 0}

    class R:
        status_code = 200
        text = "hello"

        def raise_for_status(self):
            return None

    def fake_get(*a, **k):
        calls["n"] += 1
        return R()

    monkeypatch.setattr("requests.get", fake_get)
    t1 = config.download_text("https://example.com/x", dest_name="x.txt")
    t2 = config.download_text("https://example.com/x", dest_name="x.txt")
    assert t1 == t2 == "hello"
    assert calls["n"] == 1


def test_football_data_org_missing_key_skips(monkeypatch):
    monkeypatch.delenv("FOOTBALL_DATA_API_KEY", raising=False)
    out = football_data_org.fetch_wc_matches()
    assert out == []


def test_football_data_org_with_key_mocks(monkeypatch):
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "x")

    def fake_get(url, headers=None, timeout=20):
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {"matches": [{"id": 1}]}
        r.raise_for_status.return_value = None
        return r

    with patch("requests.get", side_effect=fake_get):
        out = football_data_org.fetch_wc_matches()
        assert out and out[0]["id"] == 1


def test_claude_client_route_priority(monkeypatch):
    # Prefer groq if set
    monkeypatch.setenv("WC_LLM_BRAIN", "auto")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_KEY", raising=False)
    assert claude_client._route() == "groq"


def test_claude_client_shell_brain(monkeypatch):
    monkeypatch.setenv("WC_LLM_BRAIN", "shell")

    monkeypatch.setattr(
        claude_client,
        "_call_shell_brain",
        lambda s, p: '{"estimated_probability":0.5,"confidence":"low","action":"skip","reasoning":"r","key_factors":["a","b","c"],"red_flags":[]}',
    )
    out = claude_client.call_claude("p", "s")
    assert out["action"] == "skip"
