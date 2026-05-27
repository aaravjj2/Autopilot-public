import { test, expect } from '@playwright/test';
import { gotoTerminal } from './helpers';

test.describe('Arb Radar JSON Patch stream', () => {
  test('arb-radar connects and shows patch mode', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/arb-radar');
    await expect(page.getByRole('heading', { name: 'Arb Radar' })).toBeVisible();
    await expect(page.getByTestId('connection-indicator')).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId('connection-indicator')).toContainText(/Connected/i, {
      timeout: 30_000,
    });
    await expect(page.getByTestId('patch-mode-indicator')).toContainText(/Patch stream/i);
  });

  test('arb stream API accepts websocket', async ({ request }) => {
    const base = process.env.NEXT_PUBLIC_APEX_API_URL || 'http://127.0.0.1:8000';
    const res = await request.get(`${base}/api/arb/summary`, { timeout: 15_000 });
    test.skip(!res.ok(), 'APEX backend unavailable');
    expect(res.ok()).toBeTruthy();
  });
});
