from apex.fund.copy_scale import scale_trade
from apex.fund.tenant_crypto import encrypt_secret, decrypt_secret
from apex.observability.alerts import alert_toxic_flow
from apex.observability.prometheus_metrics import metrics_payload


def test_encrypt_roundtrip():
    enc = encrypt_secret("api-key-secret")
    assert decrypt_secret(enc) == "api-key-secret"


def test_copy_scale():
    legs = scale_trade({"size_usd": 100}, ["a1", "a2", "a3"])
    assert len(legs) == 3
    assert legs[0].size_usd == 100.0


def test_prometheus_payload():
    body = metrics_payload()
    assert isinstance(body, bytes)


def test_alert_no_url():
    assert alert_toxic_flow("test") is False
