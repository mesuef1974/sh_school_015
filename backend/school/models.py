from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Q, F


class Class(models.Model):
    name = models.CharField(max_length=100, unique=True)
    grade = models.PositiveSmallIntegerField()
    section = models.CharField(max_length=10, blank=True)
    # Denormalized count of students in this class/section for fast access
    students_count = models.PositiveIntegerField(default=0, db_index=True)
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Subjects offered for this class (managed via ClassSubject through model)
    subjects = models.ManyToManyField(
        "Subject",
        through="ClassSubject",
        related_name="classes",
        blank=True,
    )

    def __str__(self) -> str:
        return f"{self.name}"


class Student(models.Model):
    sid = models.CharField(max_length=30, unique=True)
    full_name = models.CharField(max_length=200)
    english_name = models.CharField(max_length=200, blank=True)
    national_no = models.CharField(max_length=30, unique=True, null=True, blank=True)
    needs = models.BooleanField(default=False, help_text="احتياجات خاصة")
    class_fk = models.ForeignKey(
        Class, on_delete=models.SET_NULL, null=True, related_name="students"
    )
    grade_label = models.CharField(max_length=50, blank=True, help_text="مثل 12-Science")
    section_label = models.CharField(max_length=50, blank=True, help_text="مثل 12/1")
    dob = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    phone_no = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    parent_name = models.CharField(max_length=200, blank=True)
    parent_relation = models.CharField(max_length=50, blank=True)
    parent_national_no = models.CharField(
        max_length=30, blank=True, help_text="الرقم الوطني لولي الأمر"
    )
    parent_phone = models.CharField(max_length=200, blank=True)
    extra_phone_no = models.CharField(max_length=200, blank=True)
    parent_email = models.EmailField(blank=True)
    active = models.BooleanField(default=True)
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["national_no"], name="student_natno_idx"),
            models.Index(fields=["class_fk"], name="student_class_idx"),
            models.Index(fields=["active"], name="student_active_idx"),
            models.Index(fields=["needs"], name="student_needs_idx"),
            models.Index(fields=["nationality"], name="student_nationality_idx"),
            models.Index(fields=["grade_label"], name="student_grade_label_idx"),
            models.Index(fields=["section_label"], name="student_section_label_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.sid} - {self.full_name}"

    def save(self, *args, **kwargs):
        # Auto-compute age from dob if available
        try:
            from datetime import date as _date

            if self.dob:
                today = _date.today()
                years = (
                    today.year
                    - self.dob.year
                    - ((today.month, today.day) < (self.dob.month, self.dob.day))
                )
                if years < 0:
                    years = 0
                self.age = years
        except Exception:
            # Never block saving due to age computation
            pass
        super().save(*args, **kwargs)


class Staff(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=200)
    role = models.CharField(
        max_length=50,
        choices=[
            ("admin", "أدمن"),
            ("teacher", "معلم"),
            ("school_principal", "مدير المدرسة"),
            ("academic_vice", "النائب الاكاديمي"),
            ("administrative_vice", "النائب الاداري"),
            ("supervisor", "مشرف اداري"),
            ("coordinator", "منسق"),
            ("developer", "مطور"),
            ("administrative", "إداري"),
            ("staff", "موظف"),
            # Extended roles (from job titles list)
            ("psychologist", "اخصائي نفسي"),
            ("store_keeper", "امين مخزن"),
            ("social_specialist", "أخصائي اجتماعي"),
            ("activities_specialist", "أخصائي أنشطة مدرسية"),
            ("school_secretary", "سكرتير مدرسة"),
            ("services_worker", "عامل خدمات"),
            ("it_technician", "فني تقنية معلومات"),
            ("accountant", "محاسب"),
            ("lab_biology_prep", "محضر مختبر أحياء"),
            ("lab_physics_prep", "محضر مختبر فيزياء"),
            ("science_teacher", "مدرس علوم"),
            ("support_assistant", "مرافق الدعم"),
            ("academic_advisor", "مرشد أكاديمي"),
            ("assistant_secretary", "مساعد سكرتير مدرسة"),
            ("learning_resources_officer", "مسؤول مصادر التعلم"),
            ("cafeteria_supervisor", "مشرف مقصف"),
            ("student_observer", "ملاحظ طلبه"),
            ("representative", "مندوب"),
            ("receptionist", "موظف استقبال"),
        ],
    )
    national_no = models.CharField(max_length=30, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    job_no = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    phone_no = models.CharField(max_length=30, blank=True)
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["role"], name="staff_role_idx"),
            models.Index(fields=["user"], name="staff_user_idx"),
            models.Index(fields=["email"], name="staff_email_idx"),
            models.Index(fields=["phone_no"], name="staff_phone_idx"),
            models.Index(fields=["national_no"], name="staff_natno_idx"),
            models.Index(fields=["job_no"], name="staff_jobno_idx"),
        ]

    def __str__(self) -> str:
        return self.full_name


class Subject(models.Model):
    name_ar = models.CharField("اسم المادة", max_length=150, unique=True)
    code = models.CharField(max_length=20, blank=True, null=True, unique=True)
    weekly_default = models.PositiveSmallIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name_ar"]
        indexes = [
            models.Index(fields=["is_active"], name="subject_active_idx"),
        ]

    def __str__(self) -> str:
        return self.name_ar


class ClassSubject(models.Model):
    classroom = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="class_subjects")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="class_subjects")
    weekly_default = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="العدد الافتراضي للحصص أسبوعياً لهذه المادة في هذا الصف",
    )

    class Meta:
        unique_together = ("classroom", "subject")
        verbose_name = "مادة الصف"
        verbose_name_plural = "مواد الصفوف"
        indexes = [
            models.Index(fields=["classroom"]),
            models.Index(fields=["subject"]),
        ]

    def __str__(self) -> str:
        return f"{self.classroom.name} – {self.subject.name_ar}"


class TeachingAssignment(models.Model):
    teacher = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="assignments")
    classroom = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="assignments")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="assignments")
    no_classes_weekly = models.PositiveSmallIntegerField("عدد الحصص أسبوعياً")
    notes = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("teacher", "classroom", "subject")
        indexes = [
            models.Index(fields=["teacher"]),
            models.Index(fields=["classroom"]),
            models.Index(fields=["subject"]),
        ]
        verbose_name = "تكليف تدريس"
        verbose_name_plural = "تكليفات التدريس"

    def clean(self):
        super().clean()
        # Ensure the selected subject is available for the selected classroom
        if self.classroom_id and self.subject_id:
            exists = ClassSubject.objects.filter(
                classroom_id=self.classroom_id, subject_id=self.subject_id
            ).exists()
            if not exists:
                raise ValidationError(
                    {
                        "subject": (
                            "هذه المادة غير مضافة لهذا الصف. " "أضفها من صفحة المواد للصف أولاً."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        # Enforce validation at model level
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return (
            f"{self.teacher.full_name} – {self.classroom.name} – "
            f"{self.subject.name_ar} ({self.no_classes_weekly})"
        )


class CalendarTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True)
    scope = models.CharField(
        max_length=50,
        blank=True,
        help_text="Upper, Ground, Secondary, Grade9(2-4)",
    )
    days = models.CharField(
        max_length=50,
        blank=True,
        help_text="Comma-separated days (e.g., Sun,Mon,...) or 'ALL'",
    )

    class Meta:
        verbose_name = "قالب اليوم الدراسي"
        verbose_name_plural = "قوالب اليوم الدراسي"
        indexes = [models.Index(fields=["name"], name="caltmpl_name_idx")]

    def __str__(self) -> str:
        return self.name


class CalendarSlot(models.Model):
    class Block(models.TextChoices):
        CLASS = "class", "Class"
        BREAK = "break", "Break"
        PRAYER = "prayer", "Prayer"
        OTHER = "other", "Other"

    template = models.ForeignKey(CalendarTemplate, on_delete=models.CASCADE, related_name="slots")
    day = models.CharField(max_length=10, help_text="Sun, Mon, Tue, Wed, Thu, ALL")
    period_index = models.CharField(
        max_length=16, help_text="1..n or a label like BREAK/PRAYER/OTHER"
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    block = models.CharField(
        max_length=10,
        choices=Block.choices,
        default=Block.CLASS,
        help_text="نوع الكتلة",
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "فترة زمنية"
        verbose_name_plural = "فترات زمنية"
        ordering = ["template", "day", "order", "start_time"]
        indexes = [
            models.Index(fields=["template"], name="calslot_template_idx"),
            models.Index(fields=["day"], name="calslot_day_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(end_time__gt=F("start_time")), name="calslot_time_order"
            ),
        ]
        unique_together = ("template", "day", "period_index")

    def __str__(self) -> str:
        return (
            f"{self.template.name} - {self.day} - {self.period_index} "
            f"({self.start_time}-{self.end_time})"
        )


class TimetableEntry(models.Model):
    classroom = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="timetable_entries")
    day = models.CharField(max_length=10, help_text="Sun, Mon, Tue, Wed, Thu")
    slot = models.ForeignKey(
        CalendarSlot, on_delete=models.PROTECT, related_name="timetable_entries"
    )
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    teacher = models.ForeignKey(Staff, on_delete=models.PROTECT)

    class Meta:
        verbose_name = "حصة مجدولة"
        verbose_name_plural = "حصص مجدولة"
        unique_together = ("classroom", "day", "slot")
        indexes = [
            models.Index(fields=["classroom", "day"], name="tt_class_day_idx"),
            models.Index(fields=["slot"], name="tt_slot_idx"),
            models.Index(fields=["teacher"], name="tt_teacher_idx"),
        ]

    def __str__(self) -> str:
        return (
            f"{self.classroom.name} - {self.day} - {self.slot.period_index} - "
            f"{self.subject.name_ar} - {self.teacher.full_name}"
        )


# EOF
