import { test, expect } from '@playwright/test';
import { devLogin } from './auth.helpers';
import { clickPrintAction } from './selectors';

// Print smoke (menu-aware):
// - Stubs window.print
// - Tries to click a direct print button or open a menu and click the print item
// - Skips safely if no print control is available in the current UI

test.describe('Print smoke — menu aware', () => {
  test('stub window.print → trigger print (direct or via menu)', async ({ page }) => {
    await devLogin(page);

    // Stub window.print before app scripts run
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

    const triggered = await clickPrintAction(page);

    if (!triggered) {
      test.skip(true, 'No print control detected (button or menu item); skipping print smoke');
    }

    const printed = await page.evaluate(() => (window as any).__printed === true);
    expect(printed).toBeTruthy();
  });
});