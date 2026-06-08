"""Playwright E2E tests for APEX Dashboard.

Skips entirely when:
1. Dashboard is not reachable at DASHBOARD_URL / localhost:8501, OR
2. Playwright browsers are not installed (no chromium binary available).

This prevents the ``page`` fixture from launching a browser that would hang
in headless/CI environments.
"""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

_DASHBOARD_URL: str = os.getenv("DASHBOARD_URL", "http://localhost:8501")

# ── skip state ─────────────────────────────────────────────────────────
_SKIP_REASON: str | None = None

# ── reachability guard ──────────────────────────────────────────────────
_DASHBOARD_REACHABLE: bool = False
try:
    import requests as _req

    _resp = _req.get(_DASHBOARD_URL, timeout=3)
    # Also verify the response actually contains the APEX Monitor title
    # so we don't run tests against a different app on the same port
    if "APEX Monitor" in _resp.text or "apex" in _resp.text.lower():
        _DASHBOARD_REACHABLE = True
    else:
        _SKIP_REASON = f"Dashboard at {_DASHBOARD_URL} is not APEX Monitor"
except Exception:
    pass

# ── playwright browser check ────────────────────────────────────────────
_PW_BROWSER_AVAILABLE: bool = False

try:
    from playwright.sync_api import sync_playwright

    _PW_BROWSER_AVAILABLE = True
except ImportError:
    _SKIP_REASON = "playwright not installed"

if _PW_BROWSER_AVAILABLE:
    try:
        with sync_playwright() as p:
            p.chromium.launch(headless=True).close()
    except Exception as exc:
        _SKIP_REASON = f"Playwright cannot launch browser: {exc}"

# Skip if either condition fails.
if not _DASHBOARD_REACHABLE and _SKIP_REASON is None:
    _SKIP_REASON = f"Dashboard not reachable at {_DASHBOARD_URL}"

pytestmark = pytest.mark.skipif(
    _SKIP_REASON is not None,
    reason=_SKIP_REASON or "dashboard unreachable",
)

# Import types for annotations; skipped tests never execute body.
try:
    from playwright.sync_api import Page, expect
except ImportError:  # pragma: no cover - CI backend job has no playwright
    Page = expect = None  # type: ignore[assignment,misc]


# ═══════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def dashboard_url() -> str:
    return _DASHBOARD_URL


def test_dashboard_loads(page: Page, dashboard_url: str) -> None:
    page.goto(dashboard_url)
    expect(page).to_have_title("APEX Monitor")
    expect(page.get_by_text("APEX Monitor")).to_be_visible()


def test_dashboard_has_workspace_selector(page: Page, dashboard_url: str) -> None:
    page.goto(dashboard_url)
    expect(page.get_by_text("Workspace")).to_be_visible()
    expect(page.get_by_text("Ops monitor")).to_be_visible()
    expect(page.get_by_text("Copy trading")).to_be_visible()
    expect(page.get_by_text("Polymarket desk")).to_be_visible()


def test_dashboard_live_pulse_visible(page: Page, dashboard_url: str) -> None:
    page.goto(dashboard_url)
    expect(page.get_by_text("Live pulse")).to_be_visible()
    expect(page.get_by_text("ET now")).to_be_visible()
    expect(page.get_by_text("Jobs ok (today)")).to_be_visible()
    expect(page.get_by_text("Jobs failed")).to_be_visible()


def test_dashboard_pipeline_slo_visible(page: Page, dashboard_url: str) -> None:
    page.goto(dashboard_url)
    expect(page.get_by_text("Pipeline SLO")).to_be_visible()


def test_dashboard_integrations_visible(page: Page, dashboard_url: str) -> None:
    page.goto(dashboard_url)
    expect(page.get_by_text("Integrations")).to_be_visible()


def test_dashboard_audit_explorer_visible(page: Page, dashboard_url: str) -> None:
    page.goto(dashboard_url)
    expect(page.get_by_text("Audit explorer")).to_be_visible()
    expect(page.get_by_text("Quick filter")).to_be_visible()


def test_dashboard_tabs_present(page: Page, dashboard_url: str) -> None:
    page.goto(dashboard_url)

    expected_tabs = [
        "Overview",
        "Scheduler jobs",
        "Event stream",
        "Orders & exits",
        "Risk & alerts",
        "Gates",
        "Broker (Alpaca)",
        "Equity & P&L",
        "Signal Quality",
    ]

    for tab in expected_tabs:
        expect(page.get_by_text(tab, exact=True)).to_be_visible()


def test_dashboard_overview_tab(page: Page, dashboard_url: str) -> None:
    page.goto(dashboard_url)
    page.get_by_text("Overview", exact=True).click()
    expect(page.get_by_text("Today's pipeline")).to_be_visible()
    expect(page.get_by_text("Event mix")).to_be_visible()


def test_dashboard_scheduler_jobs_tab(page: Page, dashboard_url: str) -> None:
    page.goto(dashboard_url)
    page.get_by_text("Scheduler jobs", exact=True).click()
    expect(page.get_by_text("Recent scheduler runs")).to_be_visible()


def test_dashboard_event_stream_tab(page: Page, dashboard_url: str) -> None:
    page.goto(dashboard_url)
    page.get_by_text("Event stream", exact=True).click()
    expect(page.get_by_text("Newest audit events")).to_be_visible()


def test_dashboard_orders_exits_tab(page: Page, dashboard_url: str) -> None:
    page.goto(dashboard_url)
    page.get_by_text("Orders & exits", exact=True).click()
    expect(page.get_by_text("Orders & proposals")).to_be_visible()


def test_dashboard_risk_alerts_tab(page: Page, dashboard_url: str) -> None:
    page.goto(dashboard_url)
    page.get_by_text("Risk & alerts", exact=True).click()
    expect(page.get_by_text("Risk rejections")).to_be_visible()
    expect(page.get_by_text("System alerts")).to_be_visible()


def test_dashboard_gates_tab(page: Page, dashboard_url: str) -> None:
    page.goto(dashboard_url)
    page.get_by_text("Gates", exact=True).click()
    expect(page.get_by_text("Predeployment gate results")).to_be_visible()


def test_dashboard_broker_tab(page: Page, dashboard_url: str) -> None:
    page.goto(dashboard_url)
    page.get_by_text("Broker (Alpaca)", exact=True).click()
    expect(page.get_by_text("Alpaca paper / live")).to_be_visible()


def test_dashboard_equity_pnl_tab(page: Page, dashboard_url: str) -> None:
    page.goto(dashboard_url)
    page.get_by_text("Equity & P&L", exact=True).click()
    expect(page.get_by_text("Equity Curve")).to_be_visible()
    expect(page.get_by_text("P&L Attribution")).to_be_visible()


def test_dashboard_signal_quality_tab(page: Page, dashboard_url: str) -> None:
    page.goto(dashboard_url)
    page.get_by_text("Signal Quality", exact=True).click()
    expect(page.get_by_text("Signal Quality")).to_be_visible()


def test_dashboard_csv_export_button(page: Page, dashboard_url: str) -> None:
    page.goto(dashboard_url)
    expect(page.get_by_text("Download filtered audit")).to_be_visible()


def test_dashboard_sidebar_session_info(page: Page, dashboard_url: str) -> None:
    page.goto(dashboard_url)
    expect(page.get_by_text("Session")).to_be_visible()
    expect(page.get_by_text("Log level")).to_be_visible()


def test_dashboard_responsive_layout(page: Page, dashboard_url: str) -> None:
    page.goto(dashboard_url)

    page.set_viewport_size({"width": 375, "height": 812})
    expect(page.get_by_text("APEX Monitor")).to_be_visible()

    page.set_viewport_size({"width": 768, "height": 1024})
    expect(page.get_by_text("APEX Monitor")).to_be_visible()

    page.set_viewport_size({"width": 1920, "height": 1080})
    expect(page.get_by_text("APEX Monitor")).to_be_visible()


def test_dashboard_no_console_errors(page: Page, dashboard_url: str) -> None:
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    page.goto(dashboard_url)
    page.wait_for_timeout(2000)

    critical_errors = [e for e in errors if "Failed to load" in e or "Uncaught" in e]
    assert len(critical_errors) == 0, f"Console errors found: {critical_errors}"
