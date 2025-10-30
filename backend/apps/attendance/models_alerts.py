from __future__ import annotations
from django.conf import settings
from django.db import models, transaction


class AlertNumberSequence(models.Model):
    academic_year = models.CharField(max_length=20, unique=True)
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "تسلسل تنبيهات الغياب"
        verbose_name_plural = "تسلسلات تنبيهات الغياب"

    @classmethod
    def next_number(cls, year_name: str) -> int:
        with transaction.atomic():
            seq, _ = cls.objects.select_for_update().get_or_create(
                academic_year=year_name, defaults={"last_number": 0}
            )
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