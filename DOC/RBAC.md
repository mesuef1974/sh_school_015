# نموذج الصلاحيات (RBAC) — مدرسة الشحّانية

> هذا المستند يعرّف الأدوار والصلاحيات وحدودها (Constraints) ومعايير القبول. يُستخدم كمرجع للتنفيذ في Django/DRF وواجهة المستخدم.

## 1) الأدوار الرسمية
- Admin (مدير النظام)
- Principal (المدير)
- Teachers (المعلمون)
- Staff (الموظفون/الكتبة)

## 2) مبادئ التصميم
- أقل صلاحية لازمة (Least Privilege).
- فرض الصلاحيات في الخادم أولًا (Server‑side), ثم في الواجهة (UI gating) لتحسين UX.
- دعم قيود النطاق Context Constraints (مثل: صفوف/مواد المعلّم فقط).

## 3) مصفوفة الصلاحيات (مختصر)
- Admin:
  - users: read/write/delete:any
  - roles: assign:any
  - classes, subjects, students, staff, enrollments: read/write:any
  - attendance, grades: read/write:any
  - reports: read/export:any
- Principal:
  - users: read:any
  - classes, subjects, students, staff, enrollments: read:any; write:limited (إدارية)
  - attendance, grades: read:any
  - reports: read/export:any
- Teacher:
  - classes: read:own; enrollments: read:class
  - students: read:class
  - attendance: read/write:class
  - subjects: read:own
  - grades: read:class; write:subject (مادته فقط)
  - reports: read:class; export:class
- Staff:
  - data entry: students/staff/classes/enrollments: read/write:assigned
  - reports: read:assigned; export:assigned

## 4) قيود النطاق (Constraints) — أمثلة
- Teacher:
  - subject_ids = [قائمة المواد المسندة]
  - class_ids = [قائمة الصفوف/الشُعب التي يدرّسها]
- Staff:
  - dept = 'registration' أو 'exams' لتحديد نوع البيانات المسموح بها.

## 5) ربط RBAC في Django/DRF (إرشاد تنفيذي مختصر)
- مجموعات Django: Admin, Principal, Teachers, Staff.
- Decorators/Permissions:
  - @permission_required أو Custom DRF Permission يعاين claim + constraint.
  - أمثلة مسارات يجب حمايتها:
    - GET/POST `/loads/export/assignments.*` — Admin/Principal فقط؛ Teacher على نطاق صفّه/مادته.
    - GET/POST `/loads/matrix/export.*` — Admin/Principal فقط؛ Teacher يقتصر على صفوفه.

## 6) حالات قبول (12 حالة أساسية)
1. Admin يستطيع تصدير جميع تقارير الأنصبة والمصفوفة.
2. Principal يستطيع تصدير جميع التقارير لكن لا يستطيع حذف مستخدمين.
3. Teacher يرى زر التصدير فقط عند تصفية الجدول لصفوفه/مادته.
4. Teacher لا يستطيع الوصول المباشر لمسار `/loads/export/assignments.xlsx` بدون قيود التصفية المملوكة.
5. Teacher يستطيع إدخال حضور فقط لصفوفه.
6. Teacher يستطيع إدخال درجات فقط لمادته.
7. Staff (registration) يستطيع تعديل بيانات الطلاب، ولا يستطيع تعديل الدرجات.
8. Staff (exams) يستطيع عرض الدرجات وإصدار تقاريرها، ولا يستطيع تعديل بيانات المستخدمين.
9. مستخدم بلا دور فعّال لا يرى أزرار التصدير ولا يستطيع الوصول لأي مسار محمي.
10. محاولة تجاوز RBAC عبر تغيير معلمات الطلب تُرفض بخطأ 403.
11. جميع محاولات الرفض تُسجّل في السجل مع user, path, role, reason.
12. الواجهة تخفي الأزرار غير المسموح بها، مع رسالة تلميح عند المرور.

## 7) خرائط التنفيذ (Mapping)
- Django Groups → أدوار. Permissions → نماذج/مسارات.
- قيود النطاق تخزَّن في Profile (مثال: `teacher_profile.subject_ids`, `teacher_profile.class_ids`).
- Middleware/Decorator يحقّق التوافق: role + constraint + action.

## 8) الاختبارات المقترحة
- وحدات (Unit): صلاحيات الديكوريتر/Permission لكل دور.
- تكامل (Integration): طلبات حقيقية على مسارات التصدير/الحضور/الدرجات.
- واجهة (E2E مبسّط): ظهور/اختفاء الأزرار حسب الدور.

> مرجع إضافي: `الصلاحياتRBAC.md` في جذر المستودع لشرح تفصيلي بالعربية عن سياسات الاستخدام.