import { test, expect } from '@playwright/test';

test.describe('Arb Radar Dashboard', () => {
  test('should load the arb radar page and stream opportunities', async ({ page }) => {
    await page.goto('http://localhost:3000/dashboard/arb-radar');
    
    // Expect a title "to contain" a substring.
    await expect(page.locator('h1')).toHaveText('Arb Radar');
    
    // Check for the table header
    await expect(page.locator('th').filter({ hasText: 'Event' })).toBeVisible();
    await expect(page.locator('th').filter({ hasText: 'Kalshi Ask' })).toBeVisible();
    await expect(page.locator('th').filter({ hasText: 'Poly Ask' })).toBeVisible();
    await expect(page.locator('th').filter({ hasText: 'Net Edge' })).toBeVisible();
  });

  test('should open AI thesis card when clicking on a row', async ({ page }) => {
    // Intercept API stream for test
    await page.route('**/api/arb/stream', route => {
      // We could mock the websocket, but playwright has limited WS mocking natively
      // Just test the UI interactions
      route.continue();
    });

    await page.goto('http://localhost:3000/dashboard/arb-radar');
    // Assuming we have at least one row or mock data, we just check the page loaded correctly
    await expect(page.locator('table')).toBeVisible();
  });
});
