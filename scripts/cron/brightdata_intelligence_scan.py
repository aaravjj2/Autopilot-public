from __future__ import annotations
# BRIGHTDATA INTEGRATION — 2026-05-27 — budget-aware periodic intelligence scanner

import asyncio
from datetime import datetime
from pathlib import Path

from apex.agents.arb_intelligence_agent import ArbitrageIntelligenceAgent
from apex.core.config import get_settings
from apex.core.logging import get_logger
from apex.domain.models import ArbOpportunity
from apex.integrations.brightdata_intelligence import BrightDataIntelligence
from apex.repositories.sqlite_store import SQLiteStore

LOGGER = get_logger(__name__)
ET_RUN_DATE_FMT = "%Y-%m-%d"


def _to_opportunity(row: dict) -> ArbOpportunity:
    flags = row.get("settlement_flags") or []
    if isinstance(flags, str):
        import json

        try:
            flags = json.loads(flags)
        except Exception:
            flags = [flags]
    return ArbOpportunity(
        id=str(row.get("id")),
        kalshi_ticker=str(row.get("kalshi_ticker")),
        poly_market_id=str(row.get("poly_market_id")),
        question=str(row.get("question")),
        kalshi_title=str(row.get("kalshi_title")),
        poly_title=str(row.get("poly_title")),
        kalshi_yes_ask=float(row.get("kalshi_yes_ask") or 0.0),
        poly_no_ask=float(row.get("poly_no_ask") or 0.0),
        gross_spread=float(row.get("gross_spread") or 0.0),
        net_edge=float(row.get("net_edge") or 0.0),
        settlement_match_score=float(row.get("settlement_match_score") or 0.0),
        settlement_flags=list(flags),
        volume_kalshi=float(row.get("volume_kalshi") or 0.0),
        volume_poly=float(row.get("volume_poly") or 0.0),
        category=str(row.get("category") or "UNKNOWN"),
        kelly_fraction=float(row.get("kelly_fraction") or 0.0),
    )


async def run_brightdata_intelligence_scan() -> dict[str, int]:
    settings = get_settings()
    store = SQLiteStore(settings.sqlite_path)
    intelligence = BrightDataIntelligence(settings)
    agent = ArbitrageIntelligenceAgent(settings, intelligence)

    today = datetime.now().strftime(ET_RUN_DATE_FMT)
    if not store.start_job("brightdata_intelligence_scan", today):
        return {"processed": 0, "skipped": 1}

    processed = 0
    skipped = 0
    status = "success"
    details = ""
    try:
        session = await intelligence.check_session_budget()
        if int(session.get("calls_made", 0)) >= 40:
            LOGGER.info("Skipping scan due to BrightData call budget (calls=%s)", session.get("calls_made"))
            details = "budget_guard_exit"
            return {"processed": 0, "skipped": 1}

        rows = sorted(
            store.list_arb_opportunities(limit=100),
            key=lambda r: float(r.get("net_edge") or 0.0),
            reverse=True,
        )[:5]
        seen_tickers: set[str] = set()
        buy_log = Path("data/logs/intelligence_buys.log")
        buy_log.parent.mkdir(parents=True, exist_ok=True)
        for row in rows:
            opp = _to_opportunity(row)
            if not opp.kalshi_ticker or opp.kalshi_ticker in seen_tickers:
                skipped += 1
                continue
            seen_tickers.add(opp.kalshi_ticker)
            report = await agent.run(opp)
            processed += 1
            if report.get("verdict") == "SKIP" and int(report.get("confidence_score", 0)) >= 60:
                if "intelligence_skip" not in opp.settlement_flags:
                    opp.settlement_flags.append("intelligence_skip")
                store.save_arb_opportunities([opp])
            if report.get("verdict") == "BUY" and int(report.get("confidence_score", 0)) >= 75:
                buy_log.open("a", encoding="utf-8").write(
                    f"{datetime.now().isoformat()} {opp.kalshi_ticker} BUY {report.get('confidence_score')}\n"
                )

        LOGGER.info("BrightData scan session stats: %s", await intelligence.check_session_budget())
        details = f"processed={processed},skipped={skipped}"
        return {"processed": processed, "skipped": skipped}
    except Exception as exc:
        status = "failed"
        details = str(exc)
        raise
    finally:
        store.finish_job("brightdata_intelligence_scan", today, status, details)


def main() -> None:
    result = asyncio.run(run_brightdata_intelligence_scan())
    LOGGER.info("BrightData intelligence cron completed: %s", result)


if __name__ == "__main__":
    main()
