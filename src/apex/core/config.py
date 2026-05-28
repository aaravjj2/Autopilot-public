from __future__ import annotations

import logging
from datetime import date
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from apex.core.env_bootstrap import bootstrap_environment, env_file_paths, repo_root

# NOTE: config.py intentionally uses stdlib logging to avoid a circular import
# with apex.core.logging (which imports Settings from this module).
LOGGER = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_file_paths(),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    alpaca_api_key: str = Field(default="", alias="ALPACA_API_KEY")
    alpaca_secret_key: str = Field(default="", alias="ALPACA_SECRET_KEY")
    alpaca_base_url: str = Field(
        default="https://paper-api.alpaca.markets", alias="ALPACA_BASE_URL"
    )
    alpaca_paper_trade: bool = Field(default=True, alias="ALPACA_PAPER_TRADE")

    tradier_sandbox_token: str = Field(default="", alias="TRADIER_SANDBOX_TOKEN")
    tradier_sandbox_acct: str = Field(default="", alias="TRADIER_SANDBOX_ACCT")
    tradier_base_url: str = Field(
        default="https://sandbox.tradier.com", alias="TRADIER_BASE_URL"
    )

    polymarket_mcp_path: str = Field(default="", alias="POLYMARKET_MCP_PATH")
    whitmorelabs_mcp_api_key: str = Field(default="", alias="WHITMORELABS_MCP_API_KEY")
    tradingagents_repo_path: str = Field(default="", alias="TRADINGAGENTS_REPO_PATH")
    dexter_repo_path: str = Field(default="", alias="DEXTER_REPO_PATH")
    anthropic_financial_services_repo_path: str = Field(
        default="", alias="ANTHROPIC_FINANCIAL_SERVICES_REPO_PATH"
    )
    mirofish_repo_path: str = Field(default="", alias="MIROFISH_REPO_PATH")
    daily_stock_analysis_repo_path: str = Field(
        default="", alias="DAILY_STOCK_ANALYSIS_REPO_PATH"
    )
    daily_stock_analysis_enabled: bool = Field(
        default=True, alias="DAILY_STOCK_ANALYSIS_ENABLED"
    )
    daily_stock_analysis_region: str = Field(
        default="us", alias="DAILY_STOCK_ANALYSIS_REGION"
    )
    daily_stock_analysis_market_review: bool = Field(
        default=True, alias="DAILY_STOCK_ANALYSIS_MARKET_REVIEW"
    )
    daily_stock_analysis_stock_digest: bool = Field(
        default=False, alias="DAILY_STOCK_ANALYSIS_STOCK_DIGEST"
    )
    daily_stock_analysis_max_stocks: int = Field(
        default=8, ge=1, le=30, alias="DAILY_STOCK_ANALYSIS_MAX_STOCKS"
    )
    daily_stock_analysis_timeout_market_sec: int = Field(
        default=300, ge=60, le=1800, alias="DAILY_STOCK_ANALYSIS_TIMEOUT_MARKET_SEC"
    )
    daily_stock_analysis_timeout_stocks_sec: int = Field(
        default=900, ge=120, le=3600, alias="DAILY_STOCK_ANALYSIS_TIMEOUT_STOCKS_SEC"
    )
    kronos_repo_path: str = Field(default="", alias="KRONOS_REPO_PATH")
    polymarket_repo_path: str = Field(default="", alias="POLYMARKET_REPO_PATH")
    whitmorelabs_repo_path: str = Field(default="", alias="WHITMORELABS_REPO_PATH")
    alpaca_mcp_repo_path: str = Field(default="", alias="ALPACA_MCP_REPO_PATH")

    chromadb_path: Path = Field(default=Path("./data/chromadb"), alias="CHROMADB_PATH")
    sqlite_path: Path = Field(default=Path("./data/audit.db"), alias="SQLITE_PATH")
    redis_url: str = Field(default="redis://127.0.0.1:6379/0", alias="REDIS_URL")
    kalshi_tick_mmap_path: Path = Field(
        default=Path("./data/kalshi_ticks.jsonl"), alias="KALSHI_TICK_MMAP_PATH"
    )
    arb_stream_use_patches: bool = Field(default=True, alias="ARB_STREAM_USE_PATCHES")
    grpc_port: int = Field(default=50051, alias="GRPC_PORT")
    kelly_alpha: float = Field(default=0.25, ge=0.01, le=1.0, alias="KELLY_ALPHA")
    kelly_lambda: float = Field(default=0.02, ge=0.0, le=0.2, alias="KELLY_LAMBDA")
    cftc_contract_limit_usd: float = Field(
        default=250_000.0, alias="CFTC_CONTRACT_LIMIT_USD"
    )
    var_mc_paths: int = Field(default=10_000, ge=100, le=50_000, alias="VAR_MC_PATHS")

    max_position_size_pct: float = Field(default=5.0, alias="MAX_POSITION_SIZE_PCT")
    max_sector_pct: float = Field(default=25.0, alias="MAX_SECTOR_PCT")
    daily_loss_limit_pct: float = Field(default=3.0, alias="DAILY_LOSS_LIMIT_PCT")
    max_open_positions: int = Field(default=20, alias="MAX_OPEN_POSITIONS")
    options_max_loss_pct: float = Field(default=2.0, alias="OPTIONS_MAX_LOSS_PCT")
    options_trading_enabled: bool = Field(default=True, alias="OPTIONS_TRADING_ENABLED")
    conviction_floor: float = Field(default=6.0, alias="CONVICTION_FLOOR")
    dexter_threshold: float = Field(default=7.0, alias="DEXTER_THRESHOLD")
    dexter_trigger_conviction: float = Field(
        default=8.0, alias="DEXTER_TRIGGER_CONVICTION"
    )
    pm_weight_adj: float = Field(default=0.0, alias="PM_WEIGHT_ADJ")
    watchlist_max_size: int = Field(default=60, alias="WATCHLIST_MAX_SIZE")
    iv_rank_long_threshold: float = Field(default=50.0, alias="IV_RANK_LONG_THRESHOLD")
    iv_rank_short_threshold: float = Field(
        default=50.0, alias="IV_RANK_SHORT_THRESHOLD"
    )
    earnings_blackout_days: int = Field(default=2, alias="EARNINGS_BLACKOUT_DAYS")

    weekly_focus_enabled: bool = Field(default=True, alias="WEEKLY_FOCUS_ENABLED")
    weekly_focus_symbols: str = Field(default="", alias="WEEKLY_FOCUS_SYMBOLS")
    weekly_focus_conviction_boost: float = Field(
        default=0.35, ge=0.0, le=2.0, alias="WEEKLY_FOCUS_CONVICTION_BOOST"
    )
    nvda_earnings_date: date | None = Field(default=None, alias="NVDA_EARNINGS_DATE")
    nvda_earnings_window_days: int = Field(
        default=5, ge=0, le=14, alias="NVDA_EARNINGS_WINDOW_DAYS"
    )
    nvda_earnings_conviction_boost: float = Field(
        default=0.45, ge=0.0, le=2.0, alias="NVDA_EARNINGS_CONVICTION_BOOST"
    )
    weekly_focus_relax_earnings_blackout: bool = Field(
        default=True, alias="WEEKLY_FOCUS_RELAX_EARNINGS_BLACKOUT"
    )
    weekly_focus_earnings_symbols: str = Field(
        default="NVDA", alias="WEEKLY_FOCUS_EARNINGS_SYMBOLS"
    )

    copy_trading_enabled: bool = Field(default=True, alias="COPY_TRADING_ENABLED")
    copy_trading_api_url: str = Field(
        default="http://127.0.0.1:8000", alias="COPY_TRADING_API_URL"
    )
    copy_trading_web_url: str = Field(
        default="http://127.0.0.1:3000", alias="COPY_TRADING_WEB_URL"
    )
    autopilot_local_path: str = Field(default="", alias="AUTOPILOT_LOCAL_PATH")
    quiver_api_key: str = Field(default="", alias="QUIVER_API_KEY")
    sec_api_key: str = Field(default="", alias="SEC_API_KEY")

    streamlit_port: int = Field(default=8501, alias="STREAMLIT_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    apex_log_json: bool = Field(default=False, alias="APEX_LOG_JSON")
    strict_integrations: bool = Field(default=False, alias="STRICT_INTEGRATIONS")
    autotrade_all_approved: bool = Field(default=True, alias="AUTOTRADE_ALL_APPROVED")
    demo_mode: bool = Field(default=False, alias="DEMO_MODE")
    public_demo_url: str = Field(default="", alias="PUBLIC_DEMO_URL")
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="CORS_ORIGINS",
    )

    apex_webhook_url: str = Field(default="", alias="APEX_WEBHOOK_URL")
    health_server_bind: str = Field(default="127.0.0.1", alias="APEX_HEALTH_BIND")
    health_server_port: int = Field(default=8088, alias="APEX_HEALTH_PORT")

    ingestion_fetch_max_attempts: int = Field(default=2, ge=1, le=8, alias="INGESTION_FETCH_MAX_ATTEMPTS")
    ingestion_fetch_backoff_sec: float = Field(default=1.5, ge=0.0, le=60.0, alias="INGESTION_FETCH_BACKOFF_SEC")
    scheduler_transient_max_attempts: int = Field(
        default=2, ge=1, le=8, alias="SCHEDULER_TRANSIENT_MAX_ATTEMPTS"
    )
    scheduler_transient_backoff_sec: float = Field(
        default=2.0, ge=0.0, le=120.0, alias="SCHEDULER_TRANSIENT_BACKOFF_SEC"
    )

    broker_submit_max_attempts: int = Field(default=2, ge=1, le=10, alias="BROKER_SUBMIT_MAX_ATTEMPTS")
    broker_submit_backoff_sec: float = Field(default=1.5, ge=0.0, le=60.0, alias="BROKER_SUBMIT_BACKOFF_SEC")
    broker_monitor_fill_max_attempts: int = Field(
        default=2, ge=1, le=10, alias="BROKER_MONITOR_FILL_MAX_ATTEMPTS"
    )
    broker_get_order_max_attempts: int = Field(default=2, ge=1, le=10, alias="BROKER_GET_ORDER_MAX_ATTEMPTS")
    broker_circuit_failure_threshold: int = Field(
        default=0, ge=0, le=50, alias="BROKER_CIRCUIT_FAILURE_THRESHOLD"
    )
    broker_circuit_cooldown_sec: float = Field(
        default=120.0, ge=1.0, le=3600.0, alias="BROKER_CIRCUIT_COOLDOWN_SEC"
    )

    ingestion_inter_symbol_delay_ms: int = Field(
        default=0, ge=0, le=30_000, alias="INGESTION_INTER_SYMBOL_DELAY_MS"
    )

    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    llm_model: str = Field(default="gpt-4o", alias="LLM_MODEL")
    llm_deep_think_model: str = Field(default="gpt-4o", alias="LLM_DEEP_THINK_MODEL")
    llm_quick_think_model: str = Field(
        default="gpt-4o-mini", alias="LLM_QUICK_THINK_MODEL"
    )
    llm_backend_url: str = Field(default="", alias="LLM_BACKEND_URL")
    ollama_host: str = Field(default="http://localhost:11434", alias="OLLAMA_HOST")
    ollama_model: str = Field(default="mistral:7b", alias="OLLAMA_MODEL")

    top_symbols_per_day: int = Field(default=5, alias="TOP_SYMBOLS_PER_DAY")
    initial_account_equity: float = Field(
        default=100000.0, alias="INITIAL_ACCOUNT_EQUITY"
    )

    exit_monitor_enabled: bool = Field(default=True, alias="EXIT_MONITOR_ENABLED")
    exit_stop_pct: float = Field(default=4.0, alias="EXIT_STOP_PCT")
    exit_take_profit_pct: float = Field(default=10.0, alias="EXIT_TAKE_PROFIT_PCT")
    exit_max_hold_days: int = Field(default=5, ge=0, le=365, alias="EXIT_MAX_HOLD_DAYS")
    exit_eod_flatten_enabled: bool = Field(default=True, alias="EXIT_EOD_FLATTEN_ENABLED")
    exit_signal_reversal_enabled: bool = Field(
        default=True, alias="EXIT_SIGNAL_REVERSAL_ENABLED"
    )
    exit_use_proposal_stops: bool = Field(default=True, alias="EXIT_USE_PROPOSAL_STOPS")
    trailing_stop_pct: float = Field(default=0.0, ge=0.0, le=50.0, alias="TRAILING_STOP_PCT")
    alpaca_flatten_options_to_equity: bool = Field(
        default=False, alias="ALPACA_FLATTEN_OPTIONS_TO_EQUITY"
    )

    polymarket_paper_trading_enabled: bool = Field(
        default=False, alias="POLYMARKET_PAPER_TRADING_ENABLED"
    )
    polymarket_paper_bankroll_usd: float = Field(
        default=10_000.0, ge=100.0, alias="POLYMARKET_PAPER_BANKROLL_USD"
    )
    polymarket_paper_max_order_usd: float = Field(
        default=500.0, ge=1.0, alias="POLYMARKET_PAPER_MAX_ORDER_USD"
    )
    polymarket_paper_max_open_positions: int = Field(
        default=25, ge=1, le=500, alias="POLYMARKET_PAPER_MAX_OPEN_POSITIONS"
    )
    polymarket_automated_events_enabled: bool = Field(
        default=False, alias="POLYMARKET_AUTOMATED_EVENTS_ENABLED"
    )
    polymarket_event_discovery_limit: int = Field(
        default=20, ge=1, le=100, alias="POLYMARKET_EVENT_DISCOVERY_LIMIT"
    )
    polymarket_event_min_volume_24h: float = Field(
        default=50_000.0, ge=0.0, alias="POLYMARKET_EVENT_MIN_VOLUME_24H"
    )
    polymarket_paper_default_stake_usd: float = Field(
        default=50.0, ge=1.0, alias="POLYMARKET_PAPER_DEFAULT_STAKE_USD"
    )
    polymarket_event_min_edge: float = Field(
        default=0.08, ge=0.0, le=0.49, alias="POLYMARKET_EVENT_MIN_EDGE"
    )
    polymarket_event_policy: str = Field(
        default="underdog_bins", alias="POLYMARKET_EVENT_POLICY"
    )
    polymarket_training_export_path: Path = Field(
        default=Path("./data/polymarket_training.jsonl"),
        alias="POLYMARKET_TRAINING_EXPORT_PATH",
    )
    polymarket_training_fetch_limit: int = Field(
        default=200, ge=1, le=2000, alias="POLYMARKET_TRAINING_FETCH_LIMIT"
    )

    # ---- Kalshi arb parameters --------------------------------------------------
    kalshi_access_key: str | None = Field(default=None, alias="KALSHI_API_KEY")
    kalshi_api_private_key: str | None = Field(default=None, alias="KALSHI_API_PRIVATE_KEY")
    kalshi_private_key_path: str = Field(
        default="./keys/kalshi_private_key.pem", alias="KALSHI_PRIVATE_KEY_PATH"
    )
    kalshi_base_url: str = Field(
        default="https://demo-api.kalshi.co/trade-api/v2",
        alias="KALSHI_BASE_URL",
    )
    kalshi_demo_trading_enabled: bool = Field(
        default=False,
        alias="KALSHI_DEMO_TRADING_ENABLED",
    )
    kalshi_demo_probe_enabled: bool = Field(
        default=True, alias="KALSHI_DEMO_PROBE_ENABLED"
    )
    kalshi_demo_probe_stake_usd: float = Field(
        default=5.0, ge=1.0, le=100.0, alias="KALSHI_DEMO_PROBE_STAKE_USD"
    )
    kalshi_demo_probe_interval_sec: int = Field(
        default=3600, ge=300, le=86400, alias="KALSHI_DEMO_PROBE_INTERVAL_SEC"
    )
    arb_poly_fetch_limit: int = Field(
        default=200, ge=25, le=500, alias="ARB_POLY_FETCH_LIMIT"
    )
    arb_match_min_combined_score: float = Field(
        default=0.58, alias="ARB_MATCH_MIN_COMBINED_SCORE"
    )
    arb_min_net_edge: float = Field(default=0.02, alias="ARB_MIN_NET_EDGE")
    # Pre-trade execution quality gate (applied before sizing/risk checks).
    arb_exec_min_settlement_score: float = Field(
        default=0.55, ge=0.0, le=1.0, alias="ARB_EXEC_MIN_SETTLEMENT_SCORE"
    )
    arb_exec_min_leg_volume_usd: float = Field(
        default=2000.0, ge=0.0, alias="ARB_EXEC_MIN_LEG_VOLUME_USD"
    )
    arb_exec_max_settlement_flags: int = Field(
        default=2, ge=0, le=20, alias="ARB_EXEC_MAX_SETTLEMENT_FLAGS"
    )
    arb_paper_relax_orderbook: bool = Field(
        default=True, alias="ARB_PAPER_RELAX_ORDERBOOK"
    )
    kalshi_min_volume_24h: float = Field(default=5000.0, alias="KALSHI_MIN_VOLUME_24H")
    kalshi_paper_bankroll_usd: float = Field(
        default=5000.0, alias="KALSHI_PAPER_BANKROLL_USD"
    )
    arb_max_daily_loss_usd: float = Field(
        default=500.0, alias="ARB_MAX_DAILY_LOSS_USD"
    )
    arb_scan_interval_sec: int = Field(default=180, ge=30, le=3600, alias="ARB_SCAN_INTERVAL_SEC")
    pm_agents_automation_enabled: bool = Field(
        default=True, alias="PM_AGENTS_AUTOMATION_ENABLED"
    )
    kalshi_arb_automated_paper_enabled: bool = Field(
        default=True, alias="KALSHI_ARB_AUTOMATED_PAPER_ENABLED"
    )
    kalshi_arb_max_auto_trades_per_cycle: int = Field(
        default=2, ge=0, le=10, alias="KALSHI_ARB_MAX_AUTO_TRADES_PER_CYCLE"
    )
    kalshi_scan_max_markets_per_category: int = Field(
        default=50, ge=10, le=500, alias="KALSHI_SCAN_MAX_MARKETS_PER_CATEGORY"
    )
    kalshi_scan_max_orderbooks: int = Field(
        default=80, ge=10, le=500, alias="KALSHI_SCAN_MAX_ORDERBOOKS"
    )
    kalshi_scan_orderbook_concurrency: int = Field(
        default=8, ge=1, le=32, alias="KALSHI_SCAN_ORDERBOOK_CONCURRENCY"
    )
    kalshi_agent_use_cached_opps: bool = Field(
        default=True, alias="KALSHI_AGENT_USE_CACHED_OPPS"
    )
    arb_cached_max_age_hours: float = Field(
        default=168.0, ge=1.0, le=720.0, alias="ARB_CACHED_MAX_AGE_HOURS"
    )
    pm_agent_fast_scan: bool = Field(default=True, alias="PM_AGENT_FAST_SCAN")
    equity_autopilot_enabled: bool = Field(
        default=True, alias="EQUITY_AUTOPILOT_ENABLED"
    )
    equity_loop_interval_sec: int = Field(
        default=1800, ge=300, le=14400, alias="EQUITY_LOOP_INTERVAL_SEC"
    )
    world_cup_enabled: bool = Field(default=True, alias="WORLD_CUP_ENABLED")
    world_cup_min_volume_24h: float = Field(
        default=1000.0, alias="WORLD_CUP_MIN_VOLUME_24H"
    )
    world_cup_discovery_limit: int = Field(
        default=80, ge=5, le=500, alias="WORLD_CUP_DISCOVERY_LIMIT"
    )
    world_cup_min_model_edge: float = Field(
        default=0.03, alias="WORLD_CUP_MIN_MODEL_EDGE"
    )
    world_cup_max_auto_trades_per_cycle: int = Field(
        default=3, ge=0, le=20, alias="WORLD_CUP_MAX_AUTO_TRADES_PER_CYCLE"
    )
    world_cup_score_weight: float = Field(default=0.4, alias="WORLD_CUP_SCORE_WEIGHT")
    world_cup_arb_score_weight: float = Field(default=0.35, alias="WORLD_CUP_ARB_SCORE_WEIGHT")
    world_cup_net_edge_weight: float = Field(default=0.25, alias="WORLD_CUP_NET_EDGE_WEIGHT")
    world_cup_use_poisson: bool = Field(
        default=False, alias="WORLD_CUP_USE_POISSON"
    )
    pm_agent_loop_interval_sec: int = Field(
        default=300, ge=60, le=3600, alias="PM_AGENT_LOOP_INTERVAL_SEC"
    )
    self_improvement_enabled: bool = Field(
        default=True, alias="SELF_IMPROVEMENT_ENABLED"
    )
    self_improvement_min_labeled_samples: int = Field(
        default=5, ge=3, le=500, alias="SELF_IMPROVEMENT_MIN_LABELED_SAMPLES"
    )
    self_improvement_min_accuracy_gain: float = Field(
        default=0.02,
        ge=0.0,
        le=0.5,
        alias="SELF_IMPROVEMENT_MIN_ACCURACY_GAIN",
    )
    self_improvement_loop_interval_sec: int = Field(
        default=86400, ge=3600, le=604800, alias="SELF_IMPROVEMENT_LOOP_INTERVAL_SEC"
    )
    brightdata_api_key: str | None = Field(default=None, alias="BRIGHTDATA_API_KEY")
    brightdata_max_requests_per_run: int = Field(
        default=50, ge=1, le=500, alias="BRIGHTDATA_MAX_REQUESTS_PER_RUN"
    )
    postgres_url: str = Field(default="", alias="POSTGRES_URL")

    # ---- Additional LLM provider keys ------------------------------------------
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    openrouter_key: str | None = Field(default=None, alias="OPENROUTER_KEY")
    gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )
    llm_auto_routing: bool = Field(default=True, alias="LLM_AUTO_ROUTING")

    # ---- LLM client factory ----------------------------------------------------
    def get_llm_client(self) -> object | None:  # noqa: ANN401
        """OpenAI-compatible client for the auto-resolved route (Groq/Gemini/OR/Ollama)."""
        from apex.core.llm_routing import resolve_llm_route

        route = resolve_llm_route(self)
        if route is None:
            LOGGER.warning(
                "get_llm_client: no LLM route resolved; check GROQ/GEMINI/OPENROUTER keys or Ollama availability"
            )
            return None
        if not route.base_url.strip():
            LOGGER.warning("get_llm_client: route %s has empty base_url", route.label)
            return None
        if route.provider != "ollama" and not route.api_key.strip():
            LOGGER.warning("get_llm_client: route %s has empty api_key", route.label)
            return None
        try:
            from openai import OpenAI  # type: ignore[import-untyped]

            return OpenAI(api_key=route.api_key, base_url=route.base_url)
        except ImportError:
            LOGGER.warning("get_llm_client: openai package not installed; run `pip install openai`")
            return None
        except Exception as exc:
            LOGGER.warning("get_llm_client: init failed for %s: %s", route.label, exc)
            return None

    @property
    def brightdata_enabled(self) -> bool:
        key = (self.brightdata_api_key or "").strip()
        if not key:
            return False
        if key.lower() in {"changeme", "your_api_key_here", "none", "null"}:
            LOGGER.warning("brightdata_enabled: placeholder BRIGHTDATA_API_KEY detected; disabling integration")
            return False
        return True

    # ---- Validators -------------------------------------------------------------
    @field_validator("chromadb_path", "sqlite_path", mode="after")
    @classmethod
    def _normalize_paths(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    @field_validator("polymarket_training_export_path", mode="after")
    @classmethod
    def _normalize_pm_training_path(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    @model_validator(mode="after")
    def _enforce_options_and_polymarket_policy(self) -> Settings:
        if self.options_trading_enabled and self.alpaca_flatten_options_to_equity:
            object.__setattr__(self, "alpaca_flatten_options_to_equity", False)
        if self.dexter_threshold >= self.dexter_trigger_conviction:
            LOGGER.warning(
                "DEXTER_THRESHOLD (%.1f) >= DEXTER_TRIGGER_CONVICTION (%.1f); "
                "Dexter will never activate. Set DEXTER_THRESHOLD < DEXTER_TRIGGER_CONVICTION.",
                self.dexter_threshold,
                self.dexter_trigger_conviction,
            )
        if self.exit_stop_pct >= self.exit_take_profit_pct:
            LOGGER.warning(
                "EXIT_STOP_PCT (%.1f%%) >= EXIT_TAKE_PROFIT_PCT (%.1f%%); "
                "stop-loss will trigger before take-profit.",
                self.exit_stop_pct,
                self.exit_take_profit_pct,
            )
        if self.trailing_stop_pct > 0 and not self.exit_use_proposal_stops:
            LOGGER.warning(
                "TRAILING_STOP_PCT (%.1f%%) enabled but EXIT_USE_PROPOSAL_STOPS is False; "
                "trailing stop may produce unexpected exits.",
                self.trailing_stop_pct,
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    bootstrap_environment()
    settings = Settings()
    if not settings.autopilot_local_path.strip():
        default_local = repo_root() / "autopilot-local"
        if default_local.is_dir():
            object.__setattr__(settings, "autopilot_local_path", str(default_local.resolve()))
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    settings.chromadb_path.mkdir(parents=True, exist_ok=True)
    settings.polymarket_training_export_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
