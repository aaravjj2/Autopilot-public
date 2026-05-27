from __future__ import annotations

from apex.services.settlement_auditor import SettlementAuditor

def test_matching_resolution_dates() -> None:
    k = "Resolved by official government announcement on 2026-06-01."
    p = "Market resolves on 2026-06-01 according to official sources."
    auditor = SettlementAuditor()
    verdict = auditor.verify(k, p)
    assert verdict.recommendation == "SAFE"
    assert "timing_mismatch" not in verdict.flags

def test_mismatched_source_types() -> None:
    k = "This market resolves by official Fed announcement."
    p = "Resolved by BLS reports."
    auditor = SettlementAuditor()
    verdict = auditor.verify(k, p)
    assert verdict.recommendation != "SAFE"
    assert "source_divergence" in verdict.flags

def test_resolution_time_mismatch() -> None:
    k = "Market resolves on 2026-06-01"
    p = "Market resolves on 2026-06-01"
    
    # 5 hours difference
    k_market = {"close_time": "2026-06-01T20:00:00Z"}
    p_market = {"end_date": "2026-06-01T15:00:00Z"}
    
    auditor = SettlementAuditor()
    verdict = auditor.verify(k, p, kalshi_market=k_market, poly_market=p_market)
    
    assert "RESOLUTION_TIME_MISMATCH" in verdict.flags
    # Score starts at 1.0, and 0.20 is subtracted for the mismatch.
    assert verdict.match_score == 0.8

def test_resolution_time_match() -> None:
    k = "Market resolves on 2026-06-01"
    p = "Market resolves on 2026-06-01"
    
    # 3 hours difference (should not trigger flag)
    k_market = {"close_time": "2026-06-01T20:00:00Z"}
    p_market = {"end_date": "2026-06-01T17:00:00Z"}
    
    auditor = SettlementAuditor()
    verdict = auditor.verify(k, p, kalshi_market=k_market, poly_market=p_market)
    
    assert "RESOLUTION_TIME_MISMATCH" not in verdict.flags
    assert verdict.match_score == 1.0
