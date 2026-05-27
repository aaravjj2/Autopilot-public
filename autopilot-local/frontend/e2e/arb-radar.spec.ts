import { test, expect } from '@playwright/test';

// Mock external API routes
test.beforeEach(async ({ page }) => {
  await page.route('**/api/*', async route => {
    // Simple mock response
    const url = route.request().url();
    if (url.includes('/arb')) {
      await route.fulfill({ json: { arb: [] } });
    } else {
      await route.continue();
    }
  });
});

test('arb radar loads and displays no opportunities initially', async ({ page }) => {
  await page.goto('/');
  // Wait for radar component
  const radar = page.getByTestId('arb-radar');
  await expect(radar).toBeVisible();
  // Expect placeholder text
  await expect(radar).toContainText('No arbitrage opportunities');
});
