from __future__ import annotations
from datetime import date as _date
from typing import Iterable, List, Dict, Any

from django.db import transaction
from django.utils import timezone

from school.models import AttendanceRecord  # type: ignore
from ..models import AttendanceStatus


def _class_fk_id_field() -> str:
    try:
        AttendanceRecord._meta.get_field("classroom")  # type: ignore[attr-defined]
        return "classroom_id"
    except Exception:
        pass
    try:
        AttendanceRecord._meta.get_field("class")  # type: ignore[attr-defined]
        return "class_id"
    except Exception:
        pass
    return "classroom_id"


@transaction.atomic
def bulk_save_attendance(
    *, class_id: int, dt: _date, records: Iterable[Dict[str, Any]], actor_user_id: int | None = None
) -> List[AttendanceRecord]:
    """
    Upsert-like bulk save for attendance for the given class/date.
    Each record dict should contain: {student_id: int, status: str, note?: str}
    """
    saved: list[AttendanceRecord] = []
    fk = _class_fk_id_field()
    # gather model fields to guard optional ones
    model_fields = {f.name for f in AttendanceRecord._meta.get_fields()}

    for payload in records:
        student_id = int(payload["student_id"])  # DB pk
        status = payload.get("status") or AttendanceStatus.PRESENT
        note = payload.get("note")

        lookup = {fk: class_id, "date": dt, "student_id": student_id}
        defaults: Dict[str, Any] = {"status": status}
        # Set mandatory/important metadata if model exposes these fields
        if "day_of_week" in model_fields:
            try:
                # Django/Python: Monday=1 .. Sunday=7
                defaults["day_of_week"] = int(getattr(dt, "isoweekday")())
            except Exception:
                # Fallback to 1 (Monday) if anything goes wrong
                defaults["day_of_week"] = 1
        if note is not None and "note" in model_fields:
            defaults["note"] = note
        if "source" in model_fields and not payload.get("source"):
            # Mark that this came from teacher UI by default
            defaults["source"] = "teacher"
        if "updated_at" in model_fields:
            defaults["updated_at"] = timezone.now()
        # updated_by may be a FK named updated_by; only set if present
        if actor_user_id and ("updated_by" in model_fields or "updated_by_id" in model_fields):
            defaults["updated_by_id"] = actor_user_id

        obj, _created = AttendanceRecord.objects.update_or_create(
            **lookup,
            defaults=defaults,
        )
        saved.append(obj)
    return saved
