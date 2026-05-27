#!/usr/bin/env python3
"""Stdio MCP server exposing APEX agent tools over HTTP (Rapid Agent hackathon)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

API_BASE = os.getenv("APEX_AGENT_API_BASE", "http://127.0.0.1:8000")


def _get(path: str) -> Any:
    req = urllib.request.Request(f"{API_BASE}{path}", method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _post(path: str, body: dict | None = None) -> Any:
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


TOOLS = [
    {
        "name": "scan_arbitrage",
        "description": "Scan for cross-market arbitrage opportunities",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_opportunity",
        "description": "Get arb opportunity by id",
        "inputSchema": {
            "type": "object",
            "properties": {"arb_id": {"type": "string"}},
            "required": ["arb_id"],
        },
    },
    {
        "name": "explain_risk_gates",
        "description": "Run 14-check risk stack for an arb",
        "inputSchema": {
            "type": "object",
            "properties": {"arb_id": {"type": "string"}},
            "required": ["arb_id"],
        },
    },
    {
        "name": "paper_trade_arb",
        "description": "Submit governed paper dual-leg trade",
        "inputSchema": {
            "type": "object",
            "properties": {"arb_id": {"type": "string"}},
            "required": ["arb_id"],
        },
    },
    {
        "name": "get_audit_tail",
        "description": "Recent audit log tail",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer"}},
        },
    },
    {
        "name": "backtest_summary",
        "description": "Arb backtest summary metrics",
        "inputSchema": {
            "type": "object",
            "properties": {"lookback_days": {"type": "integer"}},
        },
    },
    {
        "name": "run_mission",
        "description": "Run canned multi-step mission",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mission_id": {
                    "type": "string",
                    "enum": [
                        "morning_arb_briefing",
                        "governed_paper_execution",
                        "incident_post_mortem",
                    ],
                },
                "arb_id": {"type": "string"},
            },
            "required": ["mission_id"],
        },
    },
]


def _dispatch(name: str, arguments: dict[str, Any]) -> Any:
    if name == "scan_arbitrage":
        return _post("/api/agent/tools/scan_arbitrage")
    if name == "get_opportunity":
        return _get(f"/api/agent/tools/opportunity/{arguments['arb_id']}")
    if name == "explain_risk_gates":
        return _get(f"/api/agent/tools/risk_gates/{arguments['arb_id']}")
    if name == "paper_trade_arb":
        return _post(f"/api/agent/tools/paper_trade/{arguments['arb_id']}")
    if name == "get_audit_tail":
        limit = int(arguments.get("limit", 40))
        return _get(f"/api/agent/tools/audit_tail?limit={limit}")
    if name == "backtest_summary":
        days = int(arguments.get("lookback_days", 90))
        return _get(f"/api/agent/tools/backtest?lookback_days={days}")
    if name == "run_mission":
        mid = arguments["mission_id"]
        body = {k: v for k, v in arguments.items() if k != "mission_id"}
        return _post(f"/api/agent/run/{mid}", body)
    raise ValueError(f"Unknown tool: {name}")


def _send(msg: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def main() -> None:
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        rid = req.get("id")
        method = req.get("method")
        if method == "initialize":
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": rid,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "apex-mcp", "version": "1.0.0"},
                    },
                }
            )
        elif method == "tools/list":
            _send({"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            params = req.get("params") or {}
            name = params.get("name", "")
            args = params.get("arguments") or {}
            try:
                result = _dispatch(name, args)
                _send(
                    {
                        "jsonrpc": "2.0",
                        "id": rid,
                        "result": {
                            "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
                        },
                    }
                )
            except urllib.error.HTTPError as exc:
                body = exc.read().decode()
                _send(
                    {
                        "jsonrpc": "2.0",
                        "id": rid,
                        "error": {"code": exc.code, "message": body},
                    }
                )
            except Exception as exc:
                _send(
                    {
                        "jsonrpc": "2.0",
                        "id": rid,
                        "error": {"code": -32000, "message": str(exc)},
                    }
                )
        else:
            _send({"jsonrpc": "2.0", "id": rid, "result": {}})


if __name__ == "__main__":
    main()
