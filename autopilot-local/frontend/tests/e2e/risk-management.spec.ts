import { test, expect } from '@playwright/test';
import { gotoTerminal, sidebarLink } from './helpers';

test.describe('Risk Management (Week 6)', () => {
  test('risk page loads with VaR KPIs', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/risk-management');
    await expect(page.getByRole('heading', { name: 'Risk Management' })).toBeVisible();
    await expect(page.getByText('VIX', { exact: true })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText('VaR 99%', { exact: true })).toBeVisible();
  });

  test('risk API returns metrics', async ({ request }) => {
    const base = process.env.NEXT_PUBLIC_APEX_API_URL || 'http://127.0.0.1:8000';
    const res = await request.get(`${base}/api/risk/metrics`, { timeout: 30_000 });
    test.skip(!res.ok(), 'APEX backend unavailable');
    const body = await res.json();
    expect(body).toHaveProperty('vix');
    expect(body.var).toHaveProperty('var_99_usd');
    expect(body.cftc).toHaveProperty('limit_usd');
  });

  test('sidebar Risk link navigates', async ({ page }) => {
    await gotoTerminal(page, '/dashboard');
    const riskLink = sidebarLink(page, 'Risk');
    await riskLink.scrollIntoViewIfNeeded();
    await riskLink.click();
    await expect(page).toHaveURL(/risk-management/, { timeout: 15_000 });
  });
});
