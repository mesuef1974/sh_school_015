import { test, expect } from '@playwright/test';
import { devLogin } from './auth.helpers';

// Print smoke: stub window.print and ensure invoking print does not crash.
// Using Teacher Timetable page which exposes a print action.

test.describe('Print smoke — Teacher Timetable', () => {
  test('stub window.print and trigger print action', async ({ page }) => {
    await devLogin(page);

    // Stub window.print before page scripts run
    await page.addInitScript(() => {
      // @ts-ignore
      window.__printed = false;
      // @ts-ignore
      window.print = () => {
        // @ts-ignore
        window.__printed = true;
      };
    });

    await page.goto('/#/timetable/teacher');

    // Find a print control by accessible name or title
    const printBtn = page.locator(
      'button[aria-label="طباعة الجدول"], button:has-text("طباعة"), [title="طباعة الجدول"]'
    );

    if (await printBtn.first().isVisible().catch(() => false)) {
      await printBtn.first().click();
    } else {
      test.skip(true, 'No visible print control found on Teacher Timetable');
    }

    // Verify our stub was invoked
    const printed = await page.evaluate(() => (window as any).__printed === true);
    expect(printed).toBeTruthy();
  });
});
