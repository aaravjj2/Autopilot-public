"""FIFA World Cup 2026 tournament probability model (Elo-based v1)."""

from __future__ import annotations

import math
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from apex.core.config import Settings, get_settings
from apex.core.logging import get_logger

LOGGER = get_logger(__name__)

MODEL_VERSION = "wc_elo_v1"
MODEL_VERSION_POISSON = "wc_poisson_v1"


@dataclass
class WorldCupScore:
    fair_prob: float
    market_implied: float
    model_edge: float
    confidence: float
    contract_type: str
    model_version: str = MODEL_VERSION


def _ratings_path(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    root = settings.sqlite_path.expanduser().resolve().parent
    return root / "world_cup" / "elo_ratings_2026.json"


def load_elo_ratings(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    bundled = Path(__file__).resolve().parents[3] / "data" / "world_cup" / "elo_ratings_2026.json"
    for path in (_ratings_path(settings), bundled):
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                LOGGER.warning("elo load failed %s: %s", path, exc)
    return {"teams": {}, "home_advantage_elo": 45}


def _elo_win_prob(elo_a: float, elo_b: float, home_adv: float = 0.0) -> float:
    diff = (elo_a + home_adv) - elo_b
    return 1.0 / (1.0 + 10 ** (-diff / 400.0))


def _find_team(name: str, teams: dict[str, float]) -> tuple[str, float] | None:
    if not name:
        return None
    n = name.strip().lower()
    for k, v in teams.items():
        if k.lower() == n or k.lower() in n or n in k.lower():
            return k, float(v)
    return None


def parse_match_teams(question: str) -> tuple[str, str] | None:
    """Extract two team names from common market question patterns."""
    q = question.strip()
    patterns = [
        r"(?:will\s+)?(.+?)\s+(?:beat|defeat|vs\.?|v)\s+(.+?)(?:\?|$)",
        r"(.+?)\s+to\s+beat\s+(.+?)(?:\?|$)",
        r"(.+?)\s+vs\s+(.+?)(?:\?|$)",
    ]
    for pat in patterns:
        m = re.search(pat, q, re.I)
        if m:
            return m.group(1).strip(), m.group(2).strip()
    return None


def infer_contract_type(question: str) -> str:
    ql = question.lower()
    if "win the world cup" in ql or "world cup winner" in ql or "champion" in ql:
        return "tournament_winner"
    if "advance" in ql or "qualify" in ql or "group" in ql:
        return "advance"
    if parse_match_teams(question):
        return "match_winner"
    return "other"


def score_contract_poisson(
    row: dict[str, Any], settings: Settings | None = None
) -> WorldCupScore | None:
    """Poisson/Dixon-Coles fair prob for match_winner; None if not applicable."""
    settings = settings or get_settings()
    question = str(row.get("question") or "")
    ctype = str(row.get("contract_type") or infer_contract_type(question))
    if ctype != "match_winner":
        return None

    from apex.ml.wc_poisson import score_match_poisson

    poisson = score_match_poisson(row, settings)
    if poisson.get("teams_resolved") is None:
        return None
    fair = float(poisson["fair_prob"])

    market_yes = float(row.get("market_yes_ask") or row.get("kalshi_yes_ask") or 0.5)
    market_yes = max(0.01, min(0.99, market_yes))
    fair = max(0.01, min(0.99, fair))
    return WorldCupScore(
        fair_prob=round(fair, 4),
        market_implied=round(market_yes, 4),
        model_edge=round(fair - market_yes, 4),
        confidence=0.78,
        contract_type=ctype,
        model_version=MODEL_VERSION_POISSON,
    )


def score_contract(row: dict[str, Any], settings: Settings | None = None) -> WorldCupScore:
    settings = settings or get_settings()
    question = str(row.get("question") or "")
    ctype = str(row.get("contract_type") or infer_contract_type(question))

    if getattr(settings, "world_cup_use_poisson", False) and ctype == "match_winner":
        poisson_sc = score_contract_poisson(row, settings)
        if poisson_sc is not None:
            return poisson_sc

    data = load_elo_ratings(settings)
    teams: dict[str, float] = {str(k): float(v) for k, v in (data.get("teams") or {}).items()}
    home_adv = float(data.get("home_advantage_elo", 45))

    market_yes = float(row.get("market_yes_ask") or row.get("kalshi_yes_ask") or 0.5)
    if not math.isfinite(market_yes):
        market_yes = 0.5
    market_yes = max(0.01, min(0.99, market_yes))

    fair = 0.5
    confidence = 0.35

    if ctype == "match_winner":
        parsed = parse_match_teams(question)
        if parsed:
            ta, tb = parsed
            ra = _find_team(ta, teams)
            rb = _find_team(tb, teams)
            if ra and rb:
                fair = _elo_win_prob(ra[1], rb[1], home_adv)
                confidence = 0.72
    elif ctype == "tournament_winner":
        team_hint = question.split("?")[0].split()[-3:] if question else []
        for fragment in [" ".join(team_hint), question]:
            hit = _find_team(fragment, teams)
            if hit:
                elos = list(teams.values())
                avg = sum(elos) / len(elos) if elos else 2000
                fair = min(0.35, max(0.02, (hit[1] - avg) / 4000 + 0.08))
                confidence = 0.55
                break
    else:
        fair = market_yes
        confidence = 0.25

    fair = max(0.01, min(0.99, fair))
    edge = round(fair - market_yes, 4)
    return WorldCupScore(
        fair_prob=round(fair, 4),
        market_implied=round(market_yes, 4),
        model_edge=edge,
        confidence=confidence,
        contract_type=ctype,
    )


def apply_scores(rows: list[dict[str, Any]], settings: Settings | None = None) -> list[dict[str, Any]]:
    settings = settings or get_settings()
    w_wc = float(getattr(settings, "world_cup_score_weight", 0.4))
    w_arb = float(getattr(settings, "world_cup_arb_score_weight", 0.35))
    w_edge = float(getattr(settings, "world_cup_net_edge_weight", 0.25))

    out: list[dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        sc = score_contract(r, settings)
        r["fair_prob"] = sc.fair_prob
        r["market_implied"] = sc.market_implied
        r["model_edge"] = sc.model_edge
        r["model_confidence"] = sc.confidence
        r["contract_type"] = sc.contract_type
        r["model_version"] = sc.model_version
        arb_score = float(r.get("model_score") or r.get("net_edge") or 0)
        r["final_score"] = (
            w_wc * abs(sc.model_edge)
            + w_arb * arb_score
            + w_edge * float(r.get("net_edge") or 0)
        )
        out.append(r)
    return sorted(out, key=lambda x: -(float(x.get("final_score") or 0)))
