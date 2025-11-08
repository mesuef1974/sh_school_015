import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

async function optionalLogin(page: any) {
  const user = process.env.E2E_USER;
  const pass = process.env.E2E_PASS;
  if (!user || !pass) return;
  const base = test.info().project.use?.baseURL || process.env.E2E_BASE_URL || '';
  await page.goto(new URL('/login', base).toString());
  const userSel = "[data-test='login-username'], input[name='username'], #username, input[type='text']";
  const passSel = "[data-test='login-password'], input[name='password'], #password, input[type='password']";
  const submitSel = "[data-test='login-submit'], button[type='submit'], button:has-text('دخول'), button:has-text('Login')";
  await page.waitForTimeout(200);
  const u = page.locator(userSel).first();
  const p = page.locator(passSel).first();
  const b = page.locator(submitSel).first();
  if (!(await u.count())) return; // already logged in or SSO
  await u.fill(user);
  await p.fill(pass);
  await b.click();
  await page.waitForLoadState('networkidle');
}

async function expectNoSeriousA11yViolations(page: any, contextLabel: string) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa'])
    .disableRules(['color-contrast'])
    .analyze();
  const serious = results.violations.filter(v => (v.impact === 'serious' || v.impact === 'critical'));
  if (serious.length) {
    console.warn(`[a11y][${contextLabel}] violations:`, serious.map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.length })));
  }
  await expect(serious.length, `Accessibility serious/critical issues on ${contextLabel}`).toBe(0);
}

const base = process.env.E2E_BASE_URL || '';

if (!base) {
  test.describe('E2E alerts/teacher (skipped — no E2E_BASE_URL)', () => {
    test('skipped', async () => { test.skip(true, 'E2E_BASE_URL is not set'); });
  });
} else {
  test.describe('E2E + A11y: Alerts + Teacher Timetable', () => {
    test('Wing Absences Alerts page is reachable and accessible', async ({ page }) => {
      await page.goto(base);
      await page.waitForLoadState('domcontentloaded');
      await optionalLogin(page);
      await page.goto(new URL('/wing/absences', base).toString());
      // Expect either toolbar card or page header elements
      const header = page.getByText(/الغيابات|التنبيهات|تنبيهات الغياب/i).first();
      await expect(header.or(page.locator('section.page-grid, section.page-grid-wide'))).toBeVisible({ timeout: 10000 });
      await expectNoSeriousA11yViolations(page, 'Wing Absences Alerts');
    });

    test('Teacher Timetable weekly is reachable and accessible', async ({ page }) => {
      await page.goto(base);
      await page.waitForLoadState('domcontentloaded');
      await optionalLogin(page);
      await page.goto(new URL('/timetable/teacher', base).toString());
      // Look for known header text or table container
      const hdr = page.getByText(/جدولي الأسبوعي|جدول الحصص/i).first();
      await expect(hdr.or(page.locator('.timetable-wrapper, .timetable-modern, section.timetable-page'))).toBeVisible({ timeout: 10000 });
      await expectNoSeriousA11yViolations(page, 'Teacher Timetable');
    });
  });
}