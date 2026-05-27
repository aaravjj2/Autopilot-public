from __future__ import annotations

from apex.integrations.dexter_adapter import DexterAdapter


def test_apply_adversarial_research_reduces_when_severity_above_threshold() -> None:
    research = {"severity": 8.0, "risks": ["x"]}
    new_c, cancel, _, sev, reduced = DexterAdapter.apply_adversarial_research(
        research,
        8.5,
        severity_threshold=7.0,
        conviction_floor=6.0,
    )
    assert sev == 8.0
    assert reduced is True
    assert new_c == 7.0
    assert cancel is False


def test_apply_adversarial_research_cancels_when_below_floor() -> None:
    research = {"severity": 8.0}
    new_c, cancel, _, _, reduced = DexterAdapter.apply_adversarial_research(
        research,
        7.0,
        severity_threshold=7.0,
        conviction_floor=6.0,
    )
    assert new_c == 5.5
    assert reduced is True
    assert cancel is True


def test_apply_adversarial_no_reduction_at_or_below_threshold() -> None:
    research = {"severity": 7.0}
    new_c, cancel, _, sev, reduced = DexterAdapter.apply_adversarial_research(
        research,
        8.0,
        severity_threshold=7.0,
        conviction_floor=6.0,
    )
    assert sev == 7.0
    assert reduced is False
    assert new_c == 8.0
    assert cancel is False
