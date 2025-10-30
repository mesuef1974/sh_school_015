# دليل البدء السريع (كيف يشتغل هذا؟)

هذا الدليل يشرح بسرعة كيف تشغِّل المشروع محليًا وما الذي يحدث خلف الكواليس، مع أوامر جاهزة للنسخ.

## المتطلبات المسبقة
- Windows 10/11 مع PowerShell 7 (pwsh) مفضَّل (يعمل على PowerShell الكلاسيكي أيضًا)
- Python 3.11+ وتفعيل البيئة الافتراضية `.venv` إن وُجدت
- Node.js (إن أردت تشغيل الواجهة الأمامية)
- Docker Desktop (اختياري لتشغيل PostgreSQL وRedis محليًا)

## تثبيت المكتبات المطلوبة (أمر واحد)
- لتثبيت مكتبات الباكيند (Python) والفرونتند (Node) دفعة واحدة:

```powershell
pwsh -File scripts\ops_run.ps1 -Task install-deps
```

- لتضمين أدوات التطوير والاختبارات أيضًا (ruff/pytest وغيرها إن وُجدت في requirements-dev.txt):

```powershell
pwsh -File scripts\ops_run.ps1 -Task install-deps
# أو داخل سكربت المثبّت مباشرة:
# pwsh -File scripts\install_deps.ps1 -Dev
```

ملاحظات سريعة:
- إن لم يكن Python موجودًا على PATH سيُظهر السكربت رسالة خطأ واضحة.
- إن لم يكن Node.js/NPM مثبتًا، سيتجاوز قسم الفرونتند ويعرض تحذيرًا دون إيقاف العملية.
- حزمة @axe-core/vue الخاصة بفحص الوصولية اختيارية في التطوير؛ لا تُثبَّت تلقائيًا لتجنّب مشاكل بعض الشبكات مع سجل npm. إن رغبت بها:

```powershell
cd frontend
npm i -D @axe-core/vue
```

## تشغيل فوري (مقترح)
- أسهل طريقة الآن: انقر نقرًا مزدوجًا على الملف التالي من مستكشف الملفات لفتح مُشغّل بقائمة:
  - scripts/start_here.cmd
- أو عبر الطرفية:
  ```
  pwsh -File scripts\start_here.ps1
  ```
- من القائمة يمكنك:
  1) تشغيل الكل (dev-all)
  2) تحقق شبيه CI (verify)
  3) تشغيل خدمات Docker أو إيقافها
  4) تشغيل الباكيند فقط
  5) المساعدة
- للتشغيل المباشر دون قائمة:
  ```
  pwsh -File scripts\start_here.ps1 -Task dev-all
  pwsh -File scripts\start_here.ps1 -Task verify -StartBackend
  ```

## تشغيل كل شيء بأمر واحد
- يشغِّل الباكيند HTTPS (Uvicorn TLS) ثم ينتظر جاهزيته ويبدأ Vite مع بروكسي إلى الباكيند.

```
pwsh -File scripts\ops_run.ps1 -Task dev-all
```
- إذا كان منفذ HTTPS الافتراضي 8443 مشغولًا سيختار السكربت منفذًا حرًا تلقائيًا ويكتب القيمة في:
  - `backend/.runtime/dev_origin.txt`
  - `backend/.runtime/https_port.txt`
- Vite سيقرأ المنشأ المختار تلقائيًا عبر متغيري البيئة `VITE_BACKEND_ORIGIN` و`VITE_BACKEND_PORT`.

### تسجيل الحضور سريعًا (E2E مختصر)
- بعد تشغيل dev-all:
  1) سجّل الدخول كمستخدم إداري (أو معلّم مرتبط) عبر صفحة /login.
  2) من القائمة العلوية اختر "تسجيل الغياب".
  3) اختر الصف والتاريخ (واختر الحصة إن ظهر أكثر من حصة في اليوم نفسه).
  4) غيّر حالات الطلاب بسرعة (حاضر/غائب/متأخر/إذن خروج)، ويمكن إضافة ملاحظة.
  5) اضغط "حفظ".
     - في حال عدم توفر الشبكة، تُجدول العملية تلقائيًا في صف الأوفلاين وستُرفع عند عودة الاتصال.
  6) اختياري: اضغط "إرسال للمراجعة" لوضع السجلات تحت المراجعة من المشرف الجناحي.
- الواجهة تستخدم:
  - API: POST `/api/v1/attendance/bulk_save/` للحفظ.
  - API: GET `/api/v1/attendance/students/` و`/records/` للتحميل.
  - صف أوفلاين: `frontend/src/shared/offline/queue.ts` (التفعيل تلقائي).

## فحوص شبيهة بـ CI (تحقق سريع)
- يُجري: Django check+migrate → اختبارات SQLite → (اختياري) اختبارات PostgreSQL → فحوص الصحة إن كان الخادم يعمل.
- جديد: تشغيل اللنترز اختياريًا (لا يكسر العملية عند عدم توفر الأدوات) للفرونت والباك.

```
pwsh -File scripts\ops_run.ps1 -Task verify
```
خيارات مفيدة:
- تشغيل الباكيند مؤقتًا قبل فحوص الصحة:

  ```
  pwsh -File scripts\ops_run.ps1 -Task verify -StartBackend
  ```
- تخطي اختبارات PostgreSQL والاكتفاء بـ SQLite:

  ```
  pwsh -File scripts\ops_run.ps1 -Task verify -SkipPostgresTests
  ```

## اللنترز والتنسيق (Linters/Formatters)
- الواجهة الأمامية (Frontend): ESLint + Prettier تم إعدادهما.
  - تثبيت الأدوات (ضمن خطوة install-deps عادة):
    ```powershell
    cd frontend
    npm install
    ```
  - أوامر:
    ```powershell
    npm run lint       # فحص القواعد
    npm run lint:fix   # إصلاح تلقائي آمن
    npm run format     # تنسيق Prettier
    ```
- الباكيند (Backend): Ruff + Black + isort مفعّلة عبر pyproject.toml.
  - تثبيت أدوات التطوير:
    ```powershell
    pwsh -File scripts\install_deps.ps1 -Dev
    # أو:
    python -m pip install -r requirements-dev.txt
    ```
  - أوامر يدوية (اختياري):
    ```powershell
    python -m ruff check backend
    python -m black --check backend
    python -m isort --check-only backend
    ```
- ملاحظة: مسار verify سيحاول تشغيل هذه الفحوص ويعرض PASS/WARN/SKIP دون إيقاف العملية إذا لم تكن الأدوات مثبتة بعد.

## تشغيل خدمات Docker (PostgreSQL + Redis)
- السكربت يختار منفذًا بديلًا تلقائيًا إذا كان الافتراضي محجوزًا.

```
pwsh -File scripts\ops_run.ps1 -Task up-services
```
- ضبط المنافذ يدويًا إذا لزم:

  ```powershell
  $Env:PG_HOST_PORT='5544'; $Env:REDIS_HOST_PORT='6380'
  pwsh -File scripts\ops_run.ps1 -Task up-services
  ```
- إيقاف الخدمات:

  ```
  pwsh -File scripts\ops_run.ps1 -Task stop-services
  ```

## نقاط الصحة (Health/Live)
- بمجرد تشغيل الباكيند:
  - الحيّة: `GET /livez` تعيد 204
  - الصحة: `GET /healthz` تعيد 200 إذا قاعدة البيانات متاحة، 500 إن لم تكن
- العناوين الشائعة أثناء التطوير:
  - `https://127.0.0.1:8443/livez` و`/healthz` (أو المنفذ المختار تلقائيًا)
  - `http://127.0.0.1:8000/livez` و`/healthz` عند الرجوع لـ runserver (HTTP)

## المصادقة (واجهات موحّدة)
- الواجهة الأمامية تتواصل مع `/api` نسبيًا ويحوِّل Vite إلى الباكيند.
- نقاط Auth الأساسية:
  - `POST /api/v1/auth/login/`
  - `POST /api/v1/auth/refresh/`
  - `POST /api/v1/auth/logout/`
- تم إعداد عميل HTTP مع اعتراضات: تحديث رمز الدخول تلقائيًا، إعادة الطلب 401 مرة واحدة، ومحاولات backoff للأخطاء العابرة.

## اللغات والاتجاه (i18n/RTL)
- اللغة الافتراضية: العربية (ar)، مع الإنجليزية (en) كخيار احتياطي.
- يتم اختيار اللغة عند التشغيل حسب الترتيب: `localStorage.locale` ثم لغة المتصفح، وإلا فالقيمة من `VITE_DEFAULT_LOCALE`.
- يقوم النظام بضبط سمتي `dir` و`lang` على عنصر `html` تلقائيًا (RTL للعربية، LTR للإنجليزية).
- يوجد مُبدِّل لغات صغير في شريط الترويسة (ع/EN) للتبديل الفوري بين العربية والإنجليزية مع حفظ الاختيار.
- عند تبديل اللغة، يتم تحديث PrimeVue locale تلقائيًا (أيام/أشهر/رسائل مكونات PrimeVue) دون إعادة التحميل.
- للتبديل يدويًا أثناء التطوير يمكنك من وحدة التحكم (Console):

```js
import { setLocale } from '/src/app/i18n'
setLocale('en') // أو 'ar'
```

- لتغيير الافتراضي، حدِّث ملف `frontend/.env`:
```
VITE_DEFAULT_LOCALE=ar
VITE_FALLBACK_LOCALE=en
```

## كيف تعمل السكربتات داخليًا؟
- `scripts/serve_https.ps1`:
  - يتأكد من وجود شهادات TLS التطويرية، يختار منفذ HTTPS متاحًا (8443..8450)، ويكتب الأصل المختار في `backend/.runtime/dev_origin.txt`.
  - إن فشل TLS، يرجع إلى `runserver` على HTTP.
- `scripts/dev_all.ps1`:
  - يفتح نافذة جديدة تشغّل `serve_https.ps1`، ينتظر جاهزية `/livez`، ثم يشغّل Vite ويوجه البروكسي تلقائيًا.
- `scripts/verify_all.ps1`:
  - يمكنه تشغيل Docker (بمنافذ تلقائية عند التعارض)، إجراء المهاجرات والاختبارات، ومحاولة فحوص الصحة على المنشأ المكتشف.
- `scripts/ops_run.ps1`:
  - نقطة دخول موحدة تُغلّف الأوامر السابقة وتضيف مهمّة `help`.

## مشاكل المنافذ الشائعة وحلّها
- Postgres 5433 أو Redis 6379 قد تكون محجوزة على جهازك.
- الحل: السكربت يحاول اختيار منافذ حرة تلقائيًا. أو اضبطها يدويًا:

  ```powershell
  $Env:PG_HOST_PORT='5544'
  $Env:REDIS_HOST_PORT='6380'
  pwsh -File scripts\ops_run.ps1 -Task up-services
  ```

## تسجيل الدخول إلى لوحة الإدارة
- السكربت يضمن وجود superuser وفق `.env` إن وُجِد، أو ينشئ مستخدمًا افتراضيًا بالاسم `mesuef` (مع ضبط الأعلام فقط إن لم تُضبط كلمة مرور).
- عنوان الإدارة أثناء التطوير:

  ```
  https://127.0.0.1:<المنفذ>/admin/
  ```

## أسئلة سريعة (FAQ)
- لا أرى استجابة من `/healthz`؟
  - تأكد أن الباكيند يعمل: `ops_run.ps1 -Task start-backend` أو `dev-all`.
- أخطاء CORS في الواجهة؟
  - في التطوير نستخدم مسارًا نسبيًا `/api` مع بروكسي Vite، لذا تجنّب الاتصال بأصل مطلق مختلف.
- تعارض منافذ Vite أو Uvicorn؟
  - Uvicorn يختار منفذ HTTPS حرًا تلقائيًا ويحدّث `.runtime`.
  - Vite يستخدم 5173 افتراضيًا ويمكنه إيجاد بديل إن كان مشغولًا.

## أوامر مرجعية سريعة
```powershell
# تشغيل الكل (باك + فرونت)
pwsh -File scripts\ops_run.ps1 -Task dev-all

# تحقّق شامل شبيه CI
pwsh -File scripts\ops_run.ps1 -Task verify -StartBackend

# تشغيل خدمات Docker مع اختيار تلقائي للمنافذ
pwsh -File scripts\ops_run.ps1 -Task up-services

# إيقاف الخدمات
pwsh -File scripts\ops_run.ps1 -Task stop-services

# المساعدة
pwsh -File scripts\ops_run.ps1 -Task help
```

## الوصولية أثناء التطوير (axe)
- فحص الوصولية عبر @axe-core/vue متاح اختياريًا في بيئة التطوير فقط. لا يُضمَّن في بناء الإنتاج.
- بشكل افتراضي لا نقوم بتثبيت الحزمة لتجنّب مشاكل بعض الشبكات مع سجل npm؛ لتفعيله يدويًا:
  ```powershell
  cd frontend
  npm i -D @axe-core/vue
  # ثم فعّل العلم التالي داخل frontend/.env
  # (انسخه من .env.example إن لم يوجد)
  # VITE_ENABLE_AXE=true
  ```
- عند تفعيل العلم وتوفر الحزمة، وأثناء التصفّح في dev (vite)، ستظهر تحذيرات/أخطاء الوصولية في Console المتصفح مع تفاصيل ومواقع العناصر المخالفة.
- خطوات الاستخدام:
  1) شغِّل التطوير: `pwsh -File scripts\ops_run.ps1 -Task dev-all`
  2) افتح أدوات المطوّر (F12) → Console
  3) انتقل بين الصفحات (الرئيسية، تسجيل الدخول، صفحة جدول/جدول بيانات). ستظهر تقارير axe عند وجود مخالفات.
- المستهدف: معالجة المخالفات الحرجة (خطيرة) بحيث لا يظهر أي تحذير axe من النوع الحاد في الصفحات الأساسية.

### تحسينات واجهة للوصولية
- أضفنا رابط "تجاوز إلى المحتوى" يظهر عند الضغط على Tab أول مرة، للانتقال مباشرة إلى `<main>`.
- تمت إضافة أنماط `:focus-visible` واضحة للأزرار والروابط والعناصر التفاعلية لتسهيل التنقل بلوحة المفاتيح.
- نحرص على وجود aria-label للعناصر الأيقونية بدون نص (مثل زر العودة للرئيسية في الترويسة).

### ملاحظات RTL
- تم ضبط `dir` و`lang` على عنصر html تلقائيًا وفق اللغة.
- سنقوم بتدقيق تدريجي لاستبدال خصائص CSS الاتجاهية (left/right، margin-left/right) بخصائص منطقية (inline-start/inline-end) حيثما أمكن دون تأثيرات جانبية.

---

## ملاحظات حلّ الأعطال على ويندوز — EPERM لقفل node_modules
- الأعراض الشائعة:
  - رسائل مثل: `EPERM: operation not permitted, unlink esbuild.exe` أو ملفات Rollup الأصلية.
  - فشل `npm ci`/`npm install` أو تعذّر حذف مجلد `node_modules`.
- الأسباب المحتملة:
  - عملية Node/Vite أو أداة مراقبة في الـ IDE تمسك ملفات ثنائية داخل `node_modules`.
  - مضاد الفيروسات يقفل الملفات التنفيذية أثناء عملية التثبيت/الحذف.
- الحل الموصى به (ترتيبًا):
  1) أغلق أي عمليات قد تستخدم Node/Vite/ESBuild (نوافذ dev server، watchers، IDE).
  2) عطّل الفحص اللحظي للمستودع مؤقتًا أو أضف استثناء لمجلد المشروع في مضاد الفيروسات.
  3) أعد المحاولة:
     ```powershell
     cd frontend
     npm ci
     npm run lint
     npm run format
     ```
  4) إذا استمرت المشكلة: أعد تشغيل الجهاز ثم نفّذ الأوامر مباشرةً قبل فتح IDE.
  5) كمحاولة أخيرة بعد إعادة التشغيل:
     ```powershell
     cd frontend
     Remove-Item -Recurse -Force node_modules
     npm ci
     ```
- ملاحظة: مسار التحقق `scripts/verify_all.ps1` يتعامل الآن مع أخطاء لِنتر الواجهة كـ SKIP لتجنّب تحذيرات مزعجة محليًا عند قفل `node_modules`. عند نجاح `npm ci` سيظهر PASS طبيعيًا.

## تمكين فحص الوصولية (dev-only) عبر axe
- التكامل موجود في الشفرة ومُعطّل افتراضيًا. لتفعيله أثناء التطوير ومعالجة المخالفات الحرجة فقط:
  ```powershell
  cd frontend
  npm i -D @axe-core/vue
  # ثم فعّل العلم التالي داخل frontend/.env
  # VITE_ENABLE_AXE=true

  # شغّل بيئة التطوير
  pwsh -File scripts\ops_run.ps1 -Task dev-all
  ```
- افتح أدوات المطوّر (Console) وانتقل بين الصفحات الأساسية (الرئيسية، تسجيل الدخول، الجداول، الغياب). أصلح المخالفات الحرجة فقط.
- بعد الإغلاق أعد `VITE_ENABLE_AXE=false` لإيقافه.


---

## اختبارات طرف-لطرف (E2E) لوحدة الحضور — تشغيل محليًا

> هذه الاختبارات اختيارية للتطوير المحلي، وتُشغَّل على بيئة dev عبر Vite. تأكد أن `dev-all` يعمل قبل تشغيلها.

### التثبيت (مرة واحدة)
```powershell
cd frontend
npm i -D playwright @playwright/test @axe-core/playwright
npx playwright install --with-deps
```

### سكربتات npm المتاحة
- من `frontend/package.json`:
```json
{
  "scripts": {
    "e2e": "playwright test",
    "e2e:ui": "playwright test --ui",
    "e2e:debug": "playwright test --debug"
  }
}
```

### تشغيل الخادم محليًا ثم الاختبارات
```powershell
# في نافذة طرفية أولى (من جذر المستودع)
pwsh -File scripts\ops_run.ps1 -Task dev-all

# في نافذة ثانية
cd frontend
npm run e2e
```
- لواجهة مصورة أثناء كتابة السيناريوهات: `npm run e2e:ui`.

### الإعدادات المهمة
- عنوان الخادم: مضبوط افتراضيًا إلى `http://127.0.0.1:5173` في `frontend/playwright.config.ts`.
  - يمكن تغيير العنوان عبر المتغير `E2E_BASE_URL`.
- اعتماد dev للاختبارات: استخدم المتغيرين `E2E_USERNAME` و`E2E_PASSWORD` عند الحاجة.
- فحص الوصولية داخل E2E (axe): الاختبار `a11y.smoke.spec.ts` غير حاجز افتراضيًا؛
  - لتفعيل الفشل على المخالفات الحرجة فقط: `E2E_AXE_STRICT=true`.

### أين توجد الاختبارات؟
- `frontend/tests/e2e/`
  - `auth.helpers.ts`: مساعد تسجيل الدخول.
  - `attendance.happy.spec.ts`: مسار سعيد لتسجيل الحضور وحفظه بنجاح.
  - `attendance.offline.spec.ts`: صف الأوفلاين — حفظ دون شبكة ثم تفريغ عند عودتها.
  - `a11y.smoke.spec.ts`: فحص axe سريع (serious/critical) — غير حاجز افتراضيًا.
  - `print.sanity.spec.ts`: فحص طباعة أولي (لا ينتج ملفًا).

### ملاحظات
- إن كان Vite اختار منفذًا مختلفًا، عدّل `E2E_BASE_URL` أو `playwright.config.ts`.
- selectors داخل الاختبارات عامة، وقد تحتاج لبعض المواءمة لتطابق DOM الحالي في بيئتك.
- لتشغيل تحقق CI شبيه محليًا (بدون E2E):
```powershell
pwsh -File scripts\ops_run.ps1 -Task verify -StartBackend
```
