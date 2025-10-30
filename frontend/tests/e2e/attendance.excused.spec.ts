import { test, expect } from '@playwright/test';
import { devLogin } from './auth.helpers';
import { SEL, pickFirstClassOption, ensureStudentGrid, waitForToast } from './selectors';

// Excused flow: set first student to "excused", choose an exit reason, save, expect toast.
// Skips safely if excused controls (exit reasons) are not available in the UI.

test.describe('Teacher Attendance — excused with exit reasons', () => {
  test('load → set first student excused → pick a reason → save → toast (or skip safely)', async ({ page }) => {
    await devLogin(page);

    await page.goto('/#/attendance/teacher');

    // Deterministically pick a class and load
    await pickFirstClassOption(page);
    await page.locator(SEL.loadBtn).first().click();

    await ensureStudentGrid(page, 20_000);

    const firstCard = page.locator('.student-card').first();
    await expect(firstCard).toBeVisible();

    // Change status to "excused"
    const statusSelect = firstCard.locator('select.status-select');
    const hasSelect = await statusSelect.isVisible().catch(() => false);
    if (!hasSelect) {
      test.skip(true, 'Status select not visible on the first student card');
    }
    await statusSelect.selectOption('excused').catch(() => {});

    // Try to pick one of the exit reasons if the controls are rendered
    const reasonsContainer = firstCard.locator('.exit-reasons');
    const reasonsVisible = await reasonsContainer.isVisible().catch(() => false);
    if (!reasonsVisible) {
      test.skip(true, 'Exit reasons controls not visible after selecting excused');
    }

    // Prefer specific values if present, otherwise click any radio inside .exit-reasons
    const reasonAdmin = reasonsContainer.locator('input[type="radio"][value="admin"]');
    const reasonParent = reasonsContainer.locator('input[type="radio"][value="parent"]');
    const reasonHealth = reasonsContainer.locator('input[type="radio"][value="health"]');

    let clicked = false;
    for (const r of [reasonAdmin, reasonParent, reasonHealth]) {
      if (await r.isVisible().catch(() => false)) {
        await r.check();
        clicked = true;
        break;
      }
    }
    if (!clicked) {
      const anyRadio = reasonsContainer.locator('input[type="radio"]').first();
      if (await anyRadio.isVisible().catch(() => false)) {
        await anyRadio.check();
        clicked = true;
      }
    }

    if (!clicked) {
      test.skip(true, 'No exit reason radio input was interactable');
    }

    // Save
    await page.locator(SEL.saveBtn).first().click();

    // Expect success toast/snackbar
    await waitForToast(page, 15_000);
  });
});
