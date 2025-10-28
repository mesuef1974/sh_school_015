# دليل البدء السريع (كيف يشتغل هذا؟)

هذا الدليل يشرح بسرعة كيف تشغِّل المشروع محليًا وما الذي يحدث خلف الكواليس، مع أوامر جاهزة للنسخ.

## المتطلبات المسبقة
- Windows 10/11 مع PowerShell 7 (pwsh) مفضَّل (يعمل على PowerShell الكلاسيكي أيضًا)
- Python 3.11+ وتفعيل البيئة الافتراضية `.venv` إن وُجدت
- Node.js (إن أردت تشغيل الواجهة الأمامية)
- Docker Desktop (اختياري لتشغيل PostgreSQL وRedis محليًا)

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

## فحوص شبيهة بـ CI (تحقق سريع)
- يُجري: Django check+migrate → اختبارات SQLite → (اختياري) اختبارات PostgreSQL → فحوص الصحة إن كان الخادم يعمل.

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