import { test, expect } from '@playwright/test';
import { devLogin } from './auth.helpers';
import { SEL, pickFirstClassOption, ensureStudentGrid, waitForToast } from './selectors';

// Mixed-status scenario: set different statuses for multiple students, add a note, save, expect a toast.

test.describe('Teacher Attendance — mixed statuses', () => {
  test('load → set mixed statuses (present/absent/late+note) → save → toast', async ({ page }) => {
    await devLogin(page);

    await page.goto('/#/attendance/teacher');

    // Deterministically pick a class and load
    await pickFirstClassOption(page);
    await page.locator(SEL.loadBtn).first().click();

    await ensureStudentGrid(page, 15_000);

    const cards = page.locator('.student-card');
    const count = await cards.count();
    expect(count).toBeGreaterThan(0);

    // 1) First student → present (use quick action if available)
    const presentBtn = page.locator(SEL.markPresent).first();
    if (await presentBtn.isVisible().catch(() => false)) {
      await presentBtn.click();
    } else {
      await cards.nth(0).locator('select.status-select').selectOption('present');
    }

    // 2) Second student → absent (quick action if available)
    if (count >= 2) {
      const absentBtn = page.locator(SEL.markAbsent).first();
      if (await absentBtn.isVisible().catch(() => false)) {
        await absentBtn.click();
      } else {
        await cards.nth(1).locator('select.status-select').selectOption('absent');
      }
    }

    // 3) Third student → late + add a note (note field visible when status !== 'excused')
    if (count >= 3) {
      const third = cards.nth(2);
      const select = third.locator('select.status-select');
      if (await select.isVisible().catch(() => false)) {
        await select.selectOption('late');
        const note = third.locator('input[type="text"]');
        if (await note.isVisible().catch(() => false)) {
          await note.fill('E2E: تأخير بسيط');
        }
      }
    }

    // Save
    await page.locator(SEL.saveBtn).first().click();

    // Expect success toast/snackbar
    await waitForToast(page, 15_000);
  });
});