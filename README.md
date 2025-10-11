<!-- بسم الله الرحمن الرحيم -->
<div dir="rtl" lang="ar">

# ‏🏫 نظام إدارة مدرسة الشحانية - sh_school_015

<div dir="ltr">

[![CI](https://github.com/mesuef1974/sh_school_015/actions/workflows/python-ci.yml/badge.svg)](https://github.com/mesuef1974/sh_school_015/actions/workflows/python-ci.yml)
[![Links](https://github.com/mesuef1974/sh_school_015/actions/workflows/links-validate.yml/badge.svg)](https://github.com/mesuef1974/sh_school_015/actions/workflows/links-validate.yml)
[![CodeQL](https://github.com/mesuef1974/sh_school_015/actions/workflows/codeql.yml/badge.svg)](https://github.com/mesuef1974/sh_school_015/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

‏نظام إدارة مدرسية متكامل لمدرسة الشحانية الإعدادية الثانوية في قطر. يوفر إدارة شاملة للطلاب، الموظفين، الصفوف، الأنصبة التدريسية، مع واجهة عربية (RTL) احترافية وميزات تصدير متقدمة.

---

## 📋 جدول المحتويات

- [الميزات الرئيسية](#-الميزات-الرئيسية)
- [البنية التقنية](#-البنية-التقنية)
- [المتطلبات](#-المتطلبات)
- [التثبيت والإعداد](#-التثبيت-والإعداد)
- [التشغيل](#-التشغيل)
- [الميزات المتقدمة](#-الميزات-المتقدمة)
- [استيراد البيانات](#-استيراد-البيانات)
- [النسخ الاحتياطي](#-النسخ-الاحتياطي)
- [أمثلة API](#-أمثلة-api)
- [استكشاف الأخطاء](#-استكشاف-الأخطاء)
- [المساهمة](#-المساهمة)

---

## ✨ الميزات الرئيسية

### 🎯 إدارة البيانات الأساسية
- **الطلاب** - إدارة كاملة للطلاب مع الرقم الوطني، تاريخ الميلاد، الجنسية، وبيانات ولي الأمر
- **الموظفين** - إدارة المعلمين والإداريين مع التخصصات والصلاحيات
- **الصفوف** - إدارة الصفوف الدراسية والشعب
- **المواد** - إدارة المواد الدراسية مع ربطها بالصفوف

### 📊 لوحة الأنصبة التدريسية (`/loads/`)
- عرض وإدارة الأنصبة التدريسية بشكل تفاعلي
- استيراد من Excel (sync/async) مع معالجة ذكية
- فلترة متقدمة: معلم، صف، مادة، بحث نصي
- ترتيب ذكي حسب التخصص والأولوية
- إحصائيات KPI: إجمالي الحصص، الفجوات، التغطية
- رسوم بيانية تفاعلية للتوزيع
- **تصدير Excel**: ملفات احترافية بتنسيق A3 landscape مع ألوان وتجميع
- **تصدير PDF**: دعم WeasyPrint (preferred) مع fallback لـ ReportLab

### 🎨 مصفوفة الأنصبة (`/loads/matrix/`)
- عرض Matrix: معلم × صف (Teacher-Class Matrix)
- تعديل inline للخلايا عبر AJAX بدون reload
- ألوان تصنيفية حسب التخصص
- Tooltips للمواد المتعددة
- **تصدير Excel/PDF**: بتنسيق احترافي مع دعم RTL

### 📤 ميزات التصدير المتقدمة
| النوع | المسار | الوصف |
|------|--------|-------|
| Excel | `/loads/export/assignments.xlsx` | تصدير جدول الأنصبة بتنسيق A3 |
| PDF | `/loads/export/assignments.pdf` | تصدير PDF للأنصبة (WeasyPrint/ReportLab) |
| Excel | `/loads/matrix/export.xlsx` | تصدير مصفوفة المعلمين والصفوف |
| PDF | `/loads/matrix/export.pdf` | تصدير PDF للمصفوفة |
| CSV | `/data/<table>/export` | تصدير سريع لأي جدول بيانات |

### 🔐 الأمان والصلاحيات
- نظام صلاحيات RBAC متقدم
- مجموعات: Admin, Principal, Teachers, Staff
- JWT authentication للـ API
- Django Admin مع تخصيصات عربية

### 🌐 واجهة عربية احترافية
- دعم كامل للغة العربية (RTL)
- خطوط عربية مدمجة (Noto Kufi Arabic, Amiri)
- Bootstrap 5 مع تخصيصات عربية
- HTMX للتحديثات الديناميكية بدون JavaScript

---

## 🛠 البنية التقنية

### Backend Stack
- **Framework**: Django 5.1.4 + Django REST Framework 3.15
- **Database**: PostgreSQL 16 (عبر Docker)
- **Task Queue**: Redis + RQ (django-rq) للمهام الخلفية
- **Authentication**: JWT (djangorestframework-simplejwt)
- **Export Libraries**:
  - Excel: `openpyxl`
  - PDF: `WeasyPrint` (preferred) / `ReportLab` (fallback)
  - Arabic support: `arabic-reshaper`, `python-bidi`

### Frontend
- HTML5 + CSS3 (Bootstrap 5)
- HTMX للتفاعلية
- Chart.js للرسوم البيانية
- خطوط عربية مدمجة

### DevOps
- Docker & Docker Compose
- GitHub Actions CI/CD
- Health endpoints (`/livez`, `/healthz`)
- Environment-based settings (dev/prod)

---

## 📦 المتطلبات

### الأساسية
- **Python 3.11+** (Python 3.11 أو أحدث)
- **Docker Desktop** (لتشغيل PostgreSQL و Redis)
- **Git** (للتحكم بالإصدارات)

### للتصدير PDF (اختر واحدة)

**الطريقة الموصى بها:**

<div dir="ltr">

```powershell
pip install WeasyPrint>=60.0
```

</div>

**البديل (ReportLab):**

<div dir="ltr">

```powershell
pip install reportlab>=4.0 arabic-reshaper python-bidi
```

</div>

### للتصدير Excel

<div dir="ltr">

```powershell
pip install openpyxl>=3.1.0
```

</div>

---

## 🚀 التثبيت والإعداد

### 1️⃣ إعداد بيئة التطوير (Windows)

السكربت يقوم بكل شيء تلقائياً:

<div dir="ltr">

```powershell
# من جذر المشروع
./scripts/dev_setup.ps1
```

</div>

**ماذا يفعل؟**
- ✅ ينشئ بيئة افتراضية `.venv` (أو يصلح التالفة)
- ✅ يفعّل البيئة ويحدّث pip
- ✅ يثبّت الاعتماديات من `requirements-dev.txt`
- ✅ يشغّل فحوصات Black و Flake8
- ✅ يتحقق من `gen_index.py`

**للإعداد اليدوي:**

<div dir="ltr">

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

</div>

### 2️⃣ إعداد ملف البيئة

انسخ الملف النموذجي وعدّله:

<div dir="ltr">

```powershell
cp backend/.env.example backend/.env
```

</div>

**محتوى `.env` الأساسي:**

<div dir="ltr">

```env
# Django Settings
DJANGO_SECRET_KEY=change-me-very-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_ENV=dev

# PostgreSQL (Docker Container)
PG_DB=sh_school
PG_USER=postgres
PG_PASSWORD=postgres
PG_HOST=127.0.0.1
PG_PORT=5433

# Auto-create Superuser (optional)
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@school.qa
DJANGO_SUPERUSER_PASSWORD=Admin@12345

# Server Settings (optional)
DJANGO_RUN_HOST=0.0.0.0
DJANGO_RUN_PORT=8000
```

</div>

---

## ▶️ التشغيل

### التشغيل السريع (الكل معاً)

<div dir="ltr">

```powershell
# تشغيل كل المكونات دفعة واحدة
./scripts/dev_up.ps1
```

</div>

**ماذا يحدث؟**
1. ✅ يشغّل PostgreSQL (حاوية `pg-sh-school`)
2. ✅ يشغّل Redis (حاوية `redis-sh`)
3. ✅ يطبّق الهجرات (migrations)
4. ✅ ينشئ السوبر يوزر تلقائياً
5. ✅ يهيّئ صلاحيات RBAC
6. ✅ يشغّل RQ Worker (نافذة منفصلة)
7. ✅ يشغّل الخادم على HTTPS (8443) أو HTTP (8000)
8. ✅ يفتح المتصفح تلقائياً

### التشغيل المتقدم (خطوة بخطوة)

#### 1. تشغيل قاعدة البيانات

<div dir="ltr">

```powershell
./scripts/db_up.ps1
```

</div>

#### 2. تشغيل الخادم

<div dir="ltr">

```powershell
# HTTP عادي (منفذ 8000)
./scripts/serve.ps1

# HTTPS محلي (منفذ 8443)
./scripts/serve_https.ps1
```

</div>

#### 3. تشغيل RQ Worker (اختياري - للمهام الخلفية)

<div dir="ltr">

```powershell
./scripts/rq_worker.ps1
```

</div>

### الوصول للنظام

| الخدمة | الرابط | الوصف |
|--------|--------|-------|
| لوحة الأنصبة | http://127.0.0.1:8000/loads/ | الواجهة الرئيسية |
| مصفوفة الأنصبة | http://127.0.0.1:8000/loads/matrix/ | Teacher-Class Matrix |
| معاينة البيانات | http://127.0.0.1:8000/data/ | CRUD للجداول |
| Django Admin | http://127.0.0.1:8000/admin/ | لوحة الإدارة |
| API Root | http://127.0.0.1:8000/api/ | REST API |
| Health Check | http://127.0.0.1:8000/healthz | فحص الصحة |
| OpenAPI Docs | http://127.0.0.1:8000/api/docs/ | توثيق API |

---

## 🎓 الميزات المتقدمة

### 1️⃣ إنشاء/تحديث السوبر يوزر

**الطريقة الموصى بها:**

<div dir="ltr">

```powershell
./scripts/ensure_superuser.ps1 --username admin.pro --email admin@school.qa --password "StrongP@ssw0rd!"
```

</div>

**عبر Django مباشرة:**

<div dir="ltr">

```powershell
python backend/manage.py ensure_superuser --username admin.pro --email admin@school.qa --password "StrongP@ssw0rd!"
```

</div>

**أو عبر `.env`:** (تلقائياً عند `./scripts/serve.ps1`)

<div dir="ltr">

```env
DJANGO_SUPERUSER_USERNAME=admin.pro
DJANGO_SUPERUSER_EMAIL=admin@school.qa
DJANGO_SUPERUSER_PASSWORD=StrongP@ssw0rd!
```

</div>

### 2️⃣ HTTPS المحلي (للتطوير)

**توليد شهادة ذاتية:**

<div dir="ltr">

```powershell
./scripts/make_dev_cert.ps1
```

</div>


**تشغيل HTTPS:**

<div dir="ltr">

```powershell
./scripts/serve_https.ps1
# يفتح على: https://127.0.0.1:8443/
```

</div>


**إزالة تحذير "Not secure":**

<div dir="ltr">

```powershell
# تثبيت الشهادة في Windows Trust Store
./scripts/trust_dev_cert.ps1

# لإزالتها لاحقاً
./scripts/trust_dev_cert.ps1 -Untrust
```

</div>


### 3️⃣ بيئات الإعدادات (Dev/Prod)

**التبديل بين البيئات:**

<div dir="ltr">

```powershell
# Development (افتراضي)
$env:DJANGO_ENV='dev'
python backend/manage.py runserver

# Production (محلياً للاختبار)
$env:DJANGO_ENV='prod'
$env:DJANGO_ALLOWED_HOSTS='localhost,127.0.0.1'
python backend/manage.py runserver
```

</div>


**ملفات الإعدادات:**
- `backend/core/settings_base.py` - إعدادات مشتركة
- `backend/core/settings_dev.py` - التطوير (DEBUG=True, CORS open)
- `backend/core/settings_prod.py` - الإنتاج (SECURE_*, HSTS, whitelists)

### 4️⃣ Health Checks

| Endpoint | الوصف | الاستجابة |
|----------|-------|-----------|
| `/livez` | Liveness Probe | 204 No Content |
| `/healthz` | Readiness Probe (DB check) | 200 OK / 500 Error |

**عبر Command Line:**

<div dir="ltr">

```powershell
# يطبع "ok" أو رسالة الخطأ، exit code: 0 أو 1
python backend/manage.py healthcheck
```

</div>


**Smoke Test سريع:**

<div dir="ltr">

```powershell
./scripts/smoke.ps1
# يفحص /livez و /healthz
```

</div>


---

## 📥 استيراد البيانات

### 1️⃣ استيراد الطلاب من Excel

**دعم شيت لكل صف:**

<div dir="ltr">

```powershell
# تجربة بدون كتابة (Dry-Run)
python backend/manage.py import_students "D:\path\to\students.xlsx" --all-sheets --sheet-per-class --dry-run

# تنفيذ فعلي
python backend/manage.py import_students "D:\path\to\students.xlsx" --all-sheets --sheet-per-class
```

</div>


**مسح البيانات القديمة وإعادة الاستيراد:**

<div dir="ltr">

```powershell
python backend/manage.py import_students "D:\path\to\students.xlsx" \
    --all-sheets \
    --sheet-per-class \
    --clean \
    --nationality-xlsx "D:\path\to\nationalities.xlsx" \
    --expect-total 742
```

</div>


**الأعمدة المتوقعة في Excel:**
- `national_no` - الرقم الوطني (مفتاح أساسي)
- `studant_name` - اسم الطالب بالعربية
- `studant_englisf_name` - الاسم بالإنجليزية
- `date_of_birth` - تاريخ الميلاد (يتم حساب العمر تلقائياً)
- `nationality` أو `الجنسية` - الجنسية
- `grade` - رقم الصف (يُستخرج من اسم الشيت إن لم يوجد)
- `section` - الشعبة (يُستخدم اسم الشيت إن لم يوجد)
- `stu_phone_no` - جوال الطالب
- `stu_email` - بريد الطالب
- `parent_national_no` - الرقم الوطني لولي الأمر
- `name_parent` - اسم ولي الأمر
- `relation_parent` - علاقة ولي الأمر
- `extra_phone_no` - أرقام إضافية
- `parent_email` - بريد ولي الأمر

**خيارات متقدمة:**
- `--wipe` / `--clean` - مسح جميع الطلاب قبل الاستيراد
- `--nationality-xlsx` - ملف إضافي للجنسيات
- `--expect-total N` - التحقق من عدد السجلات المستوردة

### 2️⃣ استيراد الأنصبة من Excel

**استيراد عادي:**

<div dir="ltr">

```powershell
python backend/manage.py import_loads "D:\path\to\loads.xlsx"
```

</div>


**عبر الواجهة:** اذهب إلى `/loads/` واضغط "استيراد Excel"

### 3️⃣ استيراد الجداول من PDF

**يدعم tabula-py (مع Java) أو pdfplumber (بدون Java):**

<div dir="ltr">

```powershell
# تجربة
./scripts/backend_run.ps1 import_from_pdf "D:\path\to\pdfs" --dry-run

# تنفيذ فعلي
./scripts/backend_run.ps1 import_from_pdf "D:\path\to\pdfs"
```

</div>


**متطلبات:**
- **Tabula (preferred):** يحتاج Java على النظام، نتائج أفضل للجداول الشبكية
- **pdfplumber (fallback):** بدون Java، يعمل تلقائياً إذا فشل tabula

---

## 💾 النسخ الاحتياطي والاستعادة

### إنشاء نسخة احتياطية

**عبر Django Command (موصى به):**

<div dir="ltr">

```powershell
cd backend

# ملف SQL عادي (في backups/)
python manage.py backup_db

# مضغوط gzip
python manage.py backup_db --gzip

# مجلد مخصص
python manage.py backup_db --out "D:\my_backups"
```

</div>


**عبر PowerShell Script:**

<div dir="ltr">

```powershell
./scripts/db_backup.ps1           # SQL عادي
./scripts/db_backup.ps1 -Gzip     # مضغوط
./scripts/db_backup.ps1 -OutDir "D:\my_backups"
```

</div>


### استعادة نسخة احتياطية


<div dir="ltr">

```powershell
# استعادة مع تأكيد
./scripts/db_restore.ps1 "D:\sh_school_015\backups\pg_backup_sh_school_20251010_144522.sql"

# استعادة مباشرة بدون تأكيد
./scripts/db_restore.ps1 "D:\backups\backup.sql" -Force

# استعادة بدون حذف public schema (غير مستحسن)
./scripts/db_restore.ps1 "D:\backups\backup.sql" -SkipDrop
```

</div>


**ملاحظات:**
- تتم العملية داخل حاوية Docker `pg-sh-school`
- يتم قراءة بيانات الاتصال من `backend/.env`
- السكربت يدعم ملفات `.sql` و `.sql.gz`

---

## 🔌 أمثلة API

### الحصول على JWT Token

**PowerShell (Invoke-RestMethod):**

<div dir="ltr">

```powershell
$resp = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/token/" `
    -ContentType 'application/json' `
    -Body (@{ username = 'admin'; password = 'Admin@12345' } | ConvertTo-Json)

$access = $resp.access
$refresh = $resp.refresh
$access  # عرض التوكن
```

</div>


**cURL (سطر واحد):**

<div dir="ltr">

```powershell
curl -X POST "http://127.0.0.1:8000/api/token/" `
    -H "Content-Type: application/json" `
    -d '{"username":"admin","password":"Admin@12345"}'
```

</div>


### استدعاء API

**PowerShell:**

<div dir="ltr">

```powershell
# الصفوف
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/classes/' `
    -Headers @{ Authorization = "Bearer $access" }

# الطلاب
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/students/' `
    -Headers @{ Authorization = "Bearer $access" }

# الأنصبة التدريسية
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/teaching-assignments/' `
    -Headers @{ Authorization = "Bearer $access" }
```

</div>


**cURL:**

<div dir="ltr">

```powershell
curl "http://127.0.0.1:8000/api/classes/" -H "Authorization: Bearer $access"
```

</div>


### Endpoints المتاحة

| Endpoint | Method | الوصف |
|----------|--------|-------|
| `/api/token/` | POST | الحصول على access + refresh tokens |
| `/api/token/refresh/` | POST | تجديد access token |
| `/api/classes/` | GET, POST | قائمة/إنشاء الصفوف |
| `/api/students/` | GET, POST | قائمة/إنشاء الطلاب |
| `/api/staff/` | GET, POST | قائمة/إنشاء الموظفين |
| `/api/subjects/` | GET, POST | قائمة/إنشاء المواد |
| `/api/teaching-assignments/` | GET, POST | قائمة/إنشاء الأنصبة |
| `/api/class-subjects/` | GET, POST | ربط المواد بالصفوف |

---

## 🐛 استكشاف الأخطاء

### مشاكل PostgreSQL

**خطأ: "docker: Error response from daemon: Conflict"**

<div dir="ltr">

```powershell
# احذف الحاوية والـ volume وأعد التشغيل
docker rm -f pg-sh-school
docker volume rm pg-sh-school-data
./scripts/serve.ps1
```

</div>


**خطأ: "FATAL: password authentication failed"**

<div dir="ltr">

```powershell
# تأكد من تطابق PG_USER/PG_PASSWORD في .env مع الحاوية
# ثم احذف الـ volume وأعد الإنشاء
docker volume rm pg-sh-school-data
./scripts/db_up.ps1
```

</div>


**خطأ: "port 5433 already in use"**

<div dir="ltr">

```powershell
# غيّر PG_PORT في .env
# مثلاً: PG_PORT=5434
```

</div>


### مشاكل التصدير

**خطأ: "WeasyPrint not available"**

<div dir="ltr">

```powershell
# يتم استخدام ReportLab تلقائياً كـ fallback
# لتثبيت WeasyPrint:
pip install WeasyPrint>=60.0
```

</div>


**PDF يظهر مربعات بدل العربي:**

<div dir="ltr">

```powershell
# تأكد من وجود خطوط عربية في:
# backend/static/fonts/
# أو استخدم ReportLab مع:
pip install arabic-reshaper python-bidi
```

</div>


**خطأ: "openpyxl not found"**

<div dir="ltr">

```powershell
pip install openpyxl>=3.1.0
```

</div>


### مشاكل الاستيراد

**خطأ: "ImportError: No module named 'django'"**

<div dir="ltr">

```powershell
# تأكد من تفعيل البيئة الافتراضية
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

</div>


**خطأ: "java command is not found" (عند استيراد PDF)**

<div dir="ltr">

```powershell
# هذا طبيعي - سيستخدم pdfplumber تلقائياً
# لتثبيت Java (اختياري):
# قم بتثبيت Java JDK 8+ من oracle.com
```

</div>


### مشاكل HTTPS المحلي

**تحذير: "You're accessing the development server over HTTPS"**

<div dir="ltr">

```powershell
# استخدم HTTP صريحاً:
http://127.0.0.1:8000/

# أو شغّل HTTPS الصحيح:
./scripts/serve_https.ps1
# سيفتح على: https://127.0.0.1:8443/
```

</div>


**خطأ: "SSL certificate verify failed"**

<div dir="ltr">

```powershell
# ثبّت الشهادة في Windows:
./scripts/trust_dev_cert.ps1
```

</div>


---

## 🎨 تخصيص الواجهة

### الخطوط العربية
الخطوط المدمجة في `assets/fonts/`:
- **Noto Kufi Arabic** - للنصوص العامة
- **Amiri** - للعناوين والنصوص التقليدية

لتغيير الخطوط، عدّل `@font-face` في القوالب.

### الألوان والثيم
الألوان الأساسية في `:root` CSS variables:

<div dir="ltr">

```css
:root {
  --primary-color: #800000;    /* عنابي */
  --secondary-color: #FFD700;  /* ذهبي */
  --accent-color: #4A90E2;     /* أزرق */
}
```

</div>


### تخصيص gen_index.py
لتحديث قائمة الملفات في `index.html`:

<div dir="ltr">

```powershell
python gen_index.py        # تحديث
python gen_index.py --check  # فحص فقط
```

</div>


المتغيرات في `gen_index.py`:
- `INCLUDE_EXT` - امتدادات الملفات المرغوبة
- `EXCLUDE_DIRS` - مجلدات مستثناة
- `EXCLUDE_FILES` - ملفات محددة مستثناة

---

## 📚 وثائق إضافية

- [RBAC Documentation](DOC/RBAC.md) - نظام الصلاحيات
- [Security & Environment Variables](DOC/SECRETS_AND_ENV_ar.md) - الأمان والمتغيرات
- [Strategic Plan 2025](DOC/STRATEGY_2025_PRO_ar.md) - الخطة الاستراتيجية
- [Contributing Guidelines](CONTRIBUTING.md) - دليل المساهمة
- [Code of Conduct](CODE_OF_CONDUCT.md) - قواعد السلوك
- [Security Policy](SECURITY.md) - سياسة الأمان

---

## 🤝 المساهمة

نرحب بمساهماتك! يُرجى قراءة [CONTRIBUTING.md](CONTRIBUTING.md) أولاً.

### سير العمل المقترح

1. Fork المستودع
2. أنشئ branch للميزة: `git checkout -b feature/amazing-feature`
3. Commit التغييرات: `git commit -m "Add amazing feature"`
4. Push للـ branch: `git push origin feature/amazing-feature`
5. افتح Pull Request

### معايير الكود

- **Black** للتنسيق (line length: 100)
- **Flake8** للـ linting
- **Type hints** حيثما أمكن
- **Docstrings** للدوال والكلاسات

**تشغيل الفحوصات:**

<div dir="ltr">

```powershell
./scripts/dev_checks.ps1
# أو يدوياً:
black --check backend/
flake8 backend/ --max-line-length=100
python backend/manage.py test
```

</div>


---

## 🔒 الأمان

لتقديم بلاغ أمني، يُرجى مراجعة [SECURITY.md](SECURITY.md).

**Best Practices للإنتاج:**
- ✅ غيّر `DJANGO_SECRET_KEY` إلى قيمة عشوائية قوية
- ✅ اضبط `DJANGO_DEBUG=False`
- ✅ حدد `DJANGO_ALLOWED_HOSTS` بدقة
- ✅ استخدم HTTPS فقط (TLS 1.2+)
- ✅ فعّل HSTS و CSP headers
- ✅ استخدم PostgreSQL passwords قوية
- ✅ قم بالنسخ الاحتياطي بانتظام

---

## 📄 الترخيص

هذا المشروع مرخص بموجب [MIT License](LICENSE).


<div dir="ltr">

```
Copyright (c) 2025 مدرسة الشحانية الإعدادية الثانوية

Permission is hereby granted, free of charge, to any person obtaining a copy...
```

</div>


---

## 🌟 الشكر والتقدير

- **Django** - إطار العمل الأساسي
- **PostgreSQL** - قاعدة البيانات
- **Bootstrap** - الواجهة الأمامية
- **WeasyPrint** - تصدير PDF المتقدم
- **المساهمين** - جميع من ساهموا في هذا المشروع

---

## 📞 الدعم والاتصال

- **المستودع**: [github.com/mesuef1974/sh_school_015](https://github.com/mesuef1974/sh_school_015)
- **Issues**: [إبلاغ عن مشكلة](https://github.com/mesuef1974/sh_school_015/issues)
- **Pull Requests**: [المساهمات](https://github.com/mesuef1974/sh_school_015/pulls)

---

## 📊 الإحصائيات

- **اللغة الرئيسية**: Python 🐍
- **الإصدار**: 1.0.0
- **آخر تحديث**: أكتوبر 2025
- **الحالة**: نشط ✅

---

---

<div dir="ltr" align="center">

### Built with ❤️ for Shahania School, Qatar

**Made in Qatar 🇶🇦 | Powered by Django & PostgreSQL**

</div>

</div>
