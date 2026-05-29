# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: positions.spec.ts >> Positions Page >> positions has open/closed tabs
- Location: tests/e2e/positions.spec.ts:16:7

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
    8 × waiting for" http://127.0.0.1:3000/dashboard/positions" navigation to finish...
      - navigated to "http://127.0.0.1:3000/dashboard/positions"

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
                - paragraph [ref=e47]: "Cannot find module './611.js' Require stack: - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/.next/server/webpack-runtime.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/.next/server/app/dashboard/positions/page.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/require.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/load-components.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/build/utils.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/build/swc/options.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/build/swc/index.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/build/next-config-ts/transpile-config.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/config.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/next.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/lib/start-server.js"
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