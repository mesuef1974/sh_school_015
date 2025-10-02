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
2. اختر Source: Deploy from a branch.
3. اختر الفرع `main` (أو `master` حسب مستودعك) والمسار `/ (root)`.
4. احفظ الإعدادات وانتظر حتى يتم بناء الصفحة. سيكون موقعك متاحًا على رابط شبيه بـ:
   `https://<username>.github.io/<repository>/`

تأكد من أن الروابط نسبية (وهي كذلك هنا)، لذا ستعمل على GitHub Pages بدون تغييرات إضافية.

## سير العمل المقترح للتحديثات
1. إضافة أو تحديث الملفات داخل المجلدات.
2. تشغيل `python .\gen_index.py` لتحديث قائمة المحتوى.
3. فتح `index.html` محليًا للتأكد.
4. `git add .` ثم `git commit -m "تحديث القائمة"` ثم `git push`.
5. إذا كان GitHub Pages مفعّلًا، ستُحدَّث الصفحة تلقائيًا.

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