# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: ai-hivemind.spec.ts >> AI Hive-Mind consensus vote
- Location: tests/e2e/ai-hivemind.spec.ts:4:5

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByTestId('consensus-output')
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 15000ms
  - waiting for getByTestId('consensus-output')

```

```yaml
- complementary:
  - text: AX
  - heading "APEX Terminal" [level=1]
  - paragraph: $146,874.83 · Paper
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
    - link "Arb Radar 285":
      - /url: /dashboard/arb-radar
      - img
      - text: Arb Radar 285
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
  - text: API 3211msWS 5msArb 20ms WS live
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
  - heading "AI Hive-Mind" [level=2]
  - text: Six-agent committee votes on arb proposals (not copy-trading pilots)
  - button "Run vote"
  - text: Active proposal KX8 Q8 Edge 5.00% · Settlement 85% Committee log
  - paragraph: Run consensus on the selected arb proposal
- contentinfo: "WS: connected API: — Data age: 0s Updated: 12:35:16 AM APEX Terminal"
- alert
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | import { gotoTerminal } from './helpers';
  3  | 
  4  | test('AI Hive-Mind consensus vote', async ({ page }) => {
  5  |   await gotoTerminal(page, '/dashboard/ai-hivemind');
  6  |   await page.getByRole('button', { name: /Run vote/i }).click();
> 7  |   await expect(page.getByTestId('consensus-output')).toBeVisible({ timeout: 15_000 });
     |                                                      ^ Error: expect(locator).toBeVisible() failed
  8  |   const text = await page.getByTestId('consensus-output').textContent();
  9  |   expect(text).toBeTruthy();
  10 |   expect(text).not.toContain('consensus failed');
  11 | });
  12 | 
```