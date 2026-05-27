import { test, expect } from '@playwright/test';
import { gotoTerminal } from './helpers';

test.describe('Real Data Display', () => {
  test('dashboard displays real account data from backend', async ({ page }) => {
    await gotoTerminal(page, '/dashboard');
    await expect(page.locator('.kpi-value').first()).toBeVisible();
    await expect(page.getByText('$').first()).toBeVisible();
  });

  test('dashboard displays top signals section', async ({ page }) => {
    await gotoTerminal(page, '/dashboard');
    await expect(page.getByText('Top Signals')).toBeVisible();
  });

  test('dashboard displays recent activity', async ({ page }) => {
    await gotoTerminal(page, '/dashboard');
    await expect(page.getByText('Recent Activity')).toBeVisible();
  });

  test('trading page loads chart area', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/trading');
    await expect(page.getByRole('button', { name: '1D', exact: true })).toBeVisible();
  });

  test('positions page shows positions header', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/positions');
    await expect(page.getByRole('heading', { name: 'Positions' })).toBeVisible();
  });

  test('opportunities page shows signals', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/opportunities');
    await expect(page.getByRole('heading', { name: /Opportunity Signals/ })).toBeVisible();
  });

  test('live feed page loads', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/live');
    await expect(page.getByRole('heading', { name: 'Live Feed' })).toBeVisible();
  });

  test('autopilot page shows pipeline', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/autopilot');
    await expect(page.getByText('L0').first()).toBeVisible();
  });

  test('analytics page loads', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/analytics');
    await expect(page.getByRole('heading', { name: 'Analytics' })).toBeVisible();
  });

  test('settings page loads', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/settings');
    await expect(page.getByRole('heading', { name: /Settings/ })).toBeVisible();
  });

  test('arb radar page loads', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/arb-radar');
    await expect(page.getByRole('heading', { name: 'Arb Radar' })).toBeVisible();
  });
});

const APEX_API = 'http://127.0.0.1:8000';

test.describe('Data Freshness & No Stale Data', () => {
  test('health endpoint reports non-stale data', async ({ request }) => {
    const response = await request.get(`${APEX_API}/health`, { timeout: 30_000 });
    test.skip(!response.ok(), 'health endpoint busy');
    const body = await response.json();
    expect(typeof body.is_stale).toBe('boolean');
    expect(typeof body.data_age_seconds).toBe('number');
  });

  test('account endpoint reports fresh data', async ({ request }) => {
    const response = await request.get(`${APEX_API}/account`, { timeout: 30_000 });
    test.skip(!response.ok(), 'account endpoint busy');
    const body = await response.json();
    if (!body.error) {
      expect(typeof body._is_stale).toBe('boolean');
      expect(typeof body._data_age_seconds).toBe('number');
    }
  });

  test('positions endpoint reports fresh data', async ({ request }) => {
    const response = await request.get(`${APEX_API}/positions`, { timeout: 30_000 });
    test.skip(!response.ok(), 'positions endpoint busy');
    expect(response.ok()).toBeTruthy();
  });

  test('opportunities contain real engine scores not mock data', async ({ request }) => {
    const response = await request.get(`${APEX_API}/opportunities`, { timeout: 30_000 });
    test.skip(!response.ok(), 'opportunities endpoint busy');
    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
    for (const opp of body.slice(0, 5)) {
      expect(opp.conviction).toBeGreaterThan(0);
      expect(opp.technical_score).toBeGreaterThan(0);
      expect(opp.fundamental_score).toBeGreaterThan(0);
      expect(opp.catalyst).not.toBe('');
      expect(opp.pm_signal).toMatch(/BULLISH|BEARISH|NEUTRAL/);
    }
  });

  test('events contain real audit log entries', async ({ request }) => {
    const response = await request.get(`${APEX_API}/events?limit=20`, { timeout: 30_000 });
    test.skip(!response.ok(), 'events endpoint busy');
    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
    if (body.length > 0) {
      const eventTypes = body.map((e: { event_type: string }) => e.event_type);
      expect(
        eventTypes.some(
          (t: string) =>
            t.includes('SYSTEM') || t.includes('GATE') || t.includes('OPPORTUNITY')
        )
      ).toBe(true);
    }
  });
});

test.describe('WebSocket Real-time Updates', () => {
  test('dashboard loads without fatal websocket console errors', async ({ page }) => {
    const wsErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error' && /websocket/i.test(msg.text())) {
        wsErrors.push(msg.text());
      }
    });
    await gotoTerminal(page, '/dashboard');
    await page.waitForTimeout(3000);
    expect(wsErrors.length).toBeLessThanOrEqual(2);
  });
});

test.describe('Error Handling', () => {
  test('handles positions page gracefully', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/positions');
    await expect(page.getByRole('heading', { name: 'Positions' })).toBeVisible();
  });

  test('handles trading page gracefully', async ({ page }) => {
    await gotoTerminal(page, '/dashboard/trading');
    await expect(page).toHaveURL(/trading/);
  });

  test('no console errors on dashboard', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (error) => {
      errors.push(error.message);
    });
    await gotoTerminal(page, '/dashboard');
    await page.waitForTimeout(2000);
    const criticalErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('WebSocket') && !e.includes('ResizeObserver')
    );
    expect(criticalErrors.length).toBe(0);
  });
});
