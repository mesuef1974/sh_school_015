import { defineConfig, devices } from '@playwright/test';

// NOTE:
// - We do NOT auto-start the dev server here. Run it separately via:
//   pwsh -File scripts/ops_run.ps1 -Task dev-all
// - baseURL targets the default Vite dev address. Adjust the port if your Vite
//   chooses a different one (scripts/dev_all.ps1 may pick a free port).
// - Router is hash-based, so tests navigate using baseURL + "#/path".

const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173';

export default defineConfig({
  testDir: 'tests/e2e',
  fullyParallel: true,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  // Retry once on CI to reduce flakes; keep 0 locally
  retries: process.env.CI ? 1 : 0,
  // Wait for dev server before tests start (helps avoid ERR_CONNECTION_REFUSED locally/CI)
  // ESM-safe path (avoid require.resolve)
  globalSetup: './tests/e2e/global-setup.ts',
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    video: 'off',
    screenshot: 'off',
    locale: 'ar',
  },
  reporter: [['list'], ['html', { open: 'never' }]],
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], channel: 'msedge' },
    },
    // You can add more browsers if needed:
    // { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    // { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
});
