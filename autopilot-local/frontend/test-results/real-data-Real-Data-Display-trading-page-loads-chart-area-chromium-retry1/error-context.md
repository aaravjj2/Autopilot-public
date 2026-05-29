# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: real-data.spec.ts >> Real Data Display >> trading page loads chart area
- Location: tests/e2e/real-data.spec.ts:21:7

# Error details

```
TimeoutError: page.waitForSelector: Timeout 20000ms exceeded.
Call log:
  - waiting for locator('html[data-terminal-hydrated="true"]') to be visible

```

# Page snapshot

```yaml
- generic [ref=e2]:
  - complementary [ref=e3]:
    - generic [ref=e4]:
      - generic [ref=e5]: AX
      - generic [ref=e6]:
        - heading "APEX Terminal" [level=1] [ref=e7]
        - paragraph [ref=e8]: Paper · Live data
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
      - text: Polling
  - banner [ref=e113]:
    - button "⌕Search symbol, command…⌘K" [ref=e114] [cursor=pointer]
    - text: NYSE · Regular
    - generic [ref=e115]:
      - img [ref=e116]
      - text: Offline
    - generic [ref=e123]:
      - textbox "email" [ref=e124]
      - textbox "password" [ref=e125]
      - button "Login" [ref=e126]
      - button "Guest" [ref=e127]
    - button "Alerts" [ref=e128]:
      - img [ref=e129]
    - link "Quick Order" [ref=e132] [cursor=pointer]:
      - /url: /dashboard/trading
  - main [ref=e133]:
    - generic [ref=e134]:
      - generic [ref=e135]:
        - heading "Trading" [level=2] [ref=e136]
        - combobox [ref=e138]:
          - option "NVDA" [selected]
      - generic [ref=e140]:
        - button "1m" [ref=e141]
        - button "5m" [ref=e142]
        - button "15m" [ref=e143]
        - button "1h" [ref=e144]
        - button "4h" [ref=e145]
        - button "1D" [ref=e146]
        - button "1W" [ref=e147]
    - generic [ref=e148]:
      - generic [ref=e149]:
        - generic [ref=e150]:
          - generic [ref=e151]:
            - generic [ref=e152]: Price · NVDA
            - text: 1D
          - generic [ref=e155]: Bars 0
        - generic [ref=e156]:
          - generic [ref=e157]:
            - generic [ref=e158]: Last
            - generic [ref=e159]: —
          - generic [ref=e160]:
            - generic [ref=e161]: High
            - generic [ref=e162]: —
          - generic [ref=e163]:
            - generic [ref=e164]: Low
            - generic [ref=e165]: —
          - generic [ref=e166]:
            - generic [ref=e167]: Volume
            - generic [ref=e168]: —
      - generic [ref=e169]:
        - generic [ref=e171]: Options chain
        - paragraph [ref=e172]: No options data
  - complementary [ref=e173]:
    - generic [ref=e174]:
      - generic [ref=e175]: Order Ticket
      - generic [ref=e176]:
        - text: Symbol
        - textbox [ref=e177]: NVDA
        - generic [ref=e178]:
          - button "Buy" [ref=e179]
          - button "Sell" [ref=e180]
        - text: Qty
        - spinbutton [ref=e181]: "10"
        - text: Type
        - combobox [ref=e182]:
          - option "Market" [selected]
          - option "Limit"
        - button "Submit Paper Order" [ref=e183]
    - generic [ref=e184]:
      - generic [ref=e185]: Alerts
      - list [ref=e186]:
        - listitem [ref=e187]: Engine cache auto-refresh 30s
  - contentinfo [ref=e188]:
    - generic [ref=e189]: "WS: disconnected"
    - generic [ref=e190]: "API: —"
    - generic [ref=e191]: "Data age: 0s"
    - text: APEX Terminal
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
  27 |   await expect(page.locator('.app-shell')).toBeVisible({ timeout: 20_000 });
> 28 |   await page.waitForSelector('html[data-terminal-hydrated="true"]', { timeout: 20_000 });
     |              ^ TimeoutError: page.waitForSelector: Timeout 20000ms exceeded.
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