# خطة المهام التالية (مختصر تنفيذي)

آخر تحديث: 2025-10-28 12:23 (محلي)

هذه الخطة تلخّص الترتيب الحالي للمهام وما سننفّذه فورًا.

## 1) Phase C — Skeleton وحدة الحضور (الخطوة التالية مباشرة)
- ربط صفحة TeacherAttendance.vue بتدفّق E2E بأقل تغييرات:
  - تحميل الطلاب والسجلات بناءً على class_id + date.
  - دمج النموذج في statusMap (مفتاح: student_id → قيمة: status) مع "present" افتراضيًا لمن لا سجل له.
  - إجراءات سريعة (تحديد الكل حاضر/غائب/متأخر/مُعذَر).
  - حفظ تفاؤلي عبر صف الأوفلاين (enqueueAttendance) + Toasts نجاح/فشل.
- اختبار Back-end مسار سعيد مبسّط (pytest) لتثبيت العقد BE↔FE.
- DoD: المعلّم يحمّل الصف، يغيّر الحالات، يحفظ ويرى تأكيدًا؛ واختبار الـ API الأساسي يمر.

## 2) Phase 2 — i18n/RTL/A11y (إغلاق حرج فقط)
- فحص وصولية (اختياري عند التفعيل) على الصفحات الأساسية وإصلاح المخالفات الحرجة فقط.
- مسح RTL سريع لاستبدال left/right و margin/padding-left/right بخصائص منطقية حين يكون آمنًا.
- التحقق من aria-label للأزرار الأيقونية ومعالم skip/main.
- DoD: لا مخالفات حرجة على الصفحات الأساسية، وواجهة مستقرة RTL/LTR.

## 3) Phase B — Linters/Formatters
- Frontend: ESLint/Prettier عبر npm scripts وربطها بـ verify.
- Backend: Ruff/Black/isort عبر verify؛ توثيق أوامر الإصلاح التلقائي.
- DoD: ops_run.ps1 -Task verify يعطي PASS (دون WARN/SKIP) على مساحة عمل نظيفة.

## 4) تحديث الوثائق
- إضافة قسم "تسجيل الحضور سريعًا" إلى DOC/GETTING_STARTED_ar.md.
- تحديث DOC/STATUS_PROGRESS_ar.md بما تم إنجازه وما أُجّل.

## ما سنبدأ به الآن
- البدء فورًا بتنفيذ بند Phase C (ربط TeacherAttendance.vue E2E والحفظ التفاؤلي + اختبار happy-path).