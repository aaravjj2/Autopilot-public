import { test, expect } from '@playwright/test';
import { gotoTerminal, clickSidebar } from './helpers';

/** All sidebar tabs in TerminalLayout */
const TABS = [
  { label: 'Overview', path: '/dashboard', heading: /Command Center/ },
  { label: 'Trading', path: '/dashboard/trading', heading: /^Trading$/ },
  { label: 'Positions', path: '/dashboard/positions', heading: /^Positions$/ },
  { label: 'Signals', path: '/dashboard/opportunities', heading: /Opportunity Signals/ },
  { label: 'Autopilot', path: '/dashboard/autopilot', heading: /Autopilot Pipeline/ },
  { label: 'Arb Radar', path: '/dashboard/arb-radar', heading: /^Arb Radar$/ },
  { label: 'Risk', path: '/dashboard/risk-management', heading: /^Risk Management$/ },
  { label: 'Analytics', path: '/dashboard/analytics', heading: /^Analytics$/ },
  { label: 'Live Feed', path: '/dashboard/live', heading: /^Live Feed$/ },
  { label: 'Marketplace', path: '/dashboard/marketplace', heading: /Copy Trading Marketplace/ },
  { label: 'Kalshi', path: '/dashboard/kalshi', heading: /Kalshi Book/ },
  { label: 'Polymarket', path: '/dashboard/polymarket', heading: /Polymarket Book/ },
  { label: 'DeFi', path: '/dashboard/defi-treasury', heading: /DeFi Treasury/ },
  { label: 'Fund', path: '/dashboard/fund-admin', heading: /Fund Admin/ },
  { label: 'Hive-Mind', path: '/dashboard/ai-hivemind', heading: /AI Hive-Mind/ },
  { label: 'Settings', path: '/dashboard/settings', heading: /Settings/ },
] as const;

test.describe('Every sidebar tab', () => {
  for (const tab of TABS) {
    test(`${tab.label} loads via direct URL`, async ({ page }) => {
      await gotoTerminal(page, tab.path);
      await expect(page.getByRole('heading', { name: tab.heading })).toBeVisible();
      await expect(page.locator('.sidebar').getByRole('link', { name: tab.label, exact: true })).toHaveClass(/active/);
    });
  }

  test('navigate every tab via sidebar clicks', async ({ page }) => {
    await gotoTerminal(page, '/dashboard');
    for (const tab of TABS) {
      await clickSidebar(page, tab.label);
      await expect(page).toHaveURL(new RegExp(tab.path.replace('/', '\\/') + '(\\/)?$'));
      await expect(page.getByRole('heading', { name: tab.heading })).toBeVisible();
    }
  });
});

test.describe('Overview features', () => {
  test('Refresh Cache button', async ({ page }) => {
    test.setTimeout(120_000);
    await gotoTerminal(page, '/dashboard');
    const btn = page.getByRole('button', { name: /Refresh Cache/i });
    await expect(btn).toBeVisible();
    await btn.click();
    await expect(page.getByRole('heading', { name: /Command Center/i })).toBeVisible();
    await expect(btn).toBeEnabled({ timeout: 90_000 });
  });

  test('View all signals link', async ({ page }) => {
    await gotoTerminal(page, '/dashboard');
    await page.getByRole('link', { name: /View all/i }).click();
    await expect(page).toHaveURL(/opportunities/);
  });

  test('order ticket in right panel', async ({ page }) => {
    await gotoTerminal(page, '/dashboard');
    await expect(page.locator('.right-panel')).toBeVisible();
    await expect(page.getByText('Order Ticket')).toBeVisible();
    await expect(page.getByRole('button', { name: /Submit Paper Order/i })).toBeVisible();
  });

  test('command palette opens and navigates', async ({ page }) => {
    await gotoTerminal(page, '/dashboard');
    await page.getByTestId('cmd-trigger').click();
    await expect(page.getByTestId('cmd-dialog')).toBeVisible({ timeout: 10_000 });
    await page.getByTestId('cmd-input').fill('settings');
    await page.locator('.cmd-item').filter({ hasText: 'Settings' }).click();
    await expect(page).toHaveURL(/settings/);
  });

  test('Quick Order topbar navigates to trading', async ({ page }) => {
    await gotoTerminal(page, '/dashboard');
    await page.getByTestId('quick-order').click();
    await expect(page).toHaveURL(/trading/, { timeout: 15_000 });
  });
});

test.describe('Trading features', () => {
  test('timeframe tabs switch', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/trading');
    await page.getByTestId('tf-1h').click();
    await expect(page.getByTestId('chart-timeframe')).toHaveText('1h', { timeout: 5_000 });
  });

  test('options Calls/Puts tabs', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/trading');
    const putsTab = page.getByRole('button', { name: 'Puts', exact: true });
    if (await putsTab.isVisible().catch(() => false)) {
      await putsTab.click();
      await expect(putsTab).toHaveClass(/active/);
    }
  });

  test('symbol selector present', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/trading');
    await expect(page.locator('select').first()).toBeVisible();
  });
});

test.describe('Positions features', () => {
  test('Open and Closed tabs', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/positions');
    const tabs = page.locator('.main .card .tabs').first();
    await tabs.getByRole('button', { name: 'Closed', exact: true }).click();
    await expect(tabs.getByRole('button', { name: 'Closed', exact: true })).toBeVisible();
    await tabs.getByRole('button', { name: 'Open', exact: true }).click();
    await expect(page.getByRole('columnheader', { name: 'Symbol' })).toBeVisible();
  });
});

test.describe('Signals features', () => {
  test('symbol filter input', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/opportunities');
    const filter = page.getByPlaceholder(/Filter symbol/i);
    await filter.fill('A');
    await expect(filter).toHaveValue('A');
  });

  test('min conviction filter', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/opportunities');
    const conv = page.locator('input[type="number"]').first();
    await conv.fill('5');
    await expect(conv).toHaveValue('5');
  });
});

test.describe('Analytics features', () => {
  test('Performance / Arb Backtest / Signals tabs', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/analytics');
    const tabs = page.getByTestId('analytics-tabs');
    await tabs.getByRole('button', { name: 'Arb Backtest', exact: true }).click();
    await expect(page.getByTestId('backtest-panel')).toBeVisible({ timeout: 60_000 });
    await tabs.getByRole('button', { name: 'Signals', exact: true }).click();
    await expect(page.locator('.card-title', { hasText: 'Signal quality' })).toBeVisible();
    await tabs.getByRole('button', { name: 'Performance', exact: true }).click();
    await expect(page.getByText(/Equity|Sharpe/i).first()).toBeVisible();
  });
});

test.describe('Live Feed features', () => {
  test('filter input and limit select', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/live');
    await page.getByPlaceholder(/Filter type/i).fill('SYSTEM');
    await page.locator('select').selectOption('50');
    await expect(page.getByPlaceholder(/Filter type/i)).toHaveValue('SYSTEM');
  });
});

test.describe('Marketplace features', () => {
  test('period and sort tabs', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/marketplace');
    await page.getByRole('button', { name: '3M', exact: true }).click();
    await page.getByRole('button', { name: 'name', exact: true }).click();
  });

  test('Refresh all button', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/marketplace');
    const btn = page.getByRole('button', { name: /Refresh all/i });
    await btn.click();
    await expect(btn).toBeEnabled({ timeout: 60_000 });
  });

  test('portfolio detail page when pilots exist', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/marketplace');
    const link = page.locator('.card a').first();
    if (await link.count() > 0) {
      await link.click();
      await expect(page).toHaveURL(/\/dashboard\/marketplace\//);
      await expect(page.getByRole('button', { name: /Follow|Unfollow/i })).toBeVisible();
    }
  });
});

test.describe('Polymarket features', () => {
  test('Sync from engine button', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/polymarket');
    const btn = page.getByRole('button', { name: /Sync from engine/i });
    await btn.click();
    await expect(btn).toBeEnabled({ timeout: 30_000 });
  });
});

test.describe('Settings features', () => {
  test('Refresh integrations', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/settings');
    const btn = page.getByRole('button', { name: /Refresh/i }).first();
    await btn.click();
    await expect(btn).toBeEnabled({ timeout: 90_000 });
  });

  test('dual backend cards visible', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/settings');
    await expect(page.getByText('APEX Engine')).toBeVisible();
    await expect(page.getByText(/Marketplace API/i)).toBeVisible();
    await expect(page.getByText('Integrations (APEX)')).toBeVisible();
  });
});

test.describe('Arb Radar features', () => {
  test('page loads with opportunities or empty state', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/arb-radar');
    const hasTable = await page.locator('.table-wrap tbody tr').count();
    const hasEmpty = await page.getByText(/No arbitrage|Connecting/i).isVisible().catch(() => false);
    expect(hasTable > 0 || hasEmpty).toBeTruthy();
  });

  test('Reload button', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/arb-radar');
    await expect(page.getByRole('button', { name: /Reload/i })).toBeVisible();
  });
});

test.describe('Landing page', () => {
  test('all feature cards and launch links', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('link', { name: /Enter Terminal/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Arb Radar/i }).first()).toBeVisible();
    await expect(page.getByRole('link', { name: /Marketplace/i }).first()).toBeVisible();
  });
});

test.describe('No critical API failures in browser', () => {
  test('dashboard does not log 404 on APEX or marketplace APIs', async ({ page }) => {
    const bad: string[] = [];
    page.on('response', (res) => {
      const u = res.url();
      if (u.includes(':8000') && res.status() >= 400) {
        bad.push(`${res.status()} ${u}`);
      }
    });
    await gotoTerminal(page, '/dashboard');
    await page.waitForTimeout(5000);
    await gotoTerminal(page, '/dashboard/marketplace');
    await page.waitForTimeout(3000);
    expect(bad.filter((b) => !b.includes('favicon'))).toEqual([]);
  });
});
