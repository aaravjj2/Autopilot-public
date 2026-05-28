from __future__ import annotations

from apex.core.config import get_settings
from apex.core.env_bootstrap import bootstrap_environment
from apex.core.logging import configure_logging, get_logger
from apex.integrations.broker import (
    AlpacaBrokerAdapter,
    PaperBrokerSimulator,
    PaperKalshiBroker,
    PaperPolymarketBroker,
    VenueRoutingBroker,
)
from apex.integrations.hub import get_integration_hub
from apex.integrations.market_data import (
    TradierOptionsDataClient,
    YFinanceMarketDataClient,
    YFinanceOptionsDataClient,
)
from apex.integrations.news_regime_adapters import (
    DailyStockAnalysisAdapter,
    KronosAdapter,
    MiroFishAdapter,
)
from apex.integrations.polymarket import StubPredictionMarketClient
from apex.integrations.repo_registry import IntegrationRegistry
from apex.layers.l0.ingestion import DataIngestionService
from apex.layers.l1.brain import FinanceBrainService
from apex.layers.l2.agent_panel import MultiAgentPanelService
from apex.layers.l3.execution import ExecutionService
from apex.layers.l3.risk_checks import RiskCheckEngine
from apex.layers.l4.observability import ObservabilityService
from apex.repositories.sqlite_store import SQLiteStore
from apex.scheduler.service import run_scheduler as scheduler_runner
from apex.services.engine import ApexEngine
from apex.services.arb_engine import ArbEngine
from apex.services.test_gates import TestGateRunner

LOGGER = get_logger(__name__)


def _build_kalshi_broker(settings):
    """Internal paper simulator or Kalshi Trade API (demo/prod) when enabled."""
    if not (settings.alpaca_paper_trade or settings.polymarket_paper_trading_enabled):
        return None
    if settings.kalshi_demo_trading_enabled:
        from apex.integrations.kalshi_demo_broker import KalshiDemoBroker
        from apex.integrations.kalshi_trading import kalshi_credentials_configured

        if kalshi_credentials_configured(settings):
            try:
                return KalshiDemoBroker(settings)
            except Exception as exc:
                LOGGER.error("Kalshi demo broker unavailable, falling back to paper: %s", exc)
        else:
            LOGGER.warning(
                "KALSHI_DEMO_TRADING_ENABLED=true but API key/private key missing; using internal paper"
            )
    return PaperKalshiBroker(settings)


def build_engine() -> ApexEngine:
    bootstrap_environment()
    settings = get_settings()
    configure_logging(settings)
    store = SQLiteStore(settings.sqlite_path)

    hub = get_integration_hub()

    market_data = YFinanceMarketDataClient()
    if settings.tradier_sandbox_token:
        options_data = TradierOptionsDataClient(
            token=settings.tradier_sandbox_token,
            base_url=settings.tradier_base_url,
        )
    else:
        options_data = YFinanceOptionsDataClient()
    pm_client = hub.polymarket if hub.has_polymarket() else StubPredictionMarketClient()
    equity_broker: AlpacaBrokerAdapter | PaperBrokerSimulator
    if hub.has_alpaca() and hub.alpaca_direct is not None:
        equity_broker = AlpacaBrokerAdapter(
            alpaca=hub.alpaca_direct,
            settings=settings,
        )
    else:
        equity_broker = PaperBrokerSimulator(settings)

    pm_paper = PaperPolymarketBroker(settings) if settings.polymarket_paper_trading_enabled else None
    kalshi_paper = _build_kalshi_broker(settings)
    broker = VenueRoutingBroker(
        equity_broker=equity_broker,
        polymarket_paper=pm_paper,
        kalshi_paper=kalshi_paper,
        settings=settings,
    )

    mirofish = (
        MiroFishAdapter(settings.mirofish_repo_path)
        if settings.mirofish_repo_path
        else None
    )
    daily_stock = (
        DailyStockAnalysisAdapter(
            settings.daily_stock_analysis_repo_path,
            settings=settings,
        )
        if settings.daily_stock_analysis_repo_path
        else None
    )
    kronos = KronosAdapter(settings.kronos_repo_path or "")

    ingestion = DataIngestionService(
        market_data,
        options_data,
        pm_client,
        mirofish=mirofish,
        daily_stock=daily_stock,
        max_fetch_attempts=settings.ingestion_fetch_max_attempts,
        fetch_backoff_sec=settings.ingestion_fetch_backoff_sec,
        inter_symbol_delay_ms=settings.ingestion_inter_symbol_delay_ms,
    )
    brain = FinanceBrainService(settings, pm_client, hub=hub, kronos=kronos)
    panel = MultiAgentPanelService(settings=settings, hub=hub)
    risk_engine = RiskCheckEngine(settings)
    execution = ExecutionService(
        broker=broker, risk_engine=risk_engine, store=store, settings=settings
    )
    observability = ObservabilityService(store)
    registry = IntegrationRegistry(settings)

    from apex.domain.watchlist_candidates import DEFAULT_WATCHLIST_CANDIDATES
    from apex.domain.weekly_focus import build_effective_watchlist_candidates

    candidates = build_effective_watchlist_candidates(
        DEFAULT_WATCHLIST_CANDIDATES, settings
    )

    arb_engine = ArbEngine(settings=settings, store=store)

    return ApexEngine(
        settings=settings,
        store=store,
        ingestion=ingestion,
        brain=brain,
        panel=panel,
        execution=execution,
        observability=observability,
        integration_registry=registry,
        arb_engine=arb_engine,
        watchlist_candidates=candidates,
    )


def run_daily_cycle() -> None:
    engine = build_engine()
    engine.run_daily_cycle()


def run_scheduler() -> None:
    engine = build_engine()
    scheduler_runner(engine)


def run_autopilot() -> None:
    """Continuous paper-trading autopilot: same as ``run_scheduler`` (APScheduler, US/Eastern)."""
    run_scheduler()


def run_dashboard() -> None:
    """Launch Streamlit UI (must use ``streamlit run``, not bare import)."""
    import subprocess
    import sys
    from pathlib import Path

    settings = get_settings()
    configure_logging(settings)
    app_path = Path(__file__).resolve().parent / "dashboard" / "app.py"
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.address",
        "0.0.0.0",
        f"--server.port={settings.streamlit_port}",
    ]
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])
    raise SystemExit(subprocess.call(cmd))


def run_health_server() -> None:
    import uvicorn

    settings = get_settings()
    configure_logging(settings)
    from apex.monitor.health_server import app

    uvicorn.run(
        app,
        host=settings.health_server_bind,
        port=settings.health_server_port,
        log_level=settings.log_level.lower(),
    )


def run_polymarket_agent() -> None:
    """
    Run the Polymarket prediction-market agent: macro snapshot, intraday shifts, and
    per-symbol ticker signals (same client as ``FinanceBrainService`` / ingestion).

    Optional CLI args: ticker symbols (default AAPL MSFT NVDA SPY).

    Requires ``polymarket-mcp`` Python package for MCP-tool parity (``pip install -e
    external/polymarket-mcp-server``); otherwise Gamma REST fallback is used.
    """
    import json
    import sys

    settings = get_settings()
    configure_logging(settings)
    hub = get_integration_hub()
    if not hub.has_polymarket() or hub.polymarket is None:
        LOGGER.error(
            "Polymarket MCP adapter unavailable. Clone polymarket-mcp-server under "
            "external/polymarket-mcp-server or set POLYMARKET_REPO_PATH."
        )
        raise SystemExit(1)
    client = hub.polymarket

    macro = client.get_macro_snapshot()
    LOGGER.info("Polymarket macro snapshot: %d rows, sample=%s", len(macro), json.dumps(macro[:6], indent=2, default=str))

    shifts = client.get_intraday_macro_shift()
    LOGGER.info("Polymarket intraday macro shift: %d rows, sample=%s", len(shifts), json.dumps(shifts[:8], indent=2, default=str))

    symbols = sys.argv[1:] if len(sys.argv) > 1 else ["AAPL", "MSFT", "NVDA", "SPY"]
    signals = {sym: client.get_ticker_signal(sym) for sym in symbols}
    LOGGER.info("Polymarket ticker signals: symbols=%s, signals=%s", symbols, json.dumps(signals, indent=2, default=str))


def run_self_improvement() -> None:
    """Run one self-improvement cycle: export → train → evaluate → promote → brain refresh."""
    import json

    settings = get_settings()
    configure_logging(settings)
    engine = build_engine()
    from apex.services.self_improvement import run_self_improvement_cycle

    result = run_self_improvement_cycle(engine)
    LOGGER.info("Self-improvement cycle result: %s", json.dumps(result, indent=2, default=str))


def run_polymarket_training_export() -> None:
    """
    Append resolved Polymarket markets (public Gamma) to ``POLYMARKET_TRAINING_EXPORT_PATH``.

    One JSON object per line: ``yes_implied_at_snapshot``, ``yes_won`` (when inferable),
    ``volume``, ``question``, etc. Safe to run on a schedule for growing a training corpus.
    """
    settings = get_settings()
    configure_logging(settings)
    from apex.services.polymarket_training_export import export_resolved_markets_to_jsonl

    n = export_resolved_markets_to_jsonl(
        settings.polymarket_training_export_path,
        limit=int(settings.polymarket_training_fetch_limit),
    )
    LOGGER.info(
        "Polymarket training export: appended %d rows to %s",
        n,
        settings.polymarket_training_export_path,
    )


def run_predeployment_gates() -> None:
    engine = build_engine()
    runner = TestGateRunner(engine)
    runner.run_predeployment()


if __name__ == "__main__":
    run_daily_cycle()
