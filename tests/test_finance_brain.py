"""Offline tests for the autopilot FinanceBrain and its knowledge base.

No network is used: the LLM client is faked, and the heuristic fallback path
is exercised directly. These guard the brain's decision contract and the
integrity of the finance strategy corpus.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from apex.brain import finance_knowledge as kb
from apex.brain.finance_brain import (
    BrainVerdict,
    FinanceBrain,
    _classify_probe_error,
    _extract_json,
    _heuristic_verdict,
    _opp_facts,
)


# --------------------------------------------------------------------------- #
# Knowledge base integrity
# --------------------------------------------------------------------------- #
def test_knowledge_cards_have_unique_ids_and_content() -> None:
    cards = kb.all_cards()
    assert len(cards) >= 10
    ids = [c.id for c in cards]
    assert len(ids) == len(set(ids)), "duplicate knowledge card ids"
    for c in cards:
        assert c.title.strip()
        assert len(c.content) > 80, f"card {c.id} content too thin"
        assert c.category in kb.categories()


def test_system_prompt_includes_doctrine_and_cards() -> None:
    prompt = kb.build_system_prompt("arbitrage settlement liquidity")
    assert "PAPER mode" in prompt
    assert kb.KNOWLEDGE_VERSION in prompt
    # Retrieval should surface settlement/arbitrage cards for this query.
    assert "settlement" in prompt.lower()
    assert "arbitrage" in prompt.lower()


def test_retrieve_ranks_relevant_cards_first() -> None:
    cards = kb.retrieve("kelly sizing bankroll", limit=3)
    assert cards
    assert cards[0].id == "kelly"


def test_retrieve_empty_query_returns_defaults() -> None:
    assert kb.retrieve("", limit=4)  # no crash, returns leading cards


# --------------------------------------------------------------------------- #
# JSON extraction
# --------------------------------------------------------------------------- #
def test_extract_json_handles_prose_and_braces_in_strings() -> None:
    text = 'Sure! Here: {"action":"SKIP","rationale":"edge {tiny} after fees","risks":[]} done'
    raw = _extract_json(text)
    assert raw is not None
    assert raw.startswith("{") and raw.endswith("}")
    assert '"action":"SKIP"' in raw


def test_extract_json_returns_none_without_object() -> None:
    assert _extract_json("no json here") is None


# --------------------------------------------------------------------------- #
# Heuristic fallback verdicts (offline doctrine)
# --------------------------------------------------------------------------- #
def _facts(**kw):
    base = dict(
        id="x",
        question="q",
        net_edge=0.05,
        gross_spread=0.1,
        settlement_match_score=0.9,
        settlement_flags=[],
        volume_kalshi=20000.0,
        volume_poly=20000.0,
        kalshi_yes_ask=0.4,
        poly_no_ask=0.45,
    )
    base.update(kw)
    return base


def test_heuristic_executes_clean_opportunity() -> None:
    v = _heuristic_verdict(_facts())
    assert v.action == "EXECUTE"
    assert v.confidence > 0.5
    assert v.source == "heuristic"


def test_heuristic_skips_thin_liquidity() -> None:
    v = _heuristic_verdict(_facts(volume_poly=500.0))
    assert v.action == "SKIP"
    assert any("liquidity" in r for r in v.risks)


def test_heuristic_skips_low_settlement() -> None:
    v = _heuristic_verdict(_facts(settlement_match_score=0.3))
    assert v.action == "SKIP"


def test_heuristic_skips_nonpositive_edge() -> None:
    v = _heuristic_verdict(_facts(net_edge=0.0))
    assert v.action == "SKIP"


def test_heuristic_reviews_marginal_opportunity() -> None:
    v = _heuristic_verdict(_facts(net_edge=0.025, settlement_match_score=0.7, volume_kalshi=6000, volume_poly=6000))
    assert v.action == "REVIEW"


def test_opp_facts_parses_json_string_flags() -> None:
    facts = _opp_facts({"settlement_flags": '["time_mismatch", "source_diff"]', "net_edge": "0.04"})
    assert facts["settlement_flags"] == ["time_mismatch", "source_diff"]
    assert facts["net_edge"] == 0.04


# --------------------------------------------------------------------------- #
# Brain with offline (no LLM) and faked-LLM routes
# --------------------------------------------------------------------------- #
class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResp:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content: str) -> None:
        self._content = content
        self.calls = 0

    def create(self, **_kw):
        self.calls += 1
        return _FakeResp(self._content)


class _FakeClient:
    def __init__(self, content: str) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions(content))


def _settings_with_client(client):
    return SimpleNamespace(get_llm_client=lambda: client)


def _route(label="gemini", api_key="k"):
    from apex.core.llm_routing import LlmRoute

    return LlmRoute(
        provider="openai",
        api_key=api_key,
        base_url="https://example/v1",
        model="m",
        deep_think_model="m",
        quick_think_model="m",
        label=label,
    )


def _patch_routes(monkeypatch, routes, client=None) -> None:
    monkeypatch.setattr("apex.core.llm_routing.resolve_llm_routes", lambda *_a, **_k: routes)
    monkeypatch.setattr(
        "apex.core.llm_routing.openai_client_from_route",
        lambda _route: client,
    )


def test_brain_offline_falls_back_to_heuristic(monkeypatch) -> None:
    _patch_routes(monkeypatch, [])
    brain = FinanceBrain(settings=_settings_with_client(None))
    assert brain.is_live is False
    assert brain.operational is True
    v = brain.analyze_opportunity({"net_edge": 0.05, "settlement_match_score": 0.9, "volume_kalshi": 20000, "volume_poly": 20000})
    assert isinstance(v, BrainVerdict)
    assert v.source == "heuristic"
    ans = brain.ask("How should I size an arb?")
    assert "offline" in ans.lower() or len(ans) > 0


def test_brain_uses_llm_verdict_when_live(monkeypatch) -> None:
    client = _FakeClient('{"action":"EXECUTE","confidence":0.82,"rationale":"clean arb","risks":["timing"]}')
    _patch_routes(monkeypatch, [_route(label="groq")], client=client)
    brain = FinanceBrain(settings=_settings_with_client(client))
    assert brain.is_live is True
    v = brain.analyze_opportunity({"net_edge": 0.04, "settlement_match_score": 0.9, "volume_kalshi": 20000, "volume_poly": 20000})
    assert v.action == "EXECUTE"
    assert v.confidence == pytest.approx(0.82)
    assert v.source == "llm:groq"
    assert "timing" in v.risks


def test_brain_native_gemini_query_key(monkeypatch) -> None:
    aq_key = "AQ.test-native-key"
    _patch_routes(monkeypatch, [_route(label="gemini", api_key=aq_key)], client=None)
    calls: list[str] = []

    def _fake_generate(api_key, model, *, system, user, max_output_tokens, temperature=0.2):
        calls.append(api_key)
        return '{"action":"SKIP","confidence":0.6,"rationale":"native","risks":[]}'

    monkeypatch.setattr("apex.core.gemini_native.generate_content", _fake_generate)
    brain = FinanceBrain(settings=_settings_with_client(None))
    assert brain.is_live is True
    v = brain.analyze_opportunity({"net_edge": 0.01, "settlement_match_score": 0.5, "volume_kalshi": 100, "volume_poly": 100})
    assert v.action == "SKIP"
    assert v.source == "llm:gemini"
    assert calls == [aq_key]


def test_brain_recovers_when_llm_raises(monkeypatch) -> None:
    class _Boom:
        def __init__(self):
            self.chat = SimpleNamespace(completions=self)

        def create(self, **_kw):
            raise RuntimeError("429 rate limited")

    _patch_routes(monkeypatch, [_route(label="groq")], client=_Boom())
    brain = FinanceBrain(settings=_settings_with_client(_Boom()))
    v = brain.analyze_opportunity({"net_edge": 0.05, "settlement_match_score": 0.9, "volume_kalshi": 20000, "volume_poly": 20000})
    assert v.source == "heuristic"
    assert brain.is_live is True


def test_brain_marks_dead_on_auth_failure(monkeypatch) -> None:
    class _Boom:
        def __init__(self):
            self.chat = SimpleNamespace(completions=self)

        def create(self, **_kw):
            raise RuntimeError("403 API_KEY_INVALID")

    _patch_routes(monkeypatch, [_route(label="groq")], client=_Boom())
    brain = FinanceBrain(settings=_settings_with_client(_Boom()))
    brain.analyze_opportunity({"net_edge": 0.05, "settlement_match_score": 0.9, "volume_kalshi": 20000, "volume_poly": 20000})
    assert brain.is_live is False


def test_brain_malformed_llm_json_falls_back(monkeypatch) -> None:
    client = _FakeClient("I cannot answer that as JSON.")
    _patch_routes(monkeypatch, [_route(label="groq")], client=client)
    brain = FinanceBrain(settings=_settings_with_client(client))
    v = brain.analyze_opportunity({"net_edge": 0.05, "settlement_match_score": 0.9, "volume_kalshi": 20000, "volume_poly": 20000})
    assert v.source == "heuristic"
