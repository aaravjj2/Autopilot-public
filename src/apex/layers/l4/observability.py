from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timezone

from apex.domain.models import AgentSignalAttribution, TradeProposal
from apex.repositories.sqlite_store import SQLiteStore


@dataclass
class ObservabilityService:
    store: SQLiteStore

    def record_trade_attribution(
        self,
        proposal: TradeProposal,
        pl_realized: float,
        technical_correct: bool,
        fundamental_correct: bool,
        pm_correct: bool,
        dexter_helpful: bool,
    ) -> None:
        self.store.append_attribution(
            AgentSignalAttribution(
                symbol=proposal.symbol,
                closed_at=datetime.now(tz=timezone.utc),
                technical_correct=technical_correct,
                fundamental_correct=fundamental_correct,
                pm_correct=pm_correct,
                dexter_helpful=dexter_helpful,
                pl_realized=pl_realized,
            )
        )

    def write_trade_memory(self, proposal: TradeProposal, pl_realized: float, outcome: str) -> None:
        self.store.append_trade_memory(
            symbol=proposal.symbol,
            thesis=proposal.judge_rationale,
            outcome=outcome,
            conviction=proposal.conviction_final,
            payload={"proposal": proposal.model_dump(mode="json"), "pl_realized": pl_realized},
        )

    def feedback_threshold_adjustments(self) -> dict[str, float]:
        recent = self.store.read_table("trade_attribution", limit=20)
        if not recent:
            return {"dexter_threshold": 7.0, "pm_weight_adj": 0.0}
        wins = [row for row in recent if row["pl_realized"] > 0]
        win_rate = len(wins) / max(1, len(recent))
        pm_correct = sum(row["pm_correct"] for row in recent) / max(1, len(recent))
        dexter_threshold = 6.0 if win_rate < 0.4 else 7.0
        pm_weight_adj = -0.10 if pm_correct < 0.5 else 0.0
        return {"dexter_threshold": dexter_threshold, "pm_weight_adj": pm_weight_adj}
