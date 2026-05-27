"""Slack/Discord webhooks for risk alerts (Week 9 Day 5)."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

LOGGER = logging.getLogger(__name__)


def send_webhook(url: str, payload: dict[str, Any]) -> bool:
    if not url:
        return False
    try:
        resp = httpx.post(url, json=payload, timeout=10)
        return resp.status_code < 300
    except Exception as exc:
        LOGGER.warning("Webhook failed: %s", exc)
        return False


def alert_margin_call(equity: float, threshold: float) -> bool:
    url = os.getenv("SLACK_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK_URL", "")
    return send_webhook(
        url,
        {
            "text": f"⚠️ Margin call risk: equity ${equity:,.0f} below ${threshold:,.0f}",
            "severity": "CRITICAL",
        },
    )


def alert_toxic_flow(reason: str) -> bool:
    url = os.getenv("SLACK_WEBHOOK_URL") or ""
    return send_webhook(url, {"text": f"☠️ Toxic flow abort: {reason}", "severity": "WARNING"})


def alert_leg_imbalance(arb_id: str, poly_order_id: str, kalshi_order_id: str) -> bool:
    url = os.getenv("SLACK_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK_URL", "")
    return send_webhook(
        url,
        {
            "text": (
                f"LEG_IMBALANCE arb={arb_id} poly={poly_order_id} kalshi={kalshi_order_id}"
            ),
            "severity": "CRITICAL",
        },
    )
