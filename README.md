# منصة الوثائق - sh_school_015

[![CI](https://github.com/mesuef1974/sh_school_015/actions/workflows/python-ci.yml/badge.svg)](https://github.com/mesuef1974/sh_school_015/actions/workflows/python-ci.yml)
[![Links](https://github.com/mesuef1974/sh_school_015/actions/workflows/links-validate.yml/badge.svg)](https://github.com/mesuef1974/sh_school_015/actions/workflows/links-validate.yml)
[![CodeQL](https://github.com/mesuef1974/sh_school_015/actions/workflows/codeql.yml/badge.svg)](https://github.com/mesuef1974/sh_school_015/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

بوابة بسيطة باللغة العربية (RTL) تعرض كل الوثائق والملفات المتوفرة داخل هذا المستودع، مع توليد تلقائي للقائمة وروابط مباشرة. تم تضمين تحسينات على الواجهة لإظهار حجم الملف وتاريخ آخر تعديل مع تجميع المحتوى حسب المجلدات.

## المتطلبات
- Python 3.11 أو أحدث (3.11+) على الجهاز (Windows أو macOS أو Linux)

## كيف أُجهّز بيئة التطوير على ويندوز؟
لتجنب رسالة "No pyvenv.cfg file" وضمان توفر الأدوات (Black/Flake8)، استخدم السكربت المدمج:

```powershell
# من جذر المشروع
./scripts/dev_setup.ps1
```

ما الذي يفعله السكربت؟
- ينشئ بيئة افتراضية .venv إذا كانت مفقودة أو تالفة.
- إذا كانت `.venv` مقفلة أو معطوبة (مثلاً خطأ Permission denied أو غياب pip)، سيحاول حذفها أو استخدام مسار بديل مؤقت `.venv_fix` تلقائيًا وإصلاح pip عبر ensurepip.
- يفعّل البيئة ويحدث pip.
- يثبّت الأدوات من requirements-dev.txt (Black و Flake8).
- يشغّل فحص Black وFlake8، ويشغّل `python gen_index.py --check`. 

إذا أردت تشغيل الأوامر يدويًا:
```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
black --check gen_index.py
flake8 gen_index.py --max-line-length=100
python gen_index.py --check
```

## كيف أُحدّث قائمة المحتوى؟
1. أضف/احذف الملفات داخل المستودع (HTML, PDF, صور, Excel, …).
2. شغّل السكربت:
   - على ويندوز (PowerShell):
     ```powershell
     python .\gen_index.py
     ```
3. سيتكفّل السكربت بتحديث الجزء الموجود بين العلامتين في `index.html`:
   ```html
   <!-- AUTO_LIST_START -->
   ... يتم الاستبدال هنا تلقائيًا ...
   <!-- AUTO_LIST_END -->
   ```
4. افتح `index.html` محليًا لتتأكد من ظهور العناصر بالشكل المطلوب.
5. قم بعمل commit ثم push للتغييرات.

ملاحظات:
- السكربت يستثني تلقائيًا مجلدات شائعة مثل `.git`, `venv`, `node_modules`, `__pycache__`, `build`, `dist`.
- لروابط الويب يُستخدَم دائمًا الفاصل `/` حتى على ويندوز.
- يدعم السكربت ترميز المسارات غير اللاتينية تلقائيًا.

## تشغيل السيرفر (Django + Postgres)
لتشغيل الباكند كاملًا بطريقة احترافية على ويندوز، استخدم السكربت الموحّد:

```powershell
# من جذر المشروع
./scripts/serve.ps1
```

ماذا يفعل هذا السكربت؟
- يقرأ `backend/.env` ويشغّل حاوية PostgreSQL متوافقة مع متغيّرات `PG_*` عبر `scripts/db_up.ps1` (يتعامل مع المنافذ وكلمات السر تلقائيًا).
- يطبّق الهجرات: `python manage.py migrate`.
- ينشئ مستخدمًا إداريًا تلقائيًا إذا كانت متغيرات البيئة التالية موجودة في `.env`:
  - `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD`.
- يشغّل تهيئة صلاحيات المجموعات RBAC: `python manage.py bootstrap_rbac`.
- يبدأ الخادم: `python manage.py runserver 0.0.0.0:8000` (يمكن تغيير المضيف والمنفذ عبر `DJANGO_RUN_HOST` و`DJANGO_RUN_PORT`).

تلميحات إعداد `.env` (ملف: `backend/.env`):
```env
# مثال سريع
DJANGO_SECRET_KEY=change-me-very-secret
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

PG_DB=sh_school
PG_USER=postgres
PG_PASSWORD=postgres
PG_HOST=127.0.0.1
PG_PORT=5433  # يجب أن يطابق منفذ المضيف الذي ستحجزه Docker

# (اختياري) إنشاء سوبر يوزر تلقائيًا في أول تشغيل
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=Admin@12345

# (اختياري) تغيير مضيف/منفذ تشغيل السيرفر
DJANGO_RUN_HOST=0.0.0.0
DJANGO_RUN_PORT=8000
```

استكشاف الأخطاء الشائعة:
- تعارض اسم الحاوية: إذا ظهرت رسالة أن الحاوية `pg-sh-school` موجودة، احذفها وأعد التشغيل:
  ```powershell
  docker rm -f pg-sh-school
  docker volume rm pg-sh-school-data  # لإعادة تهيئة بيانات التطوير
  ./scripts/serve.ps1
  ```
- فشل المصادقة: تأكد أن `PG_USER/PG_PASSWORD` في `.env` تطابق إعدادات الحاوية. السكربت يعيد إنشاء الحاوية والـ volume ليتطابقا مع `.env`.
- المنفذ مشغول: غيّر `PG_PORT` في `.env` (مثلاً 5434)، ثم أعد تشغيل `./scripts/serve.ps1`.
- خطأ: Database is uninitialized and superuser password is not specified: شغّل `./scripts/serve.ps1` أو `./scripts/db_up.ps1` وسيكتشف السكربت الحالة ويُعيد تهيئة مجلد البيانات تلقائيًا بكلمة السر من `.env`.

## ما يظهر في القائمة
- يتم تجميع العناصر حسب أعلى مجلد (مثلاً: `DOC`, `assets`, أو `(الجذر)` للملفات في مستوى الجذر).
- لكل عنصر:
  - اسم/مسار الملف كنص الرابط.
  - حجم الملف (KB/MB).
  - تاريخ آخر تعديل (محلي) بصيغة `YYYY-MM-DD HH:MM`.
- يمكنك طي/فتح كل مجموعة بواسطة عنصر `<details>`. 

## تخصيص الاستثناءات
إذا رغبت باستثناء ملفات معيّنة، يمكنك تعديل المتغيرات في `gen_index.py`:
- `INCLUDE_EXT`: امتدادات الملفات المرغوبة.
- `EXCLUDE_DIRS`: مجلدات مستبعدة.
- `EXCLUDE_FILES`: ملفات محددة مستبعدة (تم استبعاد `index.html` افتراضيًا حتى لا يظهر في القائمة).

## الخطوط العربية
تم تضمين تعريفات `@font-face` لخط "Noto Kufi Arabic" وخط "Amiri" الموجودة داخل `assets/fonts` لضمان ثبات المظهر الطباعي. يمكنك تعديل التعاريف حسب حاجتك.

## النشر عبر GitHub Pages
يمكن عرض الموقع مباشرة من الفرع الرئيسي:
1. اذهب إلى Settings > Pages في مستودع GitHub.
1. اختر Source: Deploy from a branch.
1. اختر الفرع `main` (أو `master` حسب مستودعك) والمسار `/ (root)`.
1. احفظ الإعدادات وانتظر حتى يتم بناء الصفحة. سيكون موقعك متاحًا على رابط شبيه بـ:
   `https://<username>.github.io/<repository>/`

تأكد من أن الروابط نسبية (وهي كذلك هنا)، لذا ستعمل على GitHub Pages بدون تغييرات إضافية.

## سير العمل المقترح للتحديثات
1. إضافة أو تحديث الملفات داخل المجلدات.
1. تشغيل `python .\gen_index.py` لتحديث قائمة المحتوى.
1. فتح `index.html` محليًا للتأكد.
1. `git add .` ثم `git commit -m "تحديث القائمة"` ثم `git push`.
1. إذا كان GitHub Pages مفعّلًا، ستُحدَّث الصفحة تلقائيًا.

## أسئلة أو تخصيصات إضافية
- تريد ألوانًا/شعارًا مختلفًا؟ حدّث قيم الألوان في `:root` داخل `index.html` وغيّر الصور ضمن `assets/img`.
- تريد فرزًا مختلفًا أو تجميعًا أعمق؟ عدّل دالة `group_by_top` في `gen_index.py` أو طريقة الترتيب في `collect_files`.

---

## خيارات gen_index.py
- python gen_index.py: يكتب التغييرات إلى index.html (الوضع الافتراضي).
- python gen_index.py --check: يفحص فقط دون كتابة ويطبع عدد العناصر المتوقع.
- python gen_index.py --write: يفرض الكتابة حتى عند تمرير راية أخرى.

# English (brief)
Simple Arabic RTL landing page that auto-lists repository documents with direct links. Run `python gen_index.py` to regenerate the list between AUTO_LIST markers in `index.html`. Items are grouped by top-level folder and show file size and last modified timestamp. Fonts are embedded via `@font-face`. For deployment, enable GitHub Pages from the root of the main branch.

## معايير وممارسات احترافية
- قوالب قضايا (Issues) وطلبات السحب (Pull Requests) بالعربية ضمن `.github`.
- آليات CI تلقائية:
  - Python CI: تنسيق (Black) وفحص أسلوبي (Flake8) وفحص المولّد `gen_index.py --check`.
  - Links Validator: فحص الروابط في README وملفات HTML أسبوعيًا وعند كل تغيير.
  - CodeQL: تحليل أمني أساسي للشفرة (Python).
- حوكمة المستودع: `CODEOWNERS`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, وترخيص `LICENSE`.
- أدوات مطورين: `requirements-dev.txt` وتهيئة `pre-commit` اختيارية.


## نسخة احتياطية لقاعدة البيانات (Backup)
لأخذ نسخة احتياطية كاملة من قاعدة بيانات PostgreSQL المستخدمة في المشروع، لديك خياران:

- عبر أمر إدارة Django (موصى به):
  - يقوم بإنشاء ملف .sql (أو .sql.gz) داخل مجلد backups في جذر المشروع، ويستخدم حاوية Docker pg-sh-school تلقائيًا.
  
  أوامر:
  ```powershell
  # من جذر المشروع
  cd D:\sh_school_015\backend
  # ملف الإخراج الافتراضي: ..\backups\pg_backup_<db>_<YYYYmmdd_HHMMSS>.sql
  python manage.py backup_db
  
  # مخرجات مضغوطة gzip
  python manage.py backup_db --gzip
  
  # تحديد مجلد إخراج مخصص
  python manage.py backup_db --out D:\sh_school_015\my_backups
  ```
  
  ملاحظات الاستعادة (Restore):
  ```powershell
  # ملف SQL عادي
  psql -h 127.0.0.1 -U <PG_USER> -d <PG_DB> -f "D:\\sh_school_015\\backups\\pg_backup_<db>_<ts>.sql"
  
  # ملف .sql.gz
  gunzip -c "D:\\sh_school_015\\backups\\pg_backup_<db>_<ts>.sql.gz" | psql -h 127.0.0.1 -U <PG_USER> -d <PG_DB>
  ```

- سكربت PowerShell (اختياري):
  ```powershell
  # من جذر المشروع
  ./scripts/db_backup.ps1           # إخراج SQL عادي إلى مجلد backups
  ./scripts/db_backup.ps1 -Gzip     # إخراج مضغوط .sql.gz
  ./scripts/db_backup.ps1 -OutDir D:\sh_school_015\my_backups
  ```

المتطلبات:
- يجب أن تكون حاوية Docker باسم `pg-sh-school` موجودة/تعمل (يتم تشغيلها تلقائيًا عبر ./scripts/serve.ps1).
- يستخدم السكربت/الأمر متغيرات الاتصال من `backend/.env` (PG_DB, PG_USER, PG_PASSWORD, PG_HOST, PG_PORT).

## أمثلة طلبات API على PowerShell (Windows)
عند نسخ أوامر cURL المصاغة لبيئة Bash إلى PowerShell ستظهر أخطاء مثل: `-d: The term '-d' is not recognized` لأن PowerShell لا يدعم صياغة الاستدعاء متعددة الأسطر باستخدام \\ ولا يمرر الرايات بنفس الطريقة. استخدم إحدى الطرق التالية:

- الطريقة الموصى بها: Invoke-RestMethod في PowerShell

1) الحصول على توكن JWT
```powershell
# من PowerShell (سطر واحد)
$resp = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/token/" -ContentType 'application/json' -Body (@{ username = 'mesuef'; password = '123123' } | ConvertTo-Json)
$access = $resp.access
$refresh = $resp.refresh
$access
```

2) استدعاء API باستخدام التوكن
```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/classes/' -Headers @{ Authorization = "Bearer $access" }
```

- بديل: استخدام cURL الموجود على ويندوز كسطر واحد (أو مع ^ لمتابعة السطر)

1) الحصول على التوكن (كسطر واحد):
```powershell
curl -X POST "http://127.0.0.1:8000/api/token/" -H "Content-Type: application/json" -d '{"username":"mesuef","password":"123123"}'
```

2) استدعاء API بالهيدر Authorization:
```powershell
$token = "<ACCESS_TOKEN>"
curl "http://127.0.0.1:8000/api/classes/" -H "Authorization: Bearer $token"
```

ملاحظات هامة:
- لا تستخدم الشرطة المائلة العادية \\ لمتابعة الأسطر في PowerShell؛ استعمل ^ أو اكتب الأمر في سطر واحد.
- مع Invoke-RestMethod استخدم -ContentType و -Body (وحوّل الجسم إلى JSON عبر ConvertTo-Json).
- إذا كان لديك كلٌ من curl.exe و alias لـ Invoke-WebRequest، يفضّل استدعاء المسار الكامل لـ curl.exe عند الحاجة: `& $Env:SystemRoot\System32\curl.exe ...`
- تأكد من تشغيل الخادم أولًا عبر: `./scripts/serve.ps1` وأن متغيرات السوبر يوزر في backend/.env صحيحة.

# منصة الوثائق - sh_school_015

[![CI](https://github.com/mesuef1974/sh_school_015/actions/workflows/python-ci.yml/badge.svg)](https://github.com/mesuef1974/sh_school_015/actions/workflows/python-ci.yml)
[![Links](https://github.com/mesuef1974/sh_school_015/actions/workflows/links-validate.yml/badge.svg)](https://github.com/mesuef1974/sh_school_015/actions/workflows/links-validate.yml)
[![CodeQL](https://github.com/mesuef1974/sh_school_015/actions/workflows/codeql.yml/badge.svg)](https://github.com/mesuef1974/sh_school_015/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

بوابة بسيطة باللغة العربية (RTL) تعرض كل الوثائق والملفات المتوفرة داخل هذا المستودع، مع توليد تلقائي للقائمة وروابط مباشرة. تم تضمين تحسينات على الواجهة لإظهار حجم الملف وتاريخ آخر تعديل مع تجميع المحتوى حسب المجلدات.

## المتطلبات
- Python 3.11 أو أحدث (3.11+) على الجهاز (Windows أو macOS أو Linux)

## كيف أُجهّز بيئة التطوير على ويندوز؟
لتجنب رسالة "No pyvenv.cfg file" وضمان توفر الأدوات (Black/Flake8)، استخدم السكربت المدمج:

```powershell
# من جذر المشروع
./scripts/dev_setup.ps1
```

ما الذي يفعله السكربت؟
- ينشئ بيئة افتراضية .venv إذا كانت مفقودة أو تالفة.
- إذا كانت `.venv` مقفلة أو معطوبة (مثلاً خطأ Permission denied أو غياب pip)، سيحاول حذفها أو استخدام مسار بديل مؤقت `.venv_fix` تلقائيًا وإصلاح pip عبر ensurepip.
- يفعّل البيئة ويحدث pip.
- يثبّت الأدوات من requirements-dev.txt (Black و Flake8).
- يشغّل فحص Black وFlake8، ويشغّل `python gen_index.py --check`. 

إذا أردت تشغيل الأوامر يدويًا:
```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
black --check gen_index.py
flake8 gen_index.py --max-line-length=100
python gen_index.py --check
```

## كيف أُحدّث قائمة المحتوى؟
1. أضف/احذف الملفات داخل المستودع (HTML, PDF, صور, Excel, …).
2. شغّل السكربت:
   - على ويندوز (PowerShell):
     ```powershell
     python .\gen_index.py
     ```
3. سيتكفّل السكربت بتحديث الجزء الموجود بين العلامتين في `index.html`:
   ```html
   <!-- AUTO_LIST_START -->
   ... يتم الاستبدال هنا تلقائيًا ...
   <!-- AUTO_LIST_END -->
   ```
4. افتح `index.html` محليًا لتتأكد من ظهور العناصر بالشكل المطلوب.
5. قم بعمل commit ثم push للتغييرات.

ملاحظات:
- السكربت يستثني تلقائيًا مجلدات شائعة مثل `.git`, `venv`, `node_modules`, `__pycache__`, `build`, `dist`.
- لروابط الويب يُستخدَم دائمًا الفاصل `/` حتى على ويندوز.
- يدعم السكربت ترميز المسارات غير اللاتينية تلقائيًا.

## تشغيل السيرفر (Django + Postgres)
لتشغيل الباكند كاملًا بطريقة احترافية على ويندوز، استخدم السكربت الموحّد:

```powershell
# من جذر المشروع
./scripts/serve.ps1
```

هذا السكربت سيقوم بـ:
- تشغيل/إعادة تشغيل حاوية Postgres باسم `pg-sh-school` بالاعتمادات من الملف `backend/.env`.
- تطبيق الترقيات (migrations).
- إنشاء/تحديث المستخدم الخارق (superuser) تلقائيًا حسب القيم في `.env` (اسم المستخدم/البريد/كلمة المرور).
- تهيئة صلاحيات المجموعات (RBAC).
- تشغيل `runserver`.

إذا واجهت مشكلة في رقم المنفذ PG_PORT داخل `.env` (تعليق بجانبه)، سيظهر تحذير بتنظيف القيمة وسيستخدم رقمًا صحيحًا فقط.

## استيراد الجداول من PDF (بدون Java أيضًا)
إذا أردت استخدام أمر Django لاستيراد الجداول من ملفات PDF، فلديك طريقتان:

- الطريقة الأسهل (موصى بها):
  ```powershell
  # من جذر المشروع
  ./scripts/backend_run.ps1 import_from_pdf D:\sh_school_015\DOC\school_DATA --dry-run
  ```
  هذا السكربت يقوم تلقائيًا بإنشاء/تفعيل بيئة .venv وتثبيت الحزم من requirements.txt قبل تنفيذ الأمر.

- الطريقة اليدوية:
  ```powershell
  # من جذر المشروع
  python -m venv .venv
  . .\.venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  python backend\manage.py import_from_pdf D:\sh_school_015\DOC\school_DATA --dry-run
  ```

ملاحظات هامة:
- يستخدم الأمر مكتبة tabula-py إن كانت متوفرة (تحتاج Java على النظام). هذا يعطي نتائج جيدة للجداول الشبكية.
- إن لم تتوفر Java أو فشل tabula، فهناك مسار بديل تلقائي يعمل بدون Java عبر pdfplumber + pandas (تمت إضافته في هذا المشروع).
- للتأكد من توفر الاعتماديات الخاصة بالمسار البديل (بدون Java):
  ```powershell
  pip install -r requirements-dev.txt
  ```
  هذا سيثبت pandas و pdfplumber الضروريّتين للمسار البديل.
- يمكنك إزالة راية `--dry-run` للتنفيذ الفعلي بعد التأكد من صحة القراءة.

استكشاف الأخطاء:
- ImportError: No module named 'django'
  - السبب: لم تُثبّت الاعتماديات داخل البيئة الافتراضية الفعّالة.
  - الحل السريع: استخدم السكربت الموحّد:
    ```powershell
    ./scripts/backend_run.ps1 import_from_pdf D:\sh_school_015\DOC\school_DATA --dry-run
    ```
    أو ثبّت يدويًا ثم أعد التنفيذ:
    ```powershell
    . .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python backend\manage.py import_from_pdf D:\sh_school_015\DOC\school_DATA --dry-run
    ```

إذا ظهرت رسالة مثل: `java command is not found`، فهذا يعني أن tabula حاولت العمل دون Java؛ ومع ذلك سيحاول الأمر تلقائيًا استخدام pdfplumber. إذا ظهر تنبيه بضرورة تثبيت pdfplumber أو pandas فقم بتثبيتهما كما في الأعلى.

## النسخ الاحتياطي والاستعادة لقاعدة البيانات (Postgres)
- إنشاء نسخة احتياطية (داخل مجلد backups افتراضيًا):
  ```powershell
  # تأكد أن الحاوية تعمل عبر serve.ps1 أو db_up.ps1
  ./scripts/db_backup.ps1
  # أو ضغط gzip
  ./scripts/db_backup.ps1 -Gzip
  ```
- استعادة نسخة احتياطية (تحذف محتوى قاعدة البيانات أولًا):
  ```powershell
  # مثال عملي حسب طلبك لاستعادة هذا الملف:
  ./scripts/db_restore.ps1 "D:\\sh_school_015\\backups\\pg_backup_sh_school_20251003_153856.sql" -Force
  ```
  خيارات:
  - استخدم `-Force` لتخطي سؤال التأكيد.
  - استخدم `-SkipDrop` إذا كنت لا تريد حذف مخطط public قبل الاستعادة (غير مستحسن عادةً).

ملاحظات:
- السكربتان يقرآن إعدادات الاتصال من `backend/.env` (PG_USER, PG_PASSWORD, PG_DB, PG_PORT).
- تتم العملية بالكامل داخل الحاوية `pg-sh-school`، ويتم نسخ ملف النسخة الاحتياطية مؤقتًا إلى داخلها ثم حذفه.


## استيراد الطلاب من Excel (يدعم شيت لكل صف)
إذا كان ملف Excel يحتوي على ورقة (Sheet) لكل صف، أصبح أمر الاستيراد يدعم ذلك مباشرة:

- تجربة بدون كتابة (Dry-Run):
```powershell
python backend\manage.py import_students "D:\\sh_school_015\\DOC\\school_DATA\\new_studants.xlsx" --all-sheets --sheet-per-class --dry-run
```

- تنفيذ فعلي (آمن للإعادة – يعتمد على national_no):
```powershell
python backend\manage.py import_students "D:\\sh_school_015\\DOC\\school_DATA\\new_studants.xlsx" --all-sheets --sheet-per-class
```

شرح الخيارات:
- --all-sheets: يستورد كل الأوراق في المصنف (يمكن بدلاً منه استخدام: --sheet ALL).
- --sheet-per-class: يتعامل مع اسم الورقة كاسم الصف/الشعبة إذا كان عمود section مفقودًا أو فارغًا،
  ويحاول استخراج رقم الصف من اسم الورقة إذا كان عمود grade مفقودًا.
- ما زال بإمكانك تحديد ورقة معينة بالاسم أو الفهرس:
```powershell
python backend\manage.py import_students "D:\\sh_school_015\\DOC\\school_DATA\\new_studants.xlsx" --sheet "الصف- 12" --sheet-per-class --dry-run
```
ملاحظة هامة: لا تستخدم مسارًا افتراضيًا مثل `...xlsx`. يجب وضع المسار الحقيقي للملف، ووضعه بين علامات اقتباس. في سطور أوامر PowerShell داخل أمثلة Python، استخدم شرطة خلفية مزدوجة `\\` داخل السلسلة.

ملاحظات:
- الأعمدة المتوقعة إن وجدت: national_no, studant_name, studant_englisf_name, date_of_birth, needs,
  grade, section, stu_phone_no, stu_email, nationality, parent_national_no, name_parent, relation_parent,
  extra_phone_no, parent_email. أي عمود مفقود يُعامل كفارغ وستظهر رسالة تحذير.
  - ملاحظة: لا يزال الحقل القديم parent_phone مدعومًا كبديل (fallback) لملء parent_national_no إذا لم يتوفر عمود خاص به.
- عند تفعيل --sheet-per-class: إذا كان عمود section غير موجود/فارغ، سيُستخدم اسم الورقة كـ section_label
  وكذلك كاسم الصف لإنشاء/مطابقة كيان Class في قاعدة البيانات. وإذا كان عمود grade مفقودًا، سيُحاول استخراج رقم
  الصف من بداية اسم الورقة (مثل 12 من "12/1" أو "12-Science").

- معالجة تاريخ الميلاد والعمر: يتم حفظ تاريخ الميلاد (dob) كما في الملف، ويتم حساب العمر (age) تلقائيًا عند الحفظ
  اعتمادًا على تاريخ اليوم. لا حاجة لإدخال العمر يدويًا، وسيتم تحديثه تلقائيًا عند تعديل dob.
- معالجة الجنسية: يمكنك تزويد عمود باسم nationality أو بالعربية "الجنسية"، وسيتم استيراده إلى حقل الجنسية في النموذج.

### طلبك الحالي: مسح الطلاب واستيراد جديد + جلب الجنسية من ملف آخر
- لمسح جميع بيانات الطلاب ثم الاستيراد من الملف الجديد مع جلب الجنسية من ملف آخر، استخدم:
```powershell
# مسح الطلاب ثم الاستيراد من الملف الرئيسي مع اعتبار كل شيت صفًا
python backend\manage.py import_students "D:\sh_school_015\DOC\school_DATA\new_studants.xlsx" --all-sheets --sheet-per-class --clean --nationality-xlsx "D:\sh_school_015\DOC\school_DATA\students_03.xlsx" --expect-total 742
```
شرح الخيارات المضافة:
- `--wipe`: يحذف جميع سجلات الطلاب الحالية قبل الاستيراد (احذر: لا رجعة بدون نسخة احتياطية).
- `--clean`: اختصار عربي لـ "الاستيراد على نظافة" — يعمل تمامًا مثل `--wipe` لتهيئة البيانات قبل الاستيراد.
- `--nationality-xlsx`: مسار ملف Excel إضافي يحتوي على عمود الجنسية. تتم المطابقة أساسًا على الحقل national_no. إذا لم تتوفر الجنسية داخل الملف الرئيسي فسيتم أخذها من هذا الملف.
- تبقى جميع الخيارات السابقة متاحة مثل `--dry-run` للتجربة قبل التنفيذ الفعلي.
- ملاحظة: عند استخدام `--clean` أو `--wipe` سيتم إعادة ضبط تسلسل أرقام المعرّفات IDs لجدول الطلاب تلقائيًا بحيث تبدأ من 1، وعند استيراد 742 طالبًا ستكون المعرفات من 1 إلى 742.


### ملاحظة مهمة حول جوال/إيميل ولي الأمر
- العمود parent_phone_no مدعوم تلقائيًا (يُعامل كـ parent_phone) وبجانب ذلك يتم التعامل مع extra_phone_no إن وُجد.
- إذا احتوت خانة جوال ولي الأمر على رقمين أو أكثر، فسيتم توزيعها كالتالي:
  - الرقم الأول → parent_phone (الرئيسي)
  - الرقم الثاني وما بعده → extra_phone_no (مفصولة بفواصل)
- إذا لم يوجد رقم في parent_phone لكن يوجد في extra_phone_no، فسيؤخذ أول رقم من extra_phone_no كرقم رئيسي، والباقي يبقى في extra_phone_no.
- يتم تنظيف الأرقام واستخراج المتتاليات الرقمية ذات 6 أرقام فأكثر فقط، مع إزالة التكرارات والحفاظ على الترتيب.
- يتم استيراد بريد ولي الأمر من العمود parent_email (وكذلك الأسماء العربية المكافئة مثل "ايميل ولي الامر" و"البريد الالكتروني لولي الامر").
# منصة الوثائق - sh_school_015

[![CI](https://github.com/mesuef1974/sh_school_015/actions/workflows/python-ci.yml/badge.svg)](https://github.com/mesuef1974/sh_school_015/actions/workflows/python-ci.yml)
[![Links](https://github.com/mesuef1974/sh_school_015/actions/workflows/links-validate.yml/badge.svg)](https://github.com/mesuef1974/sh_school_015/actions/workflows/links-validate.yml)
[![CodeQL](https://github.com/mesuef1974/sh_school_015/actions/workflows/codeql.yml/badge.svg)](https://github.com/mesuef1974/sh_school_015/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

بوابة بسيطة باللغة العربية (RTL) تعرض كل الوثائق والملفات المتوفرة داخل هذا المستودع، مع توليد تلقائي للقائمة وروابط مباشرة. تم تضمين تحسينات على الواجهة لإظهار حجم الملف وتاريخ آخر تعديل مع تجميع المحتوى حسب المجلدات.

## المتطلبات
- Python 3.11 أو أحدث (3.11+) على الجهاز (Windows أو macOS أو Linux)

## كيف أُجهّز بيئة التطوير على ويندوز؟
لتجنب رسالة "No pyvenv.cfg file" وضمان توفر الأدوات (Black/Flake8)، استخدم السكربت المدمج:

```powershell
# من جذر المشروع
./scripts/dev_setup.ps1
```

ما الذي يفعله السكربت؟
- ينشئ بيئة افتراضية .venv إذا كانت مفقودة أو تالفة.
- إذا كانت `.venv` مقفلة أو معطوبة (مثلاً خطأ Permission denied أو غياب pip)، سيحاول حذفها أو استخدام مسار بديل مؤقت `.venv_fix` تلقائيًا وإصلاح pip عبر ensurepip.
- يفعّل البيئة ويحدث pip.
- يثبّت الأدوات من requirements-dev.txt (Black و Flake8).
- يشغّل فحص Black وFlake8، ويشغّل `python gen_index.py --check`. 

إذا أردت تشغيل الأوامر يدويًا:
```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
black --check gen_index.py
flake8 gen_index.py --max-line-length=100
python gen_index.py --check
```

## كيف أُحدّث قائمة المحتوى؟
1. أضف/احذف الملفات داخل المستودع (HTML, PDF, صور, Excel, …).
2. شغّل السكربت:
   - على ويندوز (PowerShell):
     ```powershell
     python .\gen_index.py
     ```
3. سيتكفّل السكربت بتحديث الجزء الموجود بين العلامتين في `index.html`:
   ```html
   <!-- AUTO_LIST_START -->
   ... يتم الاستبدال هنا تلقائيًا ...
   <!-- AUTO_LIST_END -->
   ```
4. افتح `index.html` محليًا لتتأكد من ظهور العناصر بالشكل المطلوب.
5. قم بعمل commit ثم push للتغييرات.

ملاحظات:
- السكربت يستثني تلقائيًا مجلدات شائعة مثل `.git`, `venv`, `node_modules`, `__pycache__`, `build`, `dist`.
- لروابط الويب يُستخدَم دائمًا الفاصل `/` حتى على ويندوز.
- يدعم السكربت ترميز المسارات غير اللاتينية تلقائيًا.

## تشغيل السيرفر (Django + Postgres)
لتشغيل الباكند كاملًا بطريقة احترافية على ويندوز، استخدم السكربت الموحّد:

... (المحتوى الأصلي مستمر أدناه) ...

## إنشاء/تحديث حساب السوبر يوزر بسرعة
هناك ثلاث طرق مضمونة وسهلة:

- الطريقة الموصى بها (تعمل من أي مكان):
  ```powershell
  scripts\ensure_superuser.ps1 --username admin.pro --email admin@school.qa --password "StrongP@ssw0rd!"
  ```

- مباشرة عبر manage.py (من داخل مجلد backend أو من الجذر):
  ```powershell
  # من الجذر
  python backend\manage.py ensure_superuser --username admin.pro --email admin@school.qa --password "StrongP@ssw0rd!"

  # أو إذا كنت داخل مجلد backend بالفعل
  python manage.py ensure_superuser --username admin.pro --email admin@school.qa --password "StrongP@ssw0rd!"
  ```

- عبر الملف الغلاف backend\ensure_superuser.py:
  ```powershell
  # وأنت في جذر المشروع
  python backend\ensure_superuser.py --username admin.pro --email admin@school.qa --password "StrongP@ssw0rd!"

  # أو إذا كنت داخل مجلد backend بالفعل (انتبه لا تُكرّر كلمة backend)
  python ensure_superuser.py --username admin.pro --email admin@school.qa --password "StrongP@ssw0rd!"
  ```

تنبيه مهم (خطأ شائع):
- إذا كنت داخل مجلد `backend` فلا تكتب `python backend\ensure_superuser.py` لأن هذا المسار سيترجم إلى `backend\\backend\\ensure_superuser.py` وهو غير موجود. بدلًا من ذلك استخدم: `python ensure_superuser.py`.

ملاحظات:
- يمكنك أيضًا وضع القيم في `backend\.env` بالمفاتيح التالية وسيقوم سكربت التشغيل بإنشاء السوبر يوزر تلقائيًا:
  ```ini
  DJANGO_SUPERUSER_USERNAME=admin.pro
  DJANGO_SUPERUSER_EMAIL=admin@school.qa
  DJANGO_SUPERUSER_PASSWORD=StrongP@ssw0rd!
  ```
  ثم شغّل:
  ```powershell
  scripts\serve.ps1
  ```
- جميع الأوامر السابقة إديمبوتنت: إذا كان المستخدم موجودًا يتم تحديث بريده/كلمته وأعلامه، وإن لم يوجد سيتم إنشاؤه.

## بيئات الإعدادات وواجهات الصحة (Settings + Health)
تم فصل إعدادات Django إلى ثلاثة ملفات في `backend/core/`:
- `settings_base.py`: إعدادات مشتركة.
- `settings_dev.py`: بيئة التطوير (DEBUG=True, CORS مفتوح، ALLOWED_HOSTS=*).
- `settings_prod.py`: بيئة الإنتاج (SECURE_*, HSTS، قوائم بيضاء لـ ALLOWED_HOSTS/CSRF/CORS).

المحوِّل `backend/core/settings.py` يختار الملف تلقائيًا بناءً على المتغير `DJANGO_ENV`:

```powershell
# افتراضيًا dev. لتجربة prod محليًا:
$env:DJANGO_ENV='prod'
$env:DJANGO_ALLOWED_HOSTS='localhost,127.0.0.1'
python backend\manage.py runserver
```

واجهات الصحة المضافة:
- `GET /livez` يعيد 204 عند جاهزية العملية (Liveness).
- `GET /healthz` يفحص اتصال قاعدة البيانات ويعيد 200 أو 500 (Readiness).
- أمر إدارة CI/CD: `python backend\manage.py healthcheck` يعيد 0 عند النجاح و1 عند الفشل (يطبع "ok" أو سبب الخطأ)، مفيد في حاويات/خدمات النظام.

تلميحات أمان الإنتاج (ملخّص):
- عيّن `DJANGO_ALLOWED_HOSTS` إلى نطاقاتك فقط (بدون بروتوكول).
- عيّن `DJANGO_CSRF_TRUSTED_ORIGINS` مع البروتوكول `https://` لنطاقات الواجهة.
- عيّن `DJANGO_CORS_ALLOWED_ORIGINS` لقائمة واجهات الويب المصرّح بها.
- حافظ على TLS عبر العاكس العكسي، وفعّل HSTS (مفعل في `prod`).

ملف نموذج للبيئة: `backend/.env.example` — انسخه إلى `backend/.env` وعدّل القيم.


## ملاحظة مهمة: تحذير "You're accessing the development server over HTTPS"
عند تشغيل الخادم التطويري بـ `runserver` ورؤية رسائل مشابهة لما يلي:

```
You're accessing the development server over HTTPS, but it only supports HTTP.
```

فهذا طبيعي لأن خادم التطوير في Django لا يدعم TLS/HTTPS. يحدث ذلك عادةً عندما يحاول المتصفح أو أداة خارجية الاتصال بالمنفذ 8000 عبر HTTPS بدل HTTP.

### ماذا أفعل؟
- استخدم رابط HTTP صريحًا: افتح `http://127.0.0.1:8000/` أو `http://localhost:8000/`.
- إذا كان لديك إشارة مرجعية (Bookmark) على `https://127.0.0.1:8000` فاحذفها أو غيّرها إلى HTTP.
- إن كان لديك إضافة متصفح تُجبر HTTPS (Force HTTPS)، عطّلها للمضيف المحلي.

### كيف أخدم HTTPS محليًا (اختياري)
إذا كنت تحتاج HTTPS محليًا (لاختبار ملفات تعريف الارتباط الآمنة أو HSTS)، لديك خيارات سريعة:

ملاحظة مهمة: تم تمكين django-extensions تلقائيًا في بيئة التطوير (settings_dev.py) لذا أمر runserver_plus سيكون متاحًا بمجرد تثبيت الحزمة في البيئة الافتراضية.

1) باستخدام django-extensions (طريقة سهلة):
```powershell
# داخل بيئتك الافتراضية
pip install django-extensions
# في حال عدم وجود شهادات dev.crt/dev.key، ولتوليدها بسرعة (يتطلب openssl):
./scripts/make_dev_cert.ps1
# ثم شغّل HTTPS على 8443:
python backend\manage.py runserver_plus --cert-file backend\certs\dev.crt --key-file backend\certs\dev.key 0.0.0.0:8443
```
ثم افتح: https://127.0.0.1:8443/

2) باستخدام Uvicorn + ASGI (بدون تغيير الكود):
```powershell
pip install uvicorn
# توليد شهادة ذاتية بسرعة (يتطلب openssl من Git for Windows):
./scripts/make_dev_cert.ps1
# ثم شغّل Uvicorn على منفذ 8443 (لاحظ استخدام المسارات بأسلوب ويندوز ممكن أيضًا):
python -m uvicorn backend.core.asgi:application --host 0.0.0.0 --port 8443 --ssl-keyfile backend\certs\dev.key --ssl-certfile backend\certs\dev.crt
```
ثم افتح: https://127.0.0.1:8443/

إذا لم يتوفر لديك openssl: يمكنك استعمال HTTP العادي على المنفذ 8000، أو تثبيت Git for Windows ليوفر openssl، أو استخدام أدوات مثل mkcert. ملفات الشهادة المتوقعة تحفظ في: backend\certs\dev.key و backend\certs\dev.crt.

نصيحة: اترك منفذ 8000 لـ HTTP التطويري الافتراضي، واستخدم منفذ 8443 لـ HTTPS المحلي عند الحاجة.


## تشغيل HTTPS محليًا (اختصار)
إذا احتجت إلى HTTPS محلي لاختبار ملفات تعريف الارتباط الآمنة أو إعدادات الأمان، استخدم السكربت الجاهز:

```powershell
# من جذر المشروع
scripts\make_dev_cert.ps1   # مرة واحدة فقط لإنشاء backend\certs\dev.key/dev.crt
scripts\serve_https.ps1     # يحاول تشغيل Uvicorn على 8443 مع TLS، ثم يسقط إلى runserver على 8000 عند الفشل
```

ملاحظات:
- السكربت يحاول توليد الشهادة تلقائيًا إذا لم يجدها، باستخدام OpenSSL (المتوفر عادة مع Git for Windows). إذا لم يتوفر OpenSSL سيعرض رسالة إرشادية.
- عند نجاح HTTPS افتح: https://127.0.0.1:8443/
- إذا فشل التشغيل عبر Uvicorn أو الشهادات غير متوفرة، سيبدأ خادم التطوير العادي على HTTP: http://127.0.0.1:8000/
- يمكنك التحكم في منفذ/مضيف HTTP الاحتياطي عبر متغيري البيئة: DJANGO_RUN_HOST و DJANGO_RUN_PORT.


## تشغيل الكل دفعة واحدة (All-in-one Dev Up)
لتشغيل كل المكوّنات محليًا بطريقة احترافية (Postgres + Redis + الهجرات + عامل RQ + الخادم HTTP/HTTPS + فحوص الصحة + فتح المتصفح):

```powershell
# من جذر المشروع
./scripts/dev_up.ps1
```

ماذا يفعل السكربت؟
- يفعّل .venv ويتحقق من المتطلبات، ويثبّت الأساسيات عند الحاجة.
- يقرأ backend/.env.
- يشغّل PostgreSQL (حاوية pg-sh-school) وRedis (حاوية redis-sh) عبر Docker.
- يطبّق الهجرات ويؤمّن السوبر يوزر (إن توفرت متغيّراته)، ويُجري bootstrap للأدوار.
- يفتح نافذتين: واحدة لعامل RQ، وأخرى لخادم HTTPS (Uvicorn + TLS) مع سقوط تلقائي إلى runserver.
- يجري فحص /healthz ويفتح المتصفح على /admin و/loads.

إيقاف الحاويات لاحقًا:
```powershell
docker stop pg-sh-school redis-sh
```


## إزالة تحذير "Not secure" على HTTPS محليًا
لإزالة تحذير المتصفح أثناء التطوير على https://127.0.0.1:8443، يمكنك تثبيت الشهادة التطويرية في مخزن الشهادات الموثوق على ويندوز:

```powershell
# من جذر المشروع
# الوثوق بالشهادة ضمن حساب المستخدم الحالي (لا يتطلب مسؤول)
scripts/trust_dev_cert.ps1

# أو استيرادها إلى مخزن الجهاز (يتطلب تشغيل PowerShell كمسؤول)
scripts/trust_dev_cert.ps1 -Machine

# لإزالة الشهادة لاحقًا (استخدم -Machine إذا كنت قد قمت بالتثبيت هناك)
scripts/trust_dev_cert.ps1 -Untrust
```
ملاحظات:
- إذا لم تكن الشهادة موجودة سيحاول السكربت إنشاء backend\certs\dev.crt عبر scripts\make_dev_cert.ps1.
- بعد الوثوق، افتح: https://127.0.0.1:8443/admin/ وسيزول التحذير في Edge/Chrome غالبًا.
- هذا الإجراء محلي للتطوير فقط؛ للإنتاج استخدم شهادة حقيقية من CA موثوقة.


## تشغيل السموك (Smoke) بسرعة
تنفيذ فحص دخولي خفيف يختبر نقاط الصحة بدون الحاجة لتشغيل خادم خارجي أو فتح متصفح.

- عبر سكربت ويندوز:
  ```powershell
  # من جذر المشروع
  scripts/smoke.ps1
  ```
- أو مباشرة عبر Django:
  ```powershell
  python backend\manage.py smoke
  ```
ما الذي يفحصه؟
- /livez يجب أن يعيد 204.
- /healthz يعيد 200 مع نص "ok" عندما قاعدة البيانات متاحة، أو 500 إذا كانت غير متاحة (يُعتبر مقبولًا كفحص دخولي).
سيُنهي بخروج 0 عند النجاح و1 عند الفشل، لتكامل سهل مع CI أو سكربتات التشغيل.