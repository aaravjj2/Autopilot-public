from __future__ import annotations
# BRIGHTDATA INTEGRATION — 2026-05-27 — settlement auditor intelligence tests

from types import SimpleNamespace

from apex.core.config import Settings
from apex.services.settlement_auditor import SettlementAuditor


def test_verify_without_intelligence_unchanged() -> None:
    auditor = SettlementAuditor(settings=Settings(brightdata_api_key="x"))
    base = auditor.verify("Resolves on 2026-06-01", "Resolves on 2026-06-01")
    again = auditor.verify("Resolves on 2026-06-01", "Resolves on 2026-06-01", intelligence=None)
    assert base.match_score == again.match_score
    assert base.flags == again.flags


def test_source_found_boosts_score() -> None:
    auditor = SettlementAuditor(settings=Settings(brightdata_api_key="x"))
    async def _source(*_args, **_kwargs):
        return {
            "found": True,
            "url": "https://www.bls.gov/release",
            "excerpt": "matching criteria",
            "confidence": 0.8,
        }
    intelligence = SimpleNamespace(get_settlement_source=_source)
    out = auditor.verify("CPI 2026-06-01", "CPI 2026-06-01", intelligence=intelligence)
    assert out.match_score == 1.0
    assert "source_verified_live" in out.flags


def test_source_conflict_adds_flag() -> None:
    auditor = SettlementAuditor(settings=Settings(brightdata_api_key="x"))
    async def _source(*_args, **_kwargs):
        return {
            "found": True,
            "url": "https://www.bls.gov/release",
            "excerpt": "Value came in at 2.2%",
            "confidence": 0.9,
        }
    intelligence = SimpleNamespace(get_settlement_source=_source)
    out = auditor.verify("CPI above 3.0%", "CPI above 3.0%", intelligence=intelligence)
    assert "source_conflict" in out.flags


def test_brightdata_exception_does_not_crash_verify() -> None:
    auditor = SettlementAuditor(settings=Settings(brightdata_api_key="x"))
    base = auditor.verify("Resolves 2026-06-01", "Resolves 2026-06-01")

    async def _boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    intelligence = SimpleNamespace(get_settlement_source=_boom)
    with_intel = auditor.verify("Resolves 2026-06-01", "Resolves 2026-06-01", intelligence=intelligence)
    assert with_intel.match_score == base.match_score
