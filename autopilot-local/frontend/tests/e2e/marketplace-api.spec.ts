import { test, expect } from '@playwright/test';

const MARKET = process.env.NEXT_PUBLIC_APEX_API_URL || 'http://127.0.0.1:8000';

test.describe('Marketplace API (unified :8000)', () => {
  test('health returns alpaca status', async ({ request }) => {
    const response = await request.get(`${MARKET}/api/health`);
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body).toHaveProperty('alpaca');
    expect(body).toHaveProperty('timestamp');
  });

  test('portfolios list returns array', async ({ request }) => {
    const response = await request.get(`${MARKET}/api/portfolios`);
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
    if (body.length > 0) {
      expect(body[0]).toHaveProperty('id');
      expect(body[0]).toHaveProperty('name');
      expect(body[0]).toHaveProperty('return_pct');
    }
  });

  test('dashboard returns account and followed', async ({ request }) => {
    const response = await request.get(`${MARKET}/api/dashboard`);
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body).toHaveProperty('account');
    expect(body).toHaveProperty('followed_portfolios');
    expect(body).toHaveProperty('positions');
  });

  test('polymarket summary', async ({ request }) => {
    const response = await request.get(`${MARKET}/api/polymarket/summary`);
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body).toHaveProperty('bankroll_usd');
  });
});
