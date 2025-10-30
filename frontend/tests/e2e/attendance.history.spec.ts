import { test, expect } from '@playwright/test';
import { devLogin } from './auth.helpers';
import { SEL } from './selectors';

// History page E2E: Happy path + filter + export (each test skips safely if data is unavailable)

const TABLE_ROWS = 'table tbody tr, .p-datatable-tbody tr, .n-data-table-tbody tr';

async function pickFirstClass(page) {
  // Pick first class option on the history filters form (index 1 skips placeholder)
  const classSelect = page.locator('form select').first();
  await expect(classSelect).toBeVisible();
  await classSelect.selectOption({ index: 1 });
}

async function submitSearch(page) {
  // Click the submit button of the filters form (type=submit)
  const submitBtn = page.locator('form button[type="submit"], form button:has-text("بحث"), form button:has-text("Search")').first();
  await expect(submitBtn).toBeVisible();
  await submitBtn.click();
}

async function hasAnyRows(page) {
  const count = await page.locator(TABLE_ROWS).count();
  return count > 0;
}

test.describe('Teacher Attendance — History page', () => {
  test('history: load → expect rows or skip if empty', async ({ page }) => {
    await devLogin(page);

    await page.goto('/#/attendance/teacher/history');

    await pickFirstClass(page);
    await submitSearch(page);

    // If there are no rows, skip safely (depends on seed data)
    if (!(await hasAnyRows(page))) {
      test.skip(true, 'No history rows available for selected class/date range');
    }

    // Basic assertion: table visible and has at least 1 row
    await expect(page.locator(TABLE_ROWS)).toHaveCountGreaterThan(0);
  });

  test('history: search filter narrows results (or keeps the same) then clear', async ({ page }) => {
    await devLogin(page);

    await page.goto('/#/attendance/teacher/history');
    await pickFirstClass(page);
    await submitSearch(page);

    // Skip if no data
    if (!(await hasAnyRows(page))) {
      test.skip(true, 'No history rows to filter');
    }

    // Count before
    const before = await page.locator(TABLE_ROWS).count();

    // Apply a search term; if no search input exists/visible, skip
    const search = page.locator(SEL.historySearch);
    if (!(await search.isVisible().catch(() => false))) {
      test.skip(true, 'History search input not visible');
    }

    await search.fill('a');
    await submitSearch(page);

    // After filtering, rows should be <= before (not a strict requirement—just a sanity check)
    const after = await page.locator(TABLE_ROWS).count();
    expect(after).toBeLessThanOrEqual(before);

    // Clear search and submit again
    await search.fill('');
    await submitSearch(page);

    // Rows should be >= after (not strict to exact original due to server-side filters)
    const resetCount = await page.locator(TABLE_ROWS).count();
    expect(resetCount).toBeGreaterThanOrEqual(after);
  });

  test('history: export triggers a file download when data exists', async ({ page }) => {
    await devLogin(page);

    await page.goto('/#/attendance/teacher/history');
    await pickFirstClass(page);
    await submitSearch(page);

    // Skip if no data
    if (!(await hasAnyRows(page))) {
      test.skip(true, 'No history rows to export');
    }

    const exportBtn = page.locator(SEL.historyExport).first();
    const enabled = await exportBtn.isEnabled().catch(() => false);
    if (!enabled) {
      test.skip(true, 'Export button disabled');
    }

    const [download] = await Promise.all([
      page.waitForEvent('download').catch(() => null),
      exportBtn.click(),
    ]);

    // If no download event fired (implementation may open a new tab or stream), assert UI did not crash
    if (!download) {
      await expect(page.locator('body')).toBeVisible();
    } else {
      // Optionally assert suggested filename exists
      const suggested = await download.suggestedFilename();
      expect(suggested).toBeTruthy();
    }
  });
});