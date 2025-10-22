from datetime import date as _date
from typing import List, Dict, Any

from django.db.models import QuerySet, Count, Q

from school.models import Student, Class, AttendanceRecord, TimetableEntry, Term  # type: ignore
from common.day_utils import iso_to_school_dow


def _class_fk_id_field() -> str:
    """Return the correct FK field name to Class on AttendanceRecord ('classroom_id' or 'class_id')."""
    # Try to detect the relationship name on the model
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
    # Fallback to classroom_id which matches the provided error's field list
    return "classroom_id"


_CLASS_FK_ID = _class_fk_id_field()


def get_students_for_class_on_date(class_id: int, dt: _date) -> QuerySet[Student]:
    # Include all students (active and inactive). Frontend can dim/disable inactive via the 'active' flag.
    # We ignore the date filter for now (roster typically static).
    return Student.objects.filter(class_fk_id=class_id).order_by("full_name")


def get_attendance_records(
    class_id: int, dt: _date, period_number: int | None = None
) -> QuerySet[AttendanceRecord]:
    # Enforce strict class scope by classroom FK and student's current class
    qs = AttendanceRecord.objects.filter(**{_CLASS_FK_ID: class_id}, date=dt).filter(
        student__class_fk_id=class_id
    )
    if period_number is not None:
        qs = qs.filter(period_number=period_number)
    return qs


def get_summary(
    *,
    scope: str,
    dt: _date,
    class_id: int | None = None,
    wing_id: int | None = None,
    class_ids: List[int] | None = None,
) -> Dict[str, Any]:
    """
    Aggregate attendance KPIs for a given scope on a specific date.
    scope: 'teacher' | 'wing' | 'school' (default)
    Returns dict with keys: date, scope, kpis{present_pct, absent, late, excused}, top_classes[], worst_classes[]
    """
    qs = AttendanceRecord.objects.filter(date=dt)

    # Optional filters (placeholders; wing filtering depends on data model relationship)
    if class_id:
        qs = qs.filter(**{_CLASS_FK_ID: class_id})
    # Filter by a provided set of class IDs (teacher scope for example)
    if class_ids:
        qs = qs.filter(**{f"{_CLASS_FK_ID}__in": list(class_ids)})
    # If there is a Wing model relation via Class.wing_id, filter using that when requested
    if wing_id and hasattr(Class, "wing_id"):
        wing_class_ids = Class.objects.filter(wing_id=wing_id).values_list("id", flat=True)
        qs = qs.filter(**{f"{_CLASS_FK_ID}__in": wing_class_ids})

    total = qs.count()
    absent = qs.filter(status="absent").count()
    late = qs.filter(status="late").count()
    excused = qs.filter(status="excused").count()
    runaway = qs.filter(status="runaway").count()
    present = qs.filter(status="present").count()

    present_pct = float(round((present / total) * 100, 1)) if total else 0.0
    # Expose raw counters to allow client-side aggregation when needed

    # Top/Worst classes by present percentage (limit 5)
    per_class = qs.values(_CLASS_FK_ID).annotate(
        total=Count("id"),
        present=Count("id", filter=Q(status="present")),
    )
    top_classes: List[Dict[str, Any]] = []
    for item in per_class:
        t = item.get("total") or 0
        p = item.get("present") or 0
        pct = float(round((p / t) * 100, 1)) if t else 0.0
        class_val = item.get(_CLASS_FK_ID)
        top_classes.append({"class_id": class_val, "present_pct": pct})
    # Attach class names for better UX (e.g., '7-1')
    try:
        ids = [x.get("class_id") for x in top_classes if x.get("class_id")]
        name_map = {
            cid: name for cid, name in Class.objects.filter(id__in=ids).values_list("id", "name")
        }
        for x in top_classes:
            cid = x.get("class_id")
            if cid in name_map:
                x["class_name"] = name_map.get(cid)
    except Exception:
        pass
    # Sort lists
    top_classes_sorted = sorted(top_classes, key=lambda x: x["present_pct"], reverse=True)[:5]
    worst_classes_sorted = sorted(top_classes, key=lambda x: x["present_pct"])[:5]

    return {
        "date": dt.isoformat(),
        "scope": scope,
        "kpis": {
            "present_pct": present_pct,
            "absent": int(absent),
            "late": int(late),
            "excused": int(excused),
            "runaway": int(runaway),
            "present": int(present),
            "total": int(total),
        },
        "top_classes": top_classes_sorted,
        "worst_classes": worst_classes_sorted,
    }


# ===== Timetable helpers =====


def _current_term() -> Term | None:
    try:
        term = Term.objects.filter(is_current=True).first()
        if term:
            return term
        return Term.objects.order_by("-id").first()
    except Exception:
        return None


def get_teacher_today_periods(*, staff_id: int, dt: _date) -> List[Dict[str, Any]]:
    """Return ordered list of today's periods for a teacher using TimetableEntry.
    Items: {period_number, classroom_id, classroom_name, subject_id, subject_name, start_time?, end_time?}
    Note: Database stores day_of_week as 1..5 (Sun..Thu). We map from ISO weekday (Mon=1..Sun=7).
    """
    term = _current_term()
    if not term:
        return []
    # Unified mapping using central util
    school_day = iso_to_school_dow(dt)
    if school_day < 1 or school_day > 5:
        return []
    # Build period time lookup for this SCHOOL weekday (1=Sun..7=Sat) from PeriodTemplate/TemplateSlot
    times_map: dict[int, tuple] = {}
    try:
        from school.models import PeriodTemplate, TemplateSlot  # type: ignore

        # PeriodTemplate.day_of_week follows school numbering (1=Sun..7=Sat)
        tpl_ids = list(
            PeriodTemplate.objects.filter(day_of_week=school_day).values_list("id", flat=True)
        )
        if tpl_ids:
            slots = (
                TemplateSlot.objects.filter(template_id__in=tpl_ids, kind="lesson")
                .exclude(number__isnull=True)
                .order_by("number", "start_time")
            )
            for s in slots:
                times_map[int(s.number)] = (s.start_time, s.end_time)
    except Exception:
        times_map = {}

    qs = (
        TimetableEntry.objects.filter(teacher_id=staff_id, term_id=term.id, day_of_week=school_day)
        .select_related("classroom", "subject")
        .order_by("period_number")
    )
    out: List[Dict[str, Any]] = []
    for e in qs:
        st_et = times_map.get(int(e.period_number))
        out.append(
            {
                "period_number": e.period_number,
                "classroom_id": e.classroom_id,
                "classroom_name": getattr(e.classroom, "name", None),
                "subject_id": e.subject_id,
                "subject_name": getattr(e.subject, "name_ar", None),
                **({"start_time": st_et[0], "end_time": st_et[1]} if st_et else {}),
            }
        )
    return out


def get_teacher_weekly_grid(*, staff_id: int) -> Dict[str, Any]:
    """Return a week grid for a teacher keyed by school day numbers where 1=Sun..5=Thu.
    This matches the database convention used in TimetableEntry and the compact timetable pages.
    Non-workdays (Fri, Sat) are omitted (left empty keys for 6,7 to maintain shape when needed).
    { days: { '1': [...], '2': [...], '3': [...], '4': [...], '5': [...] }, meta: { term_id, period_times } }
    """
    term = _current_term()
    if not term:
        return {"days": {str(i): [] for i in range(1, 8)}, "meta": {}}
    # Prepare period time maps per school day using PeriodTemplate/TemplateSlot
    # PeriodTemplate.day_of_week follows school numbering: 1=Sun .. 7=Sat
    times_per_day: Dict[int, Dict[int, tuple]] = {d: {} for d in range(1, 6)}
    try:
        from school.models import PeriodTemplate, TemplateSlot  # type: ignore

        for sd in range(1, 6):  # Sun..Thu
            tpl_ids = list(
                PeriodTemplate.objects.filter(day_of_week=sd).values_list("id", flat=True)
            )
            if not tpl_ids:
                continue
            slots = (
                TemplateSlot.objects.filter(template_id__in=tpl_ids, kind="lesson")
                .exclude(number__isnull=True)
                .order_by("number", "start_time")
            )
            td: Dict[int, tuple] = {}
            for s in slots:
                td[int(s.number)] = (s.start_time, s.end_time)
            if td:
                times_per_day[sd] = td
        # If any school day lacks a template, fall back to the first available day's map
        fallback_map: Dict[int, tuple] | None = None
        for d in range(1, 6):
            if times_per_day.get(d):
                fallback_map = times_per_day[d]
                break
        if fallback_map:
            for d in range(1, 6):
                if not times_per_day.get(d):
                    times_per_day[d] = fallback_map
    except Exception:
        pass

    # Consolidated period_times for UI fallback (use first non-empty day map)
    period_times: Dict[int, tuple] = {}
    for d in range(1, 6):
        if times_per_day.get(d):
            period_times = dict(times_per_day[d])
            break

    qs = (
        TimetableEntry.objects.filter(teacher_id=staff_id, term_id=term.id)
        .select_related("classroom", "subject")
        .order_by("day_of_week", "period_number")
    )
    # Initialize 1..7 keys; we will fill 1..5 (Sun..Thu) and leave others empty
    days: Dict[str, List[Dict[str, Any]]] = {str(i): [] for i in range(1, 8)}
    for e in qs:
        d = int(e.day_of_week)
        if d < 1 or d > 5:
            continue
        st_et = times_per_day.get(d, {}).get(int(e.period_number)) or period_times.get(
            int(e.period_number)
        )
        days[str(d)].append(
            {
                "period_number": e.period_number,
                "classroom_id": e.classroom_id,
                "classroom_name": getattr(e.classroom, "name", None),
                "subject_id": e.subject_id,
                "subject_name": getattr(e.subject, "name_ar", None),
                **({"start_time": st_et[0], "end_time": st_et[1]} if st_et else {}),
            }
        )
    return {"days": days, "meta": {"term_id": term.id, "period_times": period_times}}