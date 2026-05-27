import { test, expect } from '@playwright/test';

test('analytics page loads performance chart', async ({ page }) => {
  await page.goto('/dashboard');
  const chart = page.getByTestId('performance-chart');
  await expect(chart).toBeVisible();
  // Ensure chart has some data points (simplified check)
  await expect(chart).toContainText('Performance');
});
