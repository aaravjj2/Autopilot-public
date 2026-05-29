"""Deterministic improvement catalog when LLM providers are unavailable."""

from __future__ import annotations

from loop_modules.models import Idea

_CATALOG: dict[str, list[dict[str, str | list[str]]]] = {
    "Arb Detection Quality": [
        {
            "title": "Tune arb_min_net_edge from scan metrics",
            "description": "Lower net-edge floor when scan returns zero rows for 3 consecutive cycles.",
            "estimated_complexity": "LOW",
            "estimated_impact": "HIGH",
            "files_likely_affected": ["src/apex/core/config.py", "src/apex/services/arb_engine.py"],
            "test_strategy": "pytest tests/test_arb_engine.py",
        },
        {
            "title": "Cache Kalshi category fetches",
            "description": "Reduce 429 rate limits by caching category market lists for 60s.",
            "estimated_complexity": "MEDIUM",
            "estimated_impact": "HIGH",
            "files_likely_affected": ["src/apex/integrations/kalshi_adapter.py"],
            "test_strategy": "pytest",
        },
    ],
    "Risk & Execution": [
        {
            "title": "Expose risk gate rejection reasons in API",
            "description": "Return structured rejection codes from /api/execute for operator UX.",
            "estimated_complexity": "LOW",
            "estimated_impact": "MEDIUM",
            "files_likely_affected": ["backend_api.py", "src/apex/layers/l3/risk_checks.py"],
            "test_strategy": "pytest tests/test_risk_checks.py",
        },
    ],
    "Frontend & UX": [
        {
            "title": "Show arb_opportunities count on dashboard KPI",
            "description": "Read arb_opportunities from /health for cross-market radar KPI.",
            "estimated_complexity": "LOW",
            "estimated_impact": "MEDIUM",
            "files_likely_affected": ["autopilot-local/frontend/app/dashboard/page.tsx"],
            "test_strategy": "playwright smoke",
        },
    ],
    "Observability & Ops": [
        {
            "title": "Log scan_metrics summary each arb cycle",
            "description": "Emit coalesce hits and fetch latency percentiles to structured logs.",
            "estimated_complexity": "LOW",
            "estimated_impact": "MEDIUM",
            "files_likely_affected": ["src/apex/services/arb_scan.py"],
            "test_strategy": "pytest",
        },
    ],
    "Performance & Scale": [
        {
            "title": "Skip L2 ingest when showcase_mode active",
            "description": "Avoid orderbook hammering during demo deployments.",
            "estimated_complexity": "LOW",
            "estimated_impact": "MEDIUM",
            "files_likely_affected": ["src/apex/services/arb_scan.py"],
            "test_strategy": "pytest",
        },
    ],
}


def fallback_ideas(focus_area: str, iteration: int) -> list[Idea]:
    pool = _CATALOG.get(focus_area) or _CATALOG["Observability & Ops"]
    idx = iteration % len(pool)
    chosen = pool[idx : idx + 1]
    if not chosen:
        chosen = pool[:1]
    out: list[Idea] = []
    for item in chosen:
        out.append(
            Idea(
                title=str(item["title"]),
                description=str(item["description"]),
                focus_area=focus_area,
                estimated_complexity=str(item.get("estimated_complexity", "LOW")),
                estimated_impact=str(item.get("estimated_impact", "MEDIUM")),
                files_likely_affected=list(item.get("files_likely_affected", [])),
                test_strategy=str(item.get("test_strategy", "pytest")),
            )
        )
    return out
