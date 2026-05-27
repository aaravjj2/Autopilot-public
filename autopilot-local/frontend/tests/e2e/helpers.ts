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

export async function clickSidebar(page: Page, label: string) {
  await page.locator('.sidebar').getByRole('link', { name: label, exact: true }).click();
}
