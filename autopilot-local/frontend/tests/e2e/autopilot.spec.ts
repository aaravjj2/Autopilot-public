import { test, expect } from '@playwright/test';
import { gotoTerminal, expectSidebarNav } from './helpers';

test.describe('Autopilot Pipeline', () => {
  test('autopilot page loads', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/autopilot');
    await expect(page).toHaveURL(/autopilot/);
    await expect(page.getByRole('heading', { name: /Autopilot Pipeline/ })).toBeVisible();
  });

  test('autopilot has sidebar', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/autopilot');
    await expectSidebarNav(page);
  });

  test('autopilot shows scheduler running', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/autopilot');
    await expect(page.getByText(/RUNNING/i).first()).toBeVisible();
  });
});
