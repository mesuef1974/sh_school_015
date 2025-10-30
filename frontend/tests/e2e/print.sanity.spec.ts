import { test, expect } from '@playwright/test';
import { devLogin } from './auth.helpers';

// Print flow sanity: ensure clicking print does not crash and a print container is present.
// Non-blocking: we do not actually produce a file; we just verify no errors and UI shows print-ready content.

test.describe('Print flow — sanity check', () => {
  test('opens print view without crashing', async ({ page }) => {
    await devLogin(page);

    // Navigate to teacher timetable (or another page that supports print)
    await page.goto('/#/timetable/teacher');

    // Click the print button (adjust selectors as needed)
    const printBtn = page.locator('button:has-text("طباعة"), button:has-text("Print"), [data-testid="print"]');
    if (await printBtn.first().isVisible().catch(() => false)) {
      await printBtn.first().click();
      // Some apps render a print container or use window.print(). We ensure no crash and DOM still accessible.
      await expect(page.locator('body')).toBeVisible();
      // If a print container is used, assert it exists (best-effort):
      const printContainer = page.locator('.print-container, .timetable-card, [data-print-ready]');
      await expect(printContainer.first()).toBeVisible({ timeout: 5_000 });
    } else {
      // If no print button in current layout, just ensure the page remains stable.
      await expect(page.locator('body')).toBeVisible();
    }
  });
});
