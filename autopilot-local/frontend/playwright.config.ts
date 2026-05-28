import { defineConfig, devices } from '@playwright/test';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../..');

// WSL/Linux without DISPLAY cannot launch headed Chromium — hangs indefinitely.
const isWsl =
  process.platform === 'linux' &&
  Boolean(process.env.WSL_DISTRO_NAME || process.env.WSLENV);
const hasDisplay = Boolean(process.env.DISPLAY || process.env.WAYLAND_DISPLAY);
const headed =
  process.env.PLAYWRIGHT_HEADED === '1' ||
  (process.env.PLAYWRIGHT_HEADED !== '0' && hasDisplay && !isWsl);

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  retries: 2,
  workers: process.env.CI ? 2 : 3,
  use: {
    baseURL: 'http://127.0.0.1:3000',
    headless: true,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  // Preserve existing projects configuration for Chromium
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], headless: true },
    },
  ],
  // DB01: single unified backend on :8000 — :8001 legacy removed
  webServer: [
    {
      command: `cd "${repoRoot}" && PYTHONPATH=src ${process.env.APEX_PYTHON || 'python3'} -m uvicorn backend_api:app --host 127.0.0.1 --port 8000`,
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: 'npm run dev',
      url: 'http://127.0.0.1:3000',
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});