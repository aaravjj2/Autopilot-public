from apex.defi.treasury import detect_mev_sandwich, route_swap_1inch, sweep_idle_usdc_to_aave


def test_aave_sweep_stub():
    r = sweep_idle_usdc_to_aave(1000)
    assert r.deposited_usd == 1000


def test_mev_detection():
    assert detect_mev_sandwich({"gasUsed": 600_000}) is True
    assert detect_mev_sandwich({"gasUsed": 100_000}) is False


def test_1inch_route():
    assert route_swap_1inch("MATIC", "USDC", 100)["route"] == "paper"
