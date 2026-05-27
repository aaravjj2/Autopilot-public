from apex.ml.orderbook_imbalance import imbalance_features, predict_spread_collapse


def test_imbalance_features():
    book = {"yes": [[0.5, 200]], "no": [[0.5, 50]]}
    f = imbalance_features(book)
    assert f["bid_ask_ratio"] > 0.5
    assert predict_spread_collapse(f) > 0.5
