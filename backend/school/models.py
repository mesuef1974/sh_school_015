from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Class(models.Model):
    name = models.CharField(max_length=100, unique=True)
    grade = models.PositiveSmallIntegerField()
    section = models.CharField(max_length=10, blank=True)
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
    class_fk = models.ForeignKey(
        Class, on_delete=models.SET_NULL, null=True, related_name="students"
    )
    dob = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.sid} - {self.full_name}"


class Staff(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=200)
    role = models.CharField(
        max_length=50,
        choices=[
            ("teacher", "Teacher"),
            ("admin", "Admin"),
            ("staff", "Staff"),
        ],
    )
    national_no = models.CharField(max_length=30, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    job_no = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    phone_no = models.CharField(max_length=30, blank=True)

    def __str__(self) -> str:
        return self.full_name


class Subject(models.Model):
    name_ar = models.CharField("اسم المادة", max_length=150, unique=True)
    code = models.CharField(max_length=20, blank=True, null=True, unique=True)
    weekly_default = models.PositiveSmallIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name_ar"]

    def __str__(self) -> str:
        return self.name_ar


class ClassSubject(models.Model):
    classroom = models.ForeignKey(
        Class, on_delete=models.CASCADE, related_name="class_subjects"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="class_subjects"
    )
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
    teacher = models.ForeignKey(
        Staff, on_delete=models.CASCADE, related_name="assignments"
    )
    classroom = models.ForeignKey(
        Class, on_delete=models.CASCADE, related_name="assignments"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name="assignments"
    )
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
                            "هذه المادة غير مضافة لهذا الصف. "
                            "أضفها من صفحة المواد للصف أولاً."
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
