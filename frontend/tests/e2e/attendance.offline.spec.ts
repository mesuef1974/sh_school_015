import { test, expect } from '@playwright/test';
import { devLogin } from './auth.helpers';
import { SEL, waitForToast, waitForNetworkIdle } from './selectors';

// Offline queue E2E: saving while offline enqueues, then flushes on reconnect.
// Requires the app's offline queue to be enabled in dev (it is by default in shared/offline/queue.ts).

test.describe('Teacher Attendance — Offline queue', () => {
  test('enqueue while offline then flush on reconnect', async ({ context, page }) => {
    await devLogin(page);

    await page.goto('/#/attendance/teacher');

    // Simulate offline
    await context.setOffline(true);

    // Toggle one record
    const togglePresent = page.locator(SEL.markPresent);
    if (await togglePresent.first().isVisible().catch(() => false)) {
      await togglePresent.first().click();
    }

    // Click Save (should enqueue)
    await page.locator(SEL.saveBtn).first().click();

    // Expect UI to not crash; optionally check an offline banner/toast if available
    await expect(page.locator('body')).toBeVisible();

    // Go back online
    await context.setOffline(false);

    // Give the app a moment to flush the queue (it usually syncs automatically)
    await waitForNetworkIdle(page, 8000);

    // Expect success toast/snackbar after flush
    await waitForToast(page, 20000);
  });
});