from __future__ import annotations
from datetime import date as _date, time as _time
from typing import Iterable, List, Dict, Any, Optional

from django.db import transaction
from django.utils import timezone

from school.models import AttendanceRecord, Staff, TimetableEntry  # type: ignore
from ..models import AttendanceStatus
from ..selectors import _current_term  # reuse existing helper


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


def _map_iso_to_school_day(iso: int) -> Optional[int]:
    """Map ISO weekday (Mon=1..Sun=7) to school day (Sun=1..Thu=5).
    Returns None for non-working days (Fri=5, Sat=6 ISO).
    """
    if iso in (5, 6):
        return None
    return {7: 1, 1: 2, 2: 3, 3: 4, 4: 5}.get(iso)


def _period_times_for_day(school_day: int) -> Dict[int, tuple]:
    """Best-effort lookup of start/end times for period numbers on a given school day.
    Falls back to empty dict if no templates available."""
    try:
        from school.models import PeriodTemplate, TemplateSlot  # type: ignore

        tpl_ids = list(
            PeriodTemplate.objects.filter(day_of_week=school_day).values_list("id", flat=True)
        )
        if not tpl_ids:
            return {}
        slots = (
            TemplateSlot.objects.filter(template_id__in=tpl_ids, kind="lesson")
            .exclude(number__isnull=True)
            .order_by("number", "start_time")
        )
        out: Dict[int, tuple] = {}
        for s in slots:
            out[int(s.number)] = (s.start_time, s.end_time)
        return out
    except Exception:
        return {}


@transaction.atomic
def bulk_save_attendance(
    *,
    class_id: int,
    dt: _date,
    records: Iterable[Dict[str, Any]],
    actor_user_id: int | None = None,
    period_number: int | None = None,
) -> List[AttendanceRecord]:
    """
    Upsert-like bulk save for attendance for the given class/date.
    Each record dict should contain: {student_id: int, status: str, note?: str}
    Inference rules:
      - If period_number is provided, resolve timetable for that class/teacher/day.
      - Else, attempt to infer a single TimetableEntry for (class, teacher, term, school_day).
      - On ambiguity (multiple matches) or no match, raise ValueError with a clear message.
    """
    saved: list[AttendanceRecord] = []
    fk = _class_fk_id_field()
    model_fields = {f.name for f in AttendanceRecord._meta.get_fields()}

    # Derive teacher (Staff) from actor_user_id if possible
    staff: Staff | None = None  # type: ignore
    if actor_user_id:
        try:
            staff = Staff.objects.filter(user_id=actor_user_id).first()
        except Exception:
            staff = None

    # Determine term and school day
    term = _current_term()
    iso = int(getattr(dt, "isoweekday")())
    school_day = _map_iso_to_school_day(iso)
    if term is None:
        raise ValueError("no current term configured")
    if school_day is None:
        raise ValueError("date is not a working school day")

    # Build timetable candidates for this class/day (and teacher if available)
    qs = TimetableEntry.objects.filter(
        classroom_id=class_id, term_id=term.id, day_of_week=school_day
    )
    if staff:
        qs = qs.filter(teacher_id=getattr(staff, "id", None))
    if period_number:
        qs = qs.filter(period_number=period_number)
    candidates = list(qs.select_related("subject", "teacher"))

    # Decide on the period/subject/teacher context
    chosen: TimetableEntry | None = None
    if period_number:
        chosen = candidates[0] if len(candidates) == 1 else None
        if chosen is None:
            raise ValueError("could not resolve timetable for provided period_number")
    else:
        if len(candidates) == 1:
            chosen = candidates[0]
            period_number = int(chosen.period_number)
        elif len(candidates) == 0:
            raise ValueError(
                "no matching timetable entry for this class/teacher on the selected date"
            )
        else:
            # multiple matches → require explicit period_number
            raise ValueError("multiple timetable periods found; select a period in the UI")

    # Lookup period times (best-effort)
    times_map = _period_times_for_day(school_day)
    st_et = times_map.get(int(period_number)) if period_number else None
    start_time = st_et[0] if st_et else _time(0, 0)
    end_time = st_et[1] if st_et else _time(0, 0)

    for payload in records:
        student_id = int(payload["student_id"])  # DB pk
        status = payload.get("status") or AttendanceStatus.PRESENT
        note = payload.get("note")
        exit_reasons_in = payload.get("exit_reasons")  # string (comma) or list

        # Use a lookup that matches the uniqueness constraint to avoid clobbering other periods
        lookup = {
            fk: class_id,
            "date": dt,
            "student_id": student_id,
            "period_number": int(period_number),  # type: ignore[arg-type]
            "term_id": term.id,
        }
        defaults: Dict[str, Any] = {"status": status}

        # Mandatory timetable fields (also mirrored in lookup above)
        defaults["period_number"] = int(period_number)  # type: ignore[arg-type]
        defaults["term_id"] = term.id
        if chosen is not None:
            defaults["subject_id"] = chosen.subject_id
            defaults["teacher_id"] = chosen.teacher_id
        elif staff is not None and "teacher_id" in model_fields:
            defaults["teacher_id"] = getattr(staff, "id", None)
        # Times
        if "start_time" in model_fields:
            defaults["start_time"] = start_time
        if "end_time" in model_fields:
            defaults["end_time"] = end_time
        # Day-of-week
        if "day_of_week" in model_fields:
            defaults["day_of_week"] = int(getattr(dt, "isoweekday")())
        # Note and source
        if note is not None and "note" in model_fields:
            defaults["note"] = note
        if "source" in model_fields and not payload.get("source"):
            defaults["source"] = "teacher"
        if "updated_at" in model_fields:
            defaults["updated_at"] = timezone.now()
        if actor_user_id and ("updated_by" in model_fields or "updated_by_id" in model_fields):
            defaults["updated_by_id"] = actor_user_id

        # Exit permission fields handling (إذن خروج)
        prev: Optional[AttendanceRecord] = None
        try:
            prev = AttendanceRecord.objects.filter(**lookup).order_by("-updated_at").first()
        except Exception:
            prev = None
        # Normalize input reasons to comma-separated string
        reasons_str: Optional[str] = None
        if exit_reasons_in is not None:
            if isinstance(exit_reasons_in, list):
                try:
                    reasons_str = ",".join(
                        [str(x).strip() for x in exit_reasons_in if str(x).strip()]
                    )
                except Exception:
                    reasons_str = None
            elif isinstance(exit_reasons_in, str):
                reasons_str = exit_reasons_in
        # Apply reasons if provided
        if reasons_str is not None and "exit_reasons" in model_fields:
            defaults["exit_reasons"] = reasons_str

        # Ensure the exit reason is also reflected in the note (human-readable) when status is 'excused'
        # Mapping of reason codes to Arabic labels
        def _reason_label(code: str) -> str:
            m = {
                "admin": "إدارة",
                "wing": "مشرف الجناح",
                "nurse": "الممرض",
                "restroom": "حمام",
            }
            return m.get(code.strip().lower(), code)

        if status == "excused":
            # Derive a readable note like: "إذن خروج — إدارة"
            readable_reason = None
            if reasons_str:
                # If multiple (comma-separated), pick the first for note
                first = str(reasons_str).split(",")[0].strip()
                if first:
                    readable_reason = _reason_label(first)
            note_text = "إذن خروج" + (f" — {readable_reason}" if readable_reason else "")
            if "note" in model_fields:
                defaults["note"] = note_text

        now = timezone.now()
        if status == "excused":
            # On entering excused, stamp left_at if not already set
            if "exit_left_at" in model_fields:
                if (
                    prev is None
                    or getattr(prev, "status", None) != "excused"
                    or getattr(prev, "exit_left_at", None) is None
                ):
                    defaults["exit_left_at"] = now
        else:
            # On leaving excused state, stamp returned_at if not already set
            if "exit_returned_at" in model_fields:
                if (
                    prev is not None
                    and getattr(prev, "status", None) == "excused"
                    and getattr(prev, "exit_returned_at", None) is None
                ):
                    defaults["exit_returned_at"] = now

        obj, _created = AttendanceRecord.objects.update_or_create(
            **lookup,
            defaults=defaults,
        )
        saved.append(obj)
    return saved
