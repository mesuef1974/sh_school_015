from django.db import models
from django.conf import settings

# NOTE: Existing project likely already has attendance-related tables.
# For now we create minimal proxy-like models or placeholders only if needed.
# Prefer using existing models from `school.models` to avoid migrations now.


class AttendanceStatus(models.TextChoices):
    PRESENT = "present", "Present"
    ABSENT = "absent", "Absent"
    LATE = "late", "Late"
    EXCUSED = "excused", "Excused"


class AttendanceEvidence(models.Model):
    record = models.ForeignKey(
        "school.AttendanceRecord", on_delete=models.CASCADE, related_name="evidence"
    )
    file = models.FileField(upload_to="attendance/evidence/%Y/%m/", verbose_name="ملف الإثبات")
    content_type = models.CharField(max_length=100, blank=True, default="")
    original_name = models.CharField(max_length=255, blank=True, default="")
    note = models.CharField(max_length=300, blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_evidence_uploaded",
    )

    class Meta:
        verbose_name = "مستند إثبات حضور"
        verbose_name_plural = "مستندات إثبات الحضور"
        indexes = [models.Index(fields=["record", "uploaded_at"], name="evidence_rec_upl_idx")]