"""Monte Carlo VaR with Cholesky decomposition (Week 6 Day 3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

Z_99 = 2.326348  # standard normal 99%


@dataclass
class VaRResult:
    paths: int
    horizon_days: float
    mean_pnl: float
    std_pnl: float
    var_99: float
    cvar_99: float
    max_drawdown_p99: float


def _cholesky_cov(cov: np.ndarray) -> np.ndarray:
    cov = np.asarray(cov, dtype=float)
    cov = (cov + cov.T) / 2
    eigvals = np.linalg.eigvalsh(cov)
    if np.min(eigvals) < 1e-10:
        cov += np.eye(cov.shape[0]) * 1e-6
    return np.linalg.cholesky(cov)


def simulate_portfolio_pnl(
    weights: Sequence[float],
    expected_returns: Sequence[float],
    cov_matrix: Sequence[Sequence[float]],
    *,
    n_paths: int = 10_000,
    horizon_days: float = 1.0,
    seed: int | None = 42,
) -> VaRResult:
    """
    Generate correlated returns via Cholesky, compute portfolio P&L distribution.
    VaR_99% = mu - Z_0.99 * sigma * sqrt(dt) per master plan.
    """
    w = np.array(weights, dtype=float)
    mu = np.array(expected_returns, dtype=float)
    cov = np.array(cov_matrix, dtype=float)
    n = len(w)
    if n == 0:
        return VaRResult(0, horizon_days, 0.0, 0.0, 0.0, 0.0, 0.0)

    rng = np.random.default_rng(seed)
    L = _cholesky_cov(cov)
    z = rng.standard_normal((n_paths, n))
    correlated = z @ L.T
    asset_returns = mu + correlated * np.sqrt(max(horizon_days, 1e-9))
    portfolio_returns = asset_returns @ w
    pnl = portfolio_returns  # assume unit notional per weight sum

    var_99 = float(np.percentile(pnl, 1))
    tail = pnl[pnl <= var_99]
    cvar_99 = float(np.mean(tail)) if len(tail) else var_99

    cumulative = np.cumsum(pnl)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = cumulative - running_max
    max_dd_p99 = float(np.percentile(drawdowns, 1))

    return VaRResult(
        paths=n_paths,
        horizon_days=horizon_days,
        mean_pnl=float(np.mean(pnl)),
        std_pnl=float(np.std(pnl)),
        var_99=var_99,
        cvar_99=cvar_99,
        max_drawdown_p99=max_dd_p99,
    )


def default_arb_covariance(categories: list[str]) -> np.ndarray:
    """Category covariance prior for arb book."""
    n = len(categories)
    base = np.eye(n) * 0.02
    for i in range(n):
        for j in range(i + 1, n):
            base[i, j] = base[j, i] = 0.008
    return base
