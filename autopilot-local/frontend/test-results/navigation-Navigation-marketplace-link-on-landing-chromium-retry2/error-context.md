# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: navigation.spec.ts >> Navigation >> marketplace link on landing
- Location: tests/e2e/navigation.spec.ts:28:7

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
  - waiting for getByRole('link', { name: /Marketplace/i }).first()

```

# Page snapshot

```yaml
- generic:
  - generic [active]:
    - generic [ref=e3]:
      - generic [ref=e4]:
        - generic [ref=e5]:
          - navigation [ref=e6]:
            - button "previous" [disabled] [ref=e7]:
              - img "previous" [ref=e8]
            - generic [ref=e10]:
              - generic [ref=e11]: 1/
              - text: "1"
            - button "next" [disabled] [ref=e12]:
              - img "next" [ref=e13]
          - img
        - generic [ref=e15]:
          - link "Next.js 15.5.18 (outdated) Webpack" [ref=e16] [cursor=pointer]:
            - /url: https://nextjs.org/docs/messages/version-staleness
            - img [ref=e17]
            - generic "An outdated version detected (latest is 16.2.6), upgrade is highly recommended!" [ref=e19]: Next.js 15.5.18 (outdated)
            - generic [ref=e20]: Webpack
          - img
      - generic [ref=e21]:
        - dialog "Runtime Error" [ref=e22]:
          - generic [ref=e25]:
            - generic [ref=e26]:
              - generic [ref=e27]:
                - generic [ref=e29]: Runtime Error
                - generic [ref=e30]:
                  - button "Copy Error Info" [ref=e31] [cursor=pointer]:
                    - img [ref=e32]
                  - button "No related documentation found" [disabled] [ref=e34]:
                    - img [ref=e35]
                  - link "Learn more about enabling Node.js inspector for server code with Chrome DevTools" [ref=e37] [cursor=pointer]:
                    - /url: https://nextjs.org/docs/app/building-your-application/configuring/debugging#server-side-code
                    - img [ref=e38]
              - generic [ref=e46]:
                - paragraph [ref=e47]: "Cannot find module './611.js' Require stack: - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/.next/server/webpack-runtime.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/.next/server/app/dashboard/marketplace/page.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/require.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/load-components.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/build/utils.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/build/swc/options.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/build/swc/index.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/build/next-config-ts/transpile-config.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/config.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/next.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/lib/start-server.js"
                - button "Show More" [ref=e49] [cursor=pointer]
            - generic [ref=e51]:
              - generic [ref=e52]:
                - paragraph [ref=e53]:
                  - text: Call Stack
                  - generic [ref=e54]: "48"
                - button "Show 46 ignore-listed frame(s)" [ref=e55] [cursor=pointer]:
                  - text: Show 46 ignore-listed frame(s)
                  - img [ref=e56]
              - generic [ref=e58]:
                - generic [ref=e59]: <unknown>
                - text: .next/server/pages/_document.js (1:325)
              - generic [ref=e60]:
                - generic [ref=e61]: Object.<anonymous>
                - text: .next/server/pages/_document.js (1:371)
          - generic [ref=e62]:
            - generic [ref=e63]: "1"
            - generic [ref=e64]: "2"
        - contentinfo [ref=e65]:
          - region "Error feedback" [ref=e66]:
            - paragraph [ref=e67]:
              - link "Was this helpful?" [ref=e68] [cursor=pointer]:
                - /url: https://nextjs.org/telemetry#error-feedback
            - button "Mark as helpful" [ref=e69] [cursor=pointer]:
              - img [ref=e70]
            - button "Mark as not helpful" [ref=e73] [cursor=pointer]:
              - img [ref=e74]
    - generic [ref=e80] [cursor=pointer]:
      - button "Open Next.js Dev Tools" [ref=e81]:
        - img [ref=e82]
      - generic [ref=e85]:
        - button "Open issues overlay" [ref=e86]:
          - generic [ref=e87]:
            - generic [ref=e88]: "0"
            - generic [ref=e89]: "1"
          - generic [ref=e90]: Issue
        - button "Collapse issues badge" [ref=e91]:
          - img [ref=e92]
  - alert [ref=e94]
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
  23 |     await page.getByRole('link', { name: /Enter Terminal/ }).click();
  24 |     await expect(page).toHaveURL(/\/dashboard/);
  25 |     await expect(page.locator('.app-shell')).toBeVisible();
  26 |   });
  27 | 
  28 |   test('marketplace link on landing', async ({ page }) => {
  29 |     await page.goto('/');
> 30 |     await page.getByRole('link', { name: /Marketplace/i }).first().click();
     |                                                                    ^ Error: locator.click: Test timeout of 30000ms exceeded.
  31 |     await expect(page).toHaveURL(/\/dashboard\/marketplace/);
  32 |   });
  33 | });
  34 | 
```