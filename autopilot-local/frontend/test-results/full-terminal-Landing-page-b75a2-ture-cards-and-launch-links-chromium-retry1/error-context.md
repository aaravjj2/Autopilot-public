# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: full-terminal.spec.ts >> Landing page >> all feature cards and launch links
- Location: tests/e2e/full-terminal.spec.ts:225:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('link', { name: /Enter Terminal/i })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for getByRole('link', { name: /Enter Terminal/i })

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
  - paragraph: "Cannot find module './611.js' Require stack: - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/.next/server/webpack-runtime.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/.next/server/app/page.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/require.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/load-components.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/build/utils.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/build/swc/options.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/build/swc/index.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/build/next-config-ts/transpile-config.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/config.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/next.js - /home/aarav/Aarav/Autopilot/autopilot-local/frontend/node_modules/next/dist/server/lib/start-server.js"
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
> 227 |     await expect(page.getByRole('link', { name: /Enter Terminal/i })).toBeVisible();
      |                                                                       ^ Error: expect(locator).toBeVisible() failed
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
  248 | });
  249 | 
```