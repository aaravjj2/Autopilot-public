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
    4 × unexpected value ""
    - waiting for" http://127.0.0.1:3000/" navigation to finish...
    - navigated to "http://127.0.0.1:3000/"
    8 × unexpected value ""

```

```yaml
- navigation:
  - button "previous" [disabled]:
    - img "previous"
  - text: 1/1
  - button "next" [disabled]:
    - img "next"
- img
- link "Next.js 15.5.18 (outdated) Webpack":
  - /url: https://nextjs.org/docs/messages/version-staleness
  - img
  - text: Next.js 15.5.18 (outdated) Webpack
- img
- dialog "Runtime Error":
  - text: Runtime Error
  - button "Copy Error Info":
    - img
  - button "No related documentation found" [disabled]:
    - img
  - link "Learn more about enabling Node.js inspector for server code with Chrome DevTools":
    - /url: https://nextjs.org/docs/app/building-your-application/configuring/debugging#server-side-code
    - img
  - paragraph: "Cannot find module './611.js' Require stack: - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/.next/server/webpack-runtime.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/.next/server/app/dashboard/risk-management/page.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/require.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/load-components.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/build/utils.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/build/swc/options.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/build/swc/index.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/build/next-config-ts/transpile-config.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/config.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/next.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/lib/start-server.js"
  - button "Show More"
  - paragraph: Call Stack 48
  - button "Show 46 ignore-listed frame(s)":
    - text: Show 46 ignore-listed frame(s)
    - img
  - text: <unknown> .next/server/pages/_document.js (1:325) Object.<anonymous> .next/server/pages/_document.js (1:371)
- contentinfo:
  - region "Error feedback":
    - paragraph:
      - link "Was this helpful?":
        - /url: https://nextjs.org/telemetry#error-feedback
    - button "Mark as helpful"
    - button "Mark as not helpful"
- button "Open Next.js Dev Tools":
  - img
- button "Open issues overlay": 1 Issue
- button "Collapse issues badge":
  - img
- alert
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