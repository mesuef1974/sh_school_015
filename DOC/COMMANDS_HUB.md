# 🧭 مركز الأوامر التنفيذي (Commands Hub)

> دليل موحّد لتشغيل الأوامر الأكثر استخدامًا في المشروع مع حواجز أمان وتعليمات واضحة. موجّه لبيئة Windows/PowerShell.

- مسار سريع: استخدم المشغّل الموحّد scripts/exec_hub.ps1
- الوضع الآمن: جرّب أي مهمة مع -WhatIf قبل التنفيذ الفعلي
- التأكيد: للمهام الخطرة ستطلب -Confirm بشكل صريح

---

## 0) المتطلبات الأولية
- Python 3.11+
- Docker Desktop (للـ PostgreSQL وRedis)
- Node.js (إن كنت ستشغّل الواجهة الأمامية Vite)

تشغيل فحص ما قبل التنفيذ:

```powershell
pwsh -File scripts/preflight.ps1
```

---

## 1) مهام شائعة عبر المشغّل الموحّد

```powershell
# عرض جميع المهام المتاحة
pwsh -File scripts/exec_hub.ps1 -List

# تشغيل إعداد البيئة (venv + أدوات dev)
pwsh -File scripts/exec_hub.ps1 dev:setup

# تشغيل البيئة بالكامل (Postgres/Redis/Migrations/RQ/HTTPS)
pwsh -File scripts/exec_hub.ps1 dev:up

# تشغيل الباك والفرونت معًا (https + vite)
pwsh -File scripts/exec_hub.ps1 dev:all

# تشغيل عامل المهام RQ على طابور default
pwsh -File scripts/exec_hub.ps1 worker:start

# تدقيق شامل للنظام
pwsh -File scripts/exec_hub.ps1 audit:full

# اختبار جاهزية HTTPS (Smoke)
pwsh -File scripts/exec_hub.ps1 smoke:test

# اختبار تدفق JWT (Login Test)
# سيُطلب منك إدخال اسم المستخدم وكلمة المرور، أو مررها يدويًا إلى السكربت مباشرةً
pwsh -File scripts/exec_hub.ps1 login:test

# تمكين تمرير الخيارات إلى اختبار تسجيل الدخول عبر exec_hub:
# أمثلة:
# - تحديد BaseUrl يدويًا (بدون أو مع https:// ومع/بدون سلاش)
# - تمرير اسم المستخدم وكلمة المرور مباشرة (ينصح باستخدام نافذة إدخال عند مشاركة الشاشة)

pwsh -File scripts/exec_hub.ps1 login:test -BaseUrl 127.0.0.1:8443 -Username mesuef
# سيطلب كلمة المرور فقط

pwsh -File scripts/exec_hub.ps1 login:test -BaseUrl https://127.0.0.1:8443/ -Username admin -Password "P@ssw0rd" -SkipCertificateCheck

# مثال على تجربة بدون تنفيذ (محاكاة)
pwsh -File scripts/exec_hub.ps1 dev:up -WhatIf
```

---

## 2) الفئات والأوامر (مباشرة)

### البيئة Environment
- scripts/dev_setup.ps1: إنشاء/إصلاح venv + black/flake8 + فحص gen_index.py
- scripts/preflight.ps1: فحوص سريعة للأدوات (Python/Docker/Node)

### البنية Backend
- scripts/dev_up.ps1: تشغيل PostgreSQL/Redis وتطبيق الترحيلات وتشغيل HTTPS وRQ
- scripts/full_audit.ps1: check + showmigrations + migrate --check + healthcheck
- backend/manage.py ensure_superuser: إنشاء مشرف (يُدار داخل dev_up)
- bootstrap_rbac / ensure_staff_users / activate_staff_users (أفضل جهد)

### الواجهة Frontend
- scripts/dev_all.ps1: تشغيل السيرفر الخلفي ثم Vite dev server
- frontend: npm install ثم npm run dev (يُدار داخل dev_all)

### العمال Workers
- scripts/rq_worker.ps1 -Queue <name>: تشغيل عامل المهام RQ

---

## 3) سياسة الأمان والتنفيذ
- لا تُشغّل مهام قد تُغيّر بيانات الإنتاج من جهاز المطور. هذا الدليل موجّه لبيئة التطوير.
- استخدم -WhatIf للمراجعة أولًا. لن تُنفّذ الأوامر الفعلية في هذا الوضع.
- بعض المهام قد تتطلب -Confirm: وافق صراحةً على التنفيذ حين تُطلب.

---

## 4) استكشاف الأخطاء
- تعذّر Python: تأكد من python --version يعمل ومن venv .venv حاضر.
- تعذّر Docker: افتح Docker Desktop ثم أعد المحاولة.
- فشل اتصال Redis/Postgres: استخدم scripts/dev_up.ps1 لإعداد الحاويات أولًا.

---

## 5) روابط سريعة
- خطة التنفيذ المرئية: DOC/implementation_plan_maroon.html
- قائمة التنفيذ المتسلسلة: DOC/خطة_تنفيذ_متسلسلة.md

---

## 1.1) اختبار سريع (Smoke)
للتأكد بسرعة من جاهزية الخادم عبر HTTPS ونقاط الصحة و401 المتوقع لنقاط API بدون توثيق:

```powershell
pwsh -File scripts/dev_smoke.ps1 -HttpsOnly
```

- يستخدم المنفذ HTTPS المكتشف تلقائيًا من backend/.runtime/https_port.txt (الافتراضي 8443).
- في حال أردت التحقق من HTTP أيضًا (إن كان مفعّلًا)، أزل السويتش `-HttpsOnly`.
- عند اختبار يدوي لنقاط الـ API عبر HTTPS، تذكّر استخدام `-SkipCertificateCheck` لأن الشهادة تطويرية ذاتية التوقيع.