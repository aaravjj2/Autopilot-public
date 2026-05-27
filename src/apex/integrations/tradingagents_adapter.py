from __future__ import annotations

import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from apex.core.logging import get_logger

LOGGER = get_logger(__name__)


@dataclass
class GroqDirectAdapter:
    api_key: str = ""
    model: str = "qwen2.5:7b"
    base_url: str = "http://localhost:11434"
    provider: str = "ollama"
    extra_system_prompt: str = ""
    _client: Any = field(default=None, init=False, repr=False)
    _available: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.api_key:
            if self.provider == "openai":
                self.api_key = os.environ.get("OPENAI_API_KEY", "")
            elif self.provider == "groq":
                self.api_key = os.environ.get("GROQ_API_KEY", "")
            else:
                self.api_key = os.environ.get("GROQ_API_KEY", "")

        if self.provider == "ollama":
            self.base_url = os.environ.get("OLLAMA_HOST", self.base_url).rstrip("/")
            try:
                import requests

                ping = requests.get(f"{self.base_url}/api/tags", timeout=3)
                self._available = ping.ok
                if not self._available:
                    LOGGER.warning(
                        "Ollama not reachable at %s (HTTP %s); LLM analysis will use fallback",
                        self.base_url,
                        getattr(ping, "status_code", "?"),
                    )
            except Exception as exc:
                self._available = False
                LOGGER.warning("Ollama health check failed (%s): %s", self.base_url, exc)
        elif self.provider == "groq":
            self.base_url = (
                self.base_url
                if self.base_url and "groq.com" in self.base_url
                else "https://api.groq.com/openai/v1"
            )
            self._available = bool(self.api_key)
        elif self.provider == "openai":
            self.base_url = self.base_url or "https://api.openai.com/v1"
            self._available = bool(self.api_key)
        elif self.api_key:
            self._available = True
        else:
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def _get_client(self) -> Any:
        if self._client is None:
            if self.provider == "ollama":
                self._client = "ollama"
            else:
                try:
                    from openai import OpenAI

                    self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
                except ImportError:
                    self._client = "requests"
        return self._client

    def _ollama_reachable(self) -> bool:
        if self.provider != "ollama":
            return True
        try:
            import requests

            return bool(
                requests.get(f"{self.base_url.rstrip('/')}/api/tags", timeout=2).ok
            )
        except Exception:
            return False

    def analyze(self, symbol: str, market_data: dict[str, Any]) -> dict[str, Any]:
        if not self._available:
            return self._fallback_analysis(symbol, market_data)
        if self.provider == "ollama" and not self._ollama_reachable():
            LOGGER.warning("Ollama dropped mid-session for %s; using fallback", symbol)
            return self._fallback_analysis(symbol, market_data)

        try:
            bars = market_data.get("bars", [])
            fundamentals = market_data.get("fundamentals", {})
            current_price = bars[-1]["close"] if bars else 0.0

            prompt = self._build_prompt(symbol, current_price, fundamentals)

            response = self._call_llm(prompt)

            return self._parse_response(symbol, response, current_price)
        except Exception as exc:
            LOGGER.debug("Analysis failed: %s", exc)
            return self._fallback_analysis(symbol, market_data)

    def _call_ollama(self, prompt: str) -> str:
        import requests

        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 500},
            },
            timeout=60,
        )
        if response.ok:
            return response.json().get("message", {}).get("content", "")
        return ""

    def _call_openai_chat(self, prompt: str) -> str:
        sys_content = self._system_prompt()
        client = self._get_client()
        if client not in ("ollama", "requests"):
            try:
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": sys_content},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=500,
                )
                return (resp.choices[0].message.content or "").strip()
            except Exception as exc:
                LOGGER.debug("OpenAI-compatible SDK call failed: %s", exc)
        import requests

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        try:
            r = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": sys_content},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500,
                },
                timeout=90,
            )
            if r.ok:
                data = r.json()
                ch0 = (data.get("choices") or [{}])[0]
                msg = ch0.get("message") or {}
                return str(msg.get("content", "")).strip()
        except Exception as exc:
            LOGGER.debug("OpenAI-compatible HTTP call failed: %s", exc)
        return ""

    def _call_llm(self, prompt: str) -> str:
        if self.provider == "ollama":
            return self._call_ollama(prompt)
        return self._call_openai_chat(prompt)

    def _system_prompt(self) -> str:
        base = """You are a quantitative trading analyst. Analyze the given stock and output ONLY a JSON object with this exact format:
{"recommendation": "BUY|SELL|HOLD", "confidence": 0-10, "rationale": "brief reason", "direction": "LONG|SHORT|NEUTRAL"}
Do not include any other text. Be decisive and specific."""
        if self.extra_system_prompt:
            return base + "\n\n" + self.extra_system_prompt
        return base

    def _build_prompt(self, symbol: str, price: float, fundamentals: dict) -> str:
        return f"""Analyze {symbol} at ${price:.2f}.

Fundamentals: P/E={fundamentals.get("pe", "N/A")}, Revenue Growth={fundamentals.get("revenue_growth", "N/A")}%, Recommendation={fundamentals.get("analyst_recommendation", "N/A")}

Output ONLY JSON with: recommendation (BUY/SELL/HOLD), confidence (0-10), rationale, direction (LONG/SHORT/NEUTRAL)"""

    def _parse_response(
        self, symbol: str, response: str, current_price: float
    ) -> dict[str, Any]:
        import json
        import re

        try:
            match = re.search(r"\{[^{}]*\}", response, re.DOTALL)
            if match:
                result = json.loads(match.group())
            else:
                result = json.loads(response)

            return {
                "symbol": symbol,
                "current_price": current_price,
                "recommendation": result.get("recommendation", "HOLD"),
                "confidence": float(result.get("confidence", 5.0)),
                "rationale": result.get("rationale", ""),
                "direction": result.get("direction", "NEUTRAL"),
                "agent_type": "ollama",
            }
        except Exception:
            return self._fallback_analysis(symbol, {"bars": [{"close": current_price}]})

    def _fallback_analysis(
        self, symbol: str, market_data: dict[str, Any]
    ) -> dict[str, Any]:
        bars = market_data.get("bars", [])
        current_price = bars[-1]["close"] if bars else 0.0
        return {
            "symbol": symbol,
            "current_price": current_price,
            "recommendation": "HOLD",
            "confidence": 5.0,
            "rationale": "Analysis service unavailable",
            "direction": "NEUTRAL",
            "agent_type": "fallback",
        }

    def run_counter_thesis(
        self, symbol: str, thesis: str, conviction: float
    ) -> dict[str, Any]:
        if not self._available:
            return {"severity": 5.0, "risks": [], "recommended_action": "PROCEED"}

        try:
            prompt = f"""For {symbol}: {thesis}

This trade has conviction {conviction}/10. Find weaknesses and risks. What would kill this trade?
Output ONLY JSON: {{"severity": 1-10, "risks": ["risk1", "risk2"], "recommended_action": "REDUCE_CONVICTION|PROCEED"}}"""

            response = self._call_llm(prompt)

            import json
            import re

            match = re.search(r'\{[^{}]*"severity"[^}]*\}', response, re.DOTALL)
            if match:
                result = json.loads(match.group())
            else:
                result = {"severity": 5.0, "risks": [], "recommended_action": "PROCEED"}

            return {
                "severity": float(result.get("severity", 5.0)),
                "risks": result.get("risks", []),
                "recommended_action": result.get("recommended_action", "PROCEED"),
            }
        except Exception:
            return {"severity": 5.0, "risks": [], "recommended_action": "PROCEED"}


@dataclass
class TradingAgentsAdapter:
    repo_path: str
    llm_provider: str = "openai"
    deep_think_model: str = "qwen2.5:7b"
    quick_think_model: str = "llama3.2:3b"
    backend_url: str | None = None
    api_key: str = ""
    ollama_host: str = "http://localhost:11434"
    _graph: Any = field(default=None, init=False, repr=False)
    _available: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.repo_path:
            LOGGER.warning("TradingAgents repo path not configured")
            return
        candidate = Path(self.repo_path).expanduser().resolve()
        if not candidate.exists():
            LOGGER.warning("TradingAgents repo not found at %s", candidate)
            return
        sys.path.insert(0, str(candidate))

        if self.llm_provider == "groq":
            self.backend_url = "https://api.groq.com/openai/v1"
            if not self.api_key:
                self.api_key = os.environ.get("GROQ_API_KEY", "")
        elif self.llm_provider == "ollama":
            self.backend_url = self.ollama_host
            self.api_key = "ollama"  # ollama doesn't need key

        self._available = True
        LOGGER.info(
            "TradingAgents adapter initialized from %s (provider=%s, model=%s)",
            candidate,
            self.llm_provider,
            self.deep_think_model,
        )

    @property
    def available(self) -> bool:
        return self._available

    def _ensure_graph(self) -> Any:
        if self._graph is None:
            from tradingagents.graph.trading_graph import TradingAgentsGraph
            from tradingagents.default_config import DEFAULT_CONFIG

            config = DEFAULT_CONFIG.copy()
            config.update(
                {
                    "llm_provider": self.llm_provider,
                    "deep_think_llm": self.deep_think_model,
                    "quick_think_llm": self.quick_think_model,
                    "backend_url": self.backend_url,
                }
            )
            self._graph = TradingAgentsGraph(
                selected_analysts=["market", "news", "fundamentals"],
                debug=False,
                config=config,
            )
        return self._graph

    def analyze(self, symbol: str, trade_date: str | None = None) -> dict[str, Any]:
        if not self._available:
            return {"error": "TradingAgents not available", "decision": "HOLD"}

        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            current_price = float(hist["Close"].iloc[-1]) if len(hist) > 0 else 0.0

            if trade_date is None:
                from datetime import date

                trade_date = date.today().isoformat()

            graph = self._ensure_graph()
            _, decision = graph.propagate(symbol, trade_date)

            recommendation = "HOLD"
            confidence = 5.0
            if decision:
                decision_upper = str(decision).upper()
                if "BUY" in decision_upper or "LONG" in decision_upper:
                    recommendation = "BUY"
                    confidence = 7.5
                elif "SELL" in decision_upper or "SHORT" in decision_upper:
                    recommendation = "SELL"
                    confidence = 7.5
                elif "CLOSE" in decision_upper:
                    recommendation = "CLOSE"
                    confidence = 6.0

            return {
                "symbol": symbol,
                "current_price": current_price,
                "decision": decision,
                "recommendation": recommendation,
                "confidence": confidence,
                "agent_type": "tradingagents",
            }
        except Exception as exc:
            LOGGER.error("TradingAgents analysis failed for %s: %s", symbol, exc)
            return {"error": str(exc), "decision": "HOLD", "confidence": 5.0}

    def get_conviction_from_analysis(
        self, symbol: str, trade_date: str | None = None
    ) -> float:
        result = self.analyze(symbol, trade_date)
        if "error" in result:
            return 5.0
        return result.get("confidence", 5.0)

    def get_trade_recommendation(self, symbol: str) -> tuple[str, float, str]:
        result = self.analyze(symbol)
        if "error" in result:
            return "HOLD", 5.0, result.get("error", "unknown")
        recommendation = result.get("recommendation", "HOLD")
        confidence = result.get("confidence", 5.0)
        rationale = result.get("decision", "No decision from TradingAgents")
        return recommendation, confidence, rationale
