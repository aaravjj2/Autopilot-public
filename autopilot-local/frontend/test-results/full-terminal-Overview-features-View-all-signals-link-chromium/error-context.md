# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: full-terminal.spec.ts >> Overview features >> View all signals link
- Location: tests/e2e/full-terminal.spec.ts:59:7

# Error details

```
Error: expect(page).toHaveURL(expected) failed

Expected pattern: /opportunities/
Received string:  "http://127.0.0.1:3000/dashboard"
Timeout: 5000ms

Call log:
  - Expect "toHaveURL" with timeout 5000ms
    14 × unexpected value "http://127.0.0.1:3000/dashboard"

```

```yaml
- complementary:
  - text: AX
  - heading "APEX Terminal" [level=1]
  - paragraph: $146,882.24 · Paper
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
    - link "Arb Radar 286":
      - /url: /dashboard/arb-radar
      - img
      - text: Arb Radar 286
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
  - text: Real-time portfolio · Engine RUNNING · 12:40:48 AM
  - button "Refresh Cache"
  - text: LIVE Portfolio $146,882.24 0.01% today Buying Power $585,001.00 Cash $144,818.18 Positions 1 1 profitable Signals 0 0 high conviction Arb Active 286 50.00% win rate Real-time P&L Unrealized $47.80 Daily P&L $18.25 Position value $2,064.06 Cash $144,818.18 Prediction Market Brain
  - link "Arb Radar →":
    - /url: /dashboard/arb-radar
  - paragraph: "Arb strategy: buy Kalshi YES + Polymarket NO when net_edge ≥ 2% after Kalshi 7% fee. All execution paths are paper-only."
  - text: Kalshi ok 25 cached pairs Polymarket ok 25 cached pairs Arb cache 25 pairs · top 5.0%
  - table:
    - rowgroup:
      - row "Ticker Edge Settle":
        - columnheader "Ticker"
        - columnheader "Edge"
        - columnheader "Settle"
    - rowgroup:
      - row "KX8 5.0% 85%":
        - cell "KX8"
        - cell "5.0%"
        - cell "85%"
      - row "KX6 5.0% 85%":
        - cell "KX6"
        - cell "5.0%"
        - cell "85%"
      - row "KX4 5.0% 85%":
        - cell "KX4"
        - cell "5.0%"
        - cell "85%"
      - row "KX2 5.0% 85%":
        - cell "KX2"
        - cell "5.0%"
        - cell "85%"
      - row "KX0 5.0% 85%":
        - cell "KX0"
        - cell "5.0%"
        - cell "85%"
  - text: Equity Curve · 30D
  - table:
    - row:
      - cell
      - cell:
        - link "Charting by TradingView":
          - /url: https://www.tradingview.com/?utm_medium=lwc-link&utm_campaign=lwc-chart&utm_source=127.0.0.1/dashboard
          - img
      - cell
    - row:
      - cell
      - cell
      - cell
  - text: Risk snapshot 0.0% Daily 1 Open Watchlist
  - button "+ Add"
  - table:
    - rowgroup:
      - row "Symbol Side P&L Conv":
        - columnheader "Symbol"
        - columnheader "Side"
        - columnheader "P&L"
        - columnheader "Conv"
    - rowgroup:
      - row "MU long $47.80 —":
        - cell "MU"
        - cell "long"
        - cell "$47.80"
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
  - text: ORDER_SUBMITTED · PM-EVT-us-x-iran-permanent-peace-deal-by-june-7-2026 12:40:40 AM
  - img
  - text: ORDER_FILLED · PM-EVT-us-iran-nuclear-deal-by-may-31-974 12:40:40 AM
  - img
  - text: SYSTEM_ALERT 12:40:33 AM
  - img
  - text: SYSTEM_ALERT 12:40:33 AM
  - img
  - text: ORDER_FILLED · PM-EVT-us-announces-new-iran-agreementceasefire-extension-by-may-31-665-831-238 12:40:33 AM
  - img
  - text: ORDER_SUBMITTED · PM-EVT-us-iran-nuclear-deal-by-may-31-974 12:40:30 AM
  - img
  - text: ORDER_FILLED · PM-EVT-us-x-iran-permanent-peace-deal-by-may-31-2026-333-871-241-192-799-449-125 12:40:30 AM
  - img
  - text: ORDER_SUBMITTED · PM-EVT-us-announces-new-iran-agreementceasefire-extension-by-may-31-665-831-238 12:40:23 AM
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
- contentinfo: "WS: connected API: — Data age: 0s Updated: 12:40:48 AM APEX Terminal"
- alert
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
  40  |         page.waitForURL(new RegExp(tab.path.replace('/', '\\/') + '(\\/)?$'), { timeout: 20_000 }),
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
> 62  |     await expect(page).toHaveURL(/opportunities/);
      |                        ^ Error: expect(page).toHaveURL(expected) failed
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
  141 |     const tabs = page.getByTestId('analytics-tabs');
  142 |     await tabs.getByRole('button', { name: 'Arb Backtest', exact: true }).click();
  143 |     await expect(page.getByTestId('backtest-panel')).toBeVisible({ timeout: 60_000 });
  144 |     await tabs.getByRole('button', { name: 'Signals', exact: true }).click();
  145 |     await expect(page.locator('.card-title', { hasText: 'Signal quality' })).toBeVisible();
  146 |     await tabs.getByRole('button', { name: 'Performance', exact: true }).click();
  147 |     await expect(page.getByText(/Equity|Sharpe/i).first()).toBeVisible();
  148 |   });
  149 | });
  150 | 
  151 | test.describe('Live Feed features', () => {
  152 |   test('filter input and limit select', async ({ page }) => {
  153 |     await gotoTerminal(page, '/dashboard/live');
  154 |     await page.getByPlaceholder(/Filter type/i).fill('SYSTEM');
  155 |     await page.locator('select').selectOption('50');
  156 |     await expect(page.getByPlaceholder(/Filter type/i)).toHaveValue('SYSTEM');
  157 |   });
  158 | });
  159 | 
  160 | test.describe('Marketplace features', () => {
  161 |   test('period and sort tabs', async ({ page }) => {
  162 |     await gotoTerminal(page, '/dashboard/marketplace');
```