from apex.cross_asset.iv_probability import iv_to_probability
from apex.cross_asset.mapping import hedge_tickers_for_event


def test_iv_to_probability():
    p = iv_to_probability(0.35, 30)
    assert 0.1 < p < 0.9


def test_cross_asset_mapping():
    tickers = hedge_tickers_for_event("SPACEX_LAUNCH")
    assert "TSLA" in tickers
