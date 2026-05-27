from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from apex.core.config import Settings, get_settings
from apex.core.logging import get_logger
from apex.integrations.alpaca_adapter import AlpacaDirectIntegration
from apex.integrations.dexter_adapter import DexterAdapter
from apex.integrations.market_data import (
    YFinanceMarketDataClient,
    YFinanceOptionsDataClient,
)
from apex.integrations.financial_prompts import load_financial_services_augmentation
from apex.integrations.polymarket_adapter import PolymarketMCPAdapter
from apex.integrations.tradingagents_adapter import (
    GroqDirectAdapter,
    TradingAgentsAdapter,
)

LOGGER = get_logger(__name__)


@dataclass
class IntegrationHub:
    settings: Settings
    trading_agents: TradingAgentsAdapter | None = None
    groq_direct: GroqDirectAdapter | None = None
    dextex: DexterAdapter | None = None
    polymarket: PolymarketMCPAdapter | None = None
    alpaca_direct: AlpacaDirectIntegration | None = None
    market_data: YFinanceMarketDataClient = field(
        default_factory=YFinanceMarketDataClient
    )
    options_data: YFinanceOptionsDataClient = field(
        default_factory=YFinanceOptionsDataClient
    )
    _initialized: bool = field(default=False, init=False, repr=False)

    def initialize(self) -> None:
        if self._initialized:
            return

        self.trading_agents = self._init_trading_agents()
        self.groq_direct = self._init_groq_direct()
        self.dextex = self._init_dexter()
        self.polymarket = self._init_polymarket()
        self.alpaca_direct = self._init_alpaca_direct()

        self._initialized = True
        self._log_status()

    def _init_groq_direct(self) -> GroqDirectAdapter | None:
        from apex.core.llm_routing import resolve_llm_route

        route = resolve_llm_route(self.settings)
        prov = (route.provider if route else self.settings.llm_provider or "openai").lower()
        api_key = route.api_key if route else ""
        if not api_key:
            if prov == "openai":
                api_key = os.environ.get("OPENAI_API_KEY", "")
            elif prov == "groq":
                api_key = os.environ.get("GROQ_API_KEY", "")

        if route:
            base_url = route.base_url
            model = route.model
        elif prov == "ollama":
            base_url = self.settings.ollama_host
            model = self.settings.llm_model
        elif prov == "groq":
            base_url = self.settings.llm_backend_url or "https://api.groq.com/openai/v1"
            model = self.settings.llm_model
        else:
            base_url = self.settings.llm_backend_url or "https://api.openai.com/v1"
            model = self.settings.llm_model

        extra = load_financial_services_augmentation(
            self.settings.anthropic_financial_services_repo_path
        )
        adapter = GroqDirectAdapter(
            api_key=api_key,
            model=model,
            base_url=base_url,
            provider=prov,
            extra_system_prompt=extra,
        )
        if adapter.available:
            LOGGER.info("Groq direct adapter ready (provider=%s)", prov)
        return adapter

    def _init_trading_agents(self) -> TradingAgentsAdapter | None:
        if not self.settings.tradingagents_repo_path:
            LOGGER.info("TradingAgents repo path not configured, skipping")
            return None

        ta_provider = self.settings.llm_provider
        ta_backend = self.settings.llm_backend_url or None
        if ta_provider == "openai" and (os.getenv("APEX_LLM_ROUTE") or "") in (
            "gemini",
            "openrouter",
        ):
            ta_provider = "openai"
        adapter = TradingAgentsAdapter(
            repo_path=self.settings.tradingagents_repo_path,
            llm_provider=ta_provider,
            deep_think_model=self.settings.llm_deep_think_model,
            quick_think_model=self.settings.llm_quick_think_model,
            backend_url=ta_backend,
        )
        if adapter.available:
            LOGGER.info("TradingAgents adapter ready")
        return adapter

    def _init_dexter(self) -> DexterAdapter | None:
        repo_path = (self.settings.dexter_repo_path or "").strip()
        if not repo_path:
            bundled = Path(__file__).resolve().parents[3] / "external" / "dexter"
            if bundled.is_dir():
                repo_path = str(bundled)
                LOGGER.info("Dexter: using bundled repo at %s", bundled)
        if not repo_path:
            LOGGER.info("Dexter repo path not configured, skipping")
            return None

        adapter = DexterAdapter(
            repo_path=repo_path,
            llm_provider=self.settings.llm_provider,
            model=self.settings.llm_model,
            ollama_base_url=self.settings.ollama_host,
        )
        if adapter.available:
            LOGGER.info("Dexter adapter ready")
        return adapter

    def _init_polymarket(self) -> PolymarketMCPAdapter | None:
        repo_path = (
            self.settings.polymarket_repo_path or self.settings.polymarket_mcp_path or ""
        ).strip()
        if not repo_path:
            bundled = Path(__file__).resolve().parents[3] / "external" / "polymarket-mcp-server"
            if bundled.is_dir():
                repo_path = str(bundled)
                LOGGER.info("Polymarket MCP: using bundled repo at %s", bundled)
        if not repo_path:
            LOGGER.info("Polymarket repo path not configured, skipping")
            return None

        adapter = PolymarketMCPAdapter(repo_path=repo_path, demo_mode=False)
        if adapter.available:
            LOGGER.info("Polymarket MCP adapter ready")
        return adapter

    def _init_alpaca_direct(self) -> AlpacaDirectIntegration | None:
        adapter = AlpacaDirectIntegration(
            api_key=self.settings.alpaca_api_key,
            secret_key=self.settings.alpaca_secret_key,
            base_url=self.settings.alpaca_base_url,
        )
        if adapter.available:
            LOGGER.info("Alpaca direct integration ready")
        return adapter

    def _log_status(self) -> None:
        LOGGER.info("IntegrationHub status:")
        LOGGER.info(
            "  TradingAgents: %s", "READY" if self.trading_agents else "not configured"
        )
        LOGGER.info("  Dexter: %s", "READY" if self.dextex else "not configured")
        LOGGER.info(
            "  Polymarket: %s", "READY" if self.polymarket else "not configured"
        )
        LOGGER.info(
            "  Alpaca Direct: %s", "READY" if self.alpaca_direct else "not configured"
        )
        LOGGER.info("  Market Data (yfinance): READY")
        LOGGER.info("  Options Data (yfinance): READY")

    def get_llm_provider_config(self) -> dict[str, Any]:
        return {
            "provider": self.settings.llm_provider,
            "model": self.settings.llm_model,
            "deep_think_model": self.settings.llm_deep_think_model,
            "quick_think_model": self.settings.llm_quick_think_model,
            "backend_url": self.settings.llm_backend_url or None,
            "ollama_host": self.settings.ollama_host,
            "ollama_model": self.settings.ollama_model,
        }

    def has_trading_agents(self) -> bool:
        return self.trading_agents is not None and self.trading_agents.available

    def has_dexter(self) -> bool:
        return self.dextex is not None and self.dextex.available

    def has_polymarket(self) -> bool:
        return self.polymarket is not None and self.polymarket.available

    def has_groq(self) -> bool:
        return self.groq_direct is not None and self.groq_direct.available

    def has_alpaca(self) -> bool:
        return self.alpaca_direct is not None and self.alpaca_direct.available


_hub: IntegrationHub | None = None


def get_integration_hub() -> IntegrationHub:
    global _hub
    if _hub is None:
        settings = get_settings()
        _hub = IntegrationHub(settings=settings)
        _hub.initialize()
    return _hub


def reset_integration_hub() -> None:
    global _hub
    _hub = None
