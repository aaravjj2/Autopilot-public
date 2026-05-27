from __future__ import annotations

from unittest.mock import MagicMock

from apex.layers.l3.execution import fast_fill_peek


def test_fast_fill_peek_returns_true_when_already_filled() -> None:
    broker = MagicMock()
    broker.get_order.return_value = {"status": "filled", "filled_qty": "10"}
    settings = MagicMock()
    filled, reason = fast_fill_peek(broker, "order-1", settings)
    assert filled is True
    assert "filled" in reason


def test_fast_fill_peek_returns_false_when_cancelled() -> None:
    broker = MagicMock()
    broker.get_order.return_value = {"status": "canceled"}
    settings = MagicMock()
    filled, reason = fast_fill_peek(broker, "order-2", settings)
    assert filled is False
    assert reason == "canceled"


def test_fast_fill_peek_falls_back_to_monitor_fill() -> None:
    broker = MagicMock()
    broker.get_order.return_value = {"status": "accepted"}
    broker.monitor_fill.return_value = (True, "filled:monitor")
    settings = MagicMock()
    filled, reason = fast_fill_peek(broker, "order-3", settings)
    assert filled is True
