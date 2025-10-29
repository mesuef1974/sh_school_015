# حالة التقدّم وفق الخطة (ملخّص سريع)

- المرحلة 0 — التشغيل الآمن محليًا: مكتملة عمليًا
  - HTTPS dev يعمل عبر scripts/serve_https.ps1 مع اختيار منفذ تلقائي وكتابة backend/.runtime/dev_origin.txt
  - نقاط الصحة:
    - livez: backend/core/urls.py → تعريف الدالة ~سطر 41، المسار ~سطر 84
    - healthz: مفعّلة ومغطّاة بالاختبارات
  - سكربت dev_all.ps1 ينتظر جاهزية /livez ثم يشغّل Vite ويضبط VITE_BACKEND_ORIGIN/PORT
    - الأسطر ذات الصلة: 52–103 (الانتظار والاكتشاف)، 105–113 (الحقلان VITE_*)

- المرحلة 1 — الحوكمة والمعمارية: الأساسيات موجودة، بحاجة صقل لاحق
  - DRF + SimpleJWT مهيّأ (backend/core/settings_base.py: كتلة SIMPLE_JWT والكوكيز)
  - Linters/Formatters موجودة في المتطلبات، يمكن تعزيزها لاحقًا

- الاختبارات ذات الصلة:
  - tests/test_health.py: يغطي /livez و/healthz (تعريفات عند بدايات الملف: سطور 9–13 تقريبًا)

المهمة التالية المقترحة (وفق الترتيب بالخطة):
- المرحلة 2 — i18n + RTL + الوصولية (بدأ التنفيذ)
  - i18n: تم توصيل vue-i18n بالتطبيق (ar افتراضيًا، en احتياطيًا) مع كشف تلقائي وتخزين اختيار المستخدم.
  - dir: يتم ضبط سمة dir/lang على عنصر html تلقائيًا حسب اللغة (RTL للعربية).
  - UI: تمت إضافة مُبدِّل لغات مرئي في الترويسة (ع/EN) ويعمل فورًا ويحفظ التفضيل.
  - PrimeVue: تم ربط locale الخاصة بـ PrimeVue ديناميكيًا لتتبع لغة الواجهة فور التبديل (أيام/أشهر/رسائل).
  - A11y: تم دمج فحص @axe-core/vue لبيئة التطوير فقط + إضافة رابط "تجاوز إلى المحتوى" وأنماط :focus-visible + مُعلِن مسار Route Announcer (aria-live="polite").
  - RTL: تم استبدال خصائص اتجاهية بخصائص منطقية في بعض الأنماط، وسيستكمل التدقيق لاحقًا.
  - DoD المستهدف: axe-core بلا مخالفات حرجة على الصفحات الأساسية، تبديل اللغات يعمل عبر واجهة مرئية، ومكوّنات PrimeVue تتبع اللغة.

بدائل حسب الأولوية:
- البديل A: إكمال صقل المرحلة 1 (linters/formatters وتثبيت حزم الفرونت الأساسية)
- البديل B: القفز مباشرة للمرحلة 3 — وحدة الحضور Pilot E2E إذا كانت أولوية العمل الوظيفي أعلى

## الخطوات التالية الفورية (حسب الخطة)
- إتمام المرحلة 2 — i18n + RTL + الوصولية:
  - مراجعة سريعة بمساعدة axe (اختياري في التطوير) وإغلاق المخالفات الحرجة على الصفحات الأساسية (الرئيسية، الدخول، الجداول).
  - تدقيق RTL خفيف: استبدال الخصائص الاتجاهية المتبقية بخصائص منطقية حيثما كان آمنًا.
  - تمّ إصلاحان RTL إضافيان اليوم: استبدال left بـ inset-inline-start لكل من نقطة المؤشر الخضراء وعلامة العدّ التنازلي في TeacherTimetable.vue.
    - إضافة إصلاح للجوال: ضمن media query (max-width: 576px) تم استبدال left بـ inset-inline-start لشارة العدّ التنازلي.
  - إصلاح RTL إضافي: في ProfilePage.vue تم استبدال left: 50% بـ inset-inline-start: 50% لموضع تلميح الزر (tooltip).
  - إصلاحات RTL جديدة (اليوم):
    - BreadcrumbRtl.vue: استبدال right/left بعناصر منطقية (inset-inline-end و inset-inline) لقائمة الطيّ ونتائج البحث.
    - TeacherTimetable.vue: تثبيت عمود اليوم sticky باستخدام inset-inline-end بدل right.
    - design-system.css: استبدال border-right بـ border-inline-end في تنويعات التنبيهات (success/warning/danger/info) لدعم RTL/LTR.
  - توثيق ما تم حله وما سيُؤجل كبنود غير حرجة.
  - المرحلة B — Linters/Formatters:
    - إعداد ESLint + Prettier للواجهة مع سكربتات npm (lint/format) وتشغيلها ضمن verify.
    - إعداد Ruff + Black + isort للباك وتشغيلها ضمن verify.
  - المرحلة C — Pilot وحدة الحضور:
    - نموذج Attendance + ViewSet مع فلاتر (date,classId) وصلاحيات أساسية.
    - شاشة إدخال سريعة بالـ Vue Query وتوستس + اختبار بسيط.

  آخر تحديث: 2025-10-28 11:51 (محلي)

## المهام المتبقية (مختصر تنفيذي)
- المرحلة 2 — i18n + RTL + الوصولية (إغلاق متبقٍ):
  - فحص axe (اختياري في التطوير عند تفعيله) على الصفحات الأساسية (الرئيسية/الدخول/الجدول/الغياب) ومعالجة المخالفات الحرجة فقط.
  - تدقيق RTL خفيف: استبدال أي خصائص left/right وmargin/padding-left/right بخصائص منطقية inline-start/inline-end حيثما كان آمنًا.
  - التحقق من المعالم الدلالية للوصولية: header role="navigation" (منجز)، main role="main" + tabindex="-1" (منجز)، وتوفير aria-label لأي أزرار أيقونية بلا نص.
  - تحديث هذا المستند لتوثيق ما أُغلق وما تم تأجيله كغير حرج.
  - DoD: لا مخالفات axe حرجة على الصفحات الأساسية + واجهة تعمل بشكل صحيح في RTL/LTR + تبديل اللغات يحدّث PrimeVue.

- المرحلة B — Linters/Formatters (الحوكمة):
  - الواجهة: إضافة ESLint + Prettier بإعداد بسيط وسكربتات npm (lint، lint:fix، format) وتشغيلها ضمن verify.
  - الباكيند: تفعيل Ruff + Black + isort عبر pyproject.toml/الإعدادات الحالية وإضافة مهام تشغيل واضحة.
  - ربط الاثنين بمسار scripts/ops_run.ps1 -Task verify بحيث تُنفَّذ الفحوص محليًا بسهولة.
  - DoD: verify يمرّ على مشروع نظيف بدون أخطاء لِنتر.

- المرحلة C — Pilot وحدة الحضور (Skeleton):
  - Backend: نقاط API جاهزة (students/records/teacher/classes/history-strict/bulk_save) ضمن AttendanceViewSetV2 ✓
  - Tests (pytest): سيناريوهات أساسية تمر (SQLite/PG) بما في ذلك bulk_save ✓
  - Frontend: صفحة TeacherAttendance.vue محمولة بالكامل (تحميل/حفظ تفاؤلي + صف أوفلاين + Toasts) ✓
  - DoD: المعلّم قادر على تسجيل الحضور محليًا، والاختبارات الأساسية تمر ✓

- التوثيق وتجربة المطوّر:
  - تحديث GETTING_STARTED_ar.md وSTATUS_PROGRESS_ar.md بما يعكس إعدادات اللنتر وكيفية تشغيلها، وواجهات وحدة الحضور عند إضافتها.
  - إبقاء @axe-core/vue اختياريًا ومحمِيًا بالعلم VITE_ENABLE_AXE، مع توضيح كيفية تفعيله عند الحاجة.

- الخطوة التالية مباشرة:
  - استكمال تدقيق RTL الخفيف المتبقي ثم تفعيل مهام Linters/Formatters (المرحلة B) وربطها بمسار verify.

ملاحظة التحديث: 2025-10-28 11:49 (محلي)

---

## تحديث 2025-10-29 07:25 — إغلاق دفعة RTL/A11y والمهام التالية

- ما تم إنجازه اليوم:
  - استبدال text-align:right → text-align:end في المواضع التالية:
    - frontend/src/app/pages/LoginPage.vue (قاعدة سطح المكتب لجزء العلامة التجارية)
    - frontend/src/features/attendance/pages/TeacherAttendanceHistory.vue (رؤوس الجدول .modern-th)
    - frontend/src/features/wings/pages/WingTimetable.vue (عمود الفترات اللاصق .tt7-th-period)
  - مراجعة سريعة للتصميم: TeacherTimetable.vue يستخدم خصائص منطقية مسبقًا (inset-inline-*, text-align:start)، ولا مشاكل متبقية.
  - التحقق من العلامات الدلالية للوصولية: main[role="main"][tabindex="-1"] موجود في App.vue؛ أزرار الأدوات الأيقونية تحوي aria-label/title.
  - مسار التحقق verify: سكربتات ESLint/Prettier مضافة في frontend/package.json؛ إعداد Ruff/Black/isort موجود في pyproject.toml؛ scripts/verify_all.ps1 يشغّل اللنترز بشكل غير حاجز.

- ملاحظات RTL باقية (غير حرجة):
  - وُجدت "left/right" في إعدادات رسوم ECharts داخل StatsPage.vue كسلوك مخططات، وليست خصائص CSS؛ لا تؤثر على RTL.

- المهمة التالية المباشرة (تبدأ الآن):
  1) إتمام إغلاق المرحلة 2 — i18n + RTL + الوصولية:
     - تشغيل فحص axe اختياريًا في التطوير عبر المتغير VITE_ENABLE_AXE ومعالجة المخالفات الحرجة فقط على الصفحات: الرئيسية، الدخول، جدولي، تسجيل الغياب، سجل الغياب.
     - تدقيق RTL خفيف إضافي: التأكد من عدم وجود خصائص left/right أو margin/padding-left/right في CSS؛ استخدام inline-start/inline-end حيثما كان آمنًا.
     - DoD: لا مخالفات axe حرجة + سلوك صحيح RTL/LTR + تزامن PrimeVue مع اللغة.
  2) المرحلة B — Linters/Formatters:
     - تشغيل ESLint/Prettier للواجهة وRuff/Black/isort للخلفية عبر scripts/ops_run.ps1 -Task verify وضبط أي تحذيرات سطحية.
     - DoD: مسار verify يمرّ على شجرة نظيفة بدون أخطاء.
  3) التوثيق:
     - تحديث GETTING_STARTED_ar.md بكيفية تمكين axe وتشغيل verify/lint.

- كيفية التشغيل السريع للتحقق:
  - pwsh -File scripts/ops_run.ps1 -Task dev-all    # تشغيل الباك ثم Vite (تلقائيًا)
  - pwsh -File scripts/ops_run.ps1 -Task verify     # فحوص شبيهة بـ CI (غير حاجزة محليًا)

## تحديث 2025-10-29 07:35 — تحسين verify وإضافة تكامل axe اختياري
- تحسينات تنفيذية سريعة اليوم:
  - verify_all.ps1: عند استخدام -StartBackend أصبح السكربت ينتظر جاهزية /livez بمحاولات متعدّدة لتقليل التقارير المتذبذبة، والنتيجة: Health endpoints = PASS.
  - verify_all.ps1: إذا لم تكن تبعيات الواجهة مثبتة (لا يوجد frontend/node_modules) تتحول فحوص ESLint/Prettier إلى SKIP برسالة إرشادية بدل WARN.
  - frontend/src/main.ts: إضافة تفعيل اختياري لـ axe (dev-only) عبر import ديناميكي مشروط بالعلم VITE_ENABLE_AXE.
  - frontend/.env.example: إضافة VITE_ENABLE_AXE=false افتراضيًا مع تعليق توضيحي.
  - frontend/.eslintrc.cjs: إضافة إعداد ESLint قياسي (Vue 3 + TS + Prettier) لنتائج ثابتة.
  - backend/school/views.py: إصلاح RTL منطقي (text-align:start) في نموذج TimetableImageImportForm.
- نتيجة verify بعد التحسين: Django checks + Tests (SQLite/PG) = PASS، Health endpoints = PASS، Linters Backend = PASS، Linters Frontend = SKIP إذا لم تُثبّت التبعيات محليًا.
- التالي السريع:
  - لتفعيل فحص الوصولية أثناء التطوير: `cd frontend && npm i -D @axe-core/vue` ثم ضع `VITE_ENABLE_AXE=true` في `frontend/.env`.
  - لإغلاق لنتر الواجهة نهائيًا إلى PASS: `cd frontend && npm ci && npm run lint && npm run format`.

## تحديث 2025-10-29 09:10 — CI مُفعّل وإغلاق المرحلة 2 يقترب

- CI (GitHub Actions): تمت إضافة سير عمل `.github/workflows/ci.yml` يتضمن:
  - Backend: ruff + black + isort + Django checks + pytest (SQLite).
  - Frontend: `npm ci` + ESLint + Prettier (check) + Vite build.
- وضع التحقق المحلي:
  - Django checks + migrations: PASS
  - Tests (SQLite/PG): PASS
  - Backend linters: PASS
  - Health probes: PASS
  - Frontend lint/format: SKIP محليًا بسبب قفل Windows على `node_modules` (esbuild.exe/rollup). يمكن إغلاقه بخطوات EPERM الموثقة في GETTING_STARTED_ar.md أو الاعتماد على CI مؤقتًا حتى إزالة القفل.
- الوصولية (dev-only): تم تفعيل مسار بديل للـ axe عبر CDN داخل `frontend/src/main.ts` عند ضبط `VITE_ENABLE_AXE=true`، دون الاعتماد على تثبيت حزمة `@axe-core/vue` (التي فشلت بسبب 404 من سجل npm في بيئتك).

### ما الذي تبقّى للإغلاق النهائي للمرحلة 2
1) فك قفل `node_modules` على ويندوز ثم تشغيل:
   - `cd frontend && npm ci && npm run lint && npm run format`
   - بعد النجاح سيصبح fe_lint=PASS وfe_format=PASS ضمن verify.
2) تشغيل فحص axe مؤقتًا (dev-only) ومعالجة المخالفات الحرجة فقط على الصفحات الأساسية، ثم إعادة `VITE_ENABLE_AXE=false`.

### ملاحظات تشغيل سريعة
- إن استمرت مشكلة EPERM: أوقف عمليات Node/Vite/IDE، استثنِ مجلد المشروع مؤقتًا من مضاد الفيروسات، ثم أعد التشغيل ونفّذ الأوامر أعلاه مباشرة.
- حتى مع تعذّر التشغيل المحلي، سيقوم CI الآن بتشغيل lint/build للواجهة والتأكد من سلامة البناء.

## تحديث الحالة — 2025-10-29 14:46

- المرحلة 2 (i18n + RTL + الوصولية): مُغلقة عمليًا.
  - A11y (dev-only): تم تفعيل فحص axe أثناء التطوير ومعالجة المخالفات الحرِجة عند الحاجة، ثم إطفاؤه.
  - RTL: تم تنفيذ تدقيق منطقي واستبدال الخصائص الاتجاهية بخصائص منطقية حيث كان آمنًا.
- مسار التحقق verify (Windows-safe): أخضر بالكامل.
  - Django checks + migrations: PASS
  - Tests — SQLite: PASS
  - Tests — PostgreSQL: PASS
  - Linters Backend (Ruff/Black/isort): PASS
  - Linters/Format Frontend (ESLint/Prettier): PASS
  - Health probes (HTTPS): PASS
  - Security (اختياري غير حاجز): pip-audit = SKIP/WARN (الأداة غير مثبتة)، npm audit = WARN بيئي

ملاحظات تنفيذية:
- تم ضبط `scripts/verify_all.ps1` لاستخدام سكربتات npm مباشرة مع مسار fallback موثوق على ويندوز.
- تم تشغيل `dev-all` مع `VITE_ENABLE_AXE=true` للفحص ثم إعادتها إلى `false` بعد الإغلاق.

الخطوة التالية المقترحة:
- الانتقال إلى واحدة من:
  1) تقوية E2E لوحدة الحضور (سيناريوهات أساسية + أوفلاين + طباعة + تغذية راجعة).
  2) محور الأمن (رؤوس الأمان CSP/HSTS إنتاجًا + سياسات Referrer + Sentry FE/BE).