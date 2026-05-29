# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: submission-demo.spec.ts >> APEX Autopilot full product demo
- Location: tests/e2e/submission-demo.spec.ts:16:5

# Error details

```
Error: APEX health check failed: http://127.0.0.1:8000/health
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
          - paragraph [ref=e8]: $146,882.43 · Paper
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
        - link "Arb Radar 288" [ref=e35] [cursor=pointer]:
          - /url: /dashboard/arb-radar
          - img [ref=e36]
          - text: Arb Radar
          - generic [ref=e38]: "288"
        - link "Risk" [ref=e39] [cursor=pointer]:
          - /url: /dashboard/risk-management
          - img [ref=e40]
          - text: Risk
        - link "Hive-Mind" [ref=e42] [cursor=pointer]:
          - /url: /dashboard/ai-hivemind
          - img [ref=e43]
          - text: Hive-Mind
        - link "Analytics" [ref=e53] [cursor=pointer]:
          - /url: /dashboard/analytics
          - img [ref=e54]
          - text: Analytics
        - link "Live Feed" [ref=e57] [cursor=pointer]:
          - /url: /dashboard/live
          - img [ref=e58]
          - text: Live Feed
      - navigation [ref=e64]:
        - generic [ref=e65]: Copy Trading
        - link "Marketplace" [ref=e66] [cursor=pointer]:
          - /url: /dashboard/marketplace
          - img [ref=e67]
          - text: Marketplace
      - navigation [ref=e72]:
        - generic [ref=e73]: Prediction Markets
        - link "Kalshi" [ref=e74] [cursor=pointer]:
          - /url: /dashboard/kalshi
          - img [ref=e75]
          - text: Kalshi
        - link "Polymarket" [ref=e81] [cursor=pointer]:
          - /url: /dashboard/polymarket
          - img [ref=e82]
          - text: Polymarket
        - link "World Cup" [ref=e87] [cursor=pointer]:
          - /url: /dashboard/world-cup
          - img [ref=e88]
          - text: World Cup
      - navigation [ref=e94]:
        - generic [ref=e95]: Ops
        - link "DeFi" [ref=e96] [cursor=pointer]:
          - /url: /dashboard/defi-treasury
          - img [ref=e97]
          - text: DeFi
        - link "Fund" [ref=e99] [cursor=pointer]:
          - /url: /dashboard/fund-admin
          - img [ref=e100]
          - text: Fund
      - navigation [ref=e103]:
        - generic [ref=e104]: System
        - link "Settings" [ref=e105] [cursor=pointer]:
          - /url: /dashboard/settings
          - img [ref=e106]
          - text: Settings
      - generic [ref=e109]:
        - generic [ref=e110]:
          - generic [ref=e111]: API —
          - generic [ref=e112]: WS —
          - generic [ref=e113]: Arb —
        - generic [ref=e114]: Polling
    - banner [ref=e115]:
      - button "⌕ Search symbol, command… ⌘K" [ref=e116] [cursor=pointer]:
        - generic [ref=e117]: ⌕
        - generic [ref=e118]: Search symbol, command…
        - generic [ref=e119]: ⌘K
      - generic [ref=e120]: NYSE · Regular
      - generic [ref=e121]:
        - img [ref=e122]
        - text: Offline
      - generic [ref=e129]:
        - textbox "email" [ref=e130]
        - textbox "password" [ref=e131]
        - button "Login" [ref=e132] [cursor=pointer]
        - button "Guest" [ref=e133] [cursor=pointer]
      - button "Alerts" [ref=e134] [cursor=pointer]:
        - img [ref=e135]
      - link "Quick Order" [ref=e138] [cursor=pointer]:
        - /url: /dashboard/trading
    - main [ref=e139]:
      - generic [ref=e140]:
        - generic [ref=e141]:
          - heading "Command Center" [level=2] [ref=e142]
          - generic [ref=e143]: Real-time portfolio · Engine RUNNING · 12:50:14 AM
        - generic [ref=e144]:
          - button "Refresh Cache" [ref=e145] [cursor=pointer]
          - generic [ref=e146]: POLLING
      - generic [ref=e147]:
        - generic [ref=e148]:
          - generic [ref=e149]: Portfolio
          - generic [ref=e150]: $146,882.43
          - generic [ref=e151]: 0.01% today
        - generic [ref=e152]:
          - generic [ref=e153]: Buying Power
          - generic [ref=e154]: $585,001.00
          - generic [ref=e155]: Cash $144,818.18
        - generic [ref=e156]:
          - generic [ref=e157]: Positions
          - generic [ref=e158]: "1"
          - generic [ref=e159]: 1 profitable
        - generic [ref=e160]:
          - generic [ref=e161]: Signals
          - generic [ref=e162]: "0"
          - generic [ref=e163]: 0 high conviction
        - generic [ref=e164]:
          - generic [ref=e165]: Arb Active
          - generic [ref=e166]: "288"
          - generic [ref=e167]: 50.00% win rate
      - generic [ref=e168]:
        - generic [ref=e170]: Real-time P&L
        - generic [ref=e171]:
          - generic [ref=e172]:
            - generic [ref=e173]: Unrealized
            - generic [ref=e174]: $47.99
          - generic [ref=e175]:
            - generic [ref=e176]: Daily P&L
            - generic [ref=e177]: $18.44
          - generic [ref=e178]:
            - generic [ref=e179]: Position value
            - generic [ref=e180]: $2,064.25
          - generic [ref=e181]:
            - generic [ref=e182]: Cash
            - generic [ref=e183]: $144,818.18
      - generic [ref=e184]:
        - generic [ref=e185]:
          - generic [ref=e186]: Prediction Market Brain
          - link "Arb Radar →" [ref=e187] [cursor=pointer]:
            - /url: /dashboard/arb-radar
        - paragraph [ref=e188]: "Arb strategy: buy Kalshi YES + Polymarket NO when net_edge ≥ 2% after Kalshi 7% fee. All execution paths are paper-only."
        - generic [ref=e189]:
          - generic [ref=e190]:
            - generic [ref=e191]: Kalshi
            - generic [ref=e192]: ok
            - generic [ref=e193]: 25 cached pairs
          - generic [ref=e194]:
            - generic [ref=e195]: Polymarket
            - generic [ref=e196]: ok
            - generic [ref=e197]: 25 cached pairs
          - generic [ref=e198]:
            - generic [ref=e199]: Arb cache
            - generic [ref=e200]: 25 pairs · top 1.2%
        - table [ref=e202]:
          - rowgroup [ref=e203]:
            - row "Ticker Edge Settle" [ref=e204]:
              - columnheader "Ticker" [ref=e205]
              - columnheader "Edge" [ref=e206]
              - columnheader "Settle" [ref=e207]
          - rowgroup [ref=e208]:
            - row "KXDEMO-0091 1.2% 88%" [ref=e209]:
              - cell "KXDEMO-0091" [ref=e210]
              - cell "1.2%" [ref=e211]
              - cell "88%" [ref=e212]
            - row "KXDEMO-0086 1.2% 83%" [ref=e213]:
              - cell "KXDEMO-0086" [ref=e214]
              - cell "1.2%" [ref=e215]
              - cell "83%" [ref=e216]
            - row "KXDEMO-0081 1.2% 78%" [ref=e217]:
              - cell "KXDEMO-0081" [ref=e218]
              - cell "1.2%" [ref=e219]
              - cell "78%" [ref=e220]
            - row "KXDEMO-0071 1.2% 93%" [ref=e221]:
              - cell "KXDEMO-0071" [ref=e222]
              - cell "1.2%" [ref=e223]
              - cell "93%" [ref=e224]
            - row "KXDEMO-0066 1.2% 88%" [ref=e225]:
              - cell "KXDEMO-0066" [ref=e226]
              - cell "1.2%" [ref=e227]
              - cell "88%" [ref=e228]
      - generic [ref=e229]:
        - generic [ref=e230]:
          - generic [ref=e232]: Equity Curve · 30D
          - table [ref=e235]:
            - row [ref=e236]:
              - cell
              - cell [ref=e237]:
                - link "Charting by TradingView" [ref=e241] [cursor=pointer]:
                  - /url: https://www.tradingview.com/?utm_medium=lwc-link&utm_campaign=lwc-chart&utm_source=127.0.0.1/dashboard
                  - img [ref=e242]
              - cell [ref=e246]
            - row [ref=e250]:
              - cell
              - cell [ref=e251]
              - cell [ref=e255]
        - generic [ref=e258]:
          - generic [ref=e260]: Risk snapshot
          - generic [ref=e261]:
            - generic [ref=e262]:
              - generic [ref=e263]: 0.0%
              - text: Daily
            - generic [ref=e264]:
              - generic [ref=e265]: "1"
              - text: Open
      - generic [ref=e266]:
        - generic [ref=e267]:
          - generic [ref=e268]:
            - generic [ref=e269]: Watchlist
            - button "+ Add" [ref=e270] [cursor=pointer]
          - table [ref=e272]:
            - rowgroup [ref=e273]:
              - row "Symbol Side P&L Conv" [ref=e274]:
                - columnheader "Symbol" [ref=e275]
                - columnheader "Side" [ref=e276]
                - columnheader "P&L" [ref=e277]
                - columnheader "Conv" [ref=e278]
            - rowgroup [ref=e279]:
              - row "MU long $47.99 —" [ref=e280]:
                - cell "MU" [ref=e281]
                - cell "long" [ref=e282]:
                  - generic [ref=e283]: long
                - cell "$47.99" [ref=e284]
                - cell "—" [ref=e285]
        - generic [ref=e286]:
          - generic [ref=e288]: Agent Pipeline
          - generic [ref=e289]:
            - generic [ref=e290]:
              - strong [ref=e291]: L0
              - generic [ref=e292]: Ingest
            - generic [ref=e293]:
              - strong [ref=e294]: L1
              - generic [ref=e295]: Brain
            - generic [ref=e296]:
              - strong [ref=e297]: L2
              - generic [ref=e298]: Agents
            - generic [ref=e299]:
              - strong [ref=e300]: L3
              - generic [ref=e301]: Exec
            - generic [ref=e302]:
              - strong [ref=e303]: L4
              - generic [ref=e304]: Obs
      - generic [ref=e305]:
        - generic [ref=e306]:
          - generic [ref=e307]:
            - generic [ref=e308]: Top Signals
            - link "View all" [ref=e309] [cursor=pointer]:
              - /url: /dashboard/opportunities
          - paragraph [ref=e310]: No opportunities yet
        - generic [ref=e311]:
          - generic [ref=e313]: Recent Activity
          - generic [ref=e314]:
            - generic [ref=e315]:
              - img [ref=e316]
              - generic [ref=e320]: ORDER_FILLED · PM-EVT-us-announces-new-iran-agreementceasefire-extension-by-may-31-665-831-238
              - generic [ref=e321]: 12:48:02 AM
            - generic [ref=e322]:
              - img [ref=e323]
              - generic [ref=e327]: ORDER_SUBMITTED · PM-EVT-us-announces-new-iran-agreementceasefire-extension-by-may-31-665-831-238
              - generic [ref=e328]: 12:47:51 AM
            - generic [ref=e329]:
              - img [ref=e330]
              - generic [ref=e334]: ORDER_FILLED · PM-EVT-us-x-iran-permanent-peace-deal-by-june-7-2026
              - generic [ref=e335]: 12:47:51 AM
            - generic [ref=e336]:
              - img [ref=e337]
              - generic [ref=e341]: ORDER_SUBMITTED · PM-EVT-us-x-iran-permanent-peace-deal-by-june-7-2026
              - generic [ref=e342]: 12:47:41 AM
            - generic [ref=e343]:
              - img [ref=e344]
              - generic [ref=e348]: ORDER_FILLED · PM-EVT-us-iran-nuclear-deal-by-may-31-974
              - generic [ref=e349]: 12:47:41 AM
            - generic [ref=e350]:
              - img [ref=e351]
              - generic [ref=e355]: ORDER_SUBMITTED · PM-EVT-us-iran-nuclear-deal-by-may-31-974
              - generic [ref=e356]: 12:47:31 AM
            - generic [ref=e357]:
              - img [ref=e358]
              - generic [ref=e362]: ORDER_FILLED · PM-EVT-us-x-iran-permanent-peace-deal-by-may-31-2026-333-871-241-192-799-449-125
              - generic [ref=e363]: 12:47:31 AM
            - generic [ref=e364]:
              - img [ref=e365]
              - generic [ref=e369]: ORDER_SUBMITTED · PM-EVT-us-x-iran-permanent-peace-deal-by-may-31-2026-333-871-241-192-799-449-125
              - generic [ref=e370]: 12:47:20 AM
    - complementary [ref=e371]:
      - generic [ref=e372]:
        - generic [ref=e373]: Order Ticket
        - generic [ref=e374]:
          - generic [ref=e375]: Symbol
          - textbox [ref=e376]: MU
          - generic [ref=e377]:
            - button "Buy" [ref=e378] [cursor=pointer]
            - button "Sell" [ref=e379] [cursor=pointer]
          - generic [ref=e380]: Qty
          - spinbutton [ref=e381]: "10"
          - generic [ref=e382]: Type
          - combobox [ref=e383]:
            - option "Market" [selected]
            - option "Limit"
          - button "Submit Paper Order" [ref=e384] [cursor=pointer]
      - generic [ref=e385]:
        - generic [ref=e386]: Alerts
        - list [ref=e387]:
          - listitem [ref=e388]: Engine cache auto-refresh 30s
    - contentinfo [ref=e389]:
      - generic [ref=e390]: "WS: disconnected"
      - generic [ref=e391]: "API: —"
      - generic [ref=e392]: "Data age: 0s"
      - generic [ref=e393]: "Updated: 12:50:14 AM"
      - generic [ref=e394]: APEX Terminal
  - button "Open Next.js Dev Tools" [ref=e400] [cursor=pointer]:
    - img [ref=e401]
  - alert [ref=e404]
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
> 20 |   throw new Error(`APEX health check failed: ${APEX_HEALTH}`);
     |         ^ Error: APEX health check failed: http://127.0.0.1:8000/health
  21 | }
  22 | 
  23 | /** Navigate and wait for terminal shell (avoids networkidle hangs from WS/polling). */
  24 | export async function gotoTerminal(page: Page, path: string) {
  25 |   await waitForApexHealth();
  26 |   await page.goto(path, { waitUntil: 'load', timeout: 45_000 });
  27 |   await expect(page.locator('.app-shell')).toBeVisible({ timeout: 20_000 });
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