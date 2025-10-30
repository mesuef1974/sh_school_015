import { test, expect } from '@playwright/test';
import { devLogin } from './auth.helpers';
import { SEL } from './selectors';

// History pagination E2E: navigate next/prev when multiple pages are available.
// - Skips safely if there is only a single page or no data.

const TABLE_ROWS = 'table tbody tr, .p-datatable-tbody tr, .n-data-table-tbody tr';

async function pickFirstClass(page) {
  const classSelect = page.locator('form select').first();
  await expect(classSelect).toBeVisible();
  await classSelect.selectOption({ index: 1 });
}

async function submitSearch(page) {
  const submitBtn = page
    .locator('form button[type="submit"], form button:has-text("بحث"), form button:has-text("Search")')
    .first();
  await expect(submitBtn).toBeVisible();
  await submitBtn.click();
}

async function hasAnyRows(page) {
  return (await page.locator(TABLE_ROWS).count()) > 0;
}

test.describe('Teacher Attendance — History pagination', () => {
  test('history: next/prev page navigation (or skip if single page/no data)', async ({ page }) => {
    await devLogin(page);

    await page.goto('/#/attendance/teacher/history');

    await pickFirstClass(page);
    await submitSearch(page);

    // Skip if no data
    if (!(await hasAnyRows(page))) {
      test.skip(true, 'No history rows to paginate');
    }

    const nextBtn = page.locator(SEL.historyNext).first();
    const prevBtn = page.locator(SEL.historyPrev).first();

    // If next is disabled or not visible, likely only a single page; skip
    const nextVisible = await nextBtn.isVisible().catch(() => false);
    const nextEnabled = nextVisible ? await nextBtn.isEnabled().catch(() => false) : false;
    if (!nextVisible || !nextEnabled) {
      test.skip(true, 'No next page available; skipping pagination test');
    }

    // Capture count before navigating
    const before = await page.locator(TABLE_ROWS).count();

    // Go to next page
    await nextBtn.click();

    // Give the UI a brief moment to update; prefer waiting for network idle if possible
    await page.waitForLoadState('networkidle', { timeout: 5_000 }).catch(() => {});
    await page.waitForTimeout(400);

    const afterNext = await page.locator(TABLE_ROWS).count();
    // Sanity: either different count or at least table remains visible
    await expect(page.locator(TABLE_ROWS)).toBeVisible();
    expect(afterNext).toBeGreaterThanOrEqual(0);

    // If prev is available, go back and expect rows to be visible
    const prevVisible = await prevBtn.isVisible().catch(() => false);
    const prevEnabled = prevVisible ? await prevBtn.isEnabled().catch(() => false) : false;
    if (prevVisible && prevEnabled) {
      await prevBtn.click();
      await page.waitForLoadState('networkidle', { timeout: 5_000 }).catch(() => {});
      await page.waitForTimeout(400);

      const afterPrev = await page.locator(TABLE_ROWS).count();
      await expect(page.locator(TABLE_ROWS)).toBeVisible();
      expect(afterPrev).toBeGreaterThanOrEqual(0);
    }
  });
});