# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: navigation.spec.ts >> Navigation >> landing page loads
- Location: tests/e2e/navigation.spec.ts:5:7

# Error details

```
Error: expect(page).toHaveTitle(expected) failed

Expected pattern: /APEX/
Received string:  ""
Timeout: 5000ms

Call log:
  - Expect "toHaveTitle" with timeout 5000ms
    - waiting for" http://127.0.0.1:3000/" navigation to finish...
    - navigated to "http://127.0.0.1:3000/"
    5 × unexpected value ""

```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | import { gotoTerminal } from './helpers';
  3  | 
  4  | test.describe('Navigation', () => {
  5  |   test('landing page loads', async ({ page }) => {
  6  |     await page.goto('/');
> 7  |     await expect(page).toHaveTitle(/APEX/);
     |                        ^ Error: expect(page).toHaveTitle(expected) failed
  8  |     await expect(page.getByRole('heading', { name: /APEX Trading Terminal/ })).toBeVisible();
  9  |   });
  10 | 
  11 |   test('landing page has terminal button', async ({ page }) => {
  12 |     await page.goto('/');
  13 |     await expect(page.getByRole('link', { name: /Enter Terminal/ })).toBeVisible();
  14 |   });
  15 | 
  16 |   test('engine status visible on landing', async ({ page }) => {
  17 |     await page.goto('/');
  18 |     await expect(page.getByText(/Engine online/i)).toBeVisible();
  19 |   });
  20 | 
  21 |   test('enter terminal navigates to dashboard', async ({ page }) => {
  22 |     await page.goto('/');
  23 |     await page.getByRole('link', { name: /Enter Terminal/ }).click();
  24 |     await expect(page).toHaveURL(/\/dashboard/);
  25 |     await expect(page.locator('.app-shell')).toBeVisible();
  26 |   });
  27 | 
  28 |   test('marketplace link on landing', async ({ page }) => {
  29 |     await page.goto('/');
  30 |     await page.getByRole('link', { name: /Marketplace/i }).first().click();
  31 |     await expect(page).toHaveURL(/\/dashboard\/marketplace/);
  32 |   });
  33 | });
  34 | 
```