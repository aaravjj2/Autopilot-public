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
    28 × unexpected value "http://127.0.0.1:3000/dashboard"
    - waiting for" http://127.0.0.1:3000/dashboard" navigation to finish...
    - navigated to "http://127.0.0.1:3000/dashboard"
    3 × unexpected value "http://127.0.0.1:3000/dashboard"

```

```yaml
- complementary:
  - text: AX
  - heading "APEX Terminal" [level=1]
  - paragraph: $146,873.71 · Paper
  - navigation:
    - text: Trade
    - link "Overview":
      - /url: /dashboard
      - img
      - text: Overview
    - link "Trading":
      - /url: /dashboard/trading
      - img
      - text: Trading
    - link "Positions":
      - /url: /dashboard/positions
      - img
      - text: Positions
    - link "Signals":
      - /url: /dashboard/opportunities
      - img
      - text: Signals
  - navigation:
    - text: Intel
    - link "Autopilot":
      - /url: /dashboard/autopilot
      - img
      - text: Autopilot
    - link "Arb Radar":
      - /url: /dashboard/arb-radar
      - img
      - text: Arb Radar
    - link "Risk":
      - /url: /dashboard/risk-management
      - img
      - text: Risk
    - link "Hive-Mind":
      - /url: /dashboard/ai-hivemind
      - img
      - text: Hive-Mind
    - link "Analytics":
      - /url: /dashboard/analytics
      - img
      - text: Analytics
    - link "Live Feed":
      - /url: /dashboard/live
      - img
      - text: Live Feed
  - navigation:
    - text: Copy Trading
    - link "Marketplace":
      - /url: /dashboard/marketplace
      - img
      - text: Marketplace
  - navigation:
    - text: Prediction Markets
    - link "Kalshi":
      - /url: /dashboard/kalshi
      - img
      - text: Kalshi
    - link "Polymarket":
      - /url: /dashboard/polymarket
      - img
      - text: Polymarket
    - link "World Cup":
      - /url: /dashboard/world-cup
      - img
      - text: World Cup
  - navigation:
    - text: Ops
    - link "DeFi":
      - /url: /dashboard/defi-treasury
      - img
      - text: DeFi
    - link "Fund":
      - /url: /dashboard/fund-admin
      - img
      - text: Fund
  - navigation:
    - text: System
    - link "Settings":
      - /url: /dashboard/settings
      - img
      - text: Settings
  - text: API —WS —Arb — WS live
- banner:
  - button "⌕ Search symbol, command… ⌘K"
  - text: NYSE · Regular
  - img
  - text: Live
  - textbox "email"
  - textbox "password"
  - button "Login"
  - button "Guest"
  - button "Alerts":
    - img
  - link "Quick Order":
    - /url: /dashboard/trading
- main:
  - heading "Command Center" [level=2]
  - text: Real-time portfolio · Engine RUNNING · 12:23:13 AM
  - button "Refresh Cache"
  - text: LIVE Portfolio $146,873.71 0.01% today Buying Power $585,001.00 Cash $144,818.18 Positions 1 1 profitable Signals 0 0 high conviction Arb Active 0 — Real-time P&L Unrealized $39.27 Daily P&L $9.72 Position value $2,055.53 Cash $144,818.18 Equity Curve · 30D Risk snapshot 0.0% Daily 1 Open Watchlist
  - button "+ Add"
  - table:
    - rowgroup:
      - row "Symbol Side P&L Conv":
        - columnheader "Symbol"
        - columnheader "Side"
        - columnheader "P&L"
        - columnheader "Conv"
    - rowgroup:
      - row "MU long $39.27 —":
        - cell "MU"
        - cell "long"
        - cell "$39.27"
        - cell "—"
  - text: Agent Pipeline
  - strong: L0
  - text: Ingest
  - strong: L1
  - text: Brain
  - strong: L2
  - text: Agents
  - strong: L3
  - text: Exec
  - strong: L4
  - text: Obs Top Signals
  - link "View all":
    - /url: /dashboard/opportunities
  - paragraph: No opportunities yet
  - text: Recent Activity
  - img
  - text: ORDER_SUBMITTED · PM-EVT-us-x-iran-permanent-peace-deal-by-june-7-2026 12:22:58 AM
  - img
  - text: ORDER_FILLED · PM-EVT-us-iran-nuclear-deal-by-may-31-974 12:22:58 AM
  - img
  - text: ORDER_SUBMITTED · PM-EVT-us-iran-nuclear-deal-by-may-31-974 12:22:48 AM
  - img
  - text: ORDER_FILLED · PM-EVT-us-x-iran-permanent-peace-deal-by-may-31-2026-333-871-241-192-799-449-125 12:22:48 AM
  - img
  - text: ORDER_SUBMITTED · PM-EVT-us-x-iran-permanent-peace-deal-by-may-31-2026-333-871-241-192-799-449-125 12:22:38 AM
  - img
  - text: SYSTEM_ALERT 12:22:38 AM
  - img
  - text: PROPOSAL_CREATED · PM-EVT-us-announces-new-iran-agreementceasefire-extension-by-may-31-665-831-238 12:22:38 AM
  - img
  - text: PROPOSAL_CREATED · PM-EVT-us-x-iran-permanent-peace-deal-by-june-7-2026 12:22:38 AM
- complementary:
  - text: Order Ticket Symbol
  - textbox: MU
  - button "Buy"
  - button "Sell"
  - text: Qty
  - spinbutton: "10"
  - text: Type
  - combobox:
    - option "Market" [selected]
    - option "Limit"
  - button "Submit Paper Order"
  - text: Alerts
  - list:
    - listitem: Engine cache auto-refresh 30s
- contentinfo: "WS: connected API: — Data age: 0s Updated: 12:23:13 AM APEX Terminal"
- alert
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