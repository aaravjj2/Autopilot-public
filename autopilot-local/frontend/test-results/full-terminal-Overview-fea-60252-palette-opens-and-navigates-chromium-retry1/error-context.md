# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: full-terminal.spec.ts >> Overview features >> command palette opens and navigates
- Location: tests/e2e/full-terminal.spec.ts:72:7

# Error details

```
Error: expect(page).toHaveURL(expected) failed

Expected pattern: /settings/
Received string:  "http://127.0.0.1:3000/dashboard"
Timeout: 5000ms

Call log:
  - Expect "toHaveURL" with timeout 5000ms
    14 × unexpected value "http://127.0.0.1:3000/dashboard"

```

```yaml
- 'heading "Application error: a client-side exception has occurred while loading 127.0.0.1 (see the browser console for more information)." [level=2]'
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
> 78  |     await expect(page).toHaveURL(/settings/);
      |                        ^ Error: expect(page).toHaveURL(expected) failed
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
  163 |     await page.getByRole('button', { name: '3M', exact: true }).click();
  164 |     await page.getByRole('button', { name: 'name', exact: true }).click();
  165 |   });
  166 | 
  167 |   test('Refresh all button', async ({ page }) => {
  168 |     await gotoTerminal(page, '/dashboard/marketplace');
  169 |     const btn = page.getByRole('button', { name: /Refresh all/i });
  170 |     await btn.click();
  171 |     await expect(btn).toBeEnabled({ timeout: 60_000 });
  172 |   });
  173 | 
  174 |   test('portfolio detail page when pilots exist', async ({ page }) => {
  175 |     await gotoTerminal(page, '/dashboard/marketplace');
  176 |     const link = page.locator('.card a').first();
  177 |     if (await link.count() > 0) {
  178 |       await link.click();
```