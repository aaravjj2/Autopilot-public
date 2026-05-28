/**
 * Hackathon / Devpost submission demo — records video + screenshots into artifacts/submission/.
 */
import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { gotoTerminal, clickSidebar } from './helpers';

const ARTIFACTS = path.resolve(__dirname, '../../../../artifacts/submission');
const SCREENSHOTS = path.join(ARTIFACTS, 'screenshots');

function pause(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

test('APEX Autopilot full product demo', async ({ page }) => {
  test.setTimeout(300_000);
  fs.mkdirSync(SCREENSHOTS, { recursive: true });

  // ── API proof (fetch + optional docs page) ─────────────────────────────
  const health = await page.request.get('http://127.0.0.1:8000/health');
  expect(health.ok()).toBeTruthy();
  const healthJson = await health.json();
  fs.writeFileSync(path.join(ARTIFACTS, 'api-health.json'), JSON.stringify(healthJson, null, 2));

  const arbRes = await page.request.get('http://127.0.0.1:8000/api/arb/opportunities');
  if (!arbRes.ok()) {
    const healthProbe = await page.request.get('http://127.0.0.1:8000/health');
    const probeText = await healthProbe.text();
    throw new Error(
      `arb API ${arbRes.status()} — ensure APEX backend owns :8000. health=${probeText.slice(0, 120)}`,
    );
  }
  const arbBody = await arbRes.json();
  const arbList = Array.isArray(arbBody)
    ? arbBody
    : (arbBody as { opportunities?: unknown[]; data?: unknown[] }).opportunities ??
      (arbBody as { data?: unknown[] }).data ??
      [];
  fs.writeFileSync(
    path.join(ARTIFACTS, 'api-arb-sample.json'),
    JSON.stringify(
      {
        count: arbList.length,
        sample: arbList.slice(0, 3),
      },
      null,
      2,
    ),
  );

  const proposalsRes = await page.request.get('http://127.0.0.1:8000/proposals');
  if (proposalsRes.ok()) {
    const proposals = await proposalsRes.json();
    const plist = Array.isArray(proposals) ? proposals : [];
    fs.writeFileSync(
      path.join(ARTIFACTS, 'api-proposals-sample.json'),
      JSON.stringify({ count: plist.length, sample: plist.slice(0, 3) }, null, 2),
    );
  }

  // Title card in browser (for video intro)
  await page.setContent(`
    <!DOCTYPE html>
    <html><head><style>
      body { margin:0; background:#0b0f17; color:#f7f8fb; font-family:system-ui,sans-serif;
        display:flex; flex-direction:column; align-items:center; justify-content:center; height:100vh; }
      h1 { font-size:3rem; margin:0 0 0.5rem; color:#ff6a1a; }
      p { color:#aab5ca; font-size:1.25rem; max-width:720px; text-align:center; line-height:1.5; }
      .bar { position:absolute; left:0; top:0; bottom:0; width:8px; background:#ff6a1a; }
    </style></head><body>
      <div class="bar"></div>
      <h1>APEX Autopilot</h1>
      <p>Institutional paper-trading for Kalshi &amp; Polymarket — L0–L4 pipeline, risk gates, operator terminal</p>
      <p style="margin-top:2rem;font-size:0.9rem;">Live demo · ${new Date().toISOString().slice(0, 10)}</p>
    </body></html>
  `);
  await pause(3500);
  await page.screenshot({ path: path.join(SCREENSHOTS, '00-title.png'), fullPage: false });

  const tour: { label: string; path: string; heading: RegExp; file: string; dwellMs: number }[] = [
    { label: 'Overview', path: '/dashboard', heading: /Command Center/, file: '01-overview', dwellMs: 5000 },
    { label: 'Arb Radar', path: '/dashboard/arb-radar', heading: /^Arb Radar$/, file: '02-arb-radar', dwellMs: 6000 },
    { label: 'Signals', path: '/dashboard/opportunities', heading: /Opportunity Signals/, file: '03-signals', dwellMs: 5000 },
    { label: 'Autopilot', path: '/dashboard/autopilot', heading: /Autopilot Pipeline/, file: '04-autopilot', dwellMs: 6000 },
    { label: 'Risk', path: '/dashboard/risk-management', heading: /^Risk Management$/, file: '05-risk', dwellMs: 5000 },
    { label: 'Hive-Mind', path: '/dashboard/ai-hivemind', heading: /AI Hive-Mind/, file: '06-hivemind', dwellMs: 5000 },
    { label: 'Live Feed', path: '/dashboard/live', heading: /^Live Feed$/, file: '07-live-feed', dwellMs: 4000 },
    { label: 'Settings', path: '/dashboard/settings', heading: /Settings/, file: '08-settings', dwellMs: 5000 },
  ];

  for (const stop of tour) {
    await gotoTerminal(page, stop.path);
    await expect(page.getByRole('heading', { name: stop.heading })).toBeVisible({ timeout: 25_000 });
    await pause(stop.dwellMs);
    await page.screenshot({ path: path.join(SCREENSHOTS, `${stop.file}.png`) });
  }

  // Sidebar navigation clip (shows UX flow)
  await gotoTerminal(page, '/dashboard');
  await clickSidebar(page, 'Arb Radar');
  await pause(2000);
  await clickSidebar(page, 'Autopilot');
  await pause(2000);
  await clickSidebar(page, 'Risk');
  await pause(2000);

  // API docs (backend)
  await page.goto('http://127.0.0.1:8000/docs', { waitUntil: 'load', timeout: 30_000 });
  await pause(4000);
  await page.screenshot({ path: path.join(SCREENSHOTS, '09-api-docs.png') });

  // Outro
  await page.setContent(`
    <!DOCTYPE html>
    <html><head><style>
      body { margin:0; background:#0b0f17; color:#f7f8fb; font-family:system-ui,sans-serif;
        display:flex; flex-direction:column; align-items:center; justify-content:center; height:100vh; }
      h1 { font-size:2.2rem; color:#2fe6a7; }
      p { color:#aab5ca; font-size:1.1rem; }
      .bar { position:absolute; left:0; top:0; bottom:0; width:8px; background:#ff6a1a; }
    </style></head><body>
      <div class="bar"></div>
      <h1>Paper-only · Gate-first · Fully auditable</h1>
      <p>github.com/aaravjj2/Autopilot-public</p>
    </body></html>
  `);
  await pause(4000);
  await page.screenshot({ path: path.join(SCREENSHOTS, '10-outro.png') });
});
