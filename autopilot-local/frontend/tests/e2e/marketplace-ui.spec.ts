import { test, expect } from '@playwright/test';
import { gotoTerminal } from './helpers';

test.describe('Marketplace UI', () => {
  test('marketplace page loads', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/marketplace');
    await expect(page.getByRole('heading', { name: /Copy Trading Marketplace/ })).toBeVisible();
  });

  test('polymarket page loads', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/polymarket');
    await expect(page.getByRole('heading', { name: /Polymarket Book/ })).toBeVisible();
  });

  test('settings shows dual backends', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/settings');
    await expect(page.getByRole('heading', { name: /Settings/ })).toBeVisible();
    await expect(page.getByText('APEX Engine')).toBeVisible();
    await expect(page.getByText('Copy Trading API')).toBeVisible();
  });
});
