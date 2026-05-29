# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: full-flow.spec.ts >> Full User Flow >> complete navigation flow
- Location: tests/e2e/full-flow.spec.ts:5:7

# Error details

```
Error: expect(page).toHaveURL(expected) failed

Expected pattern: /trading/
Received string:  "http://127.0.0.1:3000/dashboard"
Timeout: 15000ms

Call log:
  - Expect "toHaveURL" with timeout 15000ms
    15 × unexpected value "http://127.0.0.1:3000/dashboard"
    - waiting for" http://127.0.0.1:3000/dashboard" navigation to finish...
    - navigated to "http://127.0.0.1:3000/dashboard"
    18 × unexpected value "http://127.0.0.1:3000/dashboard"

```

```yaml
- 'heading "Application error: a client-side exception has occurred while loading 127.0.0.1 (see the browser console for more information)." [level=2]'
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | import { gotoTerminal, clickSidebar } from './helpers';
  3  | 
  4  | test.describe('Full User Flow', () => {
  5  |   test('complete navigation flow', async ({ page }) => {
  6  |     await page.goto('/');
  7  |     await expect(page).toHaveTitle(/APEX/);
  8  | 
  9  |     await page.getByRole('link', { name: /Enter Terminal/ }).click();
  10 |     await expect(page).toHaveURL(/dashboard/);
  11 |     await expect(page.locator('.app-shell')).toBeVisible();
  12 |     await page.waitForSelector('html[data-terminal-hydrated="true"]', { timeout: 30_000 });
  13 | 
  14 |     await clickSidebar(page, 'Trading');
> 15 |     await expect(page).toHaveURL(/trading/, { timeout: 15_000 });
     |                        ^ Error: expect(page).toHaveURL(expected) failed
  16 | 
  17 |     await clickSidebar(page, 'Positions');
  18 |     await expect(page).toHaveURL(/positions/);
  19 | 
  20 |     await clickSidebar(page, 'Marketplace');
  21 |     await expect(page).toHaveURL(/marketplace/);
  22 | 
  23 |     await clickSidebar(page, 'Autopilot');
  24 |     await expect(page).toHaveURL(/autopilot/);
  25 | 
  26 |     await clickSidebar(page, 'Overview');
  27 |     await expect(page).toHaveURL(/\/dashboard\/?$/);
  28 |   });
  29 | 
  30 |   test('responsive layout', async ({ page }) => {
  31 |     await page.setViewportSize({ width: 375, height: 812 });
  32 |     await gotoTerminal(page, '/dashboard');
  33 | 
  34 |     await page.setViewportSize({ width: 1920, height: 1080 });
  35 |     await gotoTerminal(page, '/dashboard');
  36 |   });
  37 | 
  38 |   test('no critical page errors', async ({ page }) => {
  39 |     const errors: string[] = [];
  40 |     page.on('pageerror', (error) => errors.push(error.message));
  41 | 
  42 |     await gotoTerminal(page, '/dashboard');
  43 |     await gotoTerminal(page, '/dashboard/trading');
  44 |     await gotoTerminal(page, '/dashboard/marketplace');
  45 | 
  46 |     const critical = errors.filter(
  47 |       (e) => !e.includes('favicon') && !e.includes('ResizeObserver')
  48 |     );
  49 |     expect(critical.length).toBe(0);
  50 |   });
  51 | });
  52 | 
```