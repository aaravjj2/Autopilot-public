# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: full-flow.spec.ts >> Full User Flow >> no critical page errors
- Location: tests/e2e/full-flow.spec.ts:38:7

# Error details

```
Error: expect(received).toBe(expected) // Object.is equality

Expected: 0
Received: 1
```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e2]:
    - complementary [ref=e3]:
      - generic [ref=e4]:
        - generic [ref=e5]: AX
        - generic [ref=e6]:
          - heading "APEX Terminal" [level=1] [ref=e7]
          - paragraph [ref=e8]: $146,881.16 · Paper
      - navigation [ref=e9]:
        - generic [ref=e10]: Trade
        - link "Overview" [ref=e11] [cursor=pointer]:
          - /url: /dashboard
          - img [ref=e12]
          - text: Overview
        - link "Trading" [ref=e17] [cursor=pointer]:
          - /url: /dashboard/trading
          - img [ref=e18]
          - text: Trading
        - link "Positions" [ref=e21] [cursor=pointer]:
          - /url: /dashboard/positions
          - img [ref=e22]
          - text: Positions
        - link "Signals" [ref=e25] [cursor=pointer]:
          - /url: /dashboard/opportunities
          - img [ref=e26]
          - text: Signals
      - navigation [ref=e30]:
        - generic [ref=e31]: Intel
        - link "Autopilot" [ref=e32] [cursor=pointer]:
          - /url: /dashboard/autopilot
          - img [ref=e33]
          - text: Autopilot
        - link "Arb Radar" [ref=e35] [cursor=pointer]:
          - /url: /dashboard/arb-radar
          - img [ref=e36]
          - text: Arb Radar
        - link "Risk" [ref=e38] [cursor=pointer]:
          - /url: /dashboard/risk-management
          - img [ref=e39]
          - text: Risk
        - link "Hive-Mind" [ref=e41] [cursor=pointer]:
          - /url: /dashboard/ai-hivemind
          - img [ref=e42]
          - text: Hive-Mind
        - link "Analytics" [ref=e52] [cursor=pointer]:
          - /url: /dashboard/analytics
          - img [ref=e53]
          - text: Analytics
        - link "Live Feed" [ref=e56] [cursor=pointer]:
          - /url: /dashboard/live
          - img [ref=e57]
          - text: Live Feed
      - navigation [ref=e63]:
        - generic [ref=e64]: Copy Trading
        - link "Marketplace" [ref=e65] [cursor=pointer]:
          - /url: /dashboard/marketplace
          - img [ref=e66]
          - text: Marketplace
      - navigation [ref=e71]:
        - generic [ref=e72]: Prediction Markets
        - link "Kalshi" [ref=e73] [cursor=pointer]:
          - /url: /dashboard/kalshi
          - img [ref=e74]
          - text: Kalshi
        - link "Polymarket" [ref=e80] [cursor=pointer]:
          - /url: /dashboard/polymarket
          - img [ref=e81]
          - text: Polymarket
        - link "World Cup" [ref=e86] [cursor=pointer]:
          - /url: /dashboard/world-cup
          - img [ref=e87]
          - text: World Cup
      - navigation [ref=e93]:
        - generic [ref=e94]: Ops
        - link "DeFi" [ref=e95] [cursor=pointer]:
          - /url: /dashboard/defi-treasury
          - img [ref=e96]
          - text: DeFi
        - link "Fund" [ref=e98] [cursor=pointer]:
          - /url: /dashboard/fund-admin
          - img [ref=e99]
          - text: Fund
      - navigation [ref=e102]:
        - generic [ref=e103]: System
        - link "Settings" [ref=e104] [cursor=pointer]:
          - /url: /dashboard/settings
          - img [ref=e105]
          - text: Settings
      - generic [ref=e108]:
        - generic [ref=e109]:
          - generic [ref=e110]: API —
          - generic [ref=e111]: WS —
          - generic [ref=e112]: Arb —
        - generic [ref=e113]: WS live
    - banner [ref=e114]:
      - button "⌕ Search symbol, command… ⌘K" [ref=e115] [cursor=pointer]:
        - generic [ref=e116]: ⌕
        - generic [ref=e117]: Search symbol, command…
        - generic [ref=e118]: ⌘K
      - generic [ref=e119]: NYSE · Regular
      - generic [ref=e120]:
        - img [ref=e121]
        - text: Live
      - generic [ref=e125]:
        - textbox "email" [ref=e126]
        - textbox "password" [ref=e127]
        - button "Login" [ref=e128] [cursor=pointer]
        - button "Guest" [ref=e129] [cursor=pointer]
      - button "Alerts" [ref=e130] [cursor=pointer]:
        - img [ref=e131]
      - link "Quick Order" [ref=e134] [cursor=pointer]:
        - /url: /dashboard/trading
    - main [ref=e135]:
      - generic [ref=e136]:
        - generic [ref=e137]:
          - heading "Copy Trading Marketplace" [level=2] [ref=e138]
          - generic [ref=e139]: Follow Alpaca pilot portfolios · paper mirror trades (equities only)
        - button "Refresh all" [ref=e141] [cursor=pointer]
      - generic [ref=e142]:
        - generic [ref=e143]:
          - generic [ref=e144]:
            - button "1W" [ref=e145] [cursor=pointer]
            - button "1M" [ref=e146] [cursor=pointer]
            - button "3M" [ref=e147] [cursor=pointer]
            - button "6M" [ref=e148] [cursor=pointer]
            - button "1Y" [ref=e149] [cursor=pointer]
          - generic [ref=e150]:
            - button "return" [ref=e151] [cursor=pointer]
            - button "name" [ref=e152] [cursor=pointer]
            - button "newest" [ref=e153] [cursor=pointer]
        - paragraph [ref=e154]: Loading portfolios…
    - contentinfo [ref=e155]:
      - generic [ref=e156]: "WS: connected"
      - generic [ref=e157]: "API: —"
      - generic [ref=e158]: "Data age: 0s"
      - generic [ref=e159]: "Updated: 12:48:13 AM"
      - generic [ref=e160]: APEX Terminal
  - button "Open Next.js Dev Tools" [ref=e166] [cursor=pointer]:
    - img [ref=e167]
  - alert [ref=e170]
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
  15 |     await expect(page).toHaveURL(/trading/, { timeout: 15_000 });
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
> 49 |     expect(critical.length).toBe(0);
     |                             ^ Error: expect(received).toBe(expected) // Object.is equality
  50 |   });
  51 | });
  52 | 
```