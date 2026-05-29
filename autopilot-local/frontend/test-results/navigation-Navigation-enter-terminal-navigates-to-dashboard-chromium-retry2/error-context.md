# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: navigation.spec.ts >> Navigation >> enter terminal navigates to dashboard
- Location: tests/e2e/navigation.spec.ts:21:7

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
  - waiting for getByRole('link', { name: /Enter Terminal/ })
    - waiting for navigation to finish...
    6 × navigated to "http://127.0.0.1:3000/"
      - waiting for" http://127.0.0.1:3000/" navigation to finish...
    - navigated to "http://127.0.0.1:3000/"

```

# Page snapshot

```yaml
- generic [active]:
  - generic [ref=e5] [cursor=pointer]:
    - button "Open Next.js Dev Tools" [ref=e6]:
      - img [ref=e7]
    - generic [ref=e10]:
      - button "Open issues overlay" [ref=e11]:
        - generic [ref=e12]:
          - generic [ref=e13]: "0"
          - generic [ref=e14]: "1"
        - generic [ref=e15]: Issue
      - button "Collapse issues badge" [ref=e16]:
        - img [ref=e17]
  - alert [ref=e19]
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | import { gotoTerminal } from './helpers';
  3  | 
  4  | test.describe('Navigation', () => {
  5  |   test('landing page loads', async ({ page }) => {
  6  |     await page.goto('/');
  7  |     await expect(page).toHaveTitle(/APEX/);
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
> 23 |     await page.getByRole('link', { name: /Enter Terminal/ }).click();
     |                                                              ^ Error: locator.click: Test timeout of 30000ms exceeded.
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