"""FIFA World Cup Poisson / Dixon-Coles match model (paper trading only).

Paper-only analytics for fair match-outcome probabilities. Adapted from
zvizdo/fifa-wc-2026-simulation (independent Poisson grid + Dixon-Coles low-score
correction). Uses bundled Elo ratings via ``world_cup_model`` — no live orders.
"""

from __future__ import annotations

import math
from typing import Any

from apex.core.config import Settings, get_settings
from apex.core.logging import get_logger
from apex.ml.world_cup_model import _find_team, load_elo_ratings, parse_match_teams

LOGGER = get_logger(__name__)

MODEL_VERSION = "wc_poisson_v1"
DEFAULT_RHO = -0.13
DEFAULT_MAX_GOALS = 10
DEFAULT_AVG_TOTAL_GOALS = 2.7
DEFAULT_HOME_ADV_ELO = 45.0


def _poisson_pmf(k: int, lam: float) -> float:
    if k < 0:
        return 0.0
    if lam <= 0.0:
        return 1.0 if k == 0 else 0.0
    return math.exp(k * math.log(lam) - lam - math.lgamma(k + 1))


def dixon_coles_adjustment(
    home_goals: int,
    away_goals: int,
    lambda_h: float,
    lambda_a: float,
    rho: float = DEFAULT_RHO,
) -> float:
    """Dixon-Coles low-score correlation factor (multiply independent Poisson mass).

    Adjusts (0,0), (0,1), (1,0), and (1,1) cells; all other scorelines return 1.0.
    Negative ``rho`` inflates draw mass relative to independent Poisson.
    """
    if home_goals == 0 and away_goals == 0:
        factor = 1.0 - lambda_h * lambda_a * rho
    elif home_goals == 0 and away_goals == 1:
        factor = 1.0 + lambda_h * rho
    elif home_goals == 1 and away_goals == 0:
        factor = 1.0 + lambda_a * rho
    elif home_goals == 1 and away_goals == 1:
        factor = 1.0 - rho
    else:
        return 1.0
    return max(0.0001, factor)


def _build_score_matrix(
    lambda_h: float,
    lambda_a: float,
    *,
    max_goals: int,
    rho: float,
) -> list[list[float]]:
    """Joint scoreline probabilities with Dixon-Coles on low-scoring cells."""
    matrix: list[list[float]] = []
    for hg in range(max_goals + 1):
        row: list[float] = []
        p_h = _poisson_pmf(hg, lambda_h)
        for ag in range(max_goals + 1):
            p = p_h * _poisson_pmf(ag, lambda_a)
            p *= dixon_coles_adjustment(hg, ag, lambda_h, lambda_a, rho=rho)
            row.append(p)
        matrix.append(row)
    total = sum(v for row in matrix for v in row)
    if total <= 0.0:
        raise ValueError("score probability matrix has zero mass")
    return [[v / total for v in row] for row in matrix]


def match_outcome_probs(
    lambda_h: float,
    lambda_a: float,
    max_goals: int = DEFAULT_MAX_GOALS,
    rho: float = DEFAULT_RHO,
) -> dict[str, float]:
    """Home win / draw / away win from Dixon-Coles adjusted score grid."""
    matrix = _build_score_matrix(
        max(1e-6, lambda_h),
        max(1e-6, lambda_a),
        max_goals=max_goals,
        rho=rho,
    )
    home_win = 0.0
    draw = 0.0
    away_win = 0.0
    for hg, row in enumerate(matrix):
        for ag, prob in enumerate(row):
            if hg > ag:
                home_win += prob
            elif hg == ag:
                draw += prob
            else:
                away_win += prob
    return {
        "home_win": round(home_win, 6),
        "draw": round(draw, 6),
        "away_win": round(away_win, 6),
    }


def expected_goals_from_elo(
    elo_home: float,
    elo_away: float,
    *,
    home_adv: float = DEFAULT_HOME_ADV_ELO,
    avg_total_goals: float = DEFAULT_AVG_TOTAL_GOALS,
) -> tuple[float, float]:
    """Map Elo ratings to expected goals via Bradley-Terry-style strength split.

    ``lambda_home + lambda_away = avg_total_goals``. Each team's share is
    proportional to ``10^(elo/400)``, with home advantage added to the home Elo.
    """
    strength_home = 10.0 ** ((elo_home + home_adv) / 400.0)
    strength_away = 10.0 ** (elo_away / 400.0)
    denom = strength_home + strength_away
    if denom <= 0.0:
        half = avg_total_goals / 2.0
        return half, half
    lambda_h = avg_total_goals * strength_home / denom
    lambda_a = avg_total_goals * strength_away / denom
    return lambda_h, lambda_a


def _resolve_teams(row: dict[str, Any]) -> tuple[str, str] | None:
    home = row.get("home_team") or row.get("team_home")
    away = row.get("away_team") or row.get("team_away")
    if home and away:
        return str(home).strip(), str(away).strip()
    question = str(row.get("question") or "")
    return parse_match_teams(question)


def score_match_poisson(
    row: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Score a match row with Dixon-Coles Poisson 1X2 probabilities.

    First-named / home-side team maps to ``home_win`` and ``fair_prob``.
    """
    settings = settings or get_settings()
    data = load_elo_ratings(settings)
    teams: dict[str, float] = {
        str(k): float(v) for k, v in (data.get("teams") or {}).items()
    }
    home_adv = float(data.get("home_advantage_elo", DEFAULT_HOME_ADV_ELO))

    parsed = _resolve_teams(row)
    if not parsed:
        LOGGER.debug("wc_poisson: could not parse teams from row")
        return _uniform_result(teams_resolved=None)

    home_name, away_name = parsed
    if home_name.strip().lower() == away_name.strip().lower():
        LOGGER.debug("wc_poisson: home and away teams identical (%s)", home_name)
        return _uniform_result(teams_resolved=[home_name, away_name])
    home_hit = _find_team(home_name, teams)
    away_hit = _find_team(away_name, teams)
    if not home_hit or not away_hit:
        LOGGER.debug(
            "wc_poisson: missing Elo for %s vs %s",
            home_name,
            away_name,
        )
        return _uniform_result(teams_resolved=[home_name, away_name])

    lambda_h, lambda_a = expected_goals_from_elo(
        home_hit[1],
        away_hit[1],
        home_adv=home_adv,
    )
    outcomes = match_outcome_probs(lambda_h, lambda_a)
    return {
        **outcomes,
        "lambda_home": round(lambda_h, 4),
        "lambda_away": round(lambda_a, 4),
        "fair_prob": outcomes["home_win"],
        "model_version": MODEL_VERSION,
        "teams_resolved": [home_hit[0], away_hit[0]],
    }


def _uniform_result(*, teams_resolved: list[str] | None) -> dict[str, Any]:
    third = round(1.0 / 3.0, 6)
    half = DEFAULT_AVG_TOTAL_GOALS / 2.0
    return {
        "home_win": third,
        "draw": third,
        "away_win": third,
        "lambda_home": half,
        "lambda_away": half,
        "fair_prob": third,
        "model_version": MODEL_VERSION,
        "teams_resolved": teams_resolved,
    }
