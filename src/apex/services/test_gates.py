from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from apex.core.config import Settings
from apex.domain.enums import Direction, Instrument
from apex.domain.models import TradeProposal
from apex.layers.l3.risk_checks import RiskCheckEngine
from apex.services.engine import ApexEngine


@dataclass
class TestGateRunner:
    engine: ApexEngine

    def _proposal(self, **overrides) -> TradeProposal:
        payload = {
            "symbol": "AAPL",
            "direction": Direction.LONG,
            "instrument": Instrument.EQUITY,
            "entry_price": 200.0,
            "position_size_pct": 3.0,
            "stop_loss": 190.0,
            "take_profit": 220.0,
            "max_loss_dollars": 800.0,
            "conviction_final": 7.0,
            "judge_rationale": "gate test",
            "dissenting_view": "gate test",
            "sector": "Technology",
        }
        payload.update(overrides)
        return TradeProposal(**payload)

    def run_predeployment(self) -> dict[str, dict]:
        results: dict[str, dict] = {}
        settings = self.engine.settings
        risk_engine = self.engine.execution.risk_engine
        account = self.engine.execution.broker.get_account_snapshot()

        tg01_pass = settings.alpaca_paper_trade and "paper" in settings.alpaca_base_url.lower()
        results["TG-01"] = {"pass": tg01_pass, "details": "paper key verification"}

        live_settings = Settings(
            ALPACA_API_KEY=settings.alpaca_api_key,
            ALPACA_SECRET_KEY=settings.alpaca_secret_key,
            ALPACA_PAPER_TRADE=False,
            ALPACA_BASE_URL="https://api.alpaca.markets",
        )
        live_risk = RiskCheckEngine(live_settings)
        tg02_pass = not live_risk._r01_paper_account().passed
        results["TG-02"] = {"pass": tg02_pass, "details": "R01 rejects live mode"}

        bad = self._proposal(conviction_final=3.0, position_size_pct=9.0)
        chain = risk_engine.run_all(bad, account, stop_on_fail=False)
        results["TG-03"] = {"pass": len(chain) == 14, "details": "all 14 checks executed"}

        malformed_ok = False
        try:
            _ = self._proposal(entry_price=-1.0)
        except Exception:
            malformed_ok = True
        results["TG-04"] = {"pass": malformed_ok, "details": "schema blocks malformed proposal"}

        from apex.integrations.alpaca_adapter import AlpacaDirectIntegration

        alp = AlpacaDirectIntegration(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
            base_url=settings.alpaca_base_url,
        )
        acc = alp.get_account()
        tg05_pass = (
            isinstance(acc, dict)
            and acc.get("equity") is not None
            and not acc.get("error")
            and acc.get("status") not in {"error", "exception"}
        )
        results["TG-05"] = {"pass": tg05_pass, "details": "Alpaca paper account responds with equity"}

        preview_prop = self._proposal()
        preview_ok, preview_msg = self.engine.execution.broker.preview_order(preview_prop)
        results["TG-06"] = {
            "pass": preview_ok,
            "details": f"broker preview: {preview_msg}",
        }

        bars = self.engine.ingestion.market_data.get_daily_bars("SPY")
        results["TG-07"] = {"pass": len(bars) > 200, "details": "yfinance daily bars available"}

        pm = self.engine.ingestion.pm_client.get_macro_snapshot()
        pm_pass = len(pm) >= 3 and all(0 <= item.get("probability", 0) <= 1 for item in pm)
        results["TG-08"] = {"pass": pm_pass, "details": "polymarket snapshot shape valid"}

        floor_fail = risk_engine._r11_conviction_floor(self._proposal(conviction_final=5.5))
        results["TG-11"] = {"pass": not floor_fail.passed, "details": "conviction floor gate checks"}

        loss_account = account
        loss_account.daily_pl_pct = -3.5
        loss_hit = risk_engine._r05_daily_loss_limit(loss_account)
        results["TG-12"] = {"pass": not loss_hit.passed, "details": "daily loss hard block"}

        dexter_prop = self._proposal(conviction_final=8.5, dexter_severity=8.0, dexter_reduction_applied=True)
        dexter_ok = risk_engine._r12_dexter_override(dexter_prop).passed
        results["TG-13"] = {"pass": dexter_ok, "details": "dexter reduction verified"}

        earnings_prop = self._proposal(earnings_date=date.today() + timedelta(days=1))
        earnings_fail = risk_engine._r09_earnings_blackout(earnings_prop)
        results["TG-14"] = {"pass": not earnings_fail.passed, "details": "earnings blackout enforced"}

        for gate_id, data in results.items():
            self.engine.store.upsert_gate_result(gate_id, "PASS" if data["pass"] else "FAIL", data)
        return results
