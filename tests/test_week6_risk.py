from apex.risk.cftc_limits import CftcLimitTracker
from apex.risk.kelly import fractional_kelly, KellyInput, kelly_from_edge
from apex.risk.monte_carlo_var import simulate_portfolio_pnl, default_arb_covariance
from apex.risk.metrics_service import build_risk_metrics


def test_fractional_kelly_positive():
    r = fractional_kelly(KellyInput(win_prob=0.6, decimal_odds=2.0, alpha=0.25, vix=15.0))
    assert r.dampened_fraction > 0
    assert r.vix_multiplier < 1.0


def test_kelly_vix_dampens_high_vol():
    low = kelly_from_edge(0.08, vix=12.0)
    high = kelly_from_edge(0.08, vix=40.0)
    assert high.vix_multiplier < low.vix_multiplier
    assert high.dampened_fraction <= low.dampened_fraction


def test_monte_carlo_var_paths():
    cats = ["a", "b", "c"]
    cov = default_arb_covariance(cats)
    res = simulate_portfolio_pnl([1 / 3] * 3, [0.001] * 3, cov, n_paths=500, seed=1)
    assert res.paths == 500
    assert res.var_99 < res.mean_pnl or res.std_pnl > 0


def test_cftc_breach():
    t = CftcLimitTracker(limit_usd=1000.0)
    t.set_exposure("KX-TEST", 900)
    ok = t.check("KX-TEST", 50)
    assert not ok.breached
    bad = t.check("KX-TEST", 200)
    assert bad.breached


def test_build_risk_metrics_shape():
    m = build_risk_metrics(account_equity=100_000.0, arb_opportunities=[])
    assert "vix" in m
    assert "var" in m
    assert m["var"]["paths"] == 10_000
