"""FIFA World Cup 2026 Monte Carlo tournament simulator (Elo + Poisson v1)."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from apex.core.config import Settings, get_settings
from apex.core.logging import get_logger
from apex.ml.world_cup_model import _elo_win_prob, load_elo_ratings

LOGGER = get_logger(__name__)

MODEL_VERSION = "wc_montecarlo_v1"

try:
    from apex.ml.wc_poisson import simulate_group_match as _poisson_simulate_group_match
except ImportError:
    _poisson_simulate_group_match = None

# 2026 format: 12 groups of 4 (openfootball / wc2026_autopilot schedule)
GROUPS_2026: dict[str, list[str]] = {
    "A": ["Mexico", "South Africa", "South Korea", "Czech Republic"],
    "B": ["Canada", "Bosnia & Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["USA", "Paraguay", "Australia", "Turkey"],
    "E": ["Germany", "Curaçao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

_AVG_GOALS_PER_TEAM = 1.225
_KNOCKOUT_ADVANCERS = 16


@dataclass(frozen=True)
class GroupStanding:
    team: str
    points: int
    goal_diff: int
    goals_for: int


def _poisson_sample(lam: float, rng: random.Random) -> int:
    if lam <= 0:
        return 0
    limit = math.exp(-lam)
    k = 0
    p = 1.0
    while p > limit:
        k += 1
        p *= rng.random()
    return k - 1


def _expected_goals(
    home_elo: float,
    away_elo: float,
    *,
    home_advantage_elo: float,
) -> tuple[float, float]:
    sh = 10 ** (home_elo / 400.0)
    sa = 10 ** (away_elo / 400.0)
    adv = 10 ** (home_advantage_elo / 400.0)
    total = _AVG_GOALS_PER_TEAM * 2.0
    lam_home = total * (sh * adv) / (sh * adv + sa)
    lam_away = total * sa / (sh * adv + sa)
    return max(0.05, lam_home), max(0.05, lam_away)


def _inline_simulate_group_match(
    home_elo: float,
    away_elo: float,
    *,
    home_advantage_elo: float = 45.0,
    rng: random.Random | None = None,
) -> tuple[int, int]:
    rng = rng or random.Random()
    lam_h, lam_a = _expected_goals(
        home_elo, away_elo, home_advantage_elo=home_advantage_elo
    )
    return _poisson_sample(lam_h, rng), _poisson_sample(lam_a, rng)


def simulate_group_match(
    home_elo: float,
    away_elo: float,
    *,
    home_advantage_elo: float = 45.0,
    rng: random.Random | None = None,
) -> tuple[int, int]:
    """Simulate a single match; delegates to wc_poisson when available."""
    if _poisson_simulate_group_match is not None:
        return _poisson_simulate_group_match(
            home_elo,
            away_elo,
            home_advantage_elo=home_advantage_elo,
            rng=rng,
        )
    return _inline_simulate_group_match(
        home_elo,
        away_elo,
        home_advantage_elo=home_advantage_elo,
        rng=rng,
    )


def _resolve_elo(team: str, teams: dict[str, float], default: float = 1500.0) -> float:
    n = team.strip().lower()
    for k, v in teams.items():
        kl = k.lower()
        if kl == n or kl in n or n in kl:
            return float(v)
    return default


def _all_teams() -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for group in GROUPS_2026.values():
        for team in group:
            if team not in seen:
                seen.add(team)
                out.append(team)
    return out


def _simulate_group(
    teams: list[str],
    elos: dict[str, float],
    home_adv: float,
    rng: random.Random,
) -> list[GroupStanding]:
    pts: dict[str, int] = {t: 0 for t in teams}
    gf: dict[str, int] = {t: 0 for t in teams}
    ga: dict[str, int] = {t: 0 for t in teams}

    for i, home in enumerate(teams):
        for away in teams[i + 1 :]:
            hg, ag = simulate_group_match(
                elos[home],
                elos[away],
                home_advantage_elo=home_adv,
                rng=rng,
            )
            gf[home] += hg
            ga[home] += ag
            gf[away] += ag
            ga[away] += hg
            if hg > ag:
                pts[home] += 3
            elif ag > hg:
                pts[away] += 3
            else:
                pts[home] += 1
                pts[away] += 1

    standings = [
        GroupStanding(
            team=t,
            points=pts[t],
            goal_diff=gf[t] - ga[t],
            goals_for=gf[t],
        )
        for t in teams
    ]
    return sorted(
        standings,
        key=lambda s: (-s.points, -s.goal_diff, -s.goals_for, s.team),
    )


def _knockout_winner(
    home: str,
    away: str,
    elos: dict[str, float],
    rng: random.Random,
) -> str:
    hg, ag = simulate_group_match(
        elos[home],
        elos[away],
        home_advantage_elo=0.0,
        rng=rng,
    )
    if hg > ag:
        return home
    if ag > hg:
        return away
    p_home = _elo_win_prob(elos[home], elos[away], 0.0)
    return home if rng.random() < p_home else away


def _simulate_knockout(advancers: list[str], elos: dict[str, float], rng: random.Random) -> str:
    ranked = sorted(advancers, key=lambda t: (-elos[t], t))
    pool = ranked[:_KNOCKOUT_ADVANCERS]
    if len(pool) < 2:
        return pool[0] if pool else ranked[0]

    while len(pool) > 1:
        rng.shuffle(pool)
        next_round: list[str] = []
        for i in range(0, len(pool) - 1, 2):
            next_round.append(_knockout_winner(pool[i], pool[i + 1], elos, rng))
        if len(pool) % 2 == 1:
            next_round.append(pool[-1])
        pool = next_round
    return pool[0]


def simulate_tournament_once(
    settings: Settings | None = None,
    *,
    rng: random.Random | None = None,
) -> str:
    """Run one full group + knockout draw; return champion team name."""
    settings = settings or get_settings()
    rng = rng or random.Random()
    data = load_elo_ratings(settings)
    ratings: dict[str, float] = {
        str(k): float(v) for k, v in (data.get("teams") or {}).items()
    }
    home_adv = float(data.get("home_advantage_elo", 45))

    elos = {team: _resolve_elo(team, ratings) for team in _all_teams()}
    advancers: list[GroupStanding] = []

    for group_teams in GROUPS_2026.values():
        standings = _simulate_group(group_teams, elos, home_adv, rng)
        advancers.extend(standings[:2])

    advancers.sort(
        key=lambda s: (-s.points, -s.goal_diff, -s.goals_for, s.team),
    )
    knockout_pool = [s.team for s in advancers[: max(_KNOCKOUT_ADVANCERS, 2)]]
    return _simulate_knockout(knockout_pool, elos, rng)


def run_monte_carlo(
    n_sims: int = 1000,
    settings: Settings | None = None,
    *,
    seed: int | None = None,
) -> dict[str, float]:
    """Return team -> tournament win probability from n_sims independent draws."""
    settings = settings or get_settings()
    n_sims = max(1, int(n_sims))
    teams = _all_teams()
    wins: dict[str, int] = defaultdict(int)
    base_seed = seed if seed is not None else 42

    for i in range(n_sims):
        rng = random.Random(base_seed + i)
        champion = simulate_tournament_once(settings, rng=rng)
        wins[champion] += 1

    return {team: round(wins.get(team, 0) / n_sims, 6) for team in teams}


def top_teams(
    probs: dict[str, float],
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Sorted leaderboard rows for API responses."""
    rows = sorted(probs.items(), key=lambda x: (-x[1], x[0]))[:limit]
    return [{"team": t, "win_probability": p} for t, p in rows]
