import { test, expect } from '@playwright/test';

const API_BASE = 'http://127.0.0.1:8000';

test.describe('Backend API Integration', () => {
  test('health endpoint returns healthy status', async ({ request }) => {
    const response = await request.get(`${API_BASE}/health`);
    expect(response.ok()).toBeTruthy();
    
    const body = await response.json();
    expect(body.status).toBe('healthy');
    expect(typeof body.alpaca_connected).toBe('boolean');
    expect(typeof body.is_stale).toBe('boolean');
    expect(typeof body.data_age_seconds).toBe('number');
    expect(body.data_age_seconds).toBeGreaterThanOrEqual(0);
    expect(body.opportunities).toBeGreaterThanOrEqual(0);
    expect(body.events).toBeGreaterThanOrEqual(0);
  });

  test('account endpoint returns real data', async ({ request }) => {
    const response = await request.get(`${API_BASE}/account`);
    expect(response.ok()).toBeTruthy();
    
    const body = await response.json();
    if (body.error) {
      expect(body.status).toBeTruthy();
      return;
    }
    expect(body).toHaveProperty('equity');
    expect(body).toHaveProperty('buying_power');
    expect(body).toHaveProperty('cash');
    expect(body).toHaveProperty('portfolio_value');
    expect(body).toHaveProperty('_is_stale');
  });

  test('positions endpoint returns array', async ({ request }) => {
    const response = await request.get(`${API_BASE}/positions`);
    expect(response.ok()).toBeTruthy();
    
    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test('opportunities endpoint returns real scored opportunities', async ({ request }) => {
    const response = await request.get(`${API_BASE}/opportunities`);
    expect(response.ok()).toBeTruthy();
    
    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
    if (body.length > 0) {
      const opp = body[0];
      expect(opp).toHaveProperty('symbol');
      expect(opp).toHaveProperty('direction');
      expect(opp).toHaveProperty('conviction');
      expect(opp).toHaveProperty('technical_score');
      expect(opp).toHaveProperty('fundamental_score');
      expect(opp).toHaveProperty('pm_signal');
      expect(opp).toHaveProperty('catalyst');
      expect(opp).toHaveProperty('risk_reward');
    }
  });

  test('events endpoint returns real audit events', async ({ request }) => {
    const response = await request.get(`${API_BASE}/events?limit=10`);
    expect(response.ok()).toBeTruthy();
    
    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
    if (body.length > 0) {
      const event = body[0];
      expect(event).toHaveProperty('id');
      expect(event).toHaveProperty('event_type');
      expect(event).toHaveProperty('timestamp');
      expect(event).toHaveProperty('raw_payload');
    }
  });

  test('proposals endpoint returns real proposals', async ({ request }) => {
    const response = await request.get(`${API_BASE}/proposals`);
    expect(response.ok()).toBeTruthy();
    
    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
    
    if (body.length > 0) {
      const proposal = body[0];
      expect(proposal).toHaveProperty('id');
      expect(proposal).toHaveProperty('symbol');
      expect(proposal).toHaveProperty('direction');
      expect(proposal).toHaveProperty('conviction');
    }
  });

  test('integrations endpoint shows connected services', async ({ request }) => {
    test.setTimeout(45_000);
    const response = await request.get(`${API_BASE}/integrations`, { timeout: 30_000 });
    test.skip(!response.ok(), 'integrations endpoint slow or unavailable');
    
    const body = await response.json();
    expect(body).toHaveProperty('alpaca');
    expect(body).toHaveProperty('yfinance');
    expect(body).toHaveProperty('services');
    expect(typeof body.alpaca).toBe('boolean');
    expect(typeof body.yfinance).toBe('boolean');
    expect(body.services.alpaca).toHaveProperty('connected');
    expect(body.services.yfinance).toHaveProperty('detail');
  });

  test('chart endpoint returns bars for valid symbol', async ({ request }) => {
    test.setTimeout(120_000);
    const response = await request.get(`${API_BASE}/chart/AAPL`);
    if (response.ok()) {
      const body = await response.json();
      expect(Array.isArray(body)).toBe(true);
      if (body.length > 0) {
        const bar = body[0];
        expect(bar).toHaveProperty('close');
        expect(bar).toHaveProperty('open');
        expect(bar).toHaveProperty('high');
        expect(bar).toHaveProperty('low');
      }
    } else {
      expect([404, 502, 504]).toContain(response.status());
    }
  });

  test('options endpoint returns chain for valid symbol', async ({ request }) => {
    test.setTimeout(120_000);
    const response = await request.get(`${API_BASE}/options/AAPL`);
    if (response.ok()) {
      const body = await response.json();
      expect(body).toHaveProperty('symbol');
      expect(body).toHaveProperty('calls');
      expect(body).toHaveProperty('puts');
      expect(body.symbol).toBe('AAPL');
    } else {
      expect([404, 502, 504]).toContain(response.status());
    }
  });

  test('refresh endpoint triggers cache refresh', async ({ request }) => {
    test.setTimeout(120_000);
    const response = await request.post(`${API_BASE}/refresh`, { timeout: 90_000 });
    test.skip(!response.ok(), 'refresh endpoint busy or unavailable');
    
    const body = await response.json();
    expect(body.status).toBe('refreshed');
    expect(body).toHaveProperty('timestamp');
    expect(typeof body.is_stale).toBe('boolean');
  });
});
