from __future__ import annotations
# BRIGHTDATA INTEGRATION — 2026-05-27 — WC assembler intelligence tests

import sys
import importlib.util
from pathlib import Path


WC_SRC = Path(__file__).resolve().parents[1] / "wc2026_autopilot" / "src"
if str(WC_SRC) not in sys.path:
    sys.path.insert(0, str(WC_SRC))
if "db" in sys.modules:
    del sys.modules["db"]
if "config" in sys.modules:
    del sys.modules["config"]
_wc_config = importlib.util.spec_from_file_location("config", WC_SRC / "config.py")
assert _wc_config and _wc_config.loader
_wc_config_module = importlib.util.module_from_spec(_wc_config)
_wc_config.loader.exec_module(_wc_config_module)
sys.modules["config"] = _wc_config_module

from context.assembler import assemble_context  # noqa: E402


def _market() -> dict:
    return {
        "question": "Will Argentina beat France?",
        "platform": "kalshi",
        "market_id": "X",
        "implied_prob": 0.55,
        "volume": 5000,
        "open_interest": 10000,
        "closes_at": "2026-07-01T12:00:00Z",
    }


def test_assembler_uses_intelligence_when_provided(monkeypatch) -> None:
    called = {"news": 0, "fallback": 0}

    async def _news(*_args, **_kwargs):
        called["news"] += 1
        return [{"title": "Injury report", "url": "https://x", "snippet": "star ruled out"}]

    async def _live(*_args, **_kwargs):
        return {"home_score": 1, "away_score": 0, "minute": 50, "period": "LIVE", "events": [], "injuries": []}

    monkeypatch.setattr("context.assembler.fetch_team_news", lambda *_args, **_kwargs: called.__setitem__("fallback", called["fallback"] + 1) or [])
    intel = type("I", (), {"search_breaking_news": _news, "get_wc_match_live_state": _live})()
    assemble_context(_market(), bankroll=1000, open_positions=[], intelligence=intel)
    assert called["news"] >= 2
    assert called["fallback"] == 0


def test_assembler_falls_back_without_intelligence(monkeypatch) -> None:
    called = {"fallback": 0}
    monkeypatch.setattr("context.assembler.fetch_team_news", lambda *_args, **_kwargs: called.__setitem__("fallback", called["fallback"] + 1) or [])
    assemble_context(_market(), bankroll=1000, open_positions=[], intelligence=None)
    assert called["fallback"] >= 2


def test_live_state_added_to_context() -> None:
    async def _news(*_args, **_kwargs):
        return []

    async def _live(*_args, **_kwargs):
        return {"home_score": 2, "away_score": 1, "minute": 72, "period": "LIVE", "events": [], "injuries": []}

    intel = type("I", (), {"search_breaking_news": _news, "get_wc_match_live_state": _live})()
    ctx = assemble_context(_market(), bankroll=1000, open_positions=[], intelligence=intel)
    assert ctx["live_match_state"]["home_score"] == 2
    assert ctx["live_match_state"]["away_score"] == 1
    assert ctx["live_match_state"]["minute"] == 72
