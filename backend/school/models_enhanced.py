"""
Enhanced models with improved performance, validation, and features
This file contains the enhanced versions of core models
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from datetime import date as _date
import re

from .models_base import BaseModel


# ============ Enhanced Core Models ============


class ClassEnhanced(BaseModel):
    """Enhanced Class model with improved features"""

    name = models.CharField(max_length=100, unique=True, verbose_name="اسم الصف")
    grade = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        db_index=True,
        verbose_name="المرحلة",
    )
    section = models.CharField(max_length=10, blank=True, verbose_name="الشعبة")

    # Wing relationship
    wing = models.ForeignKey(
        "Wing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enhanced_classes",
        verbose_name="الجناح",
    )

    # Enhanced fields
    capacity = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="السعة القصوى للصف",
        verbose_name="السعة",
    )
    academic_level = models.CharField(
        max_length=20,
        choices=[
            ("elementary", "ابتدائي"),
            ("middle", "متوسط"),
            ("high", "ثانوي"),
        ],
        blank=True,
        db_index=True,
        verbose_name="المستوى الأكاديمي",
    )
    is_active = models.BooleanField(default=True, db_index=True, verbose_name="نشط")
    students_count = models.PositiveIntegerField(
        default=0, db_index=True, verbose_name="عدد الطلاب"
    )

    # Academic year
    academic_year = models.ForeignKey(
        "AcademicYear",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="السنة الدراسية",
    )

    # Subjects (Many-to-Many through ClassSubject)
    subjects = models.ManyToManyField(
        "Subject", through="ClassSubject", related_name="enhanced_classes", blank=True
    )

    class Meta:
        verbose_name = "صف (محسّن)"
        verbose_name_plural = "صفوف (محسّنة)"
        indexes = [
            models.Index(fields=["grade", "section"]),
            models.Index(fields=["wing", "is_active"]),
            models.Index(fields=["academic_level", "grade"]),
            models.Index(fields=["is_active", "grade"]),
        ]
        ordering = ["grade", "section"]

    def __str__(self):
        return self.name

    def clean(self):
        """Validation"""
        super().clean()
        # Validate capacity
        if self.capacity and self.students_count > self.capacity:
            raise ValidationError(
                f"عدد الطلاب ({self.students_count}) يتجاوز السعة القصوى ({self.capacity})"
            )


class StudentEnhanced(BaseModel):
    """Enhanced Student model with additional fields"""

    sid = models.CharField(max_length=30, unique=True, db_index=True, verbose_name="رقم الطالب")
    full_name = models.CharField(max_length=200, db_index=True, verbose_name="الاسم الكامل")
    english_name = models.CharField(max_length=200, blank=True, verbose_name="الاسم بالإنجليزية")

    national_no = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="رقم الهوية",
    )

    # Class relationship
    class_fk = models.ForeignKey(
        "Class",
        on_delete=models.SET_NULL,
        null=True,
        related_name="enhanced_students",
        verbose_name="الصف",
    )

    # Personal info
    needs = models.BooleanField(default=False, db_index=True, verbose_name="احتياجات خاصة")
    dob = models.DateField(null=True, blank=True, verbose_name="تاريخ الميلاد")
    age = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="العمر")
    nationality = models.CharField(
        max_length=100, blank=True, db_index=True, verbose_name="الجنسية"
    )
    gender = models.CharField(
        max_length=10,
        choices=[("male", "ذكر"), ("female", "أنثى")],
        blank=True,
        db_index=True,
        verbose_name="الجنس",
    )

    # Enhanced medical info
    blood_type = models.CharField(
        max_length=5,
        choices=[
            ("A+", "A+"),
            ("A-", "A-"),
            ("B+", "B+"),
            ("B-", "B-"),
            ("AB+", "AB+"),
            ("AB-", "AB-"),
            ("O+", "O+"),
            ("O-", "O-"),
        ],
        blank=True,
        verbose_name="فصيلة الدم",
    )
    medical_notes = models.TextField(blank=True, verbose_name="ملاحظات طبية")
    allergies = models.TextField(blank=True, verbose_name="الحساسية")

    # Contact info
    phone_validator = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="رقم الهاتف يجب أن يكون بصيغة: '+999999999'. يسمح بـ 9-15 رقم.",
    )
    phone_no = models.CharField(
        max_length=20,
        blank=True,
        validators=[phone_validator],
        verbose_name="رقم الهاتف",
    )
    extra_phone_no = models.CharField(max_length=20, blank=True, verbose_name="رقم هاتف إضافي")
    email = models.EmailField(blank=True, verbose_name="البريد الإلكتروني")

    # Parent/Guardian info
    parent_name = models.CharField(max_length=200, blank=True, verbose_name="اسم ولي الأمر")
    parent_relation = models.CharField(max_length=50, blank=True, verbose_name="صلة القرابة")
    parent_national_no = models.CharField(
        max_length=30, blank=True, verbose_name="رقم هوية ولي الأمر"
    )
    parent_phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[phone_validator],
        verbose_name="هاتف ولي الأمر",
    )
    parent_email = models.EmailField(blank=True, verbose_name="بريد ولي الأمر")
    emergency_contact = models.CharField(max_length=200, blank=True, verbose_name="جهة اتصال طارئة")

    # Academic info
    grade_label = models.CharField(max_length=50, blank=True, verbose_name="تسمية المرحلة")
    section_label = models.CharField(max_length=50, blank=True, verbose_name="تسمية الشعبة")
    enrollment_date = models.DateField(null=True, blank=True, verbose_name="تاريخ الالتحاق")
    withdrawal_date = models.DateField(null=True, blank=True, verbose_name="تاريخ الانسحاب")

    # Status
    active = models.BooleanField(default=True, db_index=True, verbose_name="نشط")
    photo = models.ImageField(
        upload_to="students/photos/", null=True, blank=True, verbose_name="الصورة"
    )

    class Meta:
        verbose_name = "طالب (محسّن)"
        verbose_name_plural = "طلاب (محسّن)"
        indexes = [
            models.Index(fields=["national_no"]),
            models.Index(fields=["class_fk", "active"]),
            models.Index(fields=["active", "grade_label"]),
            models.Index(fields=["needs", "active"]),
            models.Index(fields=["nationality", "active"]),
            models.Index(fields=["enrollment_date"]),
            models.Index(fields=["full_name"]),  # للبحث
        ]

    def __str__(self):
        return f"{self.sid} - {self.full_name}"

    def clean(self):
        """Enhanced validation"""
        super().clean()

        # Validate national_no format (10 digits)
        if self.national_no:
            clean_national = re.sub(r"\D", "", self.national_no)
            if len(clean_national) != 10:
                raise ValidationError({"national_no": "رقم الهوية يجب أن يكون 10 أرقام"})

        # Validate age range
        if self.age and (self.age < 5 or self.age > 25):
            raise ValidationError({"age": "العمر يجب أن يكون بين 5 و 25 سنة"})

        # Validate enrollment vs withdrawal
        if self.enrollment_date and self.withdrawal_date:
            if self.withdrawal_date < self.enrollment_date:
                raise ValidationError("تاريخ الانسحاب لا يمكن أن يكون قبل تاريخ الالتحاق")

    def save(self, *args, **kwargs):
        """Auto-calculate age and other fields"""
        # Calculate age from DOB
        if self.dob:
            today = _date.today()
            years = (
                today.year
                - self.dob.year
                - ((today.month, today.day) < (self.dob.month, self.dob.day))
            )
            self.age = max(0, years)

        # Auto-deactivate if withdrawn
        if self.withdrawal_date and self.withdrawal_date <= _date.today():
            self.active = False

        super().save(*args, **kwargs)


class AttendanceRecordArchive(models.Model):
    """
    Archive table for old attendance records (older than 1 year)
    Keeps the main table small and fast
    """

    # Same fields as AttendanceRecord but without foreign key constraints
    student_id = models.PositiveIntegerField(db_index=True)
    student_name = models.CharField(max_length=200)
    classroom_id = models.PositiveIntegerField(db_index=True)
    classroom_name = models.CharField(max_length=100)
    subject_id = models.PositiveIntegerField()
    subject_name = models.CharField(max_length=150)
    teacher_id = models.PositiveIntegerField()
    teacher_name = models.CharField(max_length=200)
    term_id = models.PositiveIntegerField()

    date = models.DateField(db_index=True)
    day_of_week = models.PositiveSmallIntegerField()
    period_number = models.PositiveSmallIntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    status = models.CharField(max_length=20, db_index=True)
    late_minutes = models.PositiveSmallIntegerField(default=0)
    early_minutes = models.PositiveSmallIntegerField(default=0)
    note = models.CharField(max_length=300, blank=True)

    # Archive metadata
    archived_at = models.DateTimeField(auto_now_add=True, db_index=True)
    original_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "سجل حضور (أرشيف)"
        verbose_name_plural = "سجلات حضور (أرشيف)"
        indexes = [
            models.Index(fields=["student_id", "date"]),
            models.Index(fields=["classroom_id", "date"]),
            models.Index(fields=["date", "status"]),
            models.Index(fields=["archived_at"]),
        ]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.student_name} - {self.date}"


class ExitEventAlert(models.Model):
    """
    Alerts for overdue or missing exit events
    """

    exit_event = models.ForeignKey(
        "ExitEvent",
        on_delete=models.CASCADE,
        related_name="alerts",
        verbose_name="جلسة الخروج",
    )
    alert_type = models.CharField(
        max_length=20,
        choices=[
            ("overdue", "تأخر في العودة"),
            ("missing", "لم يعد"),
            ("extended", "مدة طويلة"),
        ],
        db_index=True,
        verbose_name="نوع التنبيه",
    )
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="وقت الإرسال")
    sent_to = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="exit_alerts",
        verbose_name="المرسل إليه",
    )
    message = models.TextField(verbose_name="الرسالة")
    resolved = models.BooleanField(default=False, db_index=True, verbose_name="تم الحل")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="وقت الحل")

    class Meta:
        verbose_name = "تنبيه خروج"
        verbose_name_plural = "تنبيهات الخروج"
        indexes = [
            models.Index(fields=["exit_event", "resolved"]),
            models.Index(fields=["sent_to", "resolved"]),
            models.Index(fields=["alert_type", "sent_at"]),
        ]
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.exit_event}"
