from __future__ import annotations

import json
from typing import Any

from apex.core.logging import get_logger

LOGGER = get_logger(__name__)


def post_json_webhook(url: str, payload: dict[str, Any]) -> None:
    if not url.strip():
        return
    try:
        import requests

        r = requests.post(
            url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=8,
        )
        if not r.ok:
            LOGGER.warning("Webhook returned HTTP %s", r.status_code)
    except Exception as exc:  # noqa: BLE001
        LOGGER.debug("Webhook delivery failed: %s", exc)
