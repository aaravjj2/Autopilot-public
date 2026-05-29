"""Tests for apex.core.gemini_native — native Gemini REST client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apex.core.gemini_native import generate_content, uses_query_key_auth


# ---------------------------------------------------------------------------
# uses_query_key_auth
# ---------------------------------------------------------------------------

class TestUsesQueryKeyAuth:
    def test_aq_prefix_returns_true(self) -> None:
        assert uses_query_key_auth("AQ.abc123") is True

    def test_aq_prefix_with_whitespace(self) -> None:
        assert uses_query_key_auth("  AQ.xyz789  ") is True

    def test_aq_lowercase_still_true(self) -> None:
        assert uses_query_key_auth("aq.test-key") is True

    def test_non_aq_key_returns_false(self) -> None:
        assert uses_query_key_auth("sk-abc123") is False

    def test_empty_key_returns_false(self) -> None:
        assert uses_query_key_auth("") is False

    def test_short_key_no_prefix_returns_false(self) -> None:
        assert uses_query_key_auth("xyz") is False


# ---------------------------------------------------------------------------
# generate_content
# ---------------------------------------------------------------------------

class TestGenerateContent:
    """Test generate_content with a mocked HTTP layer."""

    def test_happy_path_returns_text(self) -> None:
        """Verify a normal Gemini response is parsed correctly."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Hello world"}],
                    }
                }
            ]
        }

        with patch("apex.core.gemini_native.requests.post", return_value=mock_resp) as post:
            text = generate_content(
                "AQ.test-key",
                "models/gemini-2.0-flash",
                system="Be helpful.",
                user="Say hello.",
            )

        assert text == "Hello world"
        # Verify the URL includes the model name
        call_url = post.call_args[0][0]
        assert "models/gemini-2.0-flash" in call_url
        # Verify auth key passed as query param
        assert post.call_args[1]["params"] == {"key": "AQ.test-key"}
        # Verify system instruction sent
        payload = post.call_args[1]["json"]
        assert payload["systemInstruction"]["parts"][0]["text"] == "Be helpful."

    def test_without_system_instruction(self) -> None:
        """When system is empty, omit systemInstruction from payload."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "ok"}]}}]
        }

        with patch("apex.core.gemini_native.requests.post", return_value=mock_resp) as post:
            generate_content(
                "AQ.k",
                "models/gemini-2.0-flash",
                system="   ",
                user="hi",
            )

        payload = post.call_args[1]["json"]
        assert "systemInstruction" not in payload

    def test_no_candidates_raises(self) -> None:
        """When candidates list is empty, raise with block reason."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "promptFeedback": {"blockReason": "SAFETY"},
            "candidates": [],
        }

        with patch("apex.core.gemini_native.requests.post", return_value=mock_resp):
            with pytest.raises(ValueError, match="no candidates.*block=SAFETY"):
                generate_content("AQ.k", "models/gemini-2.0-flash", system="", user="bad")

    def test_empty_text_raises(self) -> None:
        """When candidate text is empty, raise ValueError."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": ""}]}}]
        }

        with patch("apex.core.gemini_native.requests.post", return_value=mock_resp):
            with pytest.raises(ValueError, match="empty text"):
                generate_content("AQ.k", "models/gemini-2.0-flash", system="", user="hi")

    def test_non_dict_response_raises(self) -> None:
        """When the API returns a non-dict, raise ValueError."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = ["unexpected", "array"]

        with patch("apex.core.gemini_native.requests.post", return_value=mock_resp):
            with pytest.raises(ValueError, match="unexpected Gemini response shape"):
                generate_content("AQ.k", "models/gemini-2.0-flash", system="", user="hi")

    def test_model_id_strips_prefix(self) -> None:
        """The 'models/' prefix is removed if present, then re-added by format string."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "ok"}]}}]
        }

        with patch("apex.core.gemini_native.requests.post", return_value=mock_resp) as post:
            # Pass with prefix
            generate_content("AQ.k", "models/gemini-2.0-flash", system="", user="hi")
            call_url = post.call_args[0][0]
            assert "models/gemini-2.0-flash" in call_url

    def test_retry_on_http_error(self) -> None:
        """HTTP errors trigger retries via call_with_retries."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = ConnectionError("timeout")
        # After 3 retries, the exception propagates
        with patch("apex.core.gemini_native.requests.post", return_value=mock_resp):
            with pytest.raises(ConnectionError):
                generate_content("AQ.k", "models/gemini-2.0-flash", system="", user="hi")

    def test_parts_multiple_segments_joined(self) -> None:
        """Multiple text parts are joined together."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "First "},
                            {"text": "Second"},
                        ],
                    }
                }
            ]
        }

        with patch("apex.core.gemini_native.requests.post", return_value=mock_resp):
            text = generate_content("AQ.k", "models/gemini-2.0-flash", system="", user="hi")
            assert text == "First Second"
