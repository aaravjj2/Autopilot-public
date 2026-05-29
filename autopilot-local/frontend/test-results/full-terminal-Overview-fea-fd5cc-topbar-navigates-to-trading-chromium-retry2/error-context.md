# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: full-terminal.spec.ts >> Overview features >> Quick Order topbar navigates to trading
- Location: tests/e2e/full-terminal.spec.ts:81:7

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
        - heading "Command Center" [level=2] [ref=e136]
        - generic [ref=e137]: Real-time portfolio · Engine RUNNING · syncing…
      - generic [ref=e138]:
        - button "Refresh Cache" [ref=e139]
        - generic [ref=e140]: POLLING
    - generic [ref=e141]:
      - generic [ref=e142]:
        - generic [ref=e143]: Portfolio
        - generic [ref=e144]: $0.00
        - generic [ref=e145]: 0.00% today
      - generic [ref=e146]:
        - generic [ref=e147]: Buying Power
        - generic [ref=e148]: $0.00
        - generic [ref=e149]: Cash $0.00
      - generic [ref=e150]:
        - generic [ref=e151]: Positions
        - generic [ref=e152]: "0"
        - generic [ref=e153]: 0 profitable
      - generic [ref=e154]:
        - generic [ref=e155]: Signals
        - generic [ref=e156]: "0"
        - generic [ref=e157]: 0 high conviction
      - generic [ref=e158]:
        - generic [ref=e159]: Arb Active
        - generic [ref=e160]: "0"
        - generic [ref=e161]: —
    - generic [ref=e162]:
      - generic [ref=e164]: Real-time P&L
      - generic [ref=e165]:
        - generic [ref=e166]:
          - generic [ref=e167]: Unrealized
          - generic [ref=e168]: $0.00
        - generic [ref=e169]:
          - generic [ref=e170]: Daily P&L
          - generic [ref=e171]: $0.00
        - generic [ref=e172]:
          - generic [ref=e173]: Position value
          - generic [ref=e174]: $0.00
        - generic [ref=e175]:
          - generic [ref=e176]: Cash
          - generic [ref=e177]: $0.00
    - generic [ref=e178]:
      - generic [ref=e181]: Equity Curve · 30D
      - generic [ref=e182]:
        - generic [ref=e184]: Risk snapshot
        - generic [ref=e185]:
          - generic [ref=e186]:
            - generic [ref=e187]: 0.0%
            - text: Daily
          - generic [ref=e188]:
            - generic [ref=e189]: "0"
            - text: Open
    - generic [ref=e190]:
      - generic [ref=e191]:
        - generic [ref=e192]:
          - generic [ref=e193]: Watchlist
          - button "+ Add" [ref=e194]
        - table [ref=e196]:
          - rowgroup [ref=e197]:
            - row "Symbol Side P&L Conv" [ref=e198]:
              - columnheader "Symbol" [ref=e199]
              - columnheader "Side" [ref=e200]
              - columnheader "P&L" [ref=e201]
              - columnheader "Conv" [ref=e202]
          - rowgroup
      - generic [ref=e203]:
        - generic [ref=e205]: Agent Pipeline
        - generic [ref=e206]:
          - generic [ref=e207]:
            - strong [ref=e208]: L0
            - text: Ingest
          - generic [ref=e209]:
            - strong [ref=e210]: L1
            - text: Brain
          - generic [ref=e211]:
            - strong [ref=e212]: L2
            - text: Agents
          - generic [ref=e213]:
            - strong [ref=e214]: L3
            - text: Exec
          - generic [ref=e215]:
            - strong [ref=e216]: L4
            - text: Obs
    - generic [ref=e217]:
      - generic [ref=e218]:
        - generic [ref=e219]:
          - generic [ref=e220]: Top Signals
          - link "View all" [ref=e221] [cursor=pointer]:
            - /url: /dashboard/opportunities
        - paragraph [ref=e222]: No opportunities yet
      - generic [ref=e223]:
        - generic [ref=e225]: Recent Activity
        - paragraph [ref=e226]: No events yet
  - complementary [ref=e227]:
    - generic [ref=e228]:
      - generic [ref=e229]: Order Ticket
      - generic [ref=e230]:
        - text: Symbol
        - textbox [ref=e231]: NVDA
        - generic [ref=e232]:
          - button "Buy" [ref=e233]
          - button "Sell" [ref=e234]
        - text: Qty
        - spinbutton [ref=e235]: "10"
        - text: Type
        - combobox [ref=e236]:
          - option "Market" [selected]
          - option "Limit"
        - button "Submit Paper Order" [ref=e237]
    - generic [ref=e238]:
      - generic [ref=e239]: Alerts
      - list [ref=e240]:
        - listitem [ref=e241]: Engine cache auto-refresh 30s
  - contentinfo [ref=e242]:
    - generic [ref=e243]: "WS: disconnected"
    - generic [ref=e244]: "API: —"
    - generic [ref=e245]: "Data age: 0s"
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