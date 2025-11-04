from __future__ import annotations
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class AlertNumberSequence(models.Model):
    academic_year = models.CharField(max_length=20, unique=True)
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "تسلسل تنبيهات الغياب"
        verbose_name_plural = "تسلسلات تنبيهات الغياب"

    @classmethod
    def next_number(cls, year_name: str) -> int:
        with transaction.atomic():
            seq, _ = cls.objects.select_for_update().get_or_create(academic_year=year_name, defaults={"last_number": 0})
            seq.last_number += 1
            seq.save(update_fields=["last_number"])
            return seq.last_number


class AbsenceAlert(models.Model):
    number = models.PositiveIntegerField()
    academic_year = models.CharField(max_length=20)

    student = models.ForeignKey("school.Student", on_delete=models.PROTECT)
    class_name = models.CharField(max_length=50)
    parent_name = models.CharField(max_length=100, blank=True)
    parent_mobile = models.CharField(max_length=30, blank=True)

    period_start = models.DateField()
    period_end = models.DateField()
    excused_days = models.PositiveIntegerField(default=0)
    unexcused_days = models.PositiveIntegerField(default=0)

    notes = models.CharField(max_length=300, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("draft", "Draft"),
            ("issued", "Issued"),
            ("notified", "Notified"),
            ("signed_student", "Signed Student"),
            ("signed_parent", "Signed Parent"),
            ("archived", "Archived"),
        ],
        default="draft",
    )

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    wing = models.ForeignKey("school.Wing", on_delete=models.PROTECT, null=True, blank=True)

    delivered_via = models.CharField(max_length=20, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    signature_student = models.ImageField(upload_to="signatures/alerts/", null=True, blank=True)
    signature_parent = models.ImageField(upload_to="signatures/alerts/", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("academic_year", "number")
        indexes = [
            models.Index(fields=["academic_year", "number"]),
            models.Index(fields=["student"]),
            models.Index(fields=["wing"]),
        ]
        verbose_name = "تنبيه غياب"
        verbose_name_plural = "تنبيهات غياب"

    def __str__(self) -> str:
        return f"AbsenceAlert {self.academic_year}/{self.number} – {self.student}"


def _docx_upload_to(instance: "AbsenceAlertDocument", filename: str) -> str:
    # media path: alerts/docx/<year>/<number>-<yyyymmdd_HHMMSS>.docx
    ts = timezone.now().strftime("%Y%m%d_%H%M%S")
    return f"alerts/docx/{instance.alert.academic_year}/{instance.alert.number}-{ts}.docx"


class AbsenceAlertDocument(models.Model):
    alert = models.ForeignKey(AbsenceAlert, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to=_docx_upload_to)
    size = models.PositiveIntegerField(default=0)
    mime = models.CharField(
        max_length=100,
        default="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    sha256 = models.CharField(max_length=64, blank=True)
    template_name = models.CharField(max_length=200, blank=True)
    template_hash = models.CharField(max_length=64, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["alert", "created_at"]),
        ]
        verbose_name = "ملف تنبيه غياب (DOCX)"
        verbose_name_plural = "ملفات تنبيهات الغياب (DOCX)"
