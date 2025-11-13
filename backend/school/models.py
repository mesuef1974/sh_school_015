from datetime import time as _time

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models


class Class(models.Model):
    name = models.CharField(max_length=100, unique=True)
    grade = models.PositiveSmallIntegerField()
    section = models.CharField(max_length=10, blank=True)
    # School wing (جناح المدرسة)
    wing = models.ForeignKey(
        "Wing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classes",
        help_text="الجناح الذي يتبع له هذا الصف",
    )
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

    def save(self, *args, **kwargs):
        """Auto-derive grade/section from name if missing and auto-attach wing when possible.

        Tests create Class with only name like "12/1". Our DB requires grade not null,
        so before first insert, parse grade (and optionally section) from the name.
        Also, when wing is not set, infer it from grade/section according to school rules
        and attach the Wing object if found (best-effort; never block on errors).
        """
        try:
            if (getattr(self, "grade", None) is None) and isinstance(self.name, str):
                import re

                m = re.match(r"^\s*(\d+)[\-\./](.+)?\s*$", self.name)
                if m:
                    self.grade = int(m.group(1))
                    # If section not provided explicitly, try to set from name suffix
                    if not self.section:
                        sec = (m.group(2) or "").strip()
                        # Keep only the first token (e.g., "1" from "1A")
                        # but don't over-validate to avoid introducing new constraints
                        self.section = sec
        except Exception:
            # Never block saving due to parsing issues
            pass

        # Best-effort auto-attach wing if missing
        try:
            if getattr(self, "wing_id", None) in (None, 0):
                # Determine section number from explicit section or from name
                import re

                sec_num = None
                sec_raw = str(self.section or "").strip()
                m = re.match(r"^(\d+)", sec_raw)
                if m:
                    sec_num = int(m.group(1))
                else:
                    name = str(self.name or "")
                    m2 = re.search(r"^(\d+)[\-\./](\d+)", name.strip())
                    if m2:
                        if not getattr(self, "grade", None):
                            self.grade = int(m2.group(1))
                        sec_num = int(m2.group(2))
                grade_val = int(getattr(self, "grade", 0) or 0)
                wing_no = None
                if grade_val == 7 and sec_num and 1 <= sec_num <= 5:
                    wing_no = 1
                elif grade_val == 8 and sec_num and 1 <= sec_num <= 4:
                    wing_no = 2
                elif grade_val == 9 and sec_num == 1:
                    wing_no = 2
                elif grade_val == 9 and sec_num and 2 <= sec_num <= 4:
                    wing_no = 3
                elif grade_val == 10 and sec_num and 1 <= sec_num <= 2:
                    wing_no = 3
                elif grade_val == 10 and sec_num and 3 <= sec_num <= 4:
                    wing_no = 4
                elif grade_val == 11 and sec_num and 1 <= sec_num <= 3:
                    wing_no = 4
                elif grade_val == 11 and sec_num == 4:
                    wing_no = 5
                elif grade_val == 12 and sec_num and 1 <= sec_num <= 4:
                    wing_no = 5
                if wing_no:
                    from django.apps import apps as _apps

                    Wing = _apps.get_model("school", "Wing")
                    wing_obj = (
                        Wing.objects.filter(id=wing_no).first()
                        or Wing.objects.filter(name__icontains=str(wing_no)).first()
                    )
                    if wing_obj:
                        self.wing = wing_obj
        except Exception:
            # Never block saving due to wing inference problems
            pass
        super().save(*args, **kwargs)


class Student(models.Model):
    sid = models.CharField(max_length=30, unique=True)
    full_name = models.CharField(max_length=200)
    english_name = models.CharField(max_length=200, blank=True)
    national_no = models.CharField(max_length=30, unique=True, null=True, blank=True)
    needs = models.BooleanField(default=False, help_text="احتياجات خاصة")
    class_fk = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True, related_name="students")
    grade_label = models.CharField(max_length=50, blank=True, help_text="مثل 12-Science")
    section_label = models.CharField(max_length=50, blank=True, help_text="مثل 12/1")
    dob = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    phone_no = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    parent_name = models.CharField(max_length=200, blank=True)
    parent_relation = models.CharField(max_length=50, blank=True)
    parent_national_no = models.CharField(max_length=30, blank=True, help_text="الرقم الوطني لولي الأمر")
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
                years = today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))
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

    # --- RBAC sync: keep auth.groups in sync with Staff.role ---
    def _sync_role_group(self):
        """Ensure that the related user's auth Group membership reflects Staff.role.
        - Maps Staff.role -> canonical Group name used by the API (lowercase snake names).
        - Creates the Group if missing.
        - Removes user from other role-groups defined by this mapping to avoid stale roles.
        """
        if not getattr(self, "user_id", None):
            return
        try:
            from django.contrib.auth.models import Group
        except Exception:
            return
        # Canonical mapping from Staff.role -> Group name used by our RBAC checks
        ROLE_TO_GROUP = {
            "teacher": "teacher",
            "school_principal": "principal",
            "academic_vice": "academic_deputy",
            "administrative_vice": "administrative_deputy",
            "supervisor": "wing_supervisor",
            "coordinator": "subject_coordinator",
            "developer": "developer",
            "admin": "admin",
            "administrative": "staff",
            "staff": "staff",
        }
        target_group_name = ROLE_TO_GROUP.get(self.role)
        if not target_group_name:
            # Roles without RBAC mapping are ignored (no automatic groups)
            return
        # Ensure canonical group exists
        target_group, _ = Group.objects.get_or_create(name=target_group_name)
        user = self.user
        # Build set of all managed role groups; we will remove all then add the target
        managed_group_names = set(ROLE_TO_GROUP.values())
        # Also remove common titlecase variants to avoid duplicates, if present
        title_variants = {
            "Teacher",
            "Wing Supervisor",
            "Subject Coordinator",
            "Principal",
            "Academic Deputy",
            "Administrative Deputy",
            "Admin",
            "Developer",
            "Staff",
        }
        managed_group_names |= {g for g in title_variants}
        # Remove user from all managed groups except the target
        try:
            current = set(user.groups.values_list("name", flat=True))
            to_remove = [g for g in current if g in managed_group_names and g != target_group_name]
            if to_remove:
                user.groups.remove(*Group.objects.filter(name__in=to_remove))
        except Exception:
            pass
        # Finally, add the target if not already present
        if not user.groups.filter(name=target_group.name).exists():
            user.groups.add(target_group)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # After saving (to ensure we have PK and potential user relation), sync groups
        try:
            self._sync_role_group()
        except Exception:
            # Never block saving due to RBAC synchronization issues
            pass


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
            exists = ClassSubject.objects.filter(classroom_id=self.classroom_id, subject_id=self.subject_id).exists()
            if not exists:
                raise ValidationError(
                    {"subject": ("هذه المادة غير مضافة لهذا الصف. " "أضفها من صفحة المواد للصف أولاً.")}
                )

    def save(self, *args, **kwargs):
        # Enforce validation at model level
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return (
            f"{self.teacher.full_name} – {self.classroom.name} – " f"{self.subject.name_ar} ({self.no_classes_weekly})"
        )


# ============ Attendance and Academic Year structures ============


class AcademicYear(models.Model):
    name = models.CharField(max_length=20, unique=True)  # "2025-2026"
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["is_current"],
                condition=models.Q(is_current=True),
                name="one_current_year",
            )
        ]
        verbose_name = "سنة دراسية"
        verbose_name_plural = "سنوات دراسية"

    def __str__(self) -> str:
        return self.name


class Term(models.Model):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="terms")
    name = models.CharField(max_length=50)  # مثل: الفصل الأول
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False, db_index=True)

    class Meta:
        unique_together = ("academic_year", "name")
        verbose_name = "فصل دراسي"
        verbose_name_plural = "فصول دراسية"

    def __str__(self) -> str:
        return f"{self.academic_year.name} – {self.name}"


class Wing(models.Model):
    name = models.CharField(max_length=50, unique=True)
    floor = models.CharField(max_length=20, blank=True)  # أرضي/علوي
    notes = models.CharField(max_length=200, blank=True)
    supervisor = models.ForeignKey(
        "Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_wings",
        verbose_name="المشرف",
        help_text="المشرف المسؤول عن الجناح",
    )

    class Meta:
        verbose_name = "جناح"
        verbose_name_plural = "أجنحة"

    def __str__(self) -> str:
        return self.name


class PeriodTemplate(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    day_of_week = models.PositiveSmallIntegerField()  # 1=Sun .. 7=Sat
    scope = models.CharField(max_length=30, blank=True)  # ground/upper/secondary/...
    # Explicit link of this day template to one or more classes (الفصول)
    # This enables per-class custom timings overriding wing/floor/general scopes.
    classes = models.ManyToManyField(
        "Class",
        blank=True,
        related_name="period_templates",
        help_text="الفصول التي ينطبق عليها هذا القالب مباشرةً.",
    )
    # Existing: link this day template to one or more wings for backward compatibility.
    # Kept to avoid breaking existing data; class binding has higher priority at runtime.
    wings = models.ManyToManyField(
        "Wing",
        blank=True,
        related_name="period_templates",
        help_text="الأجنحة التي ينطبق عليها هذا القالب. يحدد ذلك الفصول التابعة لهذه الأجنحة.",
    )

    class Meta:
        verbose_name = "قالب يوم دراسي"
        verbose_name_plural = "قوالب الأيام الدراسية"

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class TemplateSlot(models.Model):
    template = models.ForeignKey(PeriodTemplate, on_delete=models.CASCADE, related_name="slots")
    number = models.PositiveSmallIntegerField(null=True, blank=True)  # رقم الحصة
    start_time = models.TimeField()
    end_time = models.TimeField()
    kind = models.CharField(max_length=20, default="lesson")  # lesson/recess/prayer

    class Meta:
        ordering = ["template", "start_time"]
        unique_together = (("template", "number"),)
        verbose_name = "مقطع زمني"
        verbose_name_plural = "مقاطع زمنية"

    def __str__(self) -> str:
        label = f"حصة {self.number}" if self.number else self.kind
        return f"{self.template.code} – {label} {self.start_time}-{self.end_time}"


class TimetableEntry(models.Model):
    classroom = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="timetable")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    teacher = models.ForeignKey(Staff, on_delete=models.PROTECT)
    day_of_week = models.PositiveSmallIntegerField()  # 1..5 (Sun..Thu)
    period_number = models.PositiveSmallIntegerField()
    term = models.ForeignKey(Term, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("classroom", "day_of_week", "period_number", "term")
        indexes = [
            models.Index(fields=["classroom", "day_of_week", "period_number"]),
            models.Index(fields=["teacher"]),
        ]
        verbose_name = "حصة مجدولة"
        verbose_name_plural = "حصص مجدولة"

    def __str__(self) -> str:
        return f"{self.classroom} D{self.day_of_week} P{self.period_number} – {self.subject} / {self.teacher}"


class AttendancePolicy(models.Model):
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="attendance_policies")
    late_threshold_minutes = models.PositiveSmallIntegerField(default=5)
    late_to_equivalent_period_minutes = models.PositiveSmallIntegerField(default=45)
    first_two_periods_numbers = models.JSONField(default=list)  # [1,2]
    lesson_lock_after_minutes = models.PositiveSmallIntegerField(default=120)
    daily_lock_time = models.TimeField(default=_time(14, 30))
    working_days = models.JSONField(default=list)  # [1,2,3,4,5]

    class Meta:
        verbose_name = "سياسة الحضور"
        verbose_name_plural = "سياسات الحضور"

    def __str__(self) -> str:
        return f"سياسة الحضور – {self.term}"


class AttendanceRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    classroom = models.ForeignKey(Class, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    teacher = models.ForeignKey(Staff, on_delete=models.PROTECT)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)

    date = models.DateField(db_index=True)
    day_of_week = models.PositiveSmallIntegerField()  # 1..7
    period_number = models.PositiveSmallIntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    status = models.CharField(
        max_length=20,
        choices=[
            ("present", "حاضر"),
            ("late", "متأخر"),
            ("absent", "غائب"),
            ("runaway", "هروب"),
            ("excused", "إذن خروج"),
            ("left_early", "انصراف مبكر"),
        ],
    )
    late_minutes = models.PositiveSmallIntegerField(default=0)
    early_minutes = models.PositiveSmallIntegerField(default=0)

    runaway_reason = models.CharField(max_length=30, blank=True)  # no_show | left_and_not_returned

    # Generic excuse fields (legacy)
    excuse_type = models.CharField(max_length=20, blank=True)  # medical|official|family|transport|other
    excuse_note = models.CharField(max_length=300, blank=True)

    # Unified human-readable note column (stores free notes and exit permission text)
    note = models.CharField(max_length=300, blank=True)

    # New: exit permission details (إذن خروج)
    exit_reasons = models.CharField(
        max_length=200, blank=True, default=""
    )  # comma-separated tags: admin,wing,nurse,restroom
    exit_left_at = models.DateTimeField(null=True, blank=True)
    exit_returned_at = models.DateTimeField(null=True, blank=True)

    source = models.CharField(max_length=20, default="teacher")  # teacher/office/import
    locked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            # Original indexes
            models.Index(fields=["student", "date"]),
            models.Index(fields=["classroom", "date"]),
            models.Index(fields=["teacher", "date"]),
            models.Index(fields=["status"]),
            # Enhanced composite indexes for performance
            models.Index(fields=["date", "status"], name="att_date_status_idx"),
            models.Index(fields=["term", "student", "status"], name="att_term_student_idx"),
            models.Index(
                fields=["teacher", "date", "period_number"],
                name="att_teacher_sched_idx",
            ),
            models.Index(
                fields=["classroom", "date", "period_number"],
                name="att_class_sched_idx",
            ),
            models.Index(fields=["date", "locked"], name="att_date_locked_idx"),
            models.Index(fields=["student", "term"], name="att_student_term_idx"),
        ]
        unique_together = ("student", "date", "period_number", "term")
        verbose_name = "سجل حضور حصة"
        verbose_name_plural = "سجلات حضور الحصص"

    def __str__(self) -> str:
        return f"{self.student} – {self.date} P{self.period_number}: {self.status}"


class AttendanceDaily(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField(db_index=True)
    school_class = models.ForeignKey(Class, on_delete=models.PROTECT)
    wing = models.ForeignKey(Wing, on_delete=models.SET_NULL, null=True, blank=True)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)

    present_periods = models.PositiveSmallIntegerField(default=0)
    absent_periods = models.PositiveSmallIntegerField(default=0)
    runaway_periods = models.PositiveSmallIntegerField(default=0)
    excused_periods = models.PositiveSmallIntegerField(default=0)
    late_minutes = models.PositiveIntegerField(default=0)
    early_minutes = models.PositiveIntegerField(default=0)

    daily_absent_unexcused = models.BooleanField(default=False)
    daily_excused = models.BooleanField(default=False)
    daily_excused_partial = models.BooleanField(default=False)

    locked = models.BooleanField(default=False)

    class Meta:
        unique_together = ("student", "date", "term")
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["school_class"]),
            models.Index(fields=["wing"]),
        ]
        verbose_name = "ملخص حضور يومي"
        verbose_name_plural = "ملخصات الحضور اليومية"

    def __str__(self) -> str:
        return f"{self.student} – {self.date}"


class AssessmentPackage(models.Model):
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="assessment_packages")
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=30, default="general")  # midterm/final/...
    start_date = models.DateField()
    end_date = models.DateField()
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = "باقة اختبارات"
        verbose_name_plural = "باقات الاختبارات"

    def __str__(self) -> str:
        return f"{self.term}: {self.name}"


class SchoolHoliday(models.Model):
    title = models.CharField(max_length=200)
    start = models.DateField()
    end = models.DateField()

    class Meta:
        verbose_name = "عطلة مدرسية"
        verbose_name_plural = "عطل مدرسية"

    def __str__(self) -> str:
        return f"{self.title} ({self.start}→{self.end})"


# EOF


class ExitEvent(models.Model):
    REASONS = (
        ("admin", "إدارة"),
        ("wing", "مشرف الجناح"),
        ("nurse", "الممرض"),
        ("restroom", "دورة المياه"),
    )

    REVIEW_STATUSES = (
        ("submitted", "بانتظار الاعتماد"),
        ("approved", "موافق عليه"),
        ("rejected", "مرفوض"),
    )

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="exit_events")
    classroom = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField(db_index=True)
    period_number = models.PositiveSmallIntegerField(null=True, blank=True)
    reason = models.CharField(max_length=20, choices=REASONS)
    note = models.CharField(max_length=300, blank=True)

    # موافقة المشرف على إذن الخروج
    review_status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUSES,
        null=True,
        blank=True,
        db_index=True,
        help_text="حالة اعتماد إذن الخروج من قبل مشرف الجناح",
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exit_events_reviewed",
        help_text="المستخدم الذي اعتمد أو رفض إذن الخروج",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_comment = models.CharField(max_length=300, blank=True, default="")

    started_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    started_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exits_started",
    )
    returned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exits_returned",
    )

    attendance_record = models.ForeignKey(AttendanceRecord, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["student", "date"]),
            models.Index(fields=["reason"]),
            models.Index(fields=["started_at"]),
            models.Index(fields=["review_status", "date"]),
        ]
        ordering = ["-started_at"]
        verbose_name = "جلسة خروج"
        verbose_name_plural = "جلسات خروج"

    def __str__(self) -> str:
        return f"{self.student} – {self.date} P{self.period_number or '-'}"

    def close(self, user=None):
        from django.utils import timezone

        if self.returned_at:
            return
        self.returned_at = timezone.now()
        self.duration_seconds = int((self.returned_at - self.started_at).total_seconds())
        if user:
            self.returned_by = user
        self.save(update_fields=["returned_at", "duration_seconds", "returned_by"])


class AttendanceLateEvent(models.Model):
    """حدث تأخر لحصة: يسجّل مدة التأخر mm:ss مع كامل سياق الحصة والطالب والمعلم الذي أدخل السجل."""

    attendance_record = models.ForeignKey("AttendanceRecord", on_delete=models.CASCADE, related_name="late_events")
    student = models.ForeignKey("Student", on_delete=models.CASCADE)
    classroom = models.ForeignKey("Class", on_delete=models.CASCADE)
    subject = models.ForeignKey("Subject", on_delete=models.PROTECT)
    teacher = models.ForeignKey("Staff", on_delete=models.PROTECT)
    recorded_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    date = models.DateField(db_index=True)
    day_of_week = models.PositiveSmallIntegerField()  # 1..7
    period_number = models.PositiveSmallIntegerField()

    start_time = models.TimeField()
    marked_at = models.DateTimeField(auto_now_add=True)

    late_seconds = models.PositiveIntegerField()
    late_mmss = models.CharField(max_length=8)  # mm:ss

    note = models.CharField(max_length=300, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["date", "period_number"]),
            models.Index(fields=["student", "date"]),
            models.Index(fields=["classroom", "date"]),
            models.Index(fields=["teacher", "date"]),
        ]
        verbose_name = "حدث تأخر"
        verbose_name_plural = "أحداث التأخر"

    def __str__(self) -> str:
        return f"{self.student} – {self.date} P{self.period_number} تأخر {self.late_mmss}"


class StudentLateSummary(Student):
    class Meta:
        proxy = True
        verbose_name = "ملخص تأخيرات الطالب"
        verbose_name_plural = "ملخصات تأخيرات الطلاب"


# --- Admin helper proxy to expose timetable links in Django Admin ---
class TimetableLinks(Class):
    """Proxy model فقط لإظهار عنصر قائمة في لوحة الأدمن يفتح صفحة روابط الجداول.

    لا ينشئ أي جداول جديدة (proxy=True)."""

    class Meta:
        proxy = True
        verbose_name = "روابط الجداول"
        verbose_name_plural = "روابط الجداول"


# روابط عامة للمنصة (خارج لوحة الأدمن)
class SiteLinks(Class):
    """Proxy model لعرض روابط الصفحات التشغيلية العامة في الأدمن.

    لا ينشئ جداول جديدة. الهدف توفير بوابة سريعة لفتح صفحات الواجهة (Portal/Vue).
    """

    class Meta:
        proxy = True
        verbose_name = "روابط المنصة"
        verbose_name_plural = "روابط المنصة"


# --- Approvals workflow (dual-control) ---
class ApprovalRequest(models.Model):
    """طلب موافقة لإجراء عالي الأثر/غير قابل للعكس.

    الهدف: توفير طبقة حوكمة بسيطة لإسناد الموافقات المزدوجة على إجراءات حساسة
    مثل: إلغاء نتيجة اختبار بسبب غش، حظر دائم، حذف صلب لسجل.
    """

    STATUS_CHOICES = (
        ("pending", "قيد الانتظار"),
        ("approved", "مقبول"),
        ("rejected", "مرفوض"),
        ("executed", "تم التنفيذ"),
    )

    # توصيف عام للهدف
    resource_type = models.CharField(max_length=50, db_index=True)
    resource_id = models.CharField(max_length=64, db_index=True)
    action = models.CharField(max_length=50, help_text="نوع الإجراء المطلوب")
    irreversible = models.BooleanField(default=False)
    impact = models.CharField(max_length=20, blank=True, default="", help_text="low|medium|high|critical")

    # بيانات الحالة والموافقات
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    justification = models.CharField(max_length=500, blank=True, default="")
    payload = models.JSONField(blank=True, null=True, help_text="بيانات إضافية لازمة للتنفيذ")

    proposed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="approvals_proposed")
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="approvals_approved"
    )
    executed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="approvals_executed"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["resource_type", "resource_id"]),
            models.Index(fields=["status", "created_at"]),
        ]
        verbose_name = "طلب موافقة"
        verbose_name_plural = "طلبات الموافقة"

    def __str__(self) -> str:
        return f"[{self.status}] {self.resource_type}:{self.resource_id} -> {self.action}"
