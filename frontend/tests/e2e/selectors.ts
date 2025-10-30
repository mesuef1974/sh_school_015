// Shared selectors and helpers for E2E tests
import { Page, expect } from '@playwright/test';

export const SEL = {
  loadBtn: 'button[data-testid="load-attendance"], form.attendance-form button:has-text("تحميل")',
  classFilter: '[data-testid="filter-class"]',
  markPresent: '[data-testid="mark-present"]',
  markAbsent: '[data-testid="mark-absent"]',
  setAllPresent: 'button[data-testid="set-all-present"]',
  submitForReview: 'button[data-testid="submit-for-review"], button:has-text("إرسال للمراجعة"), button:has-text("Submit for review")',
  saveBtn: '[data-testid="save-attendance"], button:has-text("حفظ"), button:has-text("Save")',
  studentGrid: '[data-testid="student-grid"], .student-grid',
  studentSearch: '[data-testid="student-search"], input[type="search"]',
  statusFilter: '[data-testid="status-filter"]',
  // History page selectors (optional)
  historySearch: '[data-testid="history-search"]',
  historyExport: 'button[data-testid="history-export"], button:has-text("تصدير"), button:has-text("Export")',
  historyPrev: 'button[data-testid="history-prev"]',
  historyNext: 'button[data-testid="history-next"]',
  // Print controls (direct button or within menus)
  printButton: 'button[aria-label="طباعة الجدول"], button:has-text("طباعة"), [title*="طباعة" i], button:has-text("Print"), [title*="Print" i] ',
  printMenuTrigger: 'button[aria-haspopup="menu"], button[aria-expanded][aria-controls], button:has([data-icon="print"])',
  printMenuItem: 'role=menuitem[name=/طباعة|Print/i] , [role="menu"] button:has-text("طباعة"), [role="menu"] a:has-text("طباعة")',
  // Toasts: support multiple libraries used across the app
  toast: '.Toastify__toast-body, .p-toast-message-text, .sonner-toast, .vt-notification',
};

export function toastLocator(page: Page) {
  return page.locator(SEL.toast);
}

export async function waitForToast(page: Page, timeout = 15000) {
  await expect(toastLocator(page)).toBeVisible({ timeout });
}

// Network idle helper to reduce CI flakiness (Windows)
export async function waitForNetworkIdle(page: Page, timeout = 7000) {
  await page.waitForLoadState('networkidle', { timeout }).catch(() => {});
  // small settle
  await page.waitForTimeout(500);
}

// Pick the first available class option (index 1 skips the disabled placeholder)
export async function pickFirstClassOption(page: Page) {
  const classSelect = page.locator(SEL.classFilter);
  await expect(classSelect).toBeVisible();
  await classSelect.selectOption({ index: 1 });
}

export async function ensureStudentGrid(page: Page, timeout = 15000) {
  await expect(page.locator(SEL.studentGrid)).toBeVisible({ timeout });
}

export async function getStudentCardCount(page: Page) {
  return page.locator('.student-card').count();
}

// Open a menu (trigger) then click a target item; both selectors accept multiple fallbacks
export async function openMenuAndClick(page: Page, triggerSelector: string, itemSelector: string) {
  const trigger = page.locator(triggerSelector).first();
  if (await trigger.isVisible().catch(() => false)) {
    await trigger.click();
    // small delay for menu animation
    await page.waitForTimeout(200);
    const item = page.locator(itemSelector).first();
    if (await item.isVisible().catch(() => false)) {
      await item.click();
      return true;
    }
  }
  return false;
}

// Try to trigger print either directly or via a dropdown menu
export async function clickPrintAction(page: Page) {
  const direct = page.locator(SEL.printButton).first();
  if (await direct.isVisible().catch(() => false)) {
    await direct.click();
    return true;
  }
  return openMenuAndClick(page, SEL.printMenuTrigger, SEL.printMenuItem);
}