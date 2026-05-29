"""Rule-based implementation plans keyed by fallback catalog idea titles."""

from __future__ import annotations

from loop_modules.models import Idea, ImplementationPlan, PlanStep

_DEFAULT_TESTS = [
    "python -m pytest tests/ -q --tb=short",
    "curl -fsS http://127.0.0.1:8010/health",
]

_TEMPLATES: dict[str, ImplementationPlan] = {
    "Tune arb_min_net_edge from scan metrics": ImplementationPlan(
        steps=[
            PlanStep(
                file="src/apex/services/arb_scan.py",
                action="MODIFY",
                description=(
                    "When consecutive scan cycles return zero opportunities, "
                    "log a warning with scan_metrics and temporarily relax "
                    "effective min net edge by 0.002 (floor 0.005) for the next cycle."
                ),
            ),
            PlanStep(
                file="tests/test_arb_scan.py",
                action="MODIFY",
                description="Add unit test for zero-row adaptive edge relaxation.",
            ),
        ],
        test_commands=["python -m pytest tests/test_arb_scan.py tests/test_arb_engine.py -q --tb=short"],
        rollback_steps=["git restore src/apex/services/arb_scan.py tests/test_arb_scan.py"],
        expected_artifacts=["/api/arb/opportunities"],
    ),
    "Cache Kalshi category fetches": ImplementationPlan(
        steps=[
            PlanStep(
                file="src/apex/integrations/kalshi_adapter.py",
                action="MODIFY",
                description="Add 60s TTL in-memory cache for category market list fetches; include cache hit/miss in debug logs.",
            ),
        ],
        test_commands=["python -m pytest tests/ -k kalshi -q --tb=short"],
        rollback_steps=["git restore src/apex/integrations/kalshi_adapter.py"],
        expected_artifacts=[],
    ),
    "Expose risk gate rejection reasons in API": ImplementationPlan(
        steps=[
            PlanStep(
                file="src/apex/layers/l3/risk_checks.py",
                action="MODIFY",
                description="Ensure each failed check returns a stable machine-readable code (e.g. R03_INSUFFICIENT_EDGE).",
            ),
            PlanStep(
                file="backend_api.py",
                action="MODIFY",
                description="Surface risk rejection codes in execute/paper-trade error JSON responses.",
            ),
            PlanStep(
                file="tests/test_risk_checks.py",
                action="MODIFY",
                description="Assert rejection payloads include code field for at least one gate.",
            ),
        ],
        test_commands=["python -m pytest tests/test_risk_checks.py -q --tb=short"],
        rollback_steps=["git restore src/apex/layers/l3/risk_checks.py backend_api.py tests/test_risk_checks.py"],
        expected_artifacts=["/api/execute"],
    ),
    "Show arb_opportunities count on dashboard KPI": ImplementationPlan(
        steps=[
            PlanStep(
                file="autopilot-local/frontend/app/dashboard/page.tsx",
                action="MODIFY",
                description="Fetch /health and display arb_opportunities alongside opportunities KPI tile.",
            ),
        ],
        test_commands=[
            "cd autopilot-local/frontend && npx tsc --noEmit",
            "cd autopilot-local/frontend && npx playwright test tests/e2e/smoke.spec.ts",
        ],
        rollback_steps=["git restore autopilot-local/frontend/app/dashboard/page.tsx"],
        expected_artifacts=["/dashboard"],
    ),
    "Log scan_metrics summary each arb cycle": ImplementationPlan(
        steps=[
            PlanStep(
                file="src/apex/services/arb_scan.py",
                action="MODIFY",
                description="After each scan cycle, log structured scan_metrics (duration_ms, rows, coalesce_hits) at INFO.",
            ),
        ],
        test_commands=["python -m pytest tests/test_arb_scan.py -q --tb=short"],
        rollback_steps=["git restore src/apex/services/arb_scan.py"],
        expected_artifacts=[],
    ),
    "Skip L2 ingest when showcase_mode active": ImplementationPlan(
        steps=[
            PlanStep(
                file="src/apex/services/arb_scan.py",
                action="MODIFY",
                description="When settings.showcase_mode is true, skip live L2 orderbook ingest and use seeded DB rows only.",
            ),
            PlanStep(
                file="tests/test_showcase_seed.py",
                action="MODIFY",
                description="Add test asserting showcase_mode short-circuits external L2 fetch.",
            ),
        ],
        test_commands=["python -m pytest tests/test_showcase_seed.py tests/test_arb_scan.py -q --tb=short"],
        rollback_steps=["git restore src/apex/services/arb_scan.py tests/test_showcase_seed.py"],
        expected_artifacts=["/health"],
    ),
}


def plan_for_idea(idea: Idea) -> ImplementationPlan | None:
    """Return a concrete plan for a catalog idea, or None if LLM planning is required."""
    if idea.title in _TEMPLATES:
        return _TEMPLATES[idea.title]
    # Generic plan from idea metadata when title is not in catalog
    if idea.files_likely_affected:
        steps = [
            PlanStep(
                file=path,
                action="MODIFY",
                description=f"{idea.description} (focus: {idea.focus_area})",
            )
            for path in idea.files_likely_affected[:3]
        ]
        tests = [idea.test_strategy] if idea.test_strategy else _DEFAULT_TESTS
        return ImplementationPlan(
            steps=steps,
            test_commands=tests,
            rollback_steps=[f"git restore {' '.join(idea.files_likely_affected[:3])}"],
            expected_artifacts=[],
        )
    return None
