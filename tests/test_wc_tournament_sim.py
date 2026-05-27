"""Monte Carlo World Cup tournament simulator smoke tests."""

from __future__ import annotations

import random

import pytest

from apex.ml.wc_tournament_sim import (
    MODEL_VERSION,
    run_monte_carlo,
    simulate_group_match,
    simulate_tournament_once,
)


@pytest.fixture
def seeded_elo(monkeypatch):
    teams = {
        "Brazil": 2100.0,
        "Argentina": 2080.0,
        "France": 2050.0,
        "England": 2020.0,
        "Panama": 1650.0,
        "Haiti": 1680.0,
    }
    for group_teams in (
        ("Mexico", "South Africa", "South Korea", "Czech Republic"),
        ("Canada", "Bosnia & Herzegovina", "Qatar", "Switzerland"),
        ("Brazil", "Morocco", "Haiti", "Scotland"),
        ("USA", "Paraguay", "Australia", "Turkey"),
        ("Germany", "Curaçao", "Ivory Coast", "Ecuador"),
        ("Netherlands", "Japan", "Sweden", "Tunisia"),
        ("Belgium", "Egypt", "Iran", "New Zealand"),
        ("Spain", "Cape Verde", "Saudi Arabia", "Uruguay"),
        ("France", "Senegal", "Iraq", "Norway"),
        ("Argentina", "Algeria", "Austria", "Jordan"),
        ("Portugal", "DR Congo", "Uzbekistan", "Colombia"),
        ("England", "Croatia", "Ghana", "Panama"),
    ):
        for t in group_teams:
            if t not in teams:
                teams[t] = 1800.0
    payload = {"teams": teams, "home_advantage_elo": 45}

    def _fake_load(_settings=None):
        return payload

    monkeypatch.setattr("apex.ml.wc_tournament_sim.load_elo_ratings", _fake_load)
    return payload


def test_simulate_group_match_returns_scores():
    hg, ag = simulate_group_match(2000.0, 1700.0, home_advantage_elo=45.0)
    assert isinstance(hg, int) and isinstance(ag, int)
    assert hg >= 0 and ag >= 0


def test_run_monte_carlo_smoke(seeded_elo):
    probs = run_monte_carlo(50, seed=7)
    assert MODEL_VERSION == "wc_montecarlo_v1"
    assert len(probs) == 48
    assert abs(sum(probs.values()) - 1.0) < 1e-6
    assert probs["Brazil"] > probs["Panama"]


def test_simulate_tournament_once_returns_known_team(seeded_elo):
    champ = simulate_tournament_once(rng=random.Random(99))
    assert champ in seeded_elo["teams"]
