import { test, expect } from '@playwright/test';
import { gotoTerminal } from './helpers';

test.describe('Navigation', () => {
  test('landing page loads', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/APEX/);
    await expect(page.getByRole('heading', { name: /APEX Trading Terminal/ })).toBeVisible();
  });

  test('landing page has terminal button', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('link', { name: /Enter Terminal/ })).toBeVisible();
  });

  test('engine status visible on landing', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText(/Engine online/i)).toBeVisible();
  });

  test('enter terminal navigates to dashboard', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: /Enter Terminal/ }).click();
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.locator('.app-shell')).toBeVisible();
  });

  test('marketplace link on landing', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: /Marketplace/i }).first().click();
    await expect(page).toHaveURL(/\/dashboard\/marketplace/);
  });
});
