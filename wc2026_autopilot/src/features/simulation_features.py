"""Optional bridge to APEX Poisson λ features for WC2026 simulation context."""

from __future__ import annotations

from typing import Any

try:
    from apex.ml.wc_poisson import team_lambda_features as _team_lambda_features
except ImportError:
    _team_lambda_features = None  # type: ignore[misc, assignment]


def get_match_lambda_features(
    home_team: str,
    away_team: str,
    settings: Any | None = None,
) -> dict[str, float] | None:
    """Return λ_home, λ_away, and outcome probs when apex is importable."""
    if _team_lambda_features is None:
        return None
    return _team_lambda_features(home_team, away_team, settings)
