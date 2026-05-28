"""Tests for Dixon-Coles Poisson World Cup match model."""

from __future__ import annotations

import math

import pytest

from apex.ml.wc_poisson import (
    dixon_coles_adjustment,
    expected_goals_from_elo,
    match_outcome_probs,
    score_match_poisson,
)


def test_dixon_coles_low_score_cells():
    lam_h, lam_a = 1.4, 1.1
    rho = -0.13
    assert dixon_coles_adjustment(0, 0, lam_h, lam_a, rho=rho) == pytest.approx(
        max(0.0001, 1 - lam_h * lam_a * rho)
    )
    assert dixon_coles_adjustment(0, 1, lam_h, lam_a, rho=rho) == pytest.approx(
        max(0.0001, 1 + lam_h * rho)
    )
    assert dixon_coles_adjustment(1, 0, lam_h, lam_a, rho=rho) == pytest.approx(
        max(0.0001, 1 + lam_a * rho)
    )
    assert dixon_coles_adjustment(1, 1, lam_h, lam_a, rho=rho) == pytest.approx(
        max(0.0001, 1 - rho)
    )
    assert dixon_coles_adjustment(2, 2, lam_h, lam_a, rho=rho) == 1.0


def test_match_outcome_probs_sum_to_one():
    probs = match_outcome_probs(1.5, 1.2, max_goals=10, rho=-0.13)
    total = probs["home_win"] + probs["draw"] + probs["away_win"]
    assert total == pytest.approx(1.0, abs=1e-5)


def test_negative_rho_increases_draw_vs_independent_poisson():
    lam = 1.35
    dc = match_outcome_probs(lam, lam, max_goals=10, rho=-0.13)
    independent = match_outcome_probs(lam, lam, max_goals=10, rho=0.0)
    assert dc["draw"] > independent["draw"]


def test_expected_goals_from_elo_equal_teams():
    lam_h, lam_a = expected_goals_from_elo(2000.0, 2000.0, home_adv=0.0)
    assert lam_h == pytest.approx(lam_a, rel=1e-6)
    assert lam_h + lam_a == pytest.approx(2.7, rel=1e-6)


def test_expected_goals_favor_stronger_home():
    lam_h, lam_a = expected_goals_from_elo(2100.0, 1900.0, home_adv=45.0)
    assert lam_h > lam_a
    assert lam_h + lam_a == pytest.approx(2.7, rel=1e-6)


def test_score_match_poisson_brazil_argentina():
    row = {
        "question": "Will Brazil beat Argentina?",
        "home_team": "Brazil",
        "away_team": "Argentina",
    }
    result = score_match_poisson(row)
    assert result["home_win"] > result["away_win"]
    assert result["fair_prob"] == result["home_win"]
    assert result["teams_resolved"] == ["Brazil", "Argentina"]
    assert result["lambda_home"] > result["lambda_away"]
    total = result["home_win"] + result["draw"] + result["away_win"]
    assert total == pytest.approx(1.0, abs=1e-5)
    assert result["model_version"] == "wc_poisson_v1"


def test_score_match_poisson_unknown_teams_uniform_fallback():
    result = score_match_poisson(
        {"question": "Will Zzzland beat Qqqistan?"}
    )
    assert result["home_win"] == pytest.approx(1 / 3)
    assert result["teams_resolved"] == ["Zzzland", "Qqqistan"]


def test_score_match_poisson_identical_teams_uniform_fallback():
    result = score_match_poisson({"home_team": "Brazil", "away_team": "Brazil"})
    assert result["home_win"] == pytest.approx(1 / 3)
    assert result["teams_resolved"] == ["Brazil", "Brazil"]
