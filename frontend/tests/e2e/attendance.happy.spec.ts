import { test, expect } from '@playwright/test';
import { devLogin } from './auth.helpers';
import { SEL, waitForToast } from './selectors';

// Happy-path: teacher loads a class, marks one student present, saves, and sees a success toast.

test.describe('Teacher Attendance — happy path', () => {
  test('load → mark present → save → toast', async ({ page }) => {
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

    // Mark first student as present (use stable data-testid if available)
    const markPresent = page.locator(SEL.markPresent);
    if (await markPresent.first().isVisible().catch(() => false)) {
      await markPresent.first().click();
    } else {
      // Fallback: change first status select to "present"
      const firstStatus = page.locator('.student-card select.status-select').first();
      if (await firstStatus.isVisible().catch(() => false)) {
        await firstStatus.selectOption('present');
      }
    }

    // Save attendance
    await page.locator(SEL.saveBtn).first().click();

    // Expect a toast/snackbar to appear (support multiple libraries)
    await waitForToast(page, 15_000);
  });
});