from apex.execution.sor import build_sor_from_payload, execute_sor_paper, split_notional_across_legs
from apex.execution.vwap import liquidity_gate_ok, vwap_for_size


def test_vwap_two_levels():
    levels = [(0.5, 100), (0.51, 100)]
    vwap, used = vwap_for_size(levels, 150)
    assert vwap is not None
    assert used == 2


def test_m07_liquidity_gate():
    book = {"yes": [[0.5, 100]], "no": [[0.5, 100]]}
    assert liquidity_gate_ok(book, 50, multiplier=3.0) is True
    assert liquidity_gate_ok(book, 200, multiplier=3.0) is False


def test_sor_paper_execute():
    payload = {
        "arb_id": "arb_test",
        "legs": [{"venue": "KALSHI", "side": "YES", "size_usd": 250, "limit_price": 0.45}],
    }
    req = build_sor_from_payload(payload)
    out = execute_sor_paper(req)
    assert out["status"] == "paper_routed"
    assert len(split_notional_across_legs(1000, ["KALSHI", "POLYMARKET"])) == 2
