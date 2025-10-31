### خطة اختبارات تفصيلية لصفحات وبطاقات مشرف الجناح

آخر تحديث: 2025-10-30

الغرض: توحيد التغطية الاختبارية (وحدات + تكامل API + طرف-لطرف E2E + وصولية A11y) وربطها مباشرة بكل بند من بنود خطة التنفيذ.

---

1. لوحة الغياب اليومية (/wing/attendance/daily)
- وحدات (Backend)
  - Policy: حالات تصنيف اليوم (unexcused/excused/none) وفق الحصتين الأولى والثانية، مع استثناء العطل. [UT-Daily-Policy]
- تكامل API
  - GET /api/v1/wing/overview/ يستجيب 200 وبنية KPIs صحيحة. [IT-Overview-200]
  - GET /api/v1/wing/daily-absences/ يعيد counts وitems بالحقلين p1/p2 وstate. [IT-DailyAbs-200]
  - GET /api/v1/wing/entered/, /api/v1/wing/missing/ تعيد count/items. [IT-Entered-200] [IT-Missing-200]
- E2E
  - زيارة الصفحة، عرض البطاقات، ظهور الشارات الموحّدة day-state وStatusLegend. [E2E-Daily-Cards]
- A11y
  - أزرار «تحديث» و«الانتقال» قابلة للوصول بلوحة المفاتيح ولها aria-label مناسبة. [AX-Daily-Buttons]

2. طلبات الاعتماد (/wing/approvals)
- وحدات (Backend)
  - قرارات الاعتماد/الرفض واعتبار بعذر مع RBAC جناح المشرف. [UT-Approvals-RBAC]
- تكامل API
  - GET /api/v1/wing/pending/ يعيد قائمة معلّقة. [IT-Pending-200]
  - POST /api/v1/wing/decide/ يعتمد/يرفض ويعيد {updated, action}. [IT-Decide-200]
  - POST /api/v1/wing/set-excused/ يحدّث الحالة ويقفل السجل.
    - يدعم رفع مستند إثبات اختياري (صورة/PDF) عبر multipart/form-data: evidence، evidence_note، مع ids كـ JSON string. الحجم الأقصى 5MB، الأنواع المسموحة: image/jpeg, image/png, image/webp, application/pdf. [IT-Excused-200] [IT-Excused-Evidence]
- E2E
  - التبديل بين الوضعين (daily/period)، تحديد عناصر، تنفيذ اعتماد/رفض/اعتبار بعذر مع رسائل نجاح. [E2E-Approvals-Flow]
- A11y
  - قابلية فرز رؤوس الجدول بالكيبورد، تباين ألوان الشارات وفق المعايير. [AX-Approvals-Table]

3. إدارة الغيابات وتنبيهات الغياب (/wing/absences)
- وحدات (Backend)
  - ترقيم سنوي فريد للتنبيه وربط العام الأكاديمي الحالي. [UT-Alerts-Numbering]
- تكامل API
  - GET /api/v1/attendance/absence/compute-days يحسب O/X. [IT-ComputeDays-200]
  - POST /api/v1/absence-alerts/ ينشئ تنبيهًا بالحقلين O/X. [IT-Alerts-Create-200]
  - GET /api/v1/absence-alerts/{id}/docx يعيد Word أو 404 إن غاب القالب. [IT-Alerts-Docx]
- E2E
  - اختيار طالب وفترة، حساب O/X، إصدار تنبيه، إظهار رابط تنزيل Word. [E2E-Alerts-Issue]
- A11y
  - الحقول والعناصر التفاعلية مسماة بوضوح وقابلة للوصول. [AX-Alerts-Form]

4. CSV (اختياري)
- تكامل API
  - daily-absences وentered/missing تُصدّر CSV عند ?format=csv. [IT-CSV-Exports]
- E2E
  - أزرار تصدير CSV تظهر وتعمل عند التمكين. [E2E-CSV-Buttons]

5. الأداء والموثوقية
- وحدات/تكامل
  - احترام سقف 10k عنصر/يوم، واختبار كاش للـ overview (TTL قصير). [UT-Perf-Cap] [IT-Overview-Cache]

6. الوصولية العامة (A11y)
- E2E
  - فحص دخاني axe للأخطاء الحرجة في الصفحات الثلاث. [AX-Smoke]

---

كيفية التشغيل
- Backend (pytest + pytest-django):
  - من جذر المستودع: `pytest -q`
  - أو مجلد محدد: `pytest tests/backend -q`
- Frontend (Playwright):
  - من frontend: `npx playwright test`

ملاحظات
- بعض الحالات تعتمد بيانات قاعدة محدّدة (أجنحة/صفوف/طلاب/سياسة/عطل). إن لم تتوفر في بيئة التطوير، تُوسم الاختبارات المقابلة بـ skip مع سبب واضح حتى تتوفر بيانات fixtures.
- تم توحيد الألوان عبر CSS: frontend/src/styles/attendance-status.css ويُتحقق من وجود StatusLegend في الصفحات الثلاث.