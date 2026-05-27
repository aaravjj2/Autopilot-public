import { test, expect } from '@playwright/test';
import { gotoTerminal, waitForApexHealth } from './helpers';

test.describe('Smoke', () => {
  test.beforeAll(async () => {
    await waitForApexHealth();
  });

  test('dashboard overview loads', async ({ page }) => {
    await gotoTerminal(page, '/dashboard');
    await expect(page.getByRole('heading', { name: /Command Center/i })).toBeVisible();
  });

  test('arb radar loads', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/arb-radar');
    await expect(page.getByRole('heading', { name: /^Arb Radar$/ })).toBeVisible();
  });
});
