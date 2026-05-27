import { test, expect } from '@playwright/test';
import { gotoTerminal, expectSidebarNav } from './helpers';

test.describe('Dashboard Overview', () => {
  test('dashboard page loads', async ({ page }) => {
    await gotoTerminal(page, '/dashboard');
    await expect(page).toHaveURL(/dashboard/);
    await expect(page.getByRole('heading', { name: 'Command Center' })).toBeVisible();
  });

  test('dashboard has sidebar with navigation', async ({ page }) => {
    await gotoTerminal(page, '/dashboard');
    await expectSidebarNav(page);
  });

  test('dashboard shows engine running', async ({ page }) => {
    await gotoTerminal(page, '/dashboard');
    await expect(page.getByText(/RUNNING/i).first()).toBeVisible();
  });

  test('dashboard shows portfolio KPI', async ({ page }) => {
    await gotoTerminal(page, '/dashboard');
    await expect(page.getByText('Portfolio').first()).toBeVisible();
    await expect(page.locator('.kpi-value').first()).toBeVisible();
  });
});
