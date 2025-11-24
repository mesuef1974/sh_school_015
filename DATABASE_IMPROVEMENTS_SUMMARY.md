# ملخص تحسينات قاعدة البيانات المقترحة

بناءً على تحليل نماذج Django، إليك ملخص لأهم فرص التحسين والتجويد في قاعدة بيانات منصة المدرسة.

## 1. أرشفة البيانات التاريخية (Data Archiving)

**المشكلة:** جدول `school_attendancerecord` سينمو بشكل كبير جداً مع مرور الوقت، مما سيؤدي إلى بطء في أداء الاستعلامات وعمليات الكتابة.

**الحل المقترح:**
- إنشاء نموذج جديد `AttendanceRecordArchive` يكون نسخة طبق الأصل من `AttendanceRecord`.
- تطوير سكربت إداري (Management Command) يتم تشغيله دورياً (مثلاً، في نهاية العام الدراسي) لنقل السجلات التي يزيد عمرها عن سنة من `AttendanceRecord` إلى `AttendanceRecordArchive`.

**مثال على نموذج الأرشفة:**
```python
class AttendanceRecordArchive(models.Model):
    # نفس حقول AttendanceRecord ولكن بدون قيود المفاتيح الخارجية
    # لتجنب المشاكل عند حذف السجلات الأصلية.
    student_id = models.BigIntegerField()
    classroom_id = models.BigIntegerField()
    subject_id = models.BigIntegerField()
    teacher_id = models.BigIntegerField()
    term_id = models.BigIntegerField()
    date = models.DateField(db_index=True)
    period_number = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=20)
    # ... باقي الحقول
```

## 2. تحسين الفهارس (Index Optimization)

**المشكلة:** على الرغم من وجود فهارس، قد لا تكون كافية لتغطية كل الاستعلامات المعقدة، خاصة في `AttendanceRecord`.

**الحل المقترح:**
- تحليل الاستعلامات البطيئة (يمكن استخدام `django-debug-toolbar` أو أدوات مراقبة قاعدة البيانات).
- إضافة فهارس مركبة (Composite Indexes) بناءً على الأعمدة التي يتم استخدامها معاً بشكل متكرر في `WHERE` و `JOIN`.

**مثال على فهارس مركبة إضافية في `AttendanceRecord`:**
```python
class Meta:
    indexes = [
        # ... الفهارس الحالية
        models.Index(fields=['term', 'student', 'status'], name='att_term_student_status_idx'),
        models.Index(fields=['classroom', 'date', 'status'], name='att_class_date_status_idx'),
    ]
```

## 3. توحيد البيانات باستخدام `TextChoices`

**المشكلة:** حقول مثل `excuse_type` و `runaway_reason` في `AttendanceRecord` هي حقول نصية حرة، مما يسمح بإدخال بيانات غير متناسقة.

**الحل المقترح:**
- استخدام `models.TextChoices` لتعريف قائمة بالقيم المسموح بها لهذه الحقول.

**مثال:**
```python
class AttendanceRecord(models.Model):
    class ExcuseTypes(models.TextChoices):
        MEDICAL = 'medical', 'عذر طبي'
        FAMILY = 'family', 'ظرف عائلي'
        OFFICIAL = 'official', 'مهمة رسمية'
        OTHER = 'other', 'أخرى'

    excuse_type = models.CharField(
        max_length=20,
        choices=ExcuseTypes.choices,
        blank=True
    )
    # ...
```

## 4. إلغاء التطبيع المحسوب (Strategic Denormalization)

**المشكلة:** بعض التقارير قد تتطلب حسابات معقدة بشكل متكرر (مثل إجمالي عدد أيام الغياب للطالب).

**الحل المقترح:**
- إضافة حقول تلخيصية إلى النماذج الرئيسية وتحديثها باستخدام `signals` أو مهام دورية.
- جدول `AttendanceDaily` هو مثال ممتاز على هذا المبدأ. يمكن التوسع فيه ليشمل ملخصات أخرى.

**مثال:**
- يمكن إضافة حقل `absent_days_count` إلى نموذج `Student` وتحديثه يومياً عبر مهمة ليلية (Celery task) تقوم بحساب الغياب من `AttendanceDaily`.
- **تنبيه:** يجب استخدام هذا الأسلوب بحذر لأنه يزيد من تعقيد منطق الكتابة ولكنه يحسن أداء القراءة بشكل كبير.
