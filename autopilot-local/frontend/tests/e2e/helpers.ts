import { Page, expect } from '@playwright/test';

const APEX_HEALTH = process.env.APEX_HEALTH_URL || 'http://127.0.0.1:8000/health';

/** Ensure APEX responds before UI tests (Phase 1). */
export async function waitForApexHealth(timeoutMs = 30_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(APEX_HEALTH);
      if (res.ok) {
        const body = await res.json();
        if (body && typeof body === 'object') return;
      }
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new Error(`APEX health check failed: ${APEX_HEALTH}`);
}

/** Navigate and wait for terminal shell (avoids networkidle hangs from WS/polling). */
export async function gotoTerminal(page: Page, path: string) {
  await waitForApexHealth();
  await page.goto(path, { waitUntil: 'load', timeout: 45_000 });
  await expect(page.locator('.app-shell')).toBeVisible({ timeout: 20_000 });
  await page.waitForSelector('html[data-terminal-hydrated="true"]', { timeout: 20_000 });
}

export async function expectSidebarNav(page: Page) {
  const sidebar = page.locator('.sidebar');
  await expect(sidebar.getByRole('link', { name: 'Overview' })).toBeVisible();
  await expect(sidebar.getByRole('link', { name: 'Trading' })).toBeVisible();
  await expect(sidebar.getByRole('link', { name: 'Marketplace' })).toBeVisible();
}

export async function waitForTerminalHydration(page: Page) {
  await page.waitForSelector('html[data-terminal-hydrated="true"]', { timeout: 30_000 });
}

/** Sidebar hrefs — use attribute selectors so nav badges do not break exact name matching. */
const SIDEBAR_HREFS: Record<string, string> = {
  Overview: '/dashboard',
  Trading: '/dashboard/trading',
  Positions: '/dashboard/positions',
  Signals: '/dashboard/opportunities',
  Autopilot: '/dashboard/autopilot',
  'Arb Radar': '/dashboard/arb-radar',
  Risk: '/dashboard/risk-management',
  'Hive-Mind': '/dashboard/ai-hivemind',
  Analytics: '/dashboard/analytics',
  'Live Feed': '/dashboard/live',
  Marketplace: '/dashboard/marketplace',
  Kalshi: '/dashboard/kalshi',
  Polymarket: '/dashboard/polymarket',
  DeFi: '/dashboard/defi-treasury',
  Fund: '/dashboard/fund-admin',
  Settings: '/dashboard/settings',
};

export function sidebarLink(page: Page, label: string) {
  const href = SIDEBAR_HREFS[label];
  if (href) {
    return page.locator(`.sidebar a.nav-link[href="${href}"]`);
  }
  return page.locator('.sidebar').getByRole('link', { name: label, exact: true });
}

export async function clickSidebar(page: Page, label: string) {
  await waitForTerminalHydration(page);
  const link = sidebarLink(page, label);
  await link.scrollIntoViewIfNeeded();
  await link.click();
}
