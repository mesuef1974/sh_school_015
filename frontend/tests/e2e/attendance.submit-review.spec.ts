import { test, expect } from '@playwright/test';
import { devLogin } from './auth.helpers';
import { SEL, waitForToast } from './selectors';

// Conditional E2E: "Submit for review" flow
// - Uses a stable data-testid on the button when available.
// - Safely skips if the control is not visible/enabled in the current environment (RBAC/feature flag).

test.describe('Teacher Attendance — submit for review (conditional)', () => {
  test('load → click submit-for-review → success toast (or skip if unavailable)', async ({ page }) => {
    await devLogin(page);

    await page.goto('/#/attendance/teacher');

    // Pick the first available class option (index 1 skips the disabled placeholder)
    const classSelect = page.locator(SEL.classFilter);
    await expect(classSelect).toBeVisible();
    await classSelect.selectOption({ index: 1 });

    // Click the load button
    await page.locator(SEL.loadBtn).first().click();

    // Wait for the student grid to render
    await expect(page.locator(SEL.studentGrid)).toBeVisible({ timeout: 15_000 });

    // Find the submit-for-review button
    const submitBtn = page.locator(SEL.submitForReview).first();

    // Skip if not visible or disabled in this environment
    const visible = await submitBtn.isVisible().catch(() => false);
    if (!visible) {
      test.skip(true, 'Submit-for-review control not visible; skipping scenario');
    }

    const enabled = await submitBtn.isEnabled().catch(() => false);
    if (!enabled) {
      test.skip(true, 'Submit-for-review control is disabled; skipping scenario');
    }

    // Click and expect a success toast/snackbar
    await submitBtn.click();

    // Expect a toast/snackbar to appear (supports multiple libraries)
    await expect(toastLocator(page)).toBeVisible({ timeout: 15_000 });
  });
});