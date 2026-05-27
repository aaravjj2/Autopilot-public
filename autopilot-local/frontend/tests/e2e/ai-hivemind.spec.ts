import { test, expect } from '@playwright/test';
import { gotoTerminal } from './helpers';

test('AI Hive-Mind consensus vote', async ({ page }) => {
  await gotoTerminal(page, '/dashboard/ai-hivemind');
  await page.getByRole('button', { name: /Run vote/i }).click();
  await expect(page.getByTestId('consensus-output')).toBeVisible({ timeout: 15_000 });
  const text = await page.getByTestId('consensus-output').textContent();
  expect(text).toBeTruthy();
  expect(text).not.toContain('consensus failed');
});
