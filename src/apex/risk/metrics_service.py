"""Aggregate risk metrics for API + dashboard (Week 6)."""

from __future__ import annotations

from typing import Any

from apex.risk.cftc_limits import CftcLimitTracker
from apex.risk.kelly import kelly_from_edge
from apex.risk.monte_carlo_var import default_arb_covariance, simulate_portfolio_pnl
from apex.risk.vix_client import get_vix

# Module-level tracker (persisted in-memory; DB hook later)
_cftc_tracker = CftcLimitTracker()


def get_cftc_tracker() -> CftcLimitTracker:
    return _cftc_tracker


def sync_cftc_from_positions(positions: list[dict[str, Any]]) -> None:
    tracker = get_cftc_tracker()
    tracker.exposures.clear()
    for pos in positions:
        key = str(pos.get("symbol") or pos.get("kalshi_ticker") or "unknown")
        notional = abs(float(pos.get("market_value") or pos.get("notional") or 0))
        tracker.set_exposure(key, notional)


def build_risk_metrics(
    *,
    account_equity: float = 100_000.0,
    positions: list[dict[str, Any]] | None = None,
    arb_opportunities: list[dict[str, Any]] | None = None,
    kelly_alpha: float = 0.25,
    kelly_lambda: float = 0.02,
) -> dict[str, Any]:
    vix = get_vix()
    positions = positions or []
    arbs = arb_opportunities or []

    sync_cftc_from_positions(positions)
    tracker = get_cftc_tracker()

    # Portfolio VaR by category buckets
    categories = list({str(a.get("category") or "uncategorized") for a in arbs}) or [
        "politics",
        "macro",
        "crypto",
    ]
    n = len(categories)
    weights = [1.0 / n] * n
    mu = [0.0002] * n
    cov = default_arb_covariance(categories)
    var_result = simulate_portfolio_pnl(
        weights, mu, cov, n_paths=10_000, horizon_days=1.0
    )

    # Scale VaR to equity
    var_usd = abs(var_result.var_99) * account_equity
    cvar_usd = abs(var_result.cvar_99) * account_equity

    kelly_samples = []
    for opp in arbs[:10]:
        edge = float(opp.get("net_edge") or 0)
        conf = float(opp.get("ai_confidence_score") or 0.7)
        kr = kelly_from_edge(edge, ai_confidence=conf, alpha=kelly_alpha, vix=vix, lambda_dampener=kelly_lambda)
        kelly_samples.append(
            {
                "id": opp.get("id"),
                "ticker": opp.get("kalshi_ticker"),
                "suggested_fraction": kr.dampened_fraction,
                "vix_multiplier": kr.vix_multiplier,
            }
        )

    return {
        "vix": round(vix, 2),
        "kelly_alpha": kelly_alpha,
        "kelly_lambda": kelly_lambda,
        "var": {
            "paths": var_result.paths,
            "horizon_days": var_result.horizon_days,
            "var_99_pct": round(var_result.var_99 * 100, 4),
            "var_99_usd": round(var_usd, 2),
            "cvar_99_usd": round(cvar_usd, 2),
            "mean_pnl_pct": round(var_result.mean_pnl * 100, 4),
            "std_pnl_pct": round(var_result.std_pnl * 100, 4),
            "max_drawdown_p99_pct": round(var_result.max_drawdown_p99 * 100, 4),
        },
        "cftc": {
            "limit_usd": tracker.limit_usd,
            "positions": [
                {
                    "contract": p.contract_key,
                    "notional_usd": round(p.notional_usd, 2),
                    "limit_usd": p.limit_usd,
                    "utilization_pct": round(p.utilization_pct, 1),
                    "headroom_usd": round(p.headroom_usd, 2),
                    "breached": p.breached,
                }
                for p in tracker.all_positions()[:20]
            ],
            "breach_count": len(tracker.breaches()),
        },
        "kelly_samples": kelly_samples,
        "account_equity": account_equity,
    }
