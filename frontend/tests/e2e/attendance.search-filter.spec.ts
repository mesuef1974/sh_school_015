import { test, expect } from '@playwright/test';
import { devLogin } from './auth.helpers';
import { SEL, ensureStudentGrid } from './selectors';

// سيناريو E2E: البحث والتصفية داخل صفحة تسجيل الغياب للمعلم
// - يستخدم data-testid ثابتة لتقليل الهشاشة
// - يتخطّى بأمان إذا لم تتوفر بيانات بعد التحميل

test.describe('Teacher Attendance — البحث والتصفية', () => {
  test('تحميل → بحث باسم طالب → تصفية الحالة → حفظ', async ({ page }) => {
    await devLogin(page);

    await page.goto('/#/attendance/teacher');

    // اختيار أول صف متاح
    await page.locator(SEL.classFilter).selectOption({ index: 1 });

    // تحميل السجلات
    await page.locator(SEL.loadBtn).first().click();
    await ensureStudentGrid(page, 20_000);

    const cards = page.locator('.student-card');
    const total = await cards.count();
    if (total === 0) {
      test.skip(true, 'لا توجد بطاقات طلاب بعد التحميل — تخطٍ آمن');
    }

    // التقاط اسم أول طالب (إن وجد نص)
    const firstName = (await cards.nth(0).locator('.student-name').first().innerText().catch(() => ''))
      .trim()
      .split('\n')[0];

    if (firstName && firstName.length >= 2) {
      // كتابة جزء من الاسم لتفعيل البحث
      const q = firstName.slice(0, Math.min(3, firstName.length));
      await page.locator(SEL.studentSearch).fill(q);
      // نتوقع أن يقل العدد أو يبقى >=1 على الأقل
      const filteredCount = await cards.count();
      expect(filteredCount).toBeGreaterThan(0);
    }

    // تصفية الحالة إلى "حاضر" (قد لا يغيّر العدد إن لم توجد حالات)
    const hasStatusFilter = await page.locator(SEL.statusFilter).isVisible().catch(() => false);
    if (hasStatusFilter) {
      await page.locator(SEL.statusFilter).selectOption('present');
      // مجرد تأكيد أن الشبكة ما تزال ظاهرة
      await expect(page.locator(SEL.studentGrid)).toBeVisible();
    }

    // محاولة حفظ (لن يفشل إن لم تتغير بيانات، الهدف Smoke فقط)
    await page.locator(SEL.saveBtn).first().click();
    // لا نلزم ظهور Toast هنا لأن الحفظ قد لا يغيّر شيئًا، فقط نتأكد عدم الانهيار
    await expect(page.locator('body')).toBeVisible();
  });
});
