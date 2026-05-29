# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: full-terminal.spec.ts >> Analytics features >> Performance / Arb Backtest / Signals tabs
- Location: tests/e2e/full-terminal.spec.ts:139:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText(/Equity|Sharpe/i).first()
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for getByText(/Equity|Sharpe/i).first()

```

```yaml
- 'heading "Application error: a client-side exception has occurred while loading 127.0.0.1 (see the browser console for more information)." [level=2]'
```

# Test source

```ts
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
  141 |     const tabs = page.getByTestId('analytics-tabs');
  142 |     await tabs.getByRole('button', { name: 'Arb Backtest', exact: true }).click();
  143 |     await expect(page.getByTestId('backtest-panel')).toBeVisible({ timeout: 60_000 });
  144 |     await tabs.getByRole('button', { name: 'Signals', exact: true }).click();
  145 |     await expect(page.locator('.card-title', { hasText: 'Signal quality' })).toBeVisible();
  146 |     await tabs.getByRole('button', { name: 'Performance', exact: true }).click();
> 147 |     await expect(page.getByText(/Equity|Sharpe/i).first()).toBeVisible();
      |                                                            ^ Error: expect(locator).toBeVisible() failed
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
  179 |       await expect(page).toHaveURL(/\/dashboard\/marketplace\//);
  180 |       await expect(page.getByRole('button', { name: /Follow|Unfollow/i })).toBeVisible();
  181 |     }
  182 |   });
  183 | });
  184 | 
  185 | test.describe('Polymarket features', () => {
  186 |   test('Sync from engine button', async ({ page }) => {
  187 |     await gotoTerminal(page, '/dashboard/polymarket');
  188 |     const btn = page.getByRole('button', { name: /Sync copy-trading DB/i });
  189 |     await btn.click();
  190 |     await expect(btn).toBeEnabled({ timeout: 30_000 });
  191 |   });
  192 | });
  193 | 
  194 | test.describe('Settings features', () => {
  195 |   test('Refresh integrations', async ({ page }) => {
  196 |     await gotoTerminal(page, '/dashboard/settings');
  197 |     const btn = page.getByRole('button', { name: /Refresh/i }).first();
  198 |     await btn.click();
  199 |     await expect(btn).toBeEnabled({ timeout: 90_000 });
  200 |   });
  201 | 
  202 |   test('dual backend cards visible', async ({ page }) => {
  203 |     await gotoTerminal(page, '/dashboard/settings');
  204 |     await expect(page.getByText('APEX Engine')).toBeVisible();
  205 |     await expect(page.getByText(/Copy-trading API/i)).toBeVisible();
  206 |     await expect(page.getByText('Integrations (APEX)')).toBeVisible();
  207 |   });
  208 | });
  209 | 
  210 | test.describe('Arb Radar features', () => {
  211 |   test('page loads with opportunities or empty state', async ({ page }) => {
  212 |     await gotoTerminal(page, '/dashboard/arb-radar');
  213 |     const hasTable = await page.locator('.table-wrap tbody tr').count();
  214 |     const hasEmpty = await page.getByText(/No arbitrage|Connecting/i).isVisible().catch(() => false);
  215 |     expect(hasTable > 0 || hasEmpty).toBeTruthy();
  216 |   });
  217 | 
  218 |   test('Reload button', async ({ page }) => {
  219 |     await gotoTerminal(page, '/dashboard/arb-radar');
  220 |     await expect(page.getByRole('button', { name: /Reload/i })).toBeVisible();
  221 |   });
  222 | });
  223 | 
  224 | test.describe('Landing page', () => {
  225 |   test('all feature cards and launch links', async ({ page }) => {
  226 |     await page.goto('/');
  227 |     await expect(page.getByRole('link', { name: /Enter Terminal/i })).toBeVisible();
  228 |     await expect(page.getByRole('link', { name: /Arb Radar/i }).first()).toBeVisible();
  229 |     await expect(page.getByRole('link', { name: /Marketplace/i }).first()).toBeVisible();
  230 |   });
  231 | });
  232 | 
  233 | test.describe('No critical API failures in browser', () => {
  234 |   test('dashboard does not log 404 on APEX or marketplace APIs', async ({ page }) => {
  235 |     const bad: string[] = [];
  236 |     page.on('response', (res) => {
  237 |       const u = res.url();
  238 |       if (u.includes(':8000') && res.status() >= 400) {
  239 |         bad.push(`${res.status()} ${u}`);
  240 |       }
  241 |     });
  242 |     await gotoTerminal(page, '/dashboard');
  243 |     await page.waitForTimeout(5000);
  244 |     await gotoTerminal(page, '/dashboard/marketplace');
  245 |     await page.waitForTimeout(3000);
  246 |     expect(bad.filter((b) => !b.includes('favicon'))).toEqual([]);
  247 |   });
```