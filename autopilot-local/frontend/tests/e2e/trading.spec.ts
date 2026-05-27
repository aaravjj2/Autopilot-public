import { test, expect } from '@playwright/test';
import { gotoTerminal, expectSidebarNav } from './helpers';

test.describe('Trading Page', () => {
  test('trading page loads', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/trading');
    await expect(page).toHaveURL(/trading/);
    await expect(page.getByRole('heading', { name: 'Trading' })).toBeVisible();
  });

  test('trading has sidebar', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/trading');
    await expectSidebarNav(page);
  });

  test('trading has timeframe tabs', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/trading');
    await expect(page.getByRole('button', { name: '1D', exact: true })).toBeVisible();
  });
});
