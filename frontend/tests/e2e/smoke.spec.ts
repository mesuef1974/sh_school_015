import { test, expect } from '@playwright/test';

const base = process.env.E2E_BASE_URL || '';

// Skip the whole suite if BASE_URL is not provided (env-gated)
// This keeps CI green when E2E_SMOKE is not enabled.
if (!base) {
  test.describe('E2E smoke (skipped — no E2E_BASE_URL)', () => {
    test('skipped', async () => {
      test.skip(true, 'E2E_BASE_URL is not set');
    });
  });
} else {
  test.describe('E2E smoke', () => {
    test('App loads and main shell renders', async ({ page }) => {
      await page.goto(base);
      await page.waitForLoadState('networkidle');
      // The root element should exist
      const app = page.locator('#app');
      await expect(app).toBeVisible();
      // Expect at least some text in Arabic UI (best-effort, resilient to route)
      const bodyText = await page.locator('body').innerText();
      expect(bodyText.length).toBeGreaterThan(0);
    });

    test('Wing pages are reachable (routes render without crashing)', async ({ page }) => {
      // Try common routes; tolerate 404 HTML shells (SPA will still render)
      const routes = ['/#/wing/timetable/daily', '/#/wing/exits'];
      for (const r of routes) {
        await page.goto(base + r);
        await page.waitForLoadState('networkidle');
        await expect(page.locator('#app')).toBeVisible();
      }
    });
  });
}
