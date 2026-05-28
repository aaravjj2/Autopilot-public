import { test, expect } from '@playwright/test';
import { gotoTerminal, clickSidebar } from './helpers';

test.describe('Full User Flow', () => {
  test('complete navigation flow', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/APEX/);

    await page.getByRole('link', { name: /Enter Terminal/ }).click();
    await expect(page).toHaveURL(/dashboard/);
    await expect(page.locator('.app-shell')).toBeVisible();
    await page.waitForSelector('html[data-terminal-hydrated="true"]', { timeout: 30_000 });

    await clickSidebar(page, 'Trading');
    await expect(page).toHaveURL(/trading/, { timeout: 15_000 });

    await clickSidebar(page, 'Positions');
    await expect(page).toHaveURL(/positions/);

    await clickSidebar(page, 'Marketplace');
    await expect(page).toHaveURL(/marketplace/);

    await clickSidebar(page, 'Autopilot');
    await expect(page).toHaveURL(/autopilot/);

    await clickSidebar(page, 'Overview');
    await expect(page).toHaveURL(/\/dashboard\/?$/);
  });

  test('responsive layout', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await gotoTerminal(page, '/dashboard');

    await page.setViewportSize({ width: 1920, height: 1080 });
    await gotoTerminal(page, '/dashboard');
  });

  test('no critical page errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (error) => errors.push(error.message));

    await gotoTerminal(page, '/dashboard');
    await gotoTerminal(page, '/dashboard/trading');
    await gotoTerminal(page, '/dashboard/marketplace');

    const critical = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('ResizeObserver')
    );
    expect(critical.length).toBe(0);
  });
});
