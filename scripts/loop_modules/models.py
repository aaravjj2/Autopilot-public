from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

@dataclass
class Idea:
    title: str
    description: str
    focus_area: str
    estimated_complexity: str  # LOW | MEDIUM | HIGH
    estimated_impact: str      # LOW | MEDIUM | HIGH
    files_likely_affected: list[str]
    test_strategy: str

@dataclass
class PlanStep:
    file: str
    action: str
    description: str

@dataclass
class ImplementationPlan:
    steps: list[PlanStep]
    test_commands: list[str]
    rollback_steps: list[str]
    expected_artifacts: list[str]

@dataclass
class BuildResult:
    success: bool
    files_changed: list[str]
    errors: list[str]
    duration_seconds: float

@dataclass
class TestResult:
    pytest_passed: int
    pytest_total: int
    pytest_failed: int
    tsc_passed: bool
    playwright_passed: int
    playwright_total: int
    playwright_failed: int
    playwright_screenshots: list[str]
    api_smoke_passed: bool
    cloud_smoke_passed: bool = True
    cloud_run_url: str = ""
    backtest_sharpe: float = 0.0
    backtest_win_rate: float = 0.0
    regression_passed: bool = False
    overall_passed: bool = False

@dataclass
class Artifact:
    type: str  # screenshot|video|diff|metrics
    path: str
    iteration: int
    timestamp: str

@dataclass
class LoopState:
    current_iteration: int = 1
    completed_iterations: list[int] = field(default_factory=list)
    idea_history: list[dict[str, Any]] = field(default_factory=list)
    failed_iterations: list[dict[str, Any]] = field(default_factory=list)
    metrics_history: list[dict[str, Any]] = field(default_factory=list)
    last_compact_summary: str = ""

@dataclass
class LoopContext:
    iteration: int
    recent_ideas: list[dict[str, Any]]
    test_pass_rate: float
    backtest_metrics: dict[str, Any]
    changed_files: list[str]
    compact_summary: str
    cloud_run_url: str = ""
    cloud_health: dict[str, Any] = field(default_factory=dict)
    last_test_failures: list[str] = field(default_factory=list)
