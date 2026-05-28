from __future__ import annotations

# BRIGHTDATA INTEGRATION — 2026-05-27 — MCP client configuration wrapper

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any

from apex.core.config import Settings
from apex.core.logging import get_logger

LOGGER = get_logger(__name__)


@dataclass(slots=True)
class BrightDataMcpClient:
    settings: Settings
    _proc: asyncio.subprocess.Process | None = None
    _proc_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _next_id: int = 1
    _pending: dict[int, asyncio.Future[dict[str, Any]]] = field(default_factory=dict)
    _reader_task: asyncio.Task[None] | None = None
    _tools_cache: set[str] | None = None

    def is_configured(self) -> bool:
        return bool((self.settings.brightdata_api_key or "").strip())

    def _get_mcp_env(self) -> dict[str, str]:
        return {
            "API_TOKEN": (self.settings.brightdata_api_key or "").strip(),
            "WEB_UNLOCKER_ZONE": os.getenv("WEB_UNLOCKER_ZONE", "mcp_unlocker"),
            "BROWSER_AUTH": os.getenv("BROWSER_AUTH", ""),
            "PRO_MODE": os.getenv("BRIGHTDATA_PRO_MODE", "false"),
        }

    def _get_mcp_config(self) -> dict[str, object]:
        return {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@brightdata/mcp"],
            "env": self._get_mcp_env(),
        }

    async def _ensure_started(self) -> None:
        if self._proc is not None and self._proc.returncode is None:
            return
        async with self._proc_lock:
            if self._proc is not None and self._proc.returncode is None:
                return
            if not self.is_configured():
                raise RuntimeError("BrightData MCP client not configured")

            cfg = self._get_mcp_config()
            env = os.environ.copy()
            env.update({k: str(v) for k, v in (cfg.get("env") or {}).items()})  # type: ignore[union-attr]

            self._proc = await asyncio.create_subprocess_exec(
                str(cfg["command"]),
                *[str(x) for x in (cfg["args"] or [])],  # type: ignore[index]
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            self._reader_task = asyncio.create_task(self._read_loop())
            await self._initialize_mcp()

    async def _initialize_mcp(self) -> None:
        # MCP servers typically expect initialize + initialized notification.
        try:
            await self._rpc(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "apex-autopilot", "version": "0.1"},
                },
            )
            await self._notify("notifications/initialized", {})
        except Exception as exc:
            # Some servers tolerate tool calls without init; soft-fail here.
            LOGGER.warning("BrightData MCP initialize failed (continuing): %s", exc)
        try:
            tools = await self._rpc("tools/list", {})
            names: set[str] = set()
            if isinstance(tools, dict) and isinstance(tools.get("tools"), list):
                for t in tools["tools"]:
                    if isinstance(t, dict) and isinstance(t.get("name"), str):
                        names.add(t["name"])
            self._tools_cache = names or None
        except Exception:
            self._tools_cache = None

    async def has_tool(self, name: str) -> bool:
        await self._ensure_started()
        if self._tools_cache is None:
            try:
                tools = await self._rpc("tools/list", {})
                names: set[str] = set()
                if isinstance(tools, dict) and isinstance(tools.get("tools"), list):
                    for t in tools["tools"]:
                        if isinstance(t, dict) and isinstance(t.get("name"), str):
                            names.add(t["name"])
                self._tools_cache = names or None
            except Exception:
                return False
        return bool(self._tools_cache and name in self._tools_cache)

    async def _read_loop(self) -> None:
        if self._proc is None:
            raise RuntimeError("_read_loop called before MCP process started")
        if self._proc.stdout is None:
            raise RuntimeError("MCP process has no stdout pipe")
        while True:
            line = await self._proc.stdout.readline()
            if not line:
                return
            try:
                # Avoid importing json at module scope for faster import paths.
                import json

                data = json.loads(line.decode("utf-8", errors="replace"))
            except Exception:
                continue
            if isinstance(data, dict) and "id" in data and data.get("jsonrpc") == "2.0":
                try:
                    req_id = int(data["id"])
                except Exception:
                    continue
                fut = self._pending.pop(req_id, None)
                if fut is not None and not fut.done():
                    fut.set_result(data)

    async def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        await self._ensure_started()
        if self._proc is None:
            raise RuntimeError("_rpc called before MCP process started")
        if self._proc.stdin is None:
            raise RuntimeError("MCP process has no stdin pipe")
        req_id = self._next_id
        self._next_id += 1
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending[req_id] = fut

        import json

        payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        self._proc.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
        await self._proc.stdin.drain()
        msg = await asyncio.wait_for(fut, timeout=45.0)
        if "error" in msg:
            raise RuntimeError(str(msg["error"]))
        return msg.get("result", {})

    async def _notify(self, method: str, params: dict[str, Any]) -> None:
        await self._ensure_started()
        if self._proc is None:
            raise RuntimeError("_notify called before MCP process started")
        if self._proc.stdin is None:
            raise RuntimeError("MCP process has no stdin pipe")
        import json

        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        self._proc.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
        await self._proc.stdin.drain()

    @staticmethod
    def _extract_text(result: Any) -> Any:
        # Many MCP servers return {content: [{type:"text", text:"..."}]}
        if isinstance(result, dict) and isinstance(result.get("content"), list):
            parts: list[str] = []
            for item in result["content"]:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
            return "\n".join([p for p in parts if p])
        return result

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        res = await self._rpc("tools/call", {"name": name, "arguments": arguments})
        return self._extract_text(res)

    def __repr__(self) -> str:
        return f"BrightDataMcpClient(configured={self.is_configured()})"

    def __str__(self) -> str:
        return self.__repr__()
