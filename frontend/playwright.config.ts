import { defineConfig, devices } from '@playwright/test';

// E2E smoke tests config. We keep it minimal and env-gated.
// Provide E2E_BASE_URL when running in CI or locally (e.g., http://127.0.0.1:4173).
const BASE_URL = process.env.E2E_BASE_URL || undefined;

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60_000,
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    locale: 'ar',
  },
  reporter: [['list']],
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});