import os

from autopilot import run_once
from db.seed import seed_all
import pytest


def require_live():
    if os.getenv("WC_SKIP_LIVE", "0") == "1":
        pytest.skip("WC_SKIP_LIVE=1")


def test_full_pipeline_dry_run(monkeypatch):
    require_live()
    seed_all()

    def fake_call(prompt, system):
        return {
            "estimated_probability": 0.6,
            "confidence": "medium",
            "action": "bet_yes",
            "reasoning": "edge",
            "key_factors": ["form", "h2h", "news"],
            "red_flags": [],
        }

    monkeypatch.setattr("autopilot.call_claude", fake_call)
    summary = run_once(bankroll=1000, dry_run=True)
    assert "analyzed" in summary


def test_no_api_keys_required(monkeypatch):
    require_live()
    monkeypatch.delenv("FOOTBALL_DATA_API_KEY", raising=False)
    monkeypatch.setattr(
        "autopilot.call_claude",
        lambda p, s: {
            "estimated_probability": 0.51,
            "confidence": "low",
            "action": "skip",
            "reasoning": "no edge",
            "key_factors": ["x", "y", "z"],
            "red_flags": [],
        },
    )
    out = run_once(bankroll=1000, dry_run=True)
    assert isinstance(out, dict)


def test_espn_fallback_on_failure(monkeypatch):
    from ingestion import espn_scraper

    espn_scraper._DISK_CACHE["scoreboard"] = {"events": []}

    class BadResp:
        status_code = 500

        def json(self):
            return {}

    monkeypatch.setattr("requests.get", lambda *a, **k: BadResp())
    out = espn_scraper.fetch_scoreboard()
    assert out == []
