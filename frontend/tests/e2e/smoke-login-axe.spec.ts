import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// Helper: optional login using env credentials, tolerant selectors
async function optionalLogin(page: any) {
  const base = test.info().project.use?.baseURL || '';
  // If no creds provided, skip login
  const user = process.env.E2E_USER;
  const pass = process.env.E2E_PASS;
  if (!user || !pass) return;

  // Navigate to /login (or root, then redirect)
  await page.goto(new URL('/login', base).toString());

  // Try common selectors first (data-test), then fallback to name-based
  const userSel = "[data-test='login-username'], input[name='username'], #username, input[type='text']";
  const passSel = "[data-test='login-password'], input[name='password'], #password, input[type='password']";
  const submitSel = "[data-test='login-submit'], button[type='submit'], button:has-text('دخول'), button:has-text('Login')";

  await page.waitForTimeout(200); // small settle
  const u = await page.locator(userSel).first();
  const p = await page.locator(passSel).first();
  const b = await page.locator(submitSel).first();

  // If username field not present, probably already logged in or custom SSO → skip
  if (!(await u.count())) return;

  await u.fill(user);
  await p.fill(pass);
  await b.click();

  // Wait for potential redirect after login
  await page.waitForLoadState('networkidle');
}

// Axe helper that ignores minor hints and only fails on serious/critical by default
async function expectNoSeriousA11yViolations(page: any, contextLabel: string) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa'])
    .disableRules(['color-contrast']) // optional: noisy in dev themes
    .analyze();

  const serious = results.violations.filter(v => (v.impact === 'serious' || v.impact === 'critical'));
  if (serious.length) {
    console.warn(`[a11y][${contextLabel}] violations:`, serious.map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.length })));
  }
  expect(serious.length, `Accessibility serious/critical issues on ${contextLabel}`).toBe(0);
}

// Smoke: app loads, optional login, Wing Timetable (daily/weekly) and Wing Exits render without crashes
test.describe('E2E Smoke + A11y (Wing core pages)', () => {
  test('App loads and wing pages are accessible', async ({ page, baseURL }) => {
    const base = baseURL || process.env.E2E_BASE_URL || 'http://127.0.0.1:4173';

    // Go to root and ensure app bootstraps
    await page.goto(base);
    await page.waitForLoadState('domcontentloaded');

    // Optional login if creds provided
    await optionalLogin(page);

    // Wing Timetable (daily)
    await page.goto(new URL('/wing/timetable/daily', base).toString());
    // Expect at least the page grid or header to exist
    await expect(page.locator('section.page-grid, section.page-grid-wide, [data-test="wing-timetable"]').first()).toBeVisible({ timeout: 10_000 });
    await expectNoSeriousA11yViolations(page, 'Wing Timetable Daily');

    // Wing Timetable (weekly)
    await page.goto(new URL('/wing/timetable/weekly', base).toString());
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('section.page-grid, section.page-grid-wide').first()).toBeVisible({ timeout: 10_000 });
    await expectNoSeriousA11yViolations(page, 'Wing Timetable Weekly');

    // Wing Exits
    await page.goto(new URL('/wing/exits', base).toString());
    await page.waitForLoadState('domcontentloaded');
    // Check for toolbar or empty-state text presence
    const toolbar = page.locator('.auto-card:has(input[type="date"])');
    const empty = page.getByText(/لا توجد أذونات مطابقة|لا توجد بيانات|جاري التحميل|أذونات الخروج/i).first();
    await expect(toolbar.or(empty)).toBeVisible({ timeout: 10_000 });
    await expectNoSeriousA11yViolations(page, 'Wing Exits');
  });
});
