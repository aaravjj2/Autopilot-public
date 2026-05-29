# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: full-terminal.spec.ts >> Every sidebar tab >> navigate every tab via sidebar clicks
- Location: tests/e2e/full-terminal.spec.ts:33:7

# Error details

```
TimeoutError: page.waitForURL: Timeout 20000ms exceeded.
=========================== logs ===========================
waiting for navigation until "load"
============================================================
```

# Page snapshot

```yaml
- generic [ref=e1]:
  - generic [ref=e6] [cursor=pointer]:
    - button "Open Next.js Dev Tools" [ref=e7]:
      - img [ref=e8]
    - generic [ref=e11]:
      - button "Open issues overlay" [ref=e12]:
        - generic [ref=e13]:
          - generic [ref=e14]: "0"
          - generic [ref=e15]: "1"
        - generic [ref=e16]: Issue
      - button "Collapse issues badge" [ref=e17]:
        - img [ref=e18]
  - alert [ref=e20]
  - generic [ref=e21]:
    - complementary [ref=e22]:
      - generic [ref=e23]:
        - generic [ref=e24]: AX
        - generic [ref=e25]:
          - heading "APEX Terminal" [level=1] [ref=e26]
          - paragraph [ref=e27]: $146,879.44 · Paper
      - navigation [ref=e28]:
        - generic [ref=e29]: Trade
        - link "Overview" [ref=e30] [cursor=pointer]:
          - /url: /dashboard
          - img [ref=e31]
          - text: Overview
        - link "Trading" [ref=e36] [cursor=pointer]:
          - /url: /dashboard/trading
          - img [ref=e37]
          - text: Trading
        - link "Positions" [ref=e40] [cursor=pointer]:
          - /url: /dashboard/positions
          - img [ref=e41]
          - text: Positions
        - link "Signals" [ref=e44] [cursor=pointer]:
          - /url: /dashboard/opportunities
          - img [ref=e45]
          - text: Signals
      - navigation [ref=e49]:
        - generic [ref=e50]: Intel
        - link "Autopilot" [ref=e51] [cursor=pointer]:
          - /url: /dashboard/autopilot
          - img [ref=e52]
          - text: Autopilot
        - link "Arb Radar 288" [ref=e54] [cursor=pointer]:
          - /url: /dashboard/arb-radar
          - img [ref=e55]
          - text: Arb Radar
          - generic [ref=e57]: "288"
        - link "Risk" [ref=e58] [cursor=pointer]:
          - /url: /dashboard/risk-management
          - img [ref=e59]
          - text: Risk
        - link "Hive-Mind" [ref=e61] [cursor=pointer]:
          - /url: /dashboard/ai-hivemind
          - img [ref=e62]
          - text: Hive-Mind
        - link "Analytics" [ref=e72] [cursor=pointer]:
          - /url: /dashboard/analytics
          - img [ref=e73]
          - text: Analytics
        - link "Live Feed" [active] [ref=e76] [cursor=pointer]:
          - /url: /dashboard/live
          - img [ref=e77]
          - text: Live Feed
      - navigation [ref=e83]:
        - generic [ref=e84]: Copy Trading
        - link "Marketplace" [ref=e85] [cursor=pointer]:
          - /url: /dashboard/marketplace
          - img [ref=e86]
          - text: Marketplace
      - navigation [ref=e91]:
        - generic [ref=e92]: Prediction Markets
        - link "Kalshi" [ref=e93] [cursor=pointer]:
          - /url: /dashboard/kalshi
          - img [ref=e94]
          - text: Kalshi
        - link "Polymarket" [ref=e100] [cursor=pointer]:
          - /url: /dashboard/polymarket
          - img [ref=e101]
          - text: Polymarket
        - link "World Cup" [ref=e106] [cursor=pointer]:
          - /url: /dashboard/world-cup
          - img [ref=e107]
          - text: World Cup
      - navigation [ref=e113]:
        - generic [ref=e114]: Ops
        - link "DeFi" [ref=e115] [cursor=pointer]:
          - /url: /dashboard/defi-treasury
          - img [ref=e116]
          - text: DeFi
        - link "Fund" [ref=e118] [cursor=pointer]:
          - /url: /dashboard/fund-admin
          - img [ref=e119]
          - text: Fund
      - navigation [ref=e122]:
        - generic [ref=e123]: System
        - link "Settings" [ref=e124] [cursor=pointer]:
          - /url: /dashboard/settings
          - img [ref=e125]
          - text: Settings
      - generic [ref=e128]:
        - generic [ref=e129]:
          - generic [ref=e130]: API —
          - generic [ref=e131]: WS —
          - generic [ref=e132]: Arb —
        - generic [ref=e133]: WS live
    - banner [ref=e134]:
      - button "⌕ Search symbol, command… ⌘K" [ref=e135] [cursor=pointer]:
        - generic [ref=e136]: ⌕
        - generic [ref=e137]: Search symbol, command…
        - generic [ref=e138]: ⌘K
      - generic [ref=e139]: NYSE · Regular
      - generic [ref=e140]:
        - img [ref=e141]
        - text: Live
      - generic [ref=e145]:
        - textbox "email" [ref=e146]
        - textbox "password" [ref=e147]
        - button "Login" [ref=e148] [cursor=pointer]
        - button "Guest" [ref=e149] [cursor=pointer]
      - button "Alerts" [ref=e150] [cursor=pointer]:
        - img [ref=e151]
      - link "Quick Order" [ref=e154] [cursor=pointer]:
        - /url: /dashboard/trading
    - main [ref=e155]:
      - generic [ref=e157]:
        - heading "Analytics" [level=2] [ref=e158]
        - generic [ref=e159]: Portfolio performance · Arb backtest · ML engine · Signal quality
      - generic [ref=e160]:
        - button "Performance" [ref=e161] [cursor=pointer]
        - button "Arb Backtest" [ref=e162] [cursor=pointer]
        - button "ML Engine" [ref=e163] [cursor=pointer]
        - button "Signals" [ref=e164] [cursor=pointer]
      - generic [ref=e165]:
        - generic [ref=e166]:
          - generic [ref=e167]: Sharpe
          - generic [ref=e168]: —
        - generic [ref=e169]:
          - generic [ref=e170]: Win rate
          - generic [ref=e171]: —
        - generic [ref=e172]:
          - generic [ref=e173]: Max DD
          - generic [ref=e174]: —
        - generic [ref=e175]:
          - generic [ref=e176]: Trades
          - generic [ref=e177]: —
      - generic [ref=e178]:
        - generic [ref=e180]: Equity · 60D
        - table [ref=e183]:
          - row [ref=e184]:
            - cell
            - cell [ref=e185]:
              - link "Charting by TradingView" [ref=e189] [cursor=pointer]:
                - /url: https://www.tradingview.com/?utm_medium=lwc-link&utm_campaign=lwc-chart&utm_source=127.0.0.1/dashboard/analytics
                - img [ref=e190]
            - cell [ref=e194]
          - row [ref=e198]:
            - cell
            - cell [ref=e199]
            - cell [ref=e203]
    - contentinfo [ref=e206]:
      - generic [ref=e207]: "WS: connected"
      - generic [ref=e208]: "API: —"
      - generic [ref=e209]: "Data age: 0s"
      - generic [ref=e210]: "Updated: 12:51:58 AM"
      - generic [ref=e211]: APEX Terminal
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | import { gotoTerminal, clickSidebar, sidebarLink } from './helpers';
  3   | 
  4   | /** All sidebar tabs in TerminalLayout */
  5   | const TABS = [
  6   |   { label: 'Overview', path: '/dashboard', heading: /Command Center/ },
  7   |   { label: 'Trading', path: '/dashboard/trading', heading: /^Trading$/ },
  8   |   { label: 'Positions', path: '/dashboard/positions', heading: /^Positions$/ },
  9   |   { label: 'Signals', path: '/dashboard/opportunities', heading: /Opportunity Signals/ },
  10  |   { label: 'Autopilot', path: '/dashboard/autopilot', heading: /Autopilot Pipeline/ },
  11  |   { label: 'Arb Radar', path: '/dashboard/arb-radar', heading: /^Arb Radar$/ },
  12  |   { label: 'Risk', path: '/dashboard/risk-management', heading: /^Risk Management$/ },
  13  |   { label: 'Analytics', path: '/dashboard/analytics', heading: /^Analytics$/ },
  14  |   { label: 'Live Feed', path: '/dashboard/live', heading: /^Live Feed$/ },
  15  |   { label: 'Marketplace', path: '/dashboard/marketplace', heading: /Copy Trading Marketplace/ },
  16  |   { label: 'Kalshi', path: '/dashboard/kalshi', heading: /Kalshi Book/ },
  17  |   { label: 'Polymarket', path: '/dashboard/polymarket', heading: /Polymarket Book/ },
  18  |   { label: 'DeFi', path: '/dashboard/defi-treasury', heading: /DeFi Treasury/ },
  19  |   { label: 'Fund', path: '/dashboard/fund-admin', heading: /Fund Admin/ },
  20  |   { label: 'Hive-Mind', path: '/dashboard/ai-hivemind', heading: /AI Hive-Mind/ },
  21  |   { label: 'Settings', path: '/dashboard/settings', heading: /Settings/ },
  22  | ] as const;
  23  | 
  24  | test.describe('Every sidebar tab', () => {
  25  |   for (const tab of TABS) {
  26  |     test(`${tab.label} loads via direct URL`, async ({ page }) => {
  27  |       await gotoTerminal(page, tab.path);
  28  |       await expect(page.getByRole('heading', { name: tab.heading })).toBeVisible();
  29  |       await expect(sidebarLink(page, tab.label)).toHaveClass(/active/);
  30  |     });
  31  |   }
  32  | 
  33  |   test('navigate every tab via sidebar clicks', async ({ page }) => {
  34  |     test.setTimeout(180_000);
  35  |     await gotoTerminal(page, '/dashboard');
  36  |     for (const tab of TABS) {
  37  |       const link = sidebarLink(page, tab.label);
  38  |       await link.scrollIntoViewIfNeeded();
  39  |       await Promise.all([
> 40  |         page.waitForURL(new RegExp(tab.path.replace('/', '\\/') + '(\\/)?$'), { timeout: 20_000 }),
      |              ^ TimeoutError: page.waitForURL: Timeout 20000ms exceeded.
  41  |         link.click(),
  42  |       ]);
  43  |       await expect(page.getByRole('heading', { name: tab.heading })).toBeVisible();
  44  |     }
  45  |   });
  46  | });
  47  | 
  48  | test.describe('Overview features', () => {
  49  |   test('Refresh Cache button', async ({ page }) => {
  50  |     test.setTimeout(120_000);
  51  |     await gotoTerminal(page, '/dashboard');
  52  |     const btn = page.getByRole('button', { name: /Refresh Cache/i });
  53  |     await expect(btn).toBeVisible();
  54  |     await btn.click();
  55  |     await expect(page.getByRole('heading', { name: /Command Center/i })).toBeVisible();
  56  |     await expect(btn).toBeEnabled({ timeout: 90_000 });
  57  |   });
  58  | 
  59  |   test('View all signals link', async ({ page }) => {
  60  |     await gotoTerminal(page, '/dashboard');
  61  |     await page.getByRole('link', { name: /View all/i }).click();
  62  |     await expect(page).toHaveURL(/opportunities/);
  63  |   });
  64  | 
  65  |   test('order ticket in right panel', async ({ page }) => {
  66  |     await gotoTerminal(page, '/dashboard');
  67  |     await expect(page.locator('.right-panel')).toBeVisible();
  68  |     await expect(page.getByText('Order Ticket')).toBeVisible();
  69  |     await expect(page.getByRole('button', { name: /Submit Paper Order/i })).toBeVisible();
  70  |   });
  71  | 
  72  |   test('command palette opens and navigates', async ({ page }) => {
  73  |     await gotoTerminal(page, '/dashboard');
  74  |     await page.getByTestId('cmd-trigger').click();
  75  |     await expect(page.getByTestId('cmd-dialog')).toBeVisible({ timeout: 10_000 });
  76  |     await page.getByTestId('cmd-input').fill('settings');
  77  |     await page.locator('.cmd-item').filter({ hasText: 'Settings' }).click();
  78  |     await expect(page).toHaveURL(/settings/);
  79  |   });
  80  | 
  81  |   test('Quick Order topbar navigates to trading', async ({ page }) => {
  82  |     await gotoTerminal(page, '/dashboard');
  83  |     await page.getByTestId('quick-order').click();
  84  |     await expect(page).toHaveURL(/trading/, { timeout: 15_000 });
  85  |   });
  86  | });
  87  | 
  88  | test.describe('Trading features', () => {
  89  |   test('timeframe tabs switch', async ({ page }) => {
  90  |     await gotoTerminal(page, '/dashboard/trading');
  91  |     await page.getByTestId('tf-1h').click();
  92  |     await expect(page.getByTestId('chart-timeframe')).toHaveText('1h', { timeout: 5_000 });
  93  |   });
  94  | 
  95  |   test('options Calls/Puts tabs', async ({ page }) => {
  96  |     await gotoTerminal(page, '/dashboard/trading');
  97  |     const putsTab = page.getByRole('button', { name: 'Puts', exact: true });
  98  |     if (await putsTab.isVisible().catch(() => false)) {
  99  |       await putsTab.click();
  100 |       await expect(putsTab).toHaveClass(/active/);
  101 |     }
  102 |   });
  103 | 
  104 |   test('symbol selector present', async ({ page }) => {
  105 |     await gotoTerminal(page, '/dashboard/trading');
  106 |     await expect(page.locator('select').first()).toBeVisible();
  107 |   });
  108 | });
  109 | 
  110 | test.describe('Positions features', () => {
  111 |   test('Open and Closed tabs', async ({ page }) => {
  112 |     await gotoTerminal(page, '/dashboard/positions');
  113 |     const closedTab = page.getByRole('button', { name: 'Closed', exact: true }).first();
  114 |     const openTab = page.getByRole('button', { name: 'Open', exact: true }).first();
  115 |     await closedTab.click();
  116 |     await expect(closedTab).toHaveClass(/active/);
  117 |     await openTab.click();
  118 |     await expect(page.getByRole('columnheader', { name: 'Symbol' })).toBeVisible();
  119 |   });
  120 | });
  121 | 
  122 | test.describe('Signals features', () => {
  123 |   test('symbol filter input', async ({ page }) => {
  124 |     await gotoTerminal(page, '/dashboard/opportunities');
  125 |     const filter = page.getByPlaceholder(/Filter symbol/i);
  126 |     await filter.fill('A');
  127 |     await expect(filter).toHaveValue('A');
  128 |   });
  129 | 
  130 |   test('min conviction filter', async ({ page }) => {
  131 |     await gotoTerminal(page, '/dashboard/opportunities');
  132 |     const conv = page.locator('input[type="number"]').first();
  133 |     await conv.fill('5');
  134 |     await expect(conv).toHaveValue('5');
  135 |   });
  136 | });
  137 | 
  138 | test.describe('Analytics features', () => {
  139 |   test('Performance / Arb Backtest / Signals tabs', async ({ page }) => {
  140 |     await gotoTerminal(page, '/dashboard/analytics');
```