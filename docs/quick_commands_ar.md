### أوامر السطر الجاهزة (بيئة التطوير)

- تشغيل الكل (باك‑إند + فرونت‑إند)
  - pwsh -File scripts/dev_all.ps1
  - أو: pwsh -File scripts/start_here.ps1 -Task dev-all

- استعادة كاملة من الصفر (Docker + استيراد أحدث نسخة احتياطية)
  - pwsh -File scripts/recover_env.ps1
  - بديل يدوي: pwsh -File scripts/container_new.ps1 -WithRedis -ImportLatest -AssumeYes

- استعادة أحدث نسخة احتياطية فقط (بدون إعادة تهيئة كاملة)
  - استعادة تلقائية لأحدث ملف نسخ احتياطي موجود في مجلد backups:
    - pwsh -File scripts/restore_latest.ps1
    - ملاحظة: إن كنت داخل مجلد backend يمكنك أيضًا:
      - pwsh -File scripts/restore_latest.ps1
  - تحديد مجلد النسخ الاحتياطية يدويًا (اختياري):
    - pwsh -File scripts/restore_latest.ps1 -BackupDir "D:\backups\sh_school"
  - تفعيل تحقق صارم بعد الاستعادة (اختياري):
    - pwsh -File scripts/restore_latest.ps1 -StrictVerify
  - الاستعادة دون إسقاط مخطط public الحالي أولًا (غير موصى به عادة):
    - pwsh -File scripts/restore_latest.ps1 -SkipDrop
  - بديل مباشر باستخدام سكربت الاستعادة العام (اختيار أحدث نسخة):
    - pwsh -File scripts/db_restore.ps1 -Latest -Force
    - ملاحظة: من داخل backend يتوفر نفس الغلاف:
      - pwsh -File scripts/db_restore.ps1 -Latest -Force
  - لاستعادة ملف محدَّد بعينه:
    - pwsh -File scripts/db_restore.ps1 -File ".\backups\2025-10-27_sh_school.dump" -AssumeYes

- تشغيل/إصلاح PostgreSQL محليًا (Docker)
  - تشغيل القاعدة: pwsh -File scripts/db_up.ps1
  - إعادة تهيئة قسرية (يمسح البيانات): pwsh -File scripts/db_up.ps1 -ForceReinit
  - المنفذ الذي اختاره السكربت: Get-Content backend\.runtime/pg_port.txt
  - عرض الحاويات: docker ps
  - سجلات Postgres: docker logs pg-sh-school --tail 200
  - منفذ Postgres على المضيف: docker port pg-sh-school 5432/tcp  (وإن لم يُظهر شيئًا جرب) docker port pg-sh-school
  - دخول psql داخل الحاوية: docker exec -it pg-sh-school psql -U postgres -d sh_school

- ضمان/تحديث المستخدم الإداري (Superuser)
  - المستخدم الافتراضي: pwsh -File scripts/ensure_superuser.ps1 --username mesuef --password 'Admin@12345' --email 'mesuef@example.local'
  - إنشاء/تحديث مستخدمك: pwsh -File scripts/ensure_superuser.ps1 --username YOUR_NAME --password 'StrongPass123!' --email 'you@example.local'

- فحوصات الصحة والجاهزية للباك‑إند
  - حيّة (204=UP): Invoke-WebRequest -UseBasicParsing -Uri https://127.0.0.1:8443/livez -SkipCertificateCheck | Select-Object StatusCode
  - صحة (200=OK): Invoke-WebRequest -UseBasicParsing -Uri https://127.0.0.1:8443/healthz -SkipCertificateCheck | Select-Object StatusCode,Content

- اختبار المصادقة عبر API (بدون الواجهة)
  - تسجيل دخول (PowerShell):
    Invoke-RestMethod -Method Post -Uri https://127.0.0.1:8443/api/v1/auth/login/ -Headers @{ 'Content-Type'='application/json' } -Body (@{ username='mesuef'; password='Admin@12345' } | ConvertTo-Json) -SkipCertificateCheck
  - تسجيل دخول (curl-Windows):
    curl -k -s -X POST https://127.0.0.1:8443/api/v1/auth/login/ -H "Content-Type: application/json" -d '{"username":"mesuef","password":"Admin@12345"}'
  - تحديث التوكن:
    curl -k -s -X POST https://127.0.0.1:8443/api/v1/auth/refresh/ -H "Content-Type: application/json" -d "{}"
  - تسجيل خروج:
    curl -k -s -X POST https://127.0.0.1:8443/api/v1/auth/logout/ -H "Content-Type: application/json" -d "{}"

- تشغيل الواجهة الأمامية فقط
  - cd frontend; npm install; npm run dev

- إيقاف الخدمات والتنظيف
  - إزالة Postgres: docker rm -f pg-sh-school
  - حذف حجم البيانات (يمسح كل شيء): docker volume rm pg-sh-school-data
  - إيقاف Redis (إن وجد): docker rm -f redis-sh

- تشخيصات إضافية سريعة
  - معاينة مسارات Django (DEBUG فقط): Invoke-WebRequest -UseBasicParsing -Uri https://127.0.0.1:8443/api/v1/urls -SkipCertificateCheck | Select-Object Content
  - فحص منفذ Postgres محليًا: Test-NetConnection 127.0.0.1 -Port (Get-Content backend\.runtime/pg_port.txt)
  - مزامنة الوقت (إذا ظهرت أخطاء JWT): w32tm /resync

ملاحظة: إن واجهت أي أمر يُعيد خطأ، انسخ المخرجات هنا لأعطيك أمرًا تصحيحيًا مباشرًا أو أُجري تعديلًا بسيطًا على السكربتات إذا لزم.
