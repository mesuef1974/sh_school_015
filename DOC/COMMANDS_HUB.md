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
# يمكن تمرير منفذ HTTP اختياريًا عند تفعيله:
# مثال: فحص HTTP على 8001 بدل 8000
pwsh -File scripts/exec_hub.ps1 smoke:test -HttpPort 8001

# اختبار سجل الحضور (History Smoke)
# يتحقق من 401 المتوقع على /api/v1/attendance/history بدون توثيق عبر HTTPS
pwsh -File scripts/exec_hub.ps1 history:smoke
# مع منفذ HTTP اختياري:
pwsh -File scripts/exec_hub.ps1 history:smoke -HttpPort 8001

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
- backend/manage.py import_violations [--file <path>] [--dry-run]: استيراد/تحديث كتالوج المخالفات من JSON (افتراضيًا من DOC/نماذج الغياب/violations_detailed.json)

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

---

## 6) اختبارات سريعة لكتالوج الانضباط (Discipline Catalog)
يوفّر النظام نقاط API جاهزة لقراءة كتالوج السلوكيات والمستويات (محمية بصلاحية discipline.access أو حساب Staff/Superuser).

- سحب المستويات:
```powershell
# يتطلب توكن JWT في العادة؛ في DEBUG يمكنك تجربة عبر المتصفح بعد تسجيل الدخول
curl -k -H "Accept: application/json" https://127.0.0.1:8443/api/v1/discipline/behavior-levels/
```

- سحب المخالفات مع بحث:
```powershell
curl -k -H "Accept: application/json" "https://127.0.0.1:8443/api/v1/discipline/violations/?search=الهروب"
```

- ملاحظات:
  - المسارات متاحة تحت: /api/v1/discipline/behavior-levels/ و /api/v1/discipline/violations/
  - تتطلب مصادقة JWT أو جلسة إدارية في DEBUG.
  - RBAC: مستخدمو الإدارة/المشرفون مسموح لهم افتراضيًا؛ غير ذلك يحتاجون صلاحية discipline.access.

---

## 7) أفعال سير العمل للحوادث (Incidents Workflow)
تمت إضافة أفعال أساسية ضمن ViewSet الحوادث. جميع الأمثلة التالية تفترض أنك تملك توكن JWT في المتغير TOKEN.

- إنشاء حادثة (يتطلب incident_create):
```powershell
curl -k -X POST "https://127.0.0.1:8443/api/v1/discipline/incidents/" -H "Authorization: Bearer $env:TOKEN" -H "Content-Type: application/json" -d '{"violation": 1, "student": 1, "reporter": 1, "occurred_at": "2025-11-09T10:15:00+03:00", "location": "جناح A", "narrative": "تفاصيل مختصرة"}'
```

- إرسال للمراجعة submit (يتطلب incident_submit):
```powershell
curl -k -X POST "https://127.0.0.1:8443/api/v1/discipline/incidents/{INC_ID}/submit/" -H "Authorization: Bearer $env:TOKEN"
```

- المراجعة review (يتطلب incident_review):
```powershell
curl -k -X POST "https://127.0.0.1:8443/api/v1/discipline/incidents/{INC_ID}/review/" -H "Authorization: Bearer $env:TOKEN"
```

- إضافة إجراء/عقوبة (يتطلب incident_review):
```powershell
curl -k -X POST "https://127.0.0.1:8443/api/v1/discipline/incidents/{INC_ID}/add-action/" -H "Authorization: Bearer $env:TOKEN" -H "Content-Type: application/json" -d '{"name": "تنبيه شفهي", "notes": "تم بحضور المرشد"}'
```
```powershell
curl -k -X POST "https://127.0.0.1:8443/api/v1/discipline/incidents/{INC_ID}/add-sanction/" -H "Authorization: Bearer $env:TOKEN" -H "Content-Type: application/json" -d '{"name": "تعهد خطي", "notes": "وقع الطالب"}'
```

- التصعيد escalate (يتطلب incident_escalate):
```powershell
curl -k -X POST "https://127.0.0.1:8443/api/v1/discipline/incidents/{INC_ID}/escalate/" -H "Authorization: Bearer $env:TOKEN"
```

- إشعار ولي الأمر notify-guardian (يتطلب incident_notify_guardian):
```powershell
curl -k -X POST "https://127.0.0.1:8443/api/v1/discipline/incidents/{INC_ID}/notify-guardian/" -H "Authorization: Bearer $env:TOKEN" -H "Content-Type: application/json" -d '{"channel": "internal", "note": "تم إرسال الإشعار"}'
```

- إغلاق الحالة close (يتطلب incident_close):
```powershell
curl -k -X POST "https://127.0.0.1:8443/api/v1/discipline/incidents/{INC_ID}/close/" -H "Authorization: Bearer $env:TOKEN"
```

ملاحظات:
- سياسة التكرار المفعّلة: التصعيد التلقائي عند وجود حالتين سابقتين لنفس الطالب ونفس المخالفة خلال آخر 30 يومًا (تظهر عند submit وتنعكس على committee_required عند الحاجة).
- يتجاوز المشرفون/المديرون القيود دائمًا؛ غير ذلك تُطلب الأذونات الدقيقة المذكورة أعلاه.

---

## 8) تهيئة سريعة لصلاحيات الانضباط (Bootstrap RBAC)
هناك طريقتان سريعتان:

1) عبر مركز الأوامر الموحد (يوصي به):
```powershell
# معاينة بدون تنفيذ
pwsh -File scripts/exec_hub.ps1 discipline:bootstrap-rbac -WhatIf
# تنفيذ فعلي مع تأكيد
pwsh -File scripts/exec_hub.ps1 discipline:bootstrap-rbac -Confirm
```

2) مباشرةً بأمر إدارة Django:
```powershell
cd backend
python manage.py bootstrap_discipline_rbac --with-access
```

- ينشئ/يحدّث المجموعات: Teacher, WingSupervisor, Counselor, Leadership.
- يربط الأذونات الدقيقة التالية كما في RBAC_SEEDING.md:
  - Teacher: incident_create, incident_submit
  - WingSupervisor: incident_review, incident_escalate, incident_notify_guardian, incident_close (+ discipline.access عند تمرير --with-access)
  - Counselor: incident_review, incident_notify_guardian (+ discipline.access عند تمرير --with-access)
  - Leadership: incident_review, incident_escalate, incident_notify_guardian, incident_close (+ discipline.access عند تمرير --with-access)

يمكن تكرار تشغيل الأمر دون ضرر.

### ضبط سياسات SLA والتكرار عبر متغيرات البيئة
يمكنك تخصيص السياسات بلا هجرات عبر متغيرات البيئة (or settings):
- DISCIPLINE_REVIEW_SLA_H (افتراضي 24)
- DISCIPLINE_NOTIFY_SLA_H (افتراضي 48)
- DISCIPLINE_REPEAT_WINDOW_D (افتراضي 30)
- DISCIPLINE_REPEAT_THRESHOLD (افتراضي 2)
- DISCIPLINE_AUTO_ESCALATE_SEVERITY (افتراضي true): عند بلوغ حدّ التكرار في submit تُرفع الشدة درجة واحدة (حتى 4).

مثال (ملف backend/.env):
```env
DISCIPLINE_REVIEW_SLA_H=24
DISCIPLINE_NOTIFY_SLA_H=48
DISCIPLINE_REPEAT_WINDOW_D=30
DISCIPLINE_REPEAT_THRESHOLD=2
DISCIPLINE_AUTO_ESCALATE_SEVERITY=true
```
هذه القيم تنعكس تلقائيًا في:
- حقول IncidentSerializer: review_sla_due_at/notify_sla_due_at ورايات التجاوز.
- منطق submit للتصعيد التلقائي بناءً على التكرار ورفع الشدة تلقائيًا عند تفعيله.
- ملخص summary لاحتساب عناصر تجاوز SLA.

---

## 9) لوحات مشرف الجناح – واجهات قراءة سريعة
تمت إضافة نقطتي API قرائيتين لمراقبة الحالات دون تغييرات على قاعدة البيانات:

- Kanban مبسّط (تجميـع حسب الحالة):
```powershell
curl -k -H "Authorization: Bearer $env:TOKEN" "https://127.0.0.1:8443/api/v1/discipline/incidents/kanban/?limit=20"
```
يعيد:
- counts: عدد الحالات في كل عمود (open/under_review/closed)
- columns: عناصر كل عمود بحد أقصى limit مرتبة تنازليًا حسب occurred_at

- ملخص إشرافي (7 أو 30 يومًا):
```powershell
# آخر 7 أيام (الافتراضي)
curl -k -H "Authorization: Bearer $env:TOKEN" "https://127.0.0.1:8443/api/v1/discipline/incidents/summary/?days=7"
# آخر 30 يومًا
curl -k -H "Authorization: Bearer $env:TOKEN" "https://127.0.0.1:8443/api/v1/discipline/incidents/summary/?days=30"
```
يعيد: totals, by_status, by_severity, top_violations[code,category,count], overdue{review,notify}.

الصلاحيات: يتطلب حساب staff/superuser أو صلاحية discipline.access.

---

## 10) حقول مساعدة جديدة على بطاقة الحادثة (Read-only)
زُوّد المُمثّل IncidentSerializer بحقوق قراءة إضافية لدعم الواجهات دون هجرات:
- review_sla_due_at: موعد استحقاق المراجعة = submitted_at + 24h
- notify_sla_due_at: موعد استحقاق إشعار ولي الأمر = submitted_at + 48h
- is_overdue_review, is_overdue_notify: أعلام تجاوز الـ SLA طالما الحالة under_review
- level_color: لون دلالي بحسب الشدة (1–4)

ملاحظة: سياسة التكرار المؤدية للتصعيد التلقائي ما زالت 2 حالة لنفس الطالب ونفس المخالفة خلال 30 يومًا وتطبَّق عند submit.