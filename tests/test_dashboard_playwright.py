"""Playwright E2E tests for APEX Dashboard"""
import os
import pytest
import requests

# Skip module if dashboard is not reachable
try:
    _url = os.getenv("DASHBOARD_URL", "http://localhost:8501")
    requests.get(_url, timeout=1)
except requests.exceptions.RequestException:
    pytest.skip("Dashboard is not running", allow_module_level=True)

from playwright.sync_api import Page, expect


@pytest.fixture(scope="session")
def dashboard_url():
    """Dashboard URL - can be overridden via environment variable."""
    import os
    return os.getenv("DASHBOARD_URL", "http://localhost:8501")


def test_dashboard_loads(page: Page, dashboard_url: str):
    """Test that the dashboard loads successfully."""
    page.goto(dashboard_url)
    expect(page).to_have_title("APEX Monitor")
    expect(page.get_by_text("APEX Monitor")).to_be_visible()


def test_dashboard_has_workspace_selector(page: Page, dashboard_url: str):
    """Test that workspace selector is present."""
    page.goto(dashboard_url)
    expect(page.get_by_text("Workspace")).to_be_visible()
    expect(page.get_by_text("Ops monitor")).to_be_visible()
    expect(page.get_by_text("Copy trading")).to_be_visible()
    expect(page.get_by_text("Polymarket desk")).to_be_visible()


def test_dashboard_live_pulse_visible(page: Page, dashboard_url: str):
    """Test that live pulse card is visible."""
    page.goto(dashboard_url)
    expect(page.get_by_text("Live pulse")).to_be_visible()
    expect(page.get_by_text("ET now")).to_be_visible()
    expect(page.get_by_text("Jobs ok (today)")).to_be_visible()
    expect(page.get_by_text("Jobs failed")).to_be_visible()


def test_dashboard_pipeline_slo_visible(page: Page, dashboard_url: str):
    """Test that Pipeline SLO section is visible."""
    page.goto(dashboard_url)
    expect(page.get_by_text("Pipeline SLO")).to_be_visible()


def test_dashboard_integrations_visible(page: Page, dashboard_url: str):
    """Test that Integrations section is visible."""
    page.goto(dashboard_url)
    expect(page.get_by_text("Integrations")).to_be_visible()


def test_dashboard_audit_explorer_visible(page: Page, dashboard_url: str):
    """Test that Audit explorer section is visible."""
    page.goto(dashboard_url)
    expect(page.get_by_text("Audit explorer")).to_be_visible()
    expect(page.get_by_text("Quick filter")).to_be_visible()


def test_dashboard_tabs_present(page: Page, dashboard_url: str):
    """Test that all dashboard tabs are present."""
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


def test_dashboard_overview_tab(page: Page, dashboard_url: str):
    """Test Overview tab content."""
    page.goto(dashboard_url)
    page.get_by_text("Overview", exact=True).click()
    
    expect(page.get_by_text("Today's pipeline")).to_be_visible()
    expect(page.get_by_text("Event mix")).to_be_visible()


def test_dashboard_scheduler_jobs_tab(page: Page, dashboard_url: str):
    """Test Scheduler jobs tab content."""
    page.goto(dashboard_url)
    page.get_by_text("Scheduler jobs", exact=True).click()
    
    expect(page.get_by_text("Recent scheduler runs")).to_be_visible()


def test_dashboard_event_stream_tab(page: Page, dashboard_url: str):
    """Test Event stream tab content."""
    page.goto(dashboard_url)
    page.get_by_text("Event stream", exact=True).click()
    
    expect(page.get_by_text("Newest audit events")).to_be_visible()


def test_dashboard_orders_exits_tab(page: Page, dashboard_url: str):
    """Test Orders & exits tab content."""
    page.goto(dashboard_url)
    page.get_by_text("Orders & exits", exact=True).click()
    
    expect(page.get_by_text("Orders & proposals")).to_be_visible()


def test_dashboard_risk_alerts_tab(page: Page, dashboard_url: str):
    """Test Risk & alerts tab content."""
    page.goto(dashboard_url)
    page.get_by_text("Risk & alerts", exact=True).click()
    
    expect(page.get_by_text("Risk rejections")).to_be_visible()
    expect(page.get_by_text("System alerts")).to_be_visible()


def test_dashboard_gates_tab(page: Page, dashboard_url: str):
    """Test Gates tab content."""
    page.goto(dashboard_url)
    page.get_by_text("Gates", exact=True).click()
    
    expect(page.get_by_text("Predeployment gate results")).to_be_visible()


def test_dashboard_broker_tab(page: Page, dashboard_url: str):
    """Test Broker (Alpaca) tab content."""
    page.goto(dashboard_url)
    page.get_by_text("Broker (Alpaca)", exact=True).click()
    
    expect(page.get_by_text("Alpaca paper / live")).to_be_visible()


def test_dashboard_equity_pnl_tab(page: Page, dashboard_url: str):
    """Test Equity & P&L tab content."""
    page.goto(dashboard_url)
    page.get_by_text("Equity & P&L", exact=True).click()
    
    expect(page.get_by_text("Equity Curve")).to_be_visible()
    expect(page.get_by_text("P&L Attribution")).to_be_visible()


# Discord Trades tab removed as part of cleanup.


def test_dashboard_signal_quality_tab(page: Page, dashboard_url: str):
    """Test Signal Quality tab content."""
    page.goto(dashboard_url)
    page.get_by_text("Signal Quality", exact=True).click()
    
    expect(page.get_by_text("Signal Quality")).to_be_visible()


def test_dashboard_csv_export_button(page: Page, dashboard_url: str):
    """Test that CSV export button is present."""
    page.goto(dashboard_url)
    expect(page.get_by_text("Download filtered audit")).to_be_visible()


def test_dashboard_sidebar_session_info(page: Page, dashboard_url: str):
    """Test that sidebar shows session info."""
    page.goto(dashboard_url)
    expect(page.get_by_text("Session")).to_be_visible()
    expect(page.get_by_text("Log level")).to_be_visible()


def test_dashboard_responsive_layout(page: Page, dashboard_url: str):
    """Test dashboard layout on different screen sizes."""
    page.goto(dashboard_url)
    
    # Test mobile viewport
    page.set_viewport_size({"width": 375, "height": 812})
    expect(page.get_by_text("APEX Monitor")).to_be_visible()
    
    # Test tablet viewport
    page.set_viewport_size({"width": 768, "height": 1024})
    expect(page.get_by_text("APEX Monitor")).to_be_visible()
    
    # Test desktop viewport
    page.set_viewport_size({"width": 1920, "height": 1080})
    expect(page.get_by_text("APEX Monitor")).to_be_visible()


def test_dashboard_no_console_errors(page: Page, dashboard_url: str):
    """Test that there are no console errors."""
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    
    page.goto(dashboard_url)
    page.wait_for_timeout(2000)
    
    # Filter out known non-critical errors
    critical_errors = [e for e in errors if "Failed to load" in e or "Uncaught" in e]
    assert len(critical_errors) == 0, f"Console errors found: {critical_errors}"
