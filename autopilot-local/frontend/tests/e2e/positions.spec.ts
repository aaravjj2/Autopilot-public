import { test, expect } from '@playwright/test';
import { gotoTerminal, expectSidebarNav } from './helpers';

test.describe('Positions Page', () => {
  test('positions page loads', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/positions');
    await expect(page).toHaveURL(/positions/);
    await expect(page.getByRole('heading', { name: 'Positions' })).toBeVisible();
  });

  test('positions has sidebar', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/positions');
    await expectSidebarNav(page);
  });

  test('positions has open/closed tabs', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/positions');
    const tabs = page.locator('.main .tabs').first();
    await expect(tabs.getByRole('button', { name: 'Open', exact: true })).toBeVisible();
    await expect(tabs.getByRole('button', { name: 'Closed', exact: true })).toBeVisible();
  });
});
