"""Native Gemini REST client (``?key=`` auth).

Google Cloud / AI Studio keys with an ``AQ.`` prefix must be passed as a query
parameter, not as a Bearer token on the OpenAI-compatible endpoint.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from apex.core.retry import call_with_retries

LOGGER = logging.getLogger(__name__)

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


def uses_query_key_auth(api_key: str) -> bool:
    return api_key.strip().startswith("AQ.")


def generate_content(
    api_key: str,
    model: str,
    *,
    system: str,
    user: str,
    max_output_tokens: int = 700,
    temperature: float = 0.2,
) -> str:
    """Call ``models/{model}:generateContent`` with ``key=`` query auth."""
    model_id = model.removeprefix("models/")
    url = f"{_GEMINI_BASE}/models/{model_id}:generateContent"

    payload: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
    }
    if system.strip():
        payload["systemInstruction"] = {"parts": [{"text": system}]}

    def _post() -> dict[str, Any]:
        resp = requests.post(
            url,
            params={"key": api_key.strip()},
            json=payload,
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise ValueError("unexpected Gemini response shape")
        return data

    data = call_with_retries("gemini.generateContent", _post, max_attempts=3)
    candidates = data.get("candidates") or []
    if not candidates:
        block = (data.get("promptFeedback") or {}).get("blockReason")
        raise ValueError(f"Gemini returned no candidates (block={block})")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(str(p.get("text", "")) for p in parts if isinstance(p, dict)).strip()
    if not text:
        raise ValueError("Gemini returned empty text")
    return text
