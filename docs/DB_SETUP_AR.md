# إعداد قاعدة بيانات PostgreSQL (بيئة تطوير محلية)

يوضّح هذا الدليل كيفية تشغيل قاعدة بيانات PostgreSQL محلياً لمنصّة Sh-School باستخدام السكربتات المتوفّرة في المستودع، مع استيراد أحدث نسخة احتياطية (إن وُجدت) وإعداد Redis اختيارياً.

## المتطلبات
- Windows + Docker Desktop مفعّل ويعمل.
- Python داخل بيئة افتراضية .venv (اختياري لكن مفضّل).
- PowerShell 7 أو Windows PowerShell.

## ملفات الإعداد
- ملف البيئة: backend/.env
  - أبسط صيغة: DATABASE_URL=postgres://postgres:postgres@127.0.0.1:5432/sh_school
  - بدائل: PG_* أو DB_* (مثل PG_USER/DB_USER، PG_PASSWORD/DB_PASSWORD، PG_PORT/DB_PORT ...).
  - الإعدادات الافتراضية مناسبة للتطوير: المستخدم postgres وكلمة المرور postgres والقاعدة sh_school والمنفذ 5432.

ملاحظة: تم تحسين السكربتات لالتقاط القيم من DATABASE_URL أو PG_* ثم DB_* تلقائياً.

## إنشاء وتشغيل الحاويات من الصفر
- تهيئة Postgres من الصفر + تطبيق المايغريشن + إنشاء مستخدم مشرف:
  pwsh -File scripts/container_new.ps1

- تهيئة Postgres من الصفر + استيراد أحدث نسخة احتياطية تلقائياً (إن وُجدت ملفات داخل مجلد backups\):
  pwsh -File scripts/container_new.ps1 -ImportLatest -AssumeYes

- إضافة Redis أيضاً (اختياري):
  pwsh -File scripts/container_new.ps1 -WithRedis
  أو دمج الخيارات:
  pwsh -File scripts/container_new.ps1 -WithRedis -ImportLatest -AssumeYes

بعد الانتهاء ستظهر لك سلسلة الاتصال وتقرير صحّة سريع. إذا حدث خلل فراجع السجلات عبر:
  docker logs pg-sh-school

## إصلاح قاعدة بيانات محلية فارغة أو تالفة
- السكربت التالي يحاول تشغيل Postgres، ثم يبحث عن أحدث نسخة احتياطية في backups\ ويستوردها؛ إن لم يجد نسخة، يطبق المايغريشن ويضمن وجود مستخدم مشرف:
  pwsh -File scripts/fix_db.ps1

خيارات مفيدة:
- تخطّي DROP أثناء الاستيراد (غير موصى به عادة): -SkipDrop
- تخطّي التأكيدات التفاعلية: -AssumeYes

## ملاحظات حول المصادقة وكلمة المرور
- تم تعديل فحص المصادقة في scripts/db_up.ps1 ليفرض اتصال TCP داخل الحاوية (psql -h 127.0.0.1 -p 5432) كي يلتزم بكلمة المرور نفسها التي يستخدمها Django. هذا يمنع حالات النجاح الكاذب عبر Unix socket.
- إذا كانت كلمة المرور في حجم البيانات القديم مختلفة عن backend/.env، سيكتشف السكربت ذلك ويعيد تهيئة الحجم تلقائياً.

## أين تُحفظ البيانات؟
- يتم تخزين بيانات Postgres في حجم Docker باسم: pg-sh-school-data
- يؤدي تشغيل container_new.ps1 عادة إلى إعادة تهيئة الحجم (بناءً على الخيارات) لضمان التوافق مع القيم في .env.

## Redis (اختياري)
- لتشغيل Redis محلياً مع المشروع: استخدم الخيار -WithRedis في container_new.ps1.
- يربط Redis على المنفذ 6379.

## استيراد/استعادة النسخ الاحتياطية يدوياً
- يمكنك استخدام:
  pwsh -File scripts/import_backup.ps1 -Latest -AssumeYes
- يدعم صيغ: .dump / .backup / .tar / .sql / .sql.gz
- عند وجود مشكلة مصادقة، سيقترح السكربت إعادة تهيئة Postgres ثم المحاولة مجدداً.

## استكشاف الأخطاء وإصلاحها
- تشخيص Docker:
  pwsh -File scripts/docker_diag.ps1
- إعادة تهيئة Postgres بالقوة (سيفرّغ الحجم):
  pwsh -File scripts/db_up.ps1 -ForceReinit
- التأكد من القيم في backend/.env (DATABASE_URL أو PG_*/DB_*).

## أسئلة متكررة
- ما هي بيانات الاعتماد الافتراضية؟
  المستخدم: postgres، كلمة المرور: postgres، القاعدة: sh_school، المضيف: 127.0.0.1، المنفذ: 5432.
- كيف أغيّرها؟
  عدّل backend/.env (DATABASE_URL أو PG_* أو DB_*). السكربتات والإعدادات ستلتقط التغيير تلقائياً.

انتهى. بالتوفيق!
# إعداد قاعدة بيانات PostgreSQL (بيئة تطوير محلية)

يوضّح هذا الدليل كيفية تشغيل قاعدة بيانات PostgreSQL محلياً لمنصّة Sh-School باستخدام السكربتات المتوفّرة في المستودع، مع استيراد أحدث نسخة احتياطية (إن وُجدت) وإعداد Redis اختيارياً.

## المتطلبات
- Windows + Docker Desktop مفعّل ويعمل.
- Python داخل بيئة افتراضية .venv (اختياري لكن مفضّل).
- PowerShell 7 أو Windows PowerShell.

## ملفات الإعداد
- ملف البيئة: backend/.env
  - أبسط صيغة: DATABASE_URL=postgres://postgres:postgres@127.0.0.1:5432/sh_school
  - بدائل: PG_* أو DB_* (مثل PG_USER/DB_USER، PG_PASSWORD/DB_PASSWORD، PG_PORT/DB_PORT ...).
  - الإعدادات الافتراضية مناسبة للتطوير: المستخدم postgres وكلمة المرور postgres والقاعدة sh_school والمنفذ 5432.

ملاحظة: تم تحسين السكربتات لالتقاط القيم من DATABASE_URL أو PG_* ثم DB_* تلقائياً.

## إنشاء وتشغيل الحاويات من الصفر
- تهيئة Postgres من الصفر + تطبيق المايغريشن + إنشاء مستخدم مشرف:
  pwsh -File scripts/container_new.ps1

- تهيئة Postgres من الصفر + استيراد أحدث نسخة احتياطية تلقائياً (إن وُجدت ملفات داخل مجلد backups\):
  pwsh -File scripts/container_new.ps1 -ImportLatest -AssumeYes

- إضافة Redis أيضاً (اختياري):
  pwsh -File scripts/container_new.ps1 -WithRedis
  أو دمج الخيارات:
  pwsh -File scripts/container_new.ps1 -WithRedis -ImportLatest -AssumeYes

بعد الانتهاء ستظهر لك سلسلة الاتصال وتقرير صحّة سريع. إذا حدث خلل فراجع السجلات عبر:
  docker logs pg-sh-school

## إصلاح قاعدة بيانات محلية فارغة أو تالفة
- السكربت التالي يحاول تشغيل Postgres، ثم يبحث عن أحدث نسخة احتياطية في backups\ ويستوردها؛ إن لم يجد نسخة، يطبق المايغريشن ويضمن وجود مستخدم مشرف:
  pwsh -File scripts/fix_db.ps1

خيارات مفيدة:
- تخطّي DROP أثناء الاستيراد (غير موصى به عادة): -SkipDrop
- تخطّي التأكيدات التفاعلية: -AssumeYes

## ملاحظات حول المصادقة وكلمة المرور
- تم تعديل فحص المصادقة في scripts/db_up.ps1 ليفرض اتصال TCP داخل الحاوية (psql -h 127.0.0.1 -p 5432) كي يلتزم بكلمة المرور نفسها التي يستخدمها Django. هذا يمنع حالات النجاح الكاذب عبر Unix socket.
- إذا كانت كلمة المرور في حجم البيانات القديم مختلفة عن backend/.env، سيكتشف السكربت ذلك ويعيد تهيئة الحجم تلقائياً.

## أين تُحفظ البيانات؟
- يتم تخزين بيانات Postgres في حجم Docker باسم: pg-sh-school-data
- يؤدي تشغيل container_new.ps1 عادة إلى إعادة تهيئة الحجم (بناءً على الخيارات) لضمان التوافق مع القيم في .env.

## Redis (اختياري)
- لتشغيل Redis محلياً مع المشروع: استخدم الخيار -WithRedis في container_new.ps1.
- يربط Redis على المنفذ 6379.

## استيراد/استعادة النسخ الاحتياطية يدوياً
- يمكنك استخدام:
  pwsh -File scripts/import_backup.ps1 -Latest -AssumeYes
- يدعم صيغ: .dump / .backup / .tar / .sql / .sql.gz
- عند وجود مشكلة مصادقة، سيقترح السكربت إعادة تهيئة Postgres ثم المحاولة مجدداً.

## استكشاف الأخطاء وإصلاحها
- تشخيص Docker:
  pwsh -File scripts/docker_diag.ps1
- إعادة تهيئة Postgres بالقوة (سيفرّغ الحجم):
  pwsh -File scripts/db_up.ps1 -ForceReinit
- التأكد من القيم في backend/.env (DATABASE_URL أو PG_*/DB_*).

## أسئلة متكررة
- ما هي بيانات الاعتماد الافتراضية؟
  المستخدم: postgres، كلمة المرور: postgres، القاعدة: sh_school، المضيف: 127.0.0.1، المنفذ: 5432.
- كيف أغيّرها؟
  عدّل backend/.env (DATABASE_URL أو PG_* أو DB_*). السكربتات والإعدادات ستلتقط التغيير تلقائياً.

## إنشاء حساب سوبر يوزر باحترافية (سطر واحد)
- أبسط استخدام (يقرأ من backend/.env، أو يستخدم اسم افتراضي mesuef):
  pwsh -File scripts/superuser.ps1

- تحديد الاسم والبريد وتوليد كلمة مرور قوية وعرضها:
  pwsh -File scripts/superuser.ps1 -Username admin -Email admin@example.com -RandomPassword -PrintCredentials

- تحديد كلمة مرور بشكل صريح (للتطوير فقط):
  pwsh -File scripts/superuser.ps1 -Username admin -Email admin@example.com -Password "StrongP@ss!123"

ملاحظات:
- السكربت scripts/superuser.ps1 يعتمد داخلياً على scripts/ensure_superuser.ps1 الذي يتولى فحص/إصلاح قاعدة البيانات تلقائياً (تشغيل أو إعادة تهيئة الحجم عند تعارض كلمة المرور).
- لا حاجة لتشغيل الخادم مسبقاً؛ الأمر يعمل مباشرة إذا كانت البيئة مهيّأة.
