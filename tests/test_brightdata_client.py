from __future__ import annotations
# BRIGHTDATA INTEGRATION — 2026-05-27 — MCP client configuration tests

from types import SimpleNamespace

from apex.integrations.brightdata_mcp_client import BrightDataMcpClient


def test_client_not_configured_when_key_absent() -> None:
    client = BrightDataMcpClient(SimpleNamespace(brightdata_api_key=""))  # type: ignore[arg-type]
    assert client.is_configured() is False


def test_client_configured_when_key_present() -> None:
    client = BrightDataMcpClient(SimpleNamespace(brightdata_api_key="test_key"))  # type: ignore[arg-type]
    cfg = client._get_mcp_config()
    assert client.is_configured() is True
    assert cfg["command"] == "npx"
    assert cfg["env"]["API_TOKEN"] == "test_key"


def test_mcp_env_never_exposes_key_in_logs() -> None:
    secret = "test_key_value_123"
    client = BrightDataMcpClient(SimpleNamespace(brightdata_api_key=secret))  # type: ignore[arg-type]
    assert secret not in str(client)
    assert secret not in repr(client)
