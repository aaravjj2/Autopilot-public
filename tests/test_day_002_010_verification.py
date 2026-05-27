from __future__ import annotations

from scripts.verification.verify_days_002_010 import classify_http_result


def test_classify_http_result_pass() -> None:
    status, evidence = classify_http_result(0, '{"status":"healthy"}', "")
    assert status == "PASS"
    assert "healthy" in evidence


def test_classify_http_result_blocked_for_connection_refused() -> None:
    status, evidence = classify_http_result(7, "", "Failed to connect to 127.0.0.1")
    assert status == "BLOCKED"
    assert "Failed to connect" in evidence


def test_classify_http_result_fail_for_non_json_success() -> None:
    status, evidence = classify_http_result(0, "ok", "")
    assert status == "FAIL"
    assert "missing expected JSON" in evidence
