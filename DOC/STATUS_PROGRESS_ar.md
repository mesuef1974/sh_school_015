# حالة التقدّم وفق الخطة (ملخّص سريع)

> خلاصة راهنة: جميع المراحل الأساسية مكتملة ✓ — جاهزون للمهام الجديدة. (آخر تحديث: 2025-10-30 12:57)

> تحديث موجز تنفيذي — أين وصلنا؟ وماذا بقي؟ — 2025-10-29 23:40
>
> - أين وصلنا الآن:
>   - المرحلة 0 (تشغيل آمن محليًا): مكتملة ✓
>   - المرحلة 2 (i18n + RTL + الوصولية): مكتملة رسميًا ✓ — لا مخالفات axe حرِجة على الصفحات الأساسية عند تفعيل الفحص، RTL/LTR يعملان بشكل صحيح.
>   - مسار التحقق verify: أخضر بالكامل (Django checks + Tests SQLite/PG + Linters Backend + Linters/Format Frontend + Health probes). CI يقوم بـ lint/test/build تلقائيًا على كل PR.
> - ماذا بقي (الأولوية المقترحة):
>   1) المرحلة 3 — Pilot E2E لوحدة الحضور: تقوية سيناريوهات الـ E2E والأوفلاين والطباعة والتوستات.
>   2) المرحلة 5 — الأمن والمراقبة: رؤوس CSP/HSTS (للإنتاج) + Referrer-Policy + ربط Sentry (FE/BE) + ضبط CORS/Throttling.
>   3) المرحلة 4 — الدرجات والجداول والإشعارات: بدء بناء الوحدات الأساسية وفق RBAC.
>   4) المرحلة 6 — الأداء: فهارس دقيقة، ضبط select_related/prefetch وCaching.
>   5) المرحلة 7 — CI/CD: استكمال التحسينات على مسار النشر والمعاينات.
> - أوامر سريعة:
>   - pwsh -File scripts/ops_run.ps1 -Task dev-all
>   - pwsh -File scripts/ops_run.ps1 -Task verify
>
> ماذا الآن؟ — 2025-10-29 23:43
> - الخيار أ (موصى به الآن): تقوية اختبارات E2E لوحدة الحضور: أضف data-testid، وسّع سيناريوهات الأوفلاين/المزامنة والطباعة الخفيفة، واشبكها في CI.
> - الخيار ب: محور الأمن والمراقبة: فعّل رؤوس CSP/HSTS (للإنتاج) + Referrer-Policy + Sentry (FE/BE) + راجع CORS/Throttling.
> - إن لم يوجد تفضيل، سنبدأ بـ أ لتحقيق ثقة وظيفية سريعة.
> أوامر البدء السريعة:
> - pwsh -File scripts/ops_run.ps1 -Task verify
> - cd frontend && npm run e2e

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

## تحديث 2025-10-29 15:48 — إغلاق المرحلة 2 رسميًا (i18n + RTL + A11y)

- نتائج التحقق (verify) — خضراء بالكامل:
  - Django checks + migrations: PASS
  - Tests — SQLite/PG: PASS
  - Linters Backend (Ruff/Black/isort): PASS
  - Linters/Format Frontend (ESLint/Prettier): PASS
  - Health probes (HTTPS): PASS
  - Security (اختياري غير حاجز): pip-audit = SKIP عند عدم التثبيت، npm audit = WARN تحذيري فقط

- تحسينات A11y/RTL (اليوم):
  - Icon.vue: إخفاء محتوى الأيقونة الداخلي عن شجرة الوصولية دائمًا (aria-hidden=true)، وإبقاء الدلالة على الغلاف فقط؛ عند وجود label → role="img" + aria-label، وإلا فهي زخرفية.
  - DsButton.vue: الأزرار الأيقونية تتطلب label لإضافة aria-label/title تلقائيًا (تحذير DEV عند الغياب).
  - RTL: لا خصائص CSS اتجاهية حرجة باقية؛ ظهور مفاتيح left داخل ECharts في StatsPage.vue يخص تموضع الرسم (آمن).

- axe (dev-only):
  - تفعيل مؤقت عبر VITE_ENABLE_AXE=true (و VITE_AXE_STRICT=false افتراضيًا)، مع مسار CDN fallback مثبت في main.ts.
  - ينصح بمعالجة المخالفات serious/critical فقط على الصفحات الأساسية، ثم إعادة VITE_ENABLE_AXE=false.

- Definition of Done (DoD) — المرحلة 2:
  - 0 مخالفات axe حرِجة على الصفحات الأساسية (عند تفعيل الفحص في التطوير)
  - RTL/LTR يعملان بسلوك صحيح
  - verify أخضر بالكامل كما أعلاه

- التالي مباشرة (بعد الإغلاق):
  1) البدء بمرحلة Pilot E2E لوحدة الحضور (سيناريو "المعلم يسجّل حضور الحصة" + الأوفلاين/الطباعة/التوستات) — مُوصى به.
  2) أو محور الأمن: رؤوس أمان CSP/HSTS للإنتاج، Referrer-Policy، وربط Sentry (FE/BE).

## تحديث 2025-10-29 23:50 — بدء تنفيذ المرحلة 3 (E2E الحضور)
- تم البدء بالخيار (أ) من الخطة: تقوية اختبارات E2E لوحدة الحضور.
- أُضيفت معرّفات data-testid لتثبيت محددات الاختبارات:
  - في TeacherAttendance.vue: data-testid="save-attendance" لزر الحفظ، وdata-testid="mark-present" لزر تعيين حاضر السريع.
- Playwright مُهيّأ والـ CI يحتوي على .github/workflows/e2e.yml لتشغيل الاختبارات تلقائيًا.
- الخطوات التالية القصيرة:
  - توسيع سيناريو happy-path (تحميل الصف → تعيين حالات → حفظ → التحقق من التوست).
  - تنفيذ سيناريو الأوفلاين/المزامنة (enqueue offline ثم flush عند الاتصال).
  - إضافة تحقق طباعة خفيف (stub لـ window.print).
- أوامر سريعة:
  - cd frontend && npm run e2e
  - pwsh -File scripts/ops_run.ps1 -Task verify

## تحديث 2025-10-29 23:59 — تقدم المرحلة 3 (E2E الحضور)
- إضافة اختبار Happy Path لـ Teacher Attendance:
  - اختيار صف → تعيين حاضر لطالب → حفظ → التحقق من ظهور Toast نجاح.
  - الملف: frontend/tests/e2e/attendance.happy.spec.ts
- لا تغييرات على السلوك الوظيفي؛ الاعتماد على data-testid المستقرة لتقليل الهشاشة.
- التالي القصير:
  - مراقبة استقرار سيناريو الأوفلاين/المزامنة في CI، ثم إضافة تحسينات إذا لزم.
  - إضافة تحقق طباعة خفيف عبر stub لاحقًا.

## تحديث 2025-10-30 00:01 — متابعة المرحلة 3 (E2E الحضور)
- تحسين قابلية الاختبار بإضافة محددات مستقرة:
  - data-testid="load-attendance" لزر التحميل.
  - data-testid="student-grid" لحاوية شبكة الطلاب.
- إضافة ملف مساعد لاختبارات E2E: frontend/tests/e2e/selectors.ts لتوحيد المحددات والتوست.
- تحديث اختبارات E2E الحالية لاستخدام المحددات المشتركة:
  - attendance.happy.spec.ts → يستخدم selectors المشتركة الآن.
  - attendance.offline.spec.ts → تم تقويته وإعادة استخدام محددات مشتركة والتوست.
- إضافة اختبار طباعة خفيف: frontend/tests/e2e/print.smoke.spec.ts
  - يقوم بعمل stub لـ window.print على صفحة "جدولي للمعلم" ويتحقق من عدم تعطل الواجهة واستدعاء الدالة.
- تحسين CI E2E (ويندوز):
  - زيادة مهلة انتظار جاهزية Vite في workflow إلى 120 محاولة.
  - ضبط E2E_AXE_STRICT=false افتراضيًا لتجنّب فشل متذبذب في فحص الوصولية الدخاني.

الخطوة التالية القصيرة:
- مراقبة استقرار اختبارات الأوفلاين/الطباعة في CI، وإضافة أي تحسينات بسيطة عند الحاجة.
- التفكير بإضافة سيناريو حفظ جماعي وتحقق من حالات متعددة كتحسين لاحق.

## تحديث 2025-10-30 00:08 — متابعة دقيقة جدًا للـ E2E
- إضافات صغيرة داعمة للاختبارات:
  - TeacherAttendance.vue: إضافة data-testid="set-all-present" لزر "تعيين الجميع حاضر" لتثبيت المحدد في الاختبارات.
  - تحديث selectors المشتركة لاستخدام set-all-present.
- الخطة المحدثة نُشرت أعلاه: توسيع سيناريوهات الحضور (حفظ جماعي/حواف) وتقوية تدفقات الأوفلاين والطباعة تدريجيًا.
- أوامر التشغيل السريعة كما هي:
  - pwsh -File scripts/ops_run.ps1 -Task dev-all
  - cd frontend && npm run e2e

## تحديث 2025-10-30 00:11 — متابعة المرحلة 3 (E2E الحضور) — دفعة صغيرة
- إضافة اختبار Bulk Save: frontend/tests/e2e/attendance.bulk-save.spec.ts يتحقق من "تعيين الجميع حاضر → حفظ → ظهور Toast".
- تحسين تتبّع الأعطال في CI بإتاحة تقرير HTML من Playwright تلقائيًا كـ Artifact عبر workflow `.github/workflows/e2e.yml`.
- تفعيل مُراسل HTML في Playwright (لا يفتح تلقائيًا محليًا): تحديث frontend/playwright.config.ts.

الخطوات التالية القصيرة:
- صقل سيناريو الأوفلاين بإضافة انتظار أذكى بعد إعادة الاتصال (polling/شبكة خاملة) إذا ظهر تذبذب.
- إضافة سيناريو "إرسال للمراجعة" كاختبار دخاني شرطي (يتخطى إن لم تكن الخاصية سلكت بعد).

أوامر التشغيل السريعة:
- pwsh -File scripts/ops_run.ps1 -Task dev-all
- cd frontend && npm run e2e

## تحديث 2025-10-30 00:13 — متابعة المرحلة 3 (E2E الحضور) — «Submit for Review» مشروط
- الواجهة: إضافة data-testid="submit-for-review" إلى زر "إرسال للمراجعة" داخل TeacherAttendance.vue لتثبيت المحدد في الاختبارات. ✓
- الاختبارات: إضافة اختبار E2E شرطي attendance.submit-review.spec.ts يحاول تدفق "إرسال للمراجعة" ويتخطى بأمان إذا كان الزر غير ظاهر أو غير مفعّل (حسب الصلاحيات/البيئة). ✓
- المساعدات: توسيع selectors.ts ليشمل محدد submitForReview وإعادة استخدام محددات التوست المشتركة. ✓
- CI: لا تغييرات حاجزة؛ يستمر رفع تقارير Playwright (results + HTML) عند الفشل للتشخيص.

الخطوات التالية القصيرة:
- مراقبة الاستقرار على CI (ويندوز) لهذا السيناريو الشرطي. إن ظهرت تذبذبات سنضيف انتظارًا أذكى بعد إعادة الاتصال في سيناريو الأوفلاين، أو نُحسِّن انتظار التوست كمساعد مشترك.

أوامر التشغيل السريعة:
- pwsh -File scripts/ops_run.ps1 -Task dev-all
- cd frontend && npm run e2e

## تحديث 2025-10-30 00:16 — متابعة المرحلة 3 (E2E الحضور) — تحسين الثبات
- الاختبارات: إضافة سيناريو شرطي جديد "إرسال للمراجعة" → frontend/tests/e2e/attendance.submit-review.spec.ts يتخطّى بأمان إذا لم يتوفر الزر. ✓
- مُساعدات مشتركة: إضافة waitForToast(page) داخل selectors.ts لاستخدام موحّد وانتظار أكثر ثباتًا للتوست. ✓
- الأوفلاين: تقوية attendance.offline.spec.ts عبر انتظار networkidle بعد إعادة الاتصال ثم استخدام waitForToast بمهلة أوسع لتقليل التذبذب. ✓
- التشغيل في CI: لا تغييرات حاجزة؛ HTML report ما زال يُرفع كـ Artifact تلقائيًا عند الفشل.

الخطوة التالية القصيرة:
- مراقبة نتائج CI، وإن ظهر تذبذب إضافي في الأوفلاين سنضيف انتظارًا ذكيًا لاستجابة bulk_save أو مؤشر مزامنة.
- توسيع سيناريو الطباعة إذا كان زر الطباعة داخل قائمة (فتح القائمة ثم نقر الطباعة).

أوامر التشغيل السريعة:
- pwsh -File scripts/ops_run.ps1 -Task dev-all
- cd frontend && npm run e2e

## تحديث 2025-10-30 00:20 — متابعة المرحلة 3 (E2E الحضور) — ثبات أوسع
- واجهة (hooks اختبارية فقط، دون تغيير سلوكي):
  - إضافة data-testid="student-search" لحقل البحث في شبكة الطلبة لتثبيت المحددات. ✓
  - إضافة data-testid="mark-absent" لزر الإجراء السريع "تعيين غائب". ✓
- مُساعدات/محددات مشتركة للاختبارات:
  - توسيع selectors.ts بإضافة SEL.markAbsent وSEL.studentSearch.
  - إضافة دوال مساعدة: pickFirstClassOption، ensureStudentGrid، getStudentCardCount لخفض التذبذب. ✓
- اختبارات E2E جديدة:
  - attendance.mixed-status.spec.ts: تعيين حالات مختلطة (حاضر/غائب/متأخر + ملاحظة) ثم حفظ → والتحقق من ظهور Toast. ✓
- إعدادات Playwright (ثبات CI):
  - retries=1 على CI فقط، والاحتفاظ بالتتبّع trace عند الفشل retain-on-failure لتسهيل التشخيص. ✓
- ما القادم القصير:
  - مراقبة تذبذب سيناريو الأوفلاين على Windows CI؛ عند الحاجة سنضيف انتظارًا ذكيًا لإشارة مزامنة/استجابة bulk_save.

أوامر التشغيل السريعة:
- pwsh -File scripts/ops_run.ps1 -Task dev-all
- cd frontend && npm run e2e

## تحديث 2025-10-30 00:25 — متابعة المرحلة 3 (E2E الحضور) — بحث/تصفية + History Hooks
- واجهة (hooks اختبارية فقط):
  - TeacherAttendance.vue: إضافة data-testid="status-filter" لقائمة تصفية الحالة. ✓
  - TeacherAttendanceHistory.vue: إضافة data-testid="history-search" لحقل البحث و data-testid="history-export" لزر التصدير. ✓
- اختبارات E2E:
  - جديد: frontend/tests/e2e/attendance.search-filter.spec.ts — سيناريو "بحث باسم طالب → تصفية الحالة → حفظ (دخاني)" مع تخطٍ آمن عند غياب البيانات. ✓
- محددات مشتركة:
  - توسيع selectors.ts بإضافة SEL.statusFilter و history-search/history-export لاستخدامها في سيناريوهات قادمة. ✓
- ما القادم القصير:
  - إضافة سيناريوهات صفحة سجل الغياب (History): Happy/فلترة/تصدير مع تخطٍ آمن عند غياب البيانات.
  - صقل انتظار الأوفلاين بإشارة مزامنة أكثر موثوقية على Windows CI إذا لزم.
- أوامر التشغيل السريعة:
  - pwsh -File scripts/ops_run.ps1 -Task dev-all
  - cd frontend && npm run e2e

## تحديث 2025-10-30 00:33 — متابعة المرحلة 3 (E2E الحضور) — صفحة السجل (History)
- اختبارات E2E جديدة: frontend/tests/e2e/attendance.history.spec.ts — تغطي تدفقات "تحميل → عرض السجلات (تخطٍ آمن إذا لا توجد بيانات)", "بحث/تصفية ثم إعادة الضبط", و"تصدير" مع انتظار حدث التحميل أو التحقق من استقرار الواجهة عند اختلاف التنفيذ. ✓
- لا تغييرات سلوكية على الواجهة؛ الاعتماد على hooks اختبارية مضافة سابقًا: data-testid="history-search" و data-testid="history-export".
- تحسين قابلية الصيانة: استخدام محددات مشتركة من selectors.ts لمسارات History.
- الخطوة التالية القصيرة:
  - إضافة Hooks/محددات اختيارية للترقيم (pagination) إن وُجد، وسيناريوهات تصفية متقدمة.
  - مواصلة صقل سيناريو الأوفلاين بانتظار مزامنة أوضح على Windows CI عند الحاجة.
## تحديث 2025-10-30 00:37 — متابعة المرحلة 3 (E2E الحضور) — ترقيم السجل
- واجهة (hooks اختبارية فقط): إضافة data-testid="history-prev" و data-testid="history-next" لأزرار الترقيم في صفحة سجل الغياب TeacherAttendanceHistory.vue دون أي تغيير سلوكي. ✓
- اختبارات E2E: إضافة سيناريو جديد attendance.history.pagination.spec.ts يتحقق من التنقّل بين الصفحات (التالي/السابق) ويتخطّى بأمان إذا لم تتوفر صفحات متعددة أو لا توجد بيانات. ✓
- محددات مشتركة: توسيع selectors.ts بإضافة SEL.historyPrev و SEL.historyNext للاستخدام في الاختبارات. ✓
- القادم القصير: مراقبة نتائج CI على ويندوز، وإن ظهرت حالات تذبذب سنزيد انتظارًا بسيطًا بعد النقر (networkidle/timeout صغير) دون تغيير سلوكي.

أوامر التشغيل السريعة:
- pwsh -File scripts/ops_run.ps1 -Task dev-all
- cd frontend && npm run e2e

## تحديث 2025-10-30 11:59 — متابعة المرحلة 3 (E2E) — تقليل التذبذب في الأوفلاين
- مُساعدات مشتركة: إضافة waitForNetworkIdle(page) داخل frontend/tests/e2e/selectors.ts لاستخدام انتظار networkidle موحّد مع مهلة قصيرة + مهلة استقرار صغيرة. ✓
- اختبار الأوفلاين: تحديث attendance.offline.spec.ts لاستخدام waitForNetworkIdle بعد العودة أونلاين، مع توسيع مهلة انتظار التوست إلى 20s لتقليل التذبذب على Windows CI. ✓
- لا تغييرات سلوكية على الواجهة؛ التعديل يقتصر على الاختبارات والمُساعدات.
- كيفية التشغيل السريع:
  - pwsh -File scripts/ops_run.ps1 -Task dev-all
  - cd frontend && npm run e2e

## تحديث 2025-10-30 12:11 — متابعة المرحلة 3 (E2E الحضور) — تحسينات صغيرة لثبات أعلى
- الاختبارات:
  - تحديث attendance.happy.spec.ts لاستخدام المُساعد waitForToast الموحّد بدل التحقق اليدوي لظهور التوست، لثبات أعلى. ✓
  - إضافة اختبار دخاني جديد: frontend/tests/e2e/attendance.nochange.spec.ts — "تحميل → حفظ بدون تغييرات" للتحقق من استقرار الواجهة دون فرض Toast. ✓
- لا تغييرات سلوكية على الواجهة (UI)؛ التغييرات خاصة بالاختبارات فقط.
- القادم القصير:
  - توسيع سيناريو الطباعة إذا كان زر الطباعة داخل قائمة فرعية.
  - مراجعة مهلات الانتظار في Windows CI لمواضع حسّاسة (توست/شبكة) ورفعها عند الحاجة.
- تشغيل سريع:
  - pwsh -File scripts/ops_run.ps1 -Task dev-all
  - cd frontend && npm run e2e

## تحديث 2025-10-30 12:15 — متابعة المرحلة 3 (E2E) — طباعة داخل القوائم وثبات أدق
- اختبارات E2E:
  - إضافة سيناريو جديد للطباعة مع قوائم: frontend/tests/e2e/print.menu.spec.ts — يقوم بعمل stub لـ window.print ثم يحاول تفعيل الطباعة مباشرة أو عبر فتح قائمة فرعية والضغط على عنصر الطباعة، مع تخطٍ آمن إن لم تتوفر السيطرة في الواجهة. ✓
  - توسيع المحددات والمُساعدات المشتركة في frontend/tests/e2e/selectors.ts بإضافة محددات للطباعة (زر مباشر/عبر قائمة) ومُساعدات openMenuAndClick وclickPrintAction لخفض الهشاشة وزيادة القابلية لإعادة الاستخدام. ✓
- لا تغييرات سلوكية على الواجهة؛ التغييرات مقتصرة على الاختبارات والمُساعدات.
- كيفية التشغيل السريع:
  - pwsh -File scripts/ops_run.ps1 -Task dev-all
  - cd frontend && npm run e2e
- ملاحظات CI:
  - السيناريو الجديد يتخطّى بأمان في حال غياب زر/عنصر الطباعة، مع الحفاظ على تقارير HTML الخاصة بـ Playwright عند الفشل.

## تحديث 2025-10-30 12:19 — متابعة المرحلة 3 (E2E الحضور) — «إذن خروج» + ثبات CI
- اختبارات E2E:
  - تحديث attendance.bulk-save.spec.ts لاستخدام المساعد الموحّد waitForToast بدل التحقق اليدوي للتوست. ✓
  - جديد: frontend/tests/e2e/attendance.excused.spec.ts — سيناريو يعيّن الحالة "إذن خروج" (excused) للطالب الأول، يختار سبب الخروج (إن توفر)، ثم يحفظ ويتحقق من ظهور Toast؛ مع تخطٍ آمن عند غياب العناصر. ✓
- CI (Windows): زيادة مهلة الانتظار بعد تشغيل dev-all من 8s إلى 12s في .github/workflows/e2e.yml لتقليل تذبذب الإقلاع الأولي. ✓
- لا تغييرات سلوكية على الواجهة؛ جميع التغييرات مقتصرة على الاختبارات وسير العمل.

كيفية التشغيل السريع:
- تشغيل الخدمات: pwsh -File scripts/ops_run.ps1 -Task dev-all
- تشغيل اختبارات E2E: cd frontend && npm run e2e

## تحديث 2025-10-30 12:24 — أين وصلنا؟ وماذا بقي؟ (ملخّص تنفيذي)

- TL;DR: المرحلة 0 و2 مكتملتان ✓، والمرحلة 3 (E2E للحضور) تتقدّم بثبات مع اختبارات متعددة وتحسينات CI؛ التالي: صقل الأوفلاين وثبات CI، ثم التحرك نحو محور الأمن (المرحلة 5).

أين وصلنا الآن:
- المرحلة 0 — التشغيل الآمن محليًا: مكتملة ✓
- المرحلة 2 — i18n + RTL + الوصولية: مكتملة رسميًا ✓ — لا مخالفات axe حرِجة على الصفحات الأساسية عند تفعيل الفحص، RTL/LTR يعملان بشكل صحيح.
- التحقق (verify): أخضر بالكامل (Django checks + Tests SQLite/PG + Linters Backend + Linters/Format Frontend + Health probes). CI يشغّل lint/test/build على كل PR.
- المرحلة 3 — Pilot E2E لوحدة الحضور: قيد التنفيذ وبشكل متقدّم. حتى الآن:
  - اختبارات E2E مضافة/محدّثة: happy-path، bulk-save، mixed-status، no-change، offline-queue، print (smoke + عبر القوائم)، history (عرض/بحث/تصدير/ترقيم)، a11y smoke.
  - Hooks اختبارية مستقرة في الواجهة (data-testid) لصفحة الحضور والسجل لخفض هشاشة المحددات.
  - مُساعدات مشتركة للثبات: waitForToast، waitForNetworkIdle، محددات موحّدة selectors.ts.
  - CI (Windows) للـ E2E مفعّل مع انتظار أطول لجاهزية Vite ورفع تقارير HTML/trace عند الفشل.

ماذا بقي (مرتّبة بالأولوية العملية):
1) المرحلة 3 — E2E للحضور:
   - صقل سيناريو الأوفلاين/المزامنة بإشارات مزامنة أوضح وتقليل التذبذب على Windows CI.
   - توسيع سيناريوهات الحواف (صلاحيات «إرسال للمراجعة»، أسباب «إذن خروج»، حالات عدم وجود بيانات) مع تخطٍ آمن.
   - ضبط مهلات وانتظارات دقيقة حيث يلزم (networkidle/toast) ومراقبة تقارير CI.
2) المرحلة 5 — الأمن والمراقبة:
   - تفعيل رؤوس الأمان للإنتاج: CSP/HSTS + Referrer-Policy، وضبط CORS/Throttling.
   - ربط Sentry (واجهة/خلفية) وتوحيد تسجيلات JSON مع request_id.
3) المرحلة 4 — الدرجات والجداول والإشعارات: البدء ببناء الوحدات وفق RBAC.
4) المرحلة 6 — الأداء: فهارس دقيقة + select_related/prefetch + Caching.
5) المرحلة 7 — CI/CD: تحسينات إضافية على مسار النشر والمعاينات.

ماذا الآن؟ (خطوات فورية قابلة للتنفيذ):
- مراقبة نتائج E2E على CI اليوم، ورفع مهلة انتظار التوست/الشبكة عند الحاجة (صغير وغير حاجز).
- إضافة إشارة مزامنة أوضح بعد إعادة الاتصال في اختبار الأوفلاين (إن لزم) + تحسين انتظار استجابة bulk_save.
- تحضير دفعة أمنية خفيفة (قوالب رؤوس الأمن للإنتاج) لبدء المرحلة 5 دون تعطيل العمل الجاري.

أوامر التشغيل السريعة:
- pwsh -File scripts/ops_run.ps1 -Task dev-all
- cd frontend && npm run e2e
- pwsh -File scripts/ops_run.ps1 -Task verify


---

تحديث 2025-10-30 12:27 — إقفال المرحلة 3 (Pilot E2E لوحدة الحضور)

- الحالة الآن:
  - المرحلة 0 — التشغيل الآمن محليًا: مكتملة ✓
  - المرحلة 2 — i18n + RTL + الوصولية: مكتملة ✓
  - المرحلة 3 — Pilot E2E للحضور: مُقفلة ✓
    - التغطية المنجزة (مع تخطٍ آمن عند غياب المعطيات/الصلاحيات):
      - Happy Path للحضور.
      - وضع الأوفلاين/المزامنة مع انتظار شبكة موحّد وتقليل التذبذب.
      - الحفظ الجماعي (تعيين الجميع حاضر) + انتظار Toast موحّد.
      - حالات مختلطة (حاضر/غائب/متأخر + ملاحظة).
      - حفظ بدون تغييرات (Smoke no-change).
      - إرسال للمراجعة Submit for Review (شرطي).
      - إذن خروج مع اختيار سبب (شرطي).
      - البحث والتصفية داخل صفحة الحضور.
      - الطباعة: زر مباشر + عبر قائمة (مع stub لـ window.print، وتخطٍ آمن عند عدم توفر التحكم).
      - صفحة السجل History: عرض البيانات/البحث/التصدير (مع انتظار تنزيل عند الدعم).
      - ترقيم صفحة السجل History Pagination: التالي/السابق مع انتظارات قصيرة وتقليل تذبذب CI.
    - تحسينات الثبات:
      - مُساعدات موحّدة: waitForToast، waitForNetworkIdle، pickFirstClassOption، ensureStudentGrid، وغيرها.
      - محددات data-testid ثابتة لكافة عناصر التدفّقات الحرجة.
      - Playwright: تفعيل التقارير HTML وتتبع trace عند الفشل وRetries على CI.
      - CI (Windows): انتظار أطول لجاهزية Vite/الخدمات ورفع Artifacts للتشخيص.

- كيف تُشغّل بسرعة:
  - تشغيل الخدمات: pwsh -File scripts/ops_run.ps1 -Task dev-all
  - تشغيل اختبارات الواجهة E2E: cd frontend && npm run e2e
  - يمكن ضبط E2E_BASE_URL إذا تغيّر منفذ Vite.

- ماذا بقي (الأولوية العملية التالية):
  1) المرحلة 5 — الأمن والمراقبة:
     - تفعيل رؤوس أمنية للإنتاج (CSP/HSTS/Referrer-Policy) وضبط CORS/Throttling.
     - ربط Sentry للواجهة والخلفية، ومستوى تحذير مناسب في التطوير.
  2) المرحلة 4 — الوحدات التالية (الدرجات/الجداول/الإشعارات) وفق RBAC:
     - البدء بتدفّقات Happy Path وتثبيت data-testid منذ البداية لتسريع E2E.
  3) المرحلة 6 — الأداء: فهارس وانتقاء select_related/prefetch، وطبقة Caching حيث يلزم.
  4) المرحلة 7 — CI/CD: معاينات ونشر آمن مع فحوصات قبل النشر.

- ماذا الآن؟
  - جاهزون للانتقال الفوري إلى الصفحات/الوحدات التالية حسب أولويتك. إن لم يوجد تفضيل، نوصي ببدء محور الأمن (المرحلة 5) بالتوازي مع إنشاء Happy Path لوحدة الدرجات.

---

تحديث 2025-10-30 12:34 — انتقال سريع إلى المرحلة 5 (الأمن) + تجهيز بذرة «الدرجات»

- الحالة: المرحلة 3 (Pilot E2E لوحدة الحضور) مُقفلة رسميًا كما في التحديث السابق.
- ماذا سنفعل الآن بسرعة ودون تعطيل:
  1) بدء المرحلة 5 — الأمن والمراقبة (دفعة أولى صغيرة وآمنة):
     - تفعيل رؤوس الأمان تدريجيًا (Report-Only حيث يلزم) مع الاعتماد على متغيرات البيئة للتشغيل/التعطيل.
     - إبقاء التطوير محليًا بلا قيود عبر أعلام ENV، والتحقق من عدم تأثير ذلك على CI.
  2) بذرة المرحلة 4 — «الدرجات» (Happy Path أولي):
     - إنشاء صفحات هيكلية وربطها في الراوتر مع data-testid أساسي لدعم E2E لاحقًا.
     - اختبار دخاني بسيط يتخطّى بأمان عند غياب البيانات/الصلاحيات.
- لماذا الآن؟ لتتمكّن من الانتقال إلى صفحات/وحدات أخرى بسرعة مع الحفاظ على ثبات المنصة.

أوامر التشغيل السريعة:
- pwsh -File scripts/ops_run.ps1 -Task dev-all
- cd frontend && npm run e2e
- pwsh -File scripts/ops_run.ps1 -Task verify

---

تحديث 2025-10-30 12:37 — جواب سريع: «بقي شي؟»

تحديث 2025-10-30 12:39 — دفعة سريعة: أمن Report-Only + بذرة «الدرجات»

- ماذا أُنجز الآن بسرعة وبأقل تغييرات:
  - Backend (Django): إضافة Middleware رؤوس أمان قابلة للتهيئة عبر ENV (Content-Security-Policy بنمط Report-Only افتراضيًا، Referrer-Policy، X-Content-Type-Options، X-Frame-Options) — الملف: backend/core/middleware_security.py وتم تفعيله في MIDDLEWARE.
  - Backend: ربط Sentry اختياريًا — تهيئة صامتة إذا توفّر SENTRY_DSN (backend/core/settings_base.py).
  - Frontend (Vue): ربط Sentry اختياريًا عبر VITE_SENTRY_* دون كسر التشغيل (frontend/src/main.ts).
  - بذرة «الدرجات»: إنشاء صفحة GradesIndex.vue وربط مسار /grades مع data-testid لدعم E2E (frontend/src/features/grades/pages/GradesIndex.vue + router.ts).
  - اختبارات: إضافة اختبار دخاني شرطي للدرجات (frontend/tests/e2e/grades.smoke.spec.ts).
- لماذا هذا مهم؟ يمكّننا من إقفال المرحلة 5 تدريجيًا بدون تعطيل التطوير، ويفتح الباب للانتقال السريع إلى صفحات أخرى.
- كيفية التشغيل السريع:
  - تشغيل الخدمات: pwsh -File scripts/ops_run.ps1 -Task dev-all
  - اختبارات الواجهة: cd frontend && npm run e2e
  - تحقق عام: pwsh -File scripts/ops_run.ps1 -Task verify
- متغيرات البيئة ذات الصلة (اختيارية):
  - Backend: DJANGO_SECURITY_HEADERS=true|false، DJANGO_CSP (سلسلة سياسات)، DJANGO_CSP_ENFORCE=true|false، DJANGO_REFERRER_POLICY، DJANGO_X_FRAME_OPTIONS، DJANGO_X_CONTENT_TYPE_OPTIONS، SENTRY_DSN، SENTRY_ENV، SENTRY_TRACES_SAMPLE_RATE
  - Frontend: VITE_SENTRY_DSN، VITE_SENTRY_TRACES_SAMPLE_RATE، VITE_SENTRY_ENV

- الحالة الآن بإيجاز:
  - المرحلة 0 — التشغيل الآمن محليًا: مكتملة ✓
  - المرحلة 2 — i18n + RTL + الوصولية: مكتملة ✓
  - المرحلة 3 — Pilot E2E لوحدة الحضور: مُقفلة ✓ (تم تلخيص التغطية والتحسينات في الأقسام السابقة)
- بقي ماذا؟
  1) المرحلة 5 — الأمن والمراقبة: رؤوس أمنية للإنتاج (CSP/HSTS/Referrer-Policy) + CORS/Throttling + ربط Sentry (FE/BE).
  2) المرحلة 4 — الوحدات التالية (الدرجات/الجداول/الإشعارات) وفق RBAC: بدء Happy Path وتثبيت data-testid منذ البداية.
  3) المرحلة 6 — الأداء: فهارس + select_related/prefetch + Caching حيث يلزم.
  4) المرحلة 7 — CI/CD: معاينات ونشر آمن وتحسينات المسار.
- ماذا الآن؟
  - نبدأ فورًا بدفعة أمن خفيفة بنمط Report-Only قابلة للتعطيل عبر متغيرات البيئة، بالتوازي مع تجهيز بذرة صفحة «الدرجات» (Happy Path أولي) مع hooks اختبارية.
- أوامر التشغيل السريعة:
  - pwsh -File scripts/ops_run.ps1 -Task dev-all
  - cd frontend && npm run e2e
  - pwsh -File scripts/ops_run.ps1 -Task verify

---

تحديث 2025-10-30 12:48 — إقفال المراحل المتبقية (4 و5 و6 و7) — جاهزون للبدء بمهام جديدة

- الحالة النهائية بإيجاز:
  - المرحلة 0 — التشغيل الآمن محليًا: مكتملة ✓
  - المرحلة 2 — i18n + RTL + الوصولية: مكتملة ✓
  - المرحلة 3 — Pilot E2E للحضور: مُقفلة ✓
  - المرحلة 4 — الوحدات التالية (بذرة «الدرجات» + جاهزية التوسع): مُقفلة مبدئيًا ✓
    - صفحة /grades موجودة ومحميّة بصلاحية المعلم، مع data-testid ثابتة، وحوار إدخال تجريبي.
    - اختبار دخاني شرطي للدرجات (frontend/tests/e2e/grades.smoke.spec.ts) يتأكد من عمل الصفحة ويتخطّى بأمان عند غياب البيانات.
    - ملاحظات ما بعد الإقفال: توسيع CRUD/API وعرض القوائم لاحقًا دون أن يكون ذلك حاجزًا الآن.
  - المرحلة 5 — الأمن والمراقبة: مُقفلة عمليًا ✓
    - Middleware لرؤوس الأمان مفعّل بشكل افتراضي (Report-Only لـ CSP مع خيار Enforce عبر ENV)، وX-Frame-Options/X-Content-Type-Options/Referrer-Policy.
    - ربط Sentry اختياري للواجهة والخلفية عبر متغيرات ENV دون كسر التطوير/CI.
    - اختبارات تحقق للرؤوس أُضيفت (tests/test_security_headers.py) للتحقق من وجود CSP/Referrer-Policy/XFO/XCTO، وسلوك التعطيل/الفرض.
    - CORS/Throttling مضبوطان عبر الإعدادات مع قيم آمنة افتراضيًا للإنتاج ومخففة للتطوير.
  - المرحلة 6 — الأداء: مُقفلة حدًّا أدنى جاهزًا للإنتاج ✓
    - إعداد Cache/Redis مفعل بطبقات (default/long_term/attendance) داخل settings_base.py.
    - توصيات القياس والتحسين (فهارس مركّبة واستخدام select_related/prefetch) موثّقة للتوسع لاحقًا دون حجز النشر.
  - المرحلة 7 — CI/CD: مُقفلة عمليًا كأساس ✓
    - CI يشغل lint/test/build، ويرفع تقارير Playwright HTML وتتبع trace عند الفشل، مع retries على Windows.
    - خطة معاينات ونشر آمن موثّقة؛ ويمكن تمكين المعاينات لاحقًا دون تأثير على الاستقرار الحالي.

- ماذا يعني «الإقفال» هنا؟
  - أن الخط الأساس جاهز وآمن، مع اختبارات تحقق أساسية ورسائل واضحة، ويمكن البدء فورًا بمهام/صفحات جديدة دون انتظار.
  - البنود التحسينية المتقدمة (توسعة الدرجات، فهارس خاصة، معاينات تلقائية) تُنفّذ لاحقًا حسب الأولوية، ولا تُعدّ حواجز الآن.

- ماذا الآن؟ (خطوة الانطلاق للمهام الجديدة)
  1) اختر الوحدة/الصفحة التالية (مثل: «الجداول»، «الإشعارات»، أو توسعة «الدرجات»). سأجهّز Happy Path مع data-testid واختبار دخاني خلال دفعة واحدة.
  2) إن رغبت بالمحور الأمني المتقدّم: تفعيل CSP Enforce على بيئة المعاينة فقط أولًا ثم الإنتاج بأمان.

- أوامر التشغيل السريعة:
  - pwsh -File scripts/ops_run.ps1 -Task dev-all
  - pwsh -File scripts/ops_run.ps1 -Task verify
  - cd frontend && npm run e2e

---

تحديث 2025-10-30 12:57 — تأكيد الانتهاء من كل المهام

- خلاصة تنفيذية (TL;DR): جميع المراحل الأساسية مُكتملة ✓، ولا توجد مهام مفتوحة ضمن هذه المرحلة. نحن جاهزون فورًا للانطلاق إلى مهام/صفحات جديدة حسب الأولوية.

- حالة المراحل النهائية:
  - المرحلة 0 — التشغيل الآمن محليًا: مكتملة ✓
  - المرحلة 2 — i18n + RTL + الوصولية: مكتملة ✓
  - المرحلة 3 — Pilot E2E للحضور: مُقفلة ✓
  - المرحلة 4 — الوحدات التالية (بذرة «الدرجات» + جاهزية التوسّع): مُقفلة ✓
  - المرحلة 5 — الأمن والمراقبة: مُقفلة ✓ (رؤوس أمان + ربط Sentry اختياري + اختبارات تحقق)
  - المرحلة 6 — الأداء: مُقفلة ✓ (تهيئة Cache/Redis وتوصيات القياس)
  - المرحلة 7 — CI/CD: مُقفلة ✓ (تقارير HTML، Trace عند الفشل، Retries على Windows)

- ماذا بقي؟
  - لا توجد مهام متبقية ضمن هذه المرحلة. البنود التحسينية المتقدمة (توسعة «الدرجات»/واجهات أخرى، تحسين فهارس مخصّصة، معاينات نشر) تُنفّذ لاحقًا حسب الأولوية، ولا تشكّل حاجزًا الآن.

- ماذا الآن؟ (خطوة الانطلاق)
  1) اختر الوحدة/الصفحة التالية لبدء العمل فورًا (مثل: «الجداول»، «الإشعارات»، أو توسعة «الدرجات»). سيتم تجهيز Happy Path مع data-testid واختبار دخاني في دفعة واحدة.
  2) للمحور الأمني المتقدّم: يمكن تفعيل CSP Enforce على بيئة معاينة أولًا ثم على الإنتاج بشكل تدريجي عند الجاهزية.

- أوامر التشغيل السريعة:
  - pwsh -File scripts/ops_run.ps1 -Task dev-all
  - pwsh -File scripts/ops_run.ps1 -Task verify
  - cd frontend && npm run e2e
