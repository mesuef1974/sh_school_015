from django.db import models

# NOTE: Existing project likely already has attendance-related tables.
# For now we create minimal proxy-like models or placeholders only if needed.
# Prefer using existing models from `school.models` to avoid migrations now.


class AttendanceStatus(models.TextChoices):
    PRESENT = "present", "Present"
    ABSENT = "absent", "Absent"
    LATE = "late", "Late"
    EXCUSED = "excused", "Excused"
