# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: positions.spec.ts >> Positions Page >> positions has sidebar
- Location: tests/e2e/positions.spec.ts:11:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('.app-shell')
Expected: visible
Timeout: 20000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 20000ms
  - waiting for locator('.app-shell')
    3 × waiting for" http://127.0.0.1:3000/dashboard/positions" navigation to finish...
      - navigated to "http://127.0.0.1:3000/dashboard/positions"

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
  - paragraph: "Cannot find module './611.js' Require stack: - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/.next/server/webpack-runtime.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/.next/server/app/dashboard/positions/page.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/require.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/load-components.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/build/utils.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/build/swc/options.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/build/swc/index.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/build/next-config-ts/transpile-config.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/config.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/next.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/lib/start-server.js"
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
  1  | import { Page, expect } from '@playwright/test';
  2  | 
  3  | const APEX_HEALTH = process.env.APEX_HEALTH_URL || 'http://127.0.0.1:8000/health';
  4  | 
  5  | /** Ensure APEX responds before UI tests (Phase 1). */
  6  | export async function waitForApexHealth(timeoutMs = 30_000) {
  7  |   const deadline = Date.now() + timeoutMs;
  8  |   while (Date.now() < deadline) {
  9  |     try {
  10 |       const res = await fetch(APEX_HEALTH);
  11 |       if (res.ok) {
  12 |         const body = await res.json();
  13 |         if (body && typeof body === 'object') return;
  14 |       }
  15 |     } catch {
  16 |       /* retry */
  17 |     }
  18 |     await new Promise((r) => setTimeout(r, 1000));
  19 |   }
  20 |   throw new Error(`APEX health check failed: ${APEX_HEALTH}`);
  21 | }
  22 | 
  23 | /** Navigate and wait for terminal shell (avoids networkidle hangs from WS/polling). */
  24 | export async function gotoTerminal(page: Page, path: string) {
  25 |   await waitForApexHealth();
  26 |   await page.goto(path, { waitUntil: 'load', timeout: 45_000 });
> 27 |   await expect(page.locator('.app-shell')).toBeVisible({ timeout: 20_000 });
     |                                            ^ Error: expect(locator).toBeVisible() failed
  28 |   await page.waitForSelector('html[data-terminal-hydrated="true"]', { timeout: 20_000 });
  29 | }
  30 | 
  31 | export async function expectSidebarNav(page: Page) {
  32 |   const sidebar = page.locator('.sidebar');
  33 |   await expect(sidebar.getByRole('link', { name: 'Overview' })).toBeVisible();
  34 |   await expect(sidebar.getByRole('link', { name: 'Trading' })).toBeVisible();
  35 |   await expect(sidebar.getByRole('link', { name: 'Marketplace' })).toBeVisible();
  36 | }
  37 | 
  38 | export async function waitForTerminalHydration(page: Page) {
  39 |   await page.waitForSelector('html[data-terminal-hydrated="true"]', { timeout: 30_000 });
  40 | }
  41 | 
  42 | /** Sidebar hrefs — use attribute selectors so nav badges do not break exact name matching. */
  43 | const SIDEBAR_HREFS: Record<string, string> = {
  44 |   Overview: '/dashboard',
  45 |   Trading: '/dashboard/trading',
  46 |   Positions: '/dashboard/positions',
  47 |   Signals: '/dashboard/opportunities',
  48 |   Autopilot: '/dashboard/autopilot',
  49 |   'Arb Radar': '/dashboard/arb-radar',
  50 |   Risk: '/dashboard/risk-management',
  51 |   'Hive-Mind': '/dashboard/ai-hivemind',
  52 |   Analytics: '/dashboard/analytics',
  53 |   'Live Feed': '/dashboard/live',
  54 |   Marketplace: '/dashboard/marketplace',
  55 |   Kalshi: '/dashboard/kalshi',
  56 |   Polymarket: '/dashboard/polymarket',
  57 |   DeFi: '/dashboard/defi-treasury',
  58 |   Fund: '/dashboard/fund-admin',
  59 |   Settings: '/dashboard/settings',
  60 | };
  61 | 
  62 | export function sidebarLink(page: Page, label: string) {
  63 |   const href = SIDEBAR_HREFS[label];
  64 |   if (href) {
  65 |     return page.locator(`.sidebar a.nav-link[href="${href}"]`);
  66 |   }
  67 |   return page.locator('.sidebar').getByRole('link', { name: label, exact: true });
  68 | }
  69 | 
  70 | export async function clickSidebar(page: Page, label: string) {
  71 |   await waitForTerminalHydration(page);
  72 |   const link = sidebarLink(page, label);
  73 |   await link.scrollIntoViewIfNeeded();
  74 |   await link.click();
  75 | }
  76 | 
```