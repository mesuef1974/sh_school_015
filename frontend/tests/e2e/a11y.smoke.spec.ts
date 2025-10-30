import { test, expect } from '@playwright/test';
import { AxeBuilder } from '@axe-core/playwright';

// A11y smoke — non-blocking by default. Prints serious/critical to console.
// Set E2E_AXE_STRICT=true to fail on serious/critical in CI or locally if desired.

const paths = ['/#/', '/#/login', '/#/timetable/teacher', '/#/attendance/teacher', '/#/attendance/teacher/history'];

for (const p of paths) {
  test(`a11y smoke (serious/critical) → ${p}`, async ({ page }) => {
    await page.goto(p);
    const results = await new AxeBuilder({ page }).analyze();
    const serious = results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical');
    if (serious.length) {
      // Log for visibility
      // eslint-disable-next-line no-console
      console.warn('[a11y] serious/critical violations at', p, serious.map((v) => v.id));
    }
    const strict = String(process.env.E2E_AXE_STRICT || 'false').toLowerCase() === 'true';
    if (strict) {
      expect(serious.length, `A11y serious/critical violations found at ${p}`).toBe(0);
    } else {
      // Non-strict: ensure analysis succeeded
      expect(results.violations).toBeTruthy();
    }
  });
}
