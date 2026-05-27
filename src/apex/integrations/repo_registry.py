from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from apex.core.config import Settings


@dataclass(frozen=True)
class RepoSpec:
    key: str
    repo: str
    role: str
    path_value: str
    required: bool


class IntegrationRegistry:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.specs = [
            RepoSpec(
                key="tradingagents",
                repo="TauricResearch/TradingAgents",
                role="L2 multi-agent framework",
                path_value=settings.tradingagents_repo_path,
                required=False,
            ),
            RepoSpec(
                key="dexter",
                repo="virattt/dexter",
                role="L2 adversarial deep research",
                path_value=settings.dexter_repo_path,
                required=False,
            ),
            RepoSpec(
                key="anthropic-financial-services",
                repo="anthropics/financial-services",
                role="L1 prompt patterns",
                path_value=settings.anthropic_financial_services_repo_path,
                required=False,
            ),
            RepoSpec(
                key="mirofish",
                repo="666ghj/MiroFish",
                role="L0 overnight news digest",
                path_value=settings.mirofish_repo_path,
                required=False,
            ),
            RepoSpec(
                key="daily-stock-analysis",
                repo="ZhuLinsen/daily_stock_analysis",
                role="L0 daily market analysis",
                path_value=settings.daily_stock_analysis_repo_path,
                required=False,
            ),
            RepoSpec(
                key="kronos",
                repo="shiyu-coder/Kronos",
                role="L1 regime context",
                path_value=settings.kronos_repo_path,
                required=False,
            ),
            RepoSpec(
                key="polymarket-mcp",
                repo="guangxiangdebizi/PolyMarket-MCP",
                role="L0/L1 prediction market signal layer",
                path_value=settings.polymarket_repo_path or settings.polymarket_mcp_path,
                required=False,
            ),
            RepoSpec(
                key="whitmorelabs-mcp",
                repo="whitmorelabs/polymarket-mcp",
                role="L1 whale intelligence",
                path_value=settings.whitmorelabs_repo_path,
                required=False,
            ),
            RepoSpec(
                key="alpaca-mcp",
                repo="alpacahq/alpaca-mcp-server",
                role="L3 broker execution interface",
                path_value=settings.alpaca_mcp_repo_path,
                required=False,
            ),
        ]

    @staticmethod
    def _path_status(path_value: str) -> tuple[bool, str]:
        if not path_value:
            return False, "not configured"
        candidate = Path(path_value).expanduser()
        if candidate.exists():
            return True, f"available at {candidate.resolve()}"
        return False, f"missing path {candidate}"

    def repo_status(self) -> list[dict]:
        status: list[dict] = []
        for spec in self.specs:
            available, details = self._path_status(spec.path_value)
            status.append(
                {
                    "key": spec.key,
                    "repo": spec.repo,
                    "role": spec.role,
                    "required": spec.required,
                    "available": available,
                    "details": details,
                }
            )
        return status

    def credential_status(self) -> list[dict]:
        checks = [
            (
                "alpaca-paper-mode",
                bool(self.settings.alpaca_paper_trade and "paper" in self.settings.alpaca_base_url.lower()),
                "ALPACA_PAPER_TRADE + ALPACA_BASE_URL paper endpoint",
                True,
            ),
            ("alpaca-api-key", bool(self.settings.alpaca_api_key), "ALPACA_API_KEY present", True),
            ("alpaca-secret-key", bool(self.settings.alpaca_secret_key), "ALPACA_SECRET_KEY present", True),
            (
                "tradier-token",
                bool(self.settings.tradier_sandbox_token and self.settings.tradier_sandbox_acct),
                "TRADIER_SANDBOX_TOKEN + TRADIER_SANDBOX_ACCT present",
                False,
            ),
        ]
        return [
            {
                "key": key,
                "available": available,
                "details": details,
                "required": required,
            }
            for key, available, details, required in checks
        ]

    def validate(self, strict: bool) -> dict:
        repos = self.repo_status()
        creds = self.credential_status()
        missing_required = [
            item
            for item in repos + creds
            if item["required"] and not item["available"]
        ]
        if strict and missing_required:
            missing_keys = ", ".join(item["key"] for item in missing_required)
            raise RuntimeError(f"Strict integration validation failed: {missing_keys}")
        return {
            "strict_mode": strict,
            "repos": repos,
            "credentials": creds,
            "missing_required": missing_required,
        }
