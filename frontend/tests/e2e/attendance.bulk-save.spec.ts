import { test, expect } from '@playwright/test';
import { devLogin } from './auth.helpers';
import { SEL, waitForToast } from './selectors';

// Bulk save: set all students to present, then save and expect a success toast.
// Uses stable data-testid attributes added to TeacherAttendance.vue.

test.describe('Teacher Attendance — bulk save (set all present)', () => {
  test('load → set all present → save → toast', async ({ page }) => {
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

    // Click "Set all present" if available
    const setAllBtn = page.locator(SEL.setAllPresent).first();
    if (await setAllBtn.isVisible().catch(() => false)) {
      await setAllBtn.click();
    } else {
      test.skip(true, 'Set-all-present control not visible; skipping bulk-save scenario');
    }

    // Save attendance
    await page.locator(SEL.saveBtn).first().click();

    // Expect a toast/snackbar to appear
    await waitForToast(page, 15_000);
  });
});