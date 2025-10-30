# أوامر جاهزة (Windows PowerShell)

هذا الملف يقدّم «ورقة غش» بالأوامر الأكثر استخدامًا لتشغيل المشروع والتحقق والاختبارات E2E.

> ملاحظة: جميع الأوامر التالية تُنفَّذ في PowerShell (يفضل pwsh 7+). المسارات تفترض أنك داخل جذر المستودع: `D:\sh_school_015`.

---

## 1) تشغيل كل شيء (Backend + Frontend/Vite)

يشغّل الباكيند HTTPS ثم ينتظر جاهزيته ويبدأ Vite مع بروكسي تلقائي:

```powershell
pwsh -File scripts\ops_run.ps1 -Task dev-all
```

- سيختار منفذ HTTPS حر تلقائيًا ويكتب القيمة في:
  - `backend/.runtime/dev_origin.txt`
  - `backend/.runtime/https_port.txt`
- يضبط تلقائيًا:
  - `VITE_BACKEND_ORIGIN` و`VITE_BACKEND_PORT` لواجهة Vite.

### تشغيل مباشر (بدون القائمة التفاعلية)
- يوجد مُشغّل اختياري بقائمة:
  ```powershell
  pwsh -File scripts\start_here.ps1
  # أو:
  pwsh -File scripts\start_here.ps1 -Task dev-all
  ```

---

## 2) فحوص شبيهة بـ CI (تحقق سريع)

يشغّل: Django check+migrate → اختبارات SQLite → (اختياري) اختبارات PostgreSQL → لنترز → فحوص الصحة إذا كان الخادم يعمل.

```powershell
pwsh -File scripts\ops_run.ps1 -Task verify
```

خيارات مفيدة:

- تشغيل الباكيند مؤقتًا قبل فحوص الصحة:
  ```powershell
  pwsh -File scripts\ops_run.ps1 -Task verify -StartBackend
  ```

- تخطي اختبارات PostgreSQL والاكتفاء بـ SQLite:
  ```powershell
  pwsh -File scripts\ops_run.ps1 -Task verify -SkipPostgresTests
  ```

---

## 3) الواجهة الأمامية — تثبيت/لنتر/تنسيق

من داخل مجلد الواجهة `frontend`:

```powershell
cd frontend
npm ci                 # تثبيت نظيف للتبعيات
npm run lint           # فحص ESLint
npm run lint:fix       # إصلاح تلقائي آمن (اختياري)
npm run format         # تنسيق Prettier (كتابة)
npm run format:check   # تنسيق Prettier (فحص فقط)
```

> إن ظهرت مشكلة قفل `node_modules` على ويندوز (EPERM):
> - أوقف أي عمليات Node/Vite/IDE.
> - استثنِ مجلد المشروع مؤقتًا من مضاد الفيروسات.
> - أعد التشغيل ثم نفّذ `npm ci` مباشرة.

---

## 4) تفعيل فحص الوصولية (dev-only)

فقط أثناء التطوير، لتشغيل axe عبر `src/main.ts`:

```powershell
# داخل frontend/.env
VITE_ENABLE_AXE=true
# (اختياري) فشل التطوير على مخالفات serious/critical
VITE_AXE_STRICT=false

# ثم شغّل التطوير
pwsh -File scripts\ops_run.ps1 -Task dev-all
```

بعد الإغلاق، أعد المتغيّر إلى `false`:

```powershell
# داخل frontend/.env
VITE_ENABLE_AXE=false
```

---

## 5) اختبارات طرف-لطرف (E2E) — Playwright

> تتطلب أن يكون dev-all قيد التشغيل (Vite + Backend).

### تثبيت لمرة واحدة
```powershell
cd frontend
npm i -D playwright @playwright/test @axe-core/playwright
npx playwright install --with-deps
```

> إذا تعذّر تنزيل المتصفحات محليًا بسبب الشبكة، شغّل E2E على CI (انظر القسم 7).

### تشغيل الخادم أولًا
```powershell
pwsh -File scripts\ops_run.ps1 -Task dev-all
```

### تشغيل E2E في نافذة ثانية
```powershell
cd frontend
# إذا استخدم Vite منفذًا مختلفًا، غيّر العنوان
$env:E2E_BASE_URL = 'http://127.0.0.1:<port>'

# a11y smoke (غير حاجز)
npm run e2e -- tests/e2e/a11y.smoke.spec.ts

# Happy Path لتسجيل الحضور
npm run e2e -- tests/e2e/attendance.happy.spec.ts

# الأوفلاين/تفريغ الصف
npm run e2e -- tests/e2e/attendance.offline.spec.ts

# الطباعة (Sanity)
npm run e2e -- tests/e2e/print.sanity.spec.ts

# تشغيل كامل suite
npm run e2e
```

- لتشديد axe داخل E2E (يفشل على serious/critical فقط):
  ```powershell
  $env:E2E_AXE_STRICT = 'true'
  npm run e2e -- tests/e2e/a11y.smoke.spec.ts
  ```

- بيانات الدخول الافتراضية (إن لزم):
  ```powershell
  $env:E2E_USERNAME = 'admin'
  $env:E2E_PASSWORD = 'admin'
  ```

---

## 6) أوامر سريعة أخرى

- بناء الواجهة للإنتاج:
  ```powershell
  cd frontend
  npm run build
  ```

- تشغيل معاينة الإنتاج:
  ```powershell
  cd frontend
  npm run preview
  ```

---

## 7) تشغيل E2E على CI (GitHub Actions)

عند الدفع إلى الفرع الرئيسي أو فتح PR، سيعمل Workflow التالي:

- الملف: `.github/workflows/e2e.yml`
- يقوم بـ: تثبيت deps → تنزيل متصفحات Playwright → تشغيل dev-all بالخلفية → انتظار Vite → تشغيل `npm run e2e` → رفع تقارير الفشل.

تشغيل يدوي (محليًا) مشابه لفحوص CI بدون E2E:

```powershell
pwsh -File scripts\ops_run.ps1 -Task verify -StartBackend
```

---

## 8) Troubleshooting مختصر

- `ERR_CONNECTION_REFUSED` أثناء E2E:
  - تأكد أن `dev-all` يعمل وأن `E2E_BASE_URL` يشير للمنفذ الصحيح (افتراضي 5173).
  - يوجد global-setup في Playwright ينتظر جاهزية Vite تلقائيًا.

- فشل تنزيل متصفحات Playwright محليًا:
  - جرِّب قناة متصفح النظام (مضبوطة إلى `msedge` في config).
  - أو اكتفِ بتشغيل E2E على CI حيث يتم التنزيل تلقائيًا.

- EPERM/قفل node_modules على ويندوز:
  - أوقف عمليات Node/Vite/IDE، استثنِ المشروع من مضاد الفيروسات، أعد التشغيل ثم `npm ci`.

---

> للمزيد من التفاصيل: راجع `DOC/GETTING_STARTED_ar.md` (تشغيل/تحقق/لنترز/E2E) و`DOC/STATUS_PROGRESS_ar.md` (حالة التنفيذ).
