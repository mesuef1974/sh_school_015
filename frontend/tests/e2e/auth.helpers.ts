import { Page, expect } from '@playwright/test';

/**
 * Dev login helper.
 * - Expects the dev server (Vite) to be running and backend reachable via proxy.
 * - Credentials: use E2E_USERNAME / E2E_PASSWORD env vars if set; otherwise fall back to a visible dev form.
 */
export async function devLogin(page: Page) {
  const username = process.env.E2E_USERNAME || 'admin';
  const password = process.env.E2E_PASSWORD || 'admin';

  await page.goto('/#/login');

  // Adjust selectors to your actual login form
  const userSel = 'input[name="username"], input#username, input[type="text"]';
  const passSel = 'input[name="password"], input#password, input[type="password"]';
  const btnSel = 'button[type="submit"], button:has-text("دخول"), button:has-text("Login")';

  await page.fill(userSel, username);
  await page.fill(passSel, password);
  await page.click(btnSel);

  // Expect to be redirected away from /login and see an authenticated UI element
  await page.waitForURL(/#\//, { timeout: 10_000 });
  await expect(page.locator('body')).toBeVisible();
}
