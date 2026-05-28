import { defineConfig, devices } from '@playwright/test';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../..');
const videoDir = path.resolve(repoRoot, 'artifacts/submission/video');

export default defineConfig({
  testDir: './tests/e2e',
  testMatch: 'submission-demo.spec.ts',
  timeout: 300_000,
  retries: 0,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:3000',
    headless: true,
    viewport: { width: 1920, height: 1080 },
    video: 'on',
    trace: 'off',
    screenshot: 'off',
    launchOptions: {
      args: ['--font-render-hinting=none'],
    },
  },
  projects: [{ name: 'demo', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `cd "${repoRoot}" && PYTHONPATH=src ${process.env.APEX_PYTHON || 'python'} -m uvicorn backend_api:app --host 127.0.0.1 --port 8000`,
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
  outputDir: videoDir,
});
