import { defineConfig, devices } from '@playwright/test';

const skipWebServer = !!process.env.PW_NO_WEBSERVER;
const jsonReport = process.env.PW_JSON_FILE;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  timeout: 60_000,
  reporter: jsonReport
    ? [
        ['line'],
        ['json', { outputFile: jsonReport }],
      ]
    : [['list']],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || process.env.E2E_WEB_BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    navigationTimeout: 60_000,
  },
  webServer: skipWebServer
    ? undefined
    : {
        command: 'npx next dev --port 3000',
        url: 'http://localhost:3000',
        reuseExistingServer: true,
        timeout: 120_000,
      },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  expect: {
    toHaveScreenshot: { animations: 'disabled' },
  },
});
