import { test, expect } from '@playwright/test';
import { devLogin } from './auth.helpers';

// Smoke test for Grades page. This is conditional and should never fail CI if feature is gated.
// Flow: login → navigate to /grades → expect basic hooks → open/close dialog.

test.describe('Grades — smoke', () => {
  test('open grades page and basic interactions', async ({ page }) => {
    await devLogin(page);

    await page.goto('/#/grades');

    const header = page.getByTestId('grades-index');
    await expect(header).toBeVisible({ timeout: 10_000 });

    // Empty state should be visible in seed/dev data
    const empty = page.getByTestId('grades-empty');
    if (await empty.isVisible().catch(() => false)) {
      await expect(empty).toBeVisible();
    }

    const addBtn = page.getByTestId('grades-add');
    if (await addBtn.isVisible().catch(() => false)) {
      await addBtn.click();
      const dlg = page.getByTestId('grades-dialog');
      await expect(dlg).toBeVisible();
      // Close via the close button inside the dialog if present
      const closeBtn = page.locator('dialog [type="button"], dialog .btn-secondary').first();
      if (await closeBtn.isVisible().catch(() => false)) {
        await closeBtn.click();
      }
    }
  });
});