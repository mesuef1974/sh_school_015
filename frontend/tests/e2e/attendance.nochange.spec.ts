import { test, expect } from '@playwright/test';
import { devLogin } from './auth.helpers';
import { SEL, ensureStudentGrid } from './selectors';

// No-change save: load a class and click save without modifying any statuses.
// Expectation: UI does not crash; toast may or may not appear depending on backend optimization.

test.describe('Teacher Attendance — save without changes (smoke)', () => {
  test('load → save without changes → UI stable (toast optional)', async ({ page }) => {
    await devLogin(page);

    await page.goto('/#/attendance/teacher');

    // Pick the first available class option (index 1 skips the disabled placeholder)
    const classSelect = page.locator(SEL.classFilter);
    await expect(classSelect).toBeVisible();
    await classSelect.selectOption({ index: 1 });

    // Click the load button
    await page.locator(SEL.loadBtn).first().click();

    // Wait for the student grid to render (skip safely if no students rendered)
    await ensureStudentGrid(page, 20_000);

    // Click save without making any changes
    await page.locator(SEL.saveBtn).first().click();

    // Do not assert toast strictly here; just ensure the UI remains responsive
    await expect(page.locator('body')).toBeVisible();
  });
});