# 🧪 اختبار تحويل الأيام - TEST DAY CONVERSION

## ✅ الملفات المُعدلة (8 ملفات):

### Backend - Python:
1. ✅ `backend/school/views.py`
   - السطر 3681-3687: دالة `iso_to_school_dow()`
   - السطر 3632: `api_attendance_bulk_save`
   - السطر 3702: `get_period_times`
   - السطر 3749: `get_subject_per_period`
   - السطر 3767: `get_editable_periods_for_teacher`

2. ✅ `backend/apps/attendance/selectors.py`
   - السطر 148-153: `get_teacher_today_periods`

3. ✅ `backend/apps/attendance/services/attendance.py`
   - السطر 27-38: `_map_iso_to_school_day`
   - السطر 167-169: حفظ `day_of_week`

### Frontend - JavaScript/HTML:
4. ✅ `backend/school/templates/school/teacher_week_matrix.html`
   - السطر 100-160: سكريبت تحديد الحصة الحالية

5. ✅ `backend/school/templates/_base_maronia.html`
   - السطر 357-424: دالة عامة + Auto-fix script

---

## 🔢 صيغة التحويل:

```python
# Python
school_day = iso_weekday % 7 + 1

# JavaScript
schoolDow = (jsDay === 0) ? 1 : (jsDay + 1)
```

### الترقيم الصحيح:
- **الأحد** = 1 ✅
- **الاثنين** = 2 ✅
- **الثلاثاء** = 3 ✅
- **الأربعاء** = 4 ✅
- **الخميس** = 5 ✅
- **الجمعة** = 6 ✅
- **السبت** = 7 ✅

---

## 🧪 خطوات الاختبار:

### 1. اختبار Backend:
```python
# في Django shell:
python manage.py shell

from datetime import date
from school.views import iso_to_school_dow

# اختبار يوم الثلاثاء
dt = date(2025, 10, 21)  # الثلاثاء
print(f"ISO weekday: {dt.isoweekday()}")  # يجب أن يكون: 2
print(f"School day: {iso_to_school_dow(dt)}")  # يجب أن يكون: 3 ✅
```

### 2. اختبار Frontend:
1. افتح أي صفحة في المتصفح
2. افتح Console (F12)
3. ابحث عن الرسائل:
   ```
   🕐 Current Time: ...
   📅 School Day: 3 الثلاثاء  ← يجب أن يكون 3 للثلاثاء
   📚 Current Period: 7
   ```

### 3. اختبار المربع الأخضر:
- يجب أن يظهر المربع الأخضر تحت **الثلاثاء** (3)
- في الحصة السابعة (7)

---

## 🐛 إذا استمرت المشكلة:

### افحص Console للأخطاء:
```javascript
// في Console المتصفح:
window.getSchoolDayOfWeek()  // يجب أن يرجع: 3
new Date().getDay()           // يرجع: 2 (الثلاثاء في JS)
```

### تأكد من تحديث الصفحة:
- امسح Cache: `Ctrl + Shift + R`
- أعد تشغيل Django

---

## 📊 جدول التحويل الكامل:

| اليوم    | JS getDay() | ISO isoweekday() | School Format | ✅  |
|---------|-------------|------------------|---------------|-----|
| الأحد   | 0           | 7                | 1             | ✅  |
| الاثنين | 1           | 1                | 2             | ✅  |
| الثلاثاء| 2           | 2                | 3             | ✅  |
| الأربعاء| 3           | 3                | 4             | ✅  |
| الخميس  | 4           | 4                | 5             | ✅  |
| الجمعة  | 5           | 5                | 6             | ✅  |
| السبت   | 6           | 6                | 7             | ✅  |

---

تاريخ الاختبار: 2025-10-21
الحالة: ✅ جاهز للاختبار
