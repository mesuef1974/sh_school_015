from datetime import date as _date
from typing import Any, Dict, List

from django.db.models import Count, Q, QuerySet
from school.models import AttendanceRecord, Class, ExitEvent, Student, Term, TimetableEntry  # type: ignore

try:
    from backend.common.day_utils import iso_to_school_dow
except Exception:
    from common.day_utils import iso_to_school_dow  # type: ignore

from .timing import resolve_lesson_time


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


def get_attendance_records(class_id: int, dt: _date, period_number: int | None = None) -> QuerySet[AttendanceRecord]:
    # Enforce strict class scope by classroom FK and student's current class
    qs = AttendanceRecord.objects.filter(**{_CLASS_FK_ID: class_id}, date=dt).filter(student__class_fk_id=class_id)
    if period_number is not None:
        qs = qs.filter(period_number=period_number)
    # Performance: avoid N+1 when serializing student/subject/teacher fields downstream
    try:
        qs = qs.select_related("student", "subject", "teacher")
    except Exception:
        # If any relation missing in legacy schema, degrade gracefully
        try:
            qs = qs.select_related("student", "subject")
        except Exception:
            pass
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

    # Approval gating: For non-teacher scopes and aggregate views (wing or school-wide),
    # only include records approved by wing supervisors. This ensures that student
    # attendance isn’t considered closed until supervisor approval.
    try:
        if scope != "teacher":
            # When wing-scoped, always require supervisor-approved records.
            if wing_id or (not class_id and not class_ids):
                qs = qs.filter(source="supervisor")
    except Exception:
        # If source field missing in older schemas, skip gating gracefully
        pass

    total = qs.count()
    absent = qs.filter(status="absent").count()
    late = qs.filter(status="late").count()
    excused = qs.filter(status="excused").count()
    runaway = qs.filter(status="runaway").count()
    present = qs.filter(status="present").count()

    # Compute effective totals for percentages excluding late/excused/runaway from denominator
    effective_total = present + absent
    present_pct = float(round((present / effective_total) * 100, 1)) if effective_total else 0.0
    absent_pct = float(round((absent / effective_total) * 100, 1)) if effective_total else 0.0

    # Exit events KPIs (total and open) aligned to same scope/date filters
    exit_qs = ExitEvent.objects.filter(date=dt)
    if class_id:
        exit_qs = exit_qs.filter(classroom_id=class_id)
    if class_ids:
        exit_qs = exit_qs.filter(classroom_id__in=list(class_ids))
    if wing_id and hasattr(Class, "wing_id"):
        wing_class_ids = Class.objects.filter(wing_id=wing_id).values_list("id", flat=True)
        exit_qs = exit_qs.filter(classroom_id__in=wing_class_ids)
    exit_events_total = exit_qs.count()
    exit_events_open = exit_qs.filter(returned_at__isnull=True).count()

    # Top/Worst classes by present percentage (limit 5) using effective_total per class
    per_class = qs.values(_CLASS_FK_ID).annotate(
        total=Count("id"),
        present=Count("id", filter=Q(status="present")),
        absent=Count("id", filter=Q(status="absent")),
    )
    top_classes: List[Dict[str, Any]] = []
    for item in per_class:
        p = int(item.get("present") or 0)
        a = int(item.get("absent") or 0)
        eff = p + a
        pct = float(round((p / eff) * 100, 1)) if eff else 0.0
        class_val = item.get(_CLASS_FK_ID)
        top_classes.append({"class_id": class_val, "present_pct": pct})
    # Attach class names for better UX (e.g., '7-1')
    try:
        ids = [x.get("class_id") for x in top_classes if x.get("class_id")]
        name_map = {cid: name for cid, name in Class.objects.filter(id__in=ids).values_list("id", "name")}
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
            "absent_pct": absent_pct,
            "effective_total": int(effective_total),
            "absent": int(absent),
            "late": int(late),
            "excused": int(excused),
            "runaway": int(runaway),
            "present": int(present),
            "total": int(total),
            "exit_events_total": int(exit_events_total),
            "exit_events_open": int(exit_events_open),
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
    Timing is resolved from PeriodTemplate/TemplateSlot taking into account wing/floor scope when available.
    """
    term = _current_term()
    if not term:
        return []
    # Unified mapping using central util
    school_day = iso_to_school_dow(dt)
    if school_day < 1 or school_day > 5:
        return []

    # Helper to normalize scope values (wing.floor may be Arabic/English)
    def _norm_scope(val: str | None) -> str | None:
        if not val:
            return None
        v = str(val).strip().lower()
        # Arabic to English mapping and common variants
        mapping = {
            "أرضي": "ground",
            "ارضى": "ground",
            "ارضي": "ground",
            "الدور الارضي": "ground",
            "الأرضي": "ground",
            "علوي": "upper",
            "الدور العلوي": "upper",
        }
        return mapping.get(v, v or None)

    # Infer wing number when Class.wing is not available using grade/section rules provided by school
    def _infer_wing_no(cls) -> int | None:
        try:
            # Prefer explicit wing relation id if present
            w = getattr(cls, "wing", None)
            if w and getattr(w, "id", None):
                return int(w.id)
            grade = int(getattr(cls, "grade", 0) or 0)
            # section may be like "1", "1A", "1-Science" or "1/ث"; take leading int
            sec_raw = str(getattr(cls, "section", "") or "").strip()
            sec = None
            import re

            m = re.match(r"^(\d+)", sec_raw)
            if m:
                sec = int(m.group(1))
            else:
                # try parse from name like "11/2" or "11-2"
                name = str(getattr(cls, "name", "") or "")
                m2 = re.search(r"^(\d+)[\-\./](\d+)", name.strip())
                if m2:
                    grade = grade or int(m2.group(1))
                    sec = int(m2.group(2))
            if not grade or sec is None:
                return None
            # Mapping per user specification
            if grade == 7 and 1 <= sec <= 5:
                return 1
            if grade == 8 and 1 <= sec <= 4:
                return 2
            if grade == 9 and sec == 1:
                return 2
            if grade == 9 and 2 <= sec <= 4:
                return 3
            if grade == 10 and 1 <= sec <= 2:
                return 3
            if grade == 10 and 3 <= sec <= 4:
                return 4
            if grade == 11 and 1 <= sec <= 3:
                return 4
            if grade == 11 and sec == 4:
                return 5
            if grade == 12 and 1 <= sec <= 4:
                return 5
            return None
        except Exception:
            return None

    def _wing_floor_from_no(wing_no: int | None) -> str | None:
        if wing_no is None:
            return None
        return "ground" if wing_no in (1, 2) else ("upper" if wing_no in (3, 4, 5) else None)

    # Cache of times per (day, scope)
    times_cache: dict[tuple[int, str | None], dict[int, tuple]] = {}
    # Cache of times per (day, wing_id)
    times_cache_wing: dict[tuple[int, int], dict[int, tuple]] = {}
    # Cache of times per (day, class_id)
    times_cache_class: dict[tuple[int, int], dict[int, tuple]] = {}

    def _times_for(day: int, scope: str | None) -> dict[int, tuple]:
        key = (day, scope or None)
        if key in times_cache:
            return times_cache[key]
        try:
            from school.models import PeriodTemplate, TemplateSlot  # type: ignore

            base_qs = PeriodTemplate.objects.filter(day_of_week=day)
            tpl_ids: list[int] = []
            if scope:
                tpl_ids = list(base_qs.filter(scope__iexact=scope).values_list("id", flat=True))
            # Fallback to any template for the day if scoped not found
            if not tpl_ids:
                tpl_ids = list(base_qs.values_list("id", flat=True))
            slots_map: dict[int, tuple] = {}
            if tpl_ids:
                slots = (
                    TemplateSlot.objects.filter(template_id__in=tpl_ids, kind="lesson")
                    .exclude(number__isnull=True)
                    .order_by("number", "start_time")
                )
                for s in slots:
                    slots_map[int(s.number)] = (s.start_time, s.end_time)
            times_cache[key] = slots_map
            return slots_map
        except Exception:
            times_cache[key] = {}
            return {}

    def _times_for_by_wing(day: int, wing_id: int) -> dict[int, tuple]:
        key = (day, wing_id)
        if key in times_cache_wing:
            return times_cache_wing[key]
        try:
            from school.models import PeriodTemplate, TemplateSlot  # type: ignore

            tpl_ids = list(
                PeriodTemplate.objects.filter(day_of_week=day, wings__id=wing_id).values_list("id", flat=True)
            )
            slots_map: dict[int, tuple] = {}
            if tpl_ids:
                slots = (
                    TemplateSlot.objects.filter(template_id__in=tpl_ids, kind="lesson")
                    .exclude(number__isnull=True)
                    .order_by("number", "start_time")
                )
                for s in slots:
                    slots_map[int(s.number)] = (s.start_time, s.end_time)
            times_cache_wing[key] = slots_map
            return slots_map
        except Exception:
            times_cache_wing[key] = {}
            return {}

    def _times_for_by_class(day: int, class_id: int) -> dict[int, tuple]:
        key = (day, class_id)
        if key in times_cache_class:
            return times_cache_class[key]
        try:
            from school.models import PeriodTemplate, TemplateSlot  # type: ignore

            tpl_ids = list(
                PeriodTemplate.objects.filter(day_of_week=day, classes__id=class_id).values_list("id", flat=True)
            )
            slots_map: dict[int, tuple] = {}
            if tpl_ids:
                slots = (
                    TemplateSlot.objects.filter(template_id__in=tpl_ids, kind="lesson")
                    .exclude(number__isnull=True)
                    .order_by("number", "start_time")
                )
                for s in slots:
                    slots_map[int(s.number)] = (s.start_time, s.end_time)
            times_cache_class[key] = slots_map
            return slots_map
        except Exception:
            times_cache_class[key] = {}
            return {}

    qs = (
        TimetableEntry.objects.filter(teacher_id=staff_id, term_id=term.id, day_of_week=school_day)
        .select_related("classroom", "classroom__wing", "subject")
        .order_by("period_number")
    )
    out: List[Dict[str, Any]] = []
    for e in qs:
        cls = e.classroom
        wing = getattr(cls, "wing", None)
        wing_no = getattr(wing, "id", None) or _infer_wing_no(cls)
        # Try centralized resolver with explicit Wing 3 Thursday support first
        st_et = None
        try:
            wno = int(getattr(cls, "wing_id", None) or 0) or (_infer_wing_no(cls) or 0)
        except Exception:
            wno = 0
        st_et = resolve_lesson_time(cls=cls, day=int(school_day), period_number=int(e.period_number))
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
    Response shape remains backward-compatible:
      { days: { '1': [...], ... }, meta: { term_id, period_times, columns_by_day?, slot_meta_by_day? } }
    - columns_by_day (optional): ordered column tokens per school day including recess/prayer slots.
      Example: { '1': ['P1','RECESS-1','P2','P3','PRAYER-1','P4', ...] }
    - slot_meta_by_day (optional): metadata for non-lesson tokens with labels and times.
      Example: { '1': { 'RECESS-1': {kind:'recess', label:'استراحة', start_time:'10:10', end_time:'10:25'}, ... } }
    Period times are resolved from PeriodTemplate/TemplateSlot with wing/floor scope where available.
    """
    term = _current_term()
    if not term:
        return {"days": {str(i): [] for i in range(1, 8)}, "meta": {}}

    # Helper to normalize scope values (same as in get_teacher_today_periods)
    def _norm_scope(val: str | None) -> str | None:
        if not val:
            return None
        v = str(val).strip().lower()
        mapping = {
            "أرضي": "ground",
            "ارضى": "ground",
            "ارضي": "ground",
            "الدور الارضي": "ground",
            "الأرضي": "ground",
            "علوي": "upper",
            "الدور العلوي": "upper",
        }
        return mapping.get(v, v or None)

    # Infer wing number when not available via relation, using school rules
    def _infer_wing_no(cls) -> int | None:
        try:
            w = getattr(cls, "wing", None)
            if w and getattr(w, "id", None):
                return int(w.id)
            grade = int(getattr(cls, "grade", 0) or 0)
            sec_raw = str(getattr(cls, "section", "") or "").strip()
            sec = None
            import re

            m = re.match(r"^(\d+)", sec_raw)
            if m:
                sec = int(m.group(1))
            else:
                name = str(getattr(cls, "name", "") or "")
                m2 = re.search(r"^(\d+)[\-\./](\d+)", name.strip())
                if m2:
                    grade = grade or int(m2.group(1))
                    sec = int(m2.group(2))
            if not grade or sec is None:
                return None
            if grade == 7 and 1 <= sec <= 5:
                return 1
            if grade == 8 and 1 <= sec <= 4:
                return 2
            if grade == 9 and sec == 1:
                return 2
            if grade == 9 and 2 <= sec <= 4:
                return 3
            if grade == 10 and 1 <= sec <= 2:
                return 3
            if grade == 10 and 3 <= sec <= 4:
                return 4
            if grade == 11 and 1 <= sec <= 3:
                return 4
            if grade == 11 and sec == 4:
                return 5
            if grade == 12 and 1 <= sec <= 4:
                return 5
            return None
        except Exception:
            return None

    def _wing_floor_from_no(wing_no: int | None) -> str | None:
        if wing_no is None:
            return None
        return "ground" if wing_no in (1, 2) else ("upper" if wing_no in (3, 4, 5) else None)

    # Cache times per (day, scope)
    times_cache: Dict[tuple[int, str | None], Dict[int, tuple]] = {}
    # Cache times per (day, wing_id)
    times_cache_wing: Dict[tuple[int, int], Dict[int, tuple]] = {}
    # Cache times per (day, class_id)
    times_cache_class: Dict[tuple[int, int], Dict[int, tuple]] = {}

    def _times_for(day: int, scope: str | None) -> Dict[int, tuple]:
        key = (day, scope or None)
        if key in times_cache:
            return times_cache[key]
        try:
            from school.models import PeriodTemplate, TemplateSlot  # type: ignore

            base_qs = PeriodTemplate.objects.filter(day_of_week=day)
            tpl_ids: list[int] = []
            if scope:
                tpl_ids = list(base_qs.filter(scope__iexact=scope).values_list("id", flat=True))
            if not tpl_ids:
                tpl_ids = list(base_qs.values_list("id", flat=True))
            slots_map: Dict[int, tuple] = {}
            if tpl_ids:
                slots = (
                    TemplateSlot.objects.filter(template_id__in=tpl_ids, kind="lesson")
                    .exclude(number__isnull=True)
                    .order_by("number", "start_time")
                )
                for s in slots:
                    slots_map[int(s.number)] = (s.start_time, s.end_time)
            times_cache[key] = slots_map
            return slots_map
        except Exception:
            times_cache[key] = {}
            return {}

    def _times_for_by_wing(day: int, wing_id: int) -> Dict[int, tuple]:
        key = (day, wing_id)
        if key in times_cache_wing:
            return times_cache_wing[key]
        try:
            from school.models import PeriodTemplate, TemplateSlot  # type: ignore

            tpl_ids = list(
                PeriodTemplate.objects.filter(day_of_week=day, wings__id=wing_id).values_list("id", flat=True)
            )
            slots_map: Dict[int, tuple] = {}
            if tpl_ids:
                slots = (
                    TemplateSlot.objects.filter(template_id__in=tpl_ids, kind="lesson")
                    .exclude(number__isnull=True)
                    .order_by("number", "start_time")
                )
                for s in slots:
                    slots_map[int(s.number)] = (s.start_time, s.end_time)
            times_cache_wing[key] = slots_map
            return slots_map
        except Exception:
            times_cache_wing[key] = {}
            return {}

    def _times_for_by_class(day: int, class_id: int) -> Dict[int, tuple]:
        key = (day, class_id)
        if key in times_cache_class:
            return times_cache_class[key]
        try:
            from school.models import PeriodTemplate, TemplateSlot  # type: ignore

            tpl_ids = list(
                PeriodTemplate.objects.filter(day_of_week=day, classes__id=class_id).values_list("id", flat=True)
            )
            slots_map: Dict[int, tuple] = {}
            if tpl_ids:
                slots = (
                    TemplateSlot.objects.filter(template_id__in=tpl_ids, kind="lesson")
                    .exclude(number__isnull=True)
                    .order_by("number", "start_time")
                )
                for s in slots:
                    slots_map[int(s.number)] = (s.start_time, s.end_time)
            times_cache_class[key] = slots_map
            return slots_map
        except Exception:
            times_cache_class[key] = {}
            return {}

    # Consolidated generic period_times fallback (first available day without scope)
    period_times: Dict[int, tuple] = {}
    for d in range(1, 6):
        tm = _times_for(d, None)
        if tm:
            period_times = dict(tm)
            break

    qs = (
        TimetableEntry.objects.filter(teacher_id=staff_id, term_id=term.id)
        .select_related("classroom", "classroom__wing", "subject")
        .order_by("day_of_week", "period_number")
    )

    # Build columns_by_day and slot_meta_by_day using PeriodTemplate/TemplateSlot including recess/prayer
    columns_by_day: Dict[str, list[str]] = {str(i): [] for i in range(1, 8)}
    slot_meta_by_day: Dict[str, Dict[str, Dict[str, Any]]] = {str(i): {} for i in range(1, 8)}
    try:
        from school.models import PeriodTemplate, TemplateSlot  # type: ignore

        # Collect class ids per day from the teacher's timetable
        classes_per_day: Dict[int, set[int]] = {i: set() for i in range(1, 8)}
        for e in qs:
            d = int(e.day_of_week)
            if 1 <= d <= 7:
                classes_per_day[d].add(int(e.classroom_id))
        # For each day, choose representative templates with priority: classes -> generic
        for d in range(1, 8):
            tpl_qs = PeriodTemplate.objects.filter(day_of_week=d)
            tpl_ids: list[int] = []
            cls_ids = list(classes_per_day.get(d) or [])
            if cls_ids:
                tpl_ids = list(tpl_qs.filter(classes__id__in=cls_ids).distinct().values_list("id", flat=True))
            if not tpl_ids:
                tpl_ids = list(tpl_qs.values_list("id", flat=True))
            if not tpl_ids:
                continue
            # Fetch all slots (lesson/recess/prayer/...) ordered by time
            slots = TemplateSlot.objects.filter(template_id__in=tpl_ids).order_by("start_time", "number")
            # Build ordered tokens, ensuring uniqueness and logical interleaving by time
            tokens: list[str] = []
            used_lessons: set[int] = set()
            kind_counters: Dict[str, int] = {}
            for s in slots:
                kind = (getattr(s, "kind", "lesson") or "lesson").strip().lower()
                if kind == "lesson":
                    try:
                        num = int(getattr(s, "number", 0) or 0)
                    except Exception:
                        num = 0
                    if num and num not in used_lessons:
                        tok = f"P{num}"
                        tokens.append(tok)
                        used_lessons.add(num)
                else:
                    # Non-lesson: create stable token per order occurrence of this kind
                    cnt = kind_counters.get(kind, 0) + 1
                    kind_counters[kind] = cnt
                    tok = f"{kind.upper()}-{cnt}"
                    # Save meta
                    try:
                        lbl_map = {"recess": "استراحة", "break": "استراحة", "prayer": "الصلاة"}
                        label = lbl_map.get(kind, kind)
                        slot_meta_by_day[str(d)][tok] = {
                            "kind": kind,
                            "label": label,
                            "start_time": getattr(s, "start_time", None),
                            "end_time": getattr(s, "end_time", None),
                        }
                    except Exception:
                        pass
                    tokens.append(tok)
            if tokens:
                columns_by_day[str(d)] = tokens
    except Exception:
        pass

    # Initialize 1..7 keys; we will fill 1..5 (Sun..Thu) and leave others empty
    days: Dict[str, List[Dict[str, Any]]] = {str(i): [] for i in range(1, 8)}
    for e in qs:
        d = int(e.day_of_week)
        if d < 1 or d > 5:
            continue
        cls = e.classroom
        # Use Wing 3 Thursday resolver first when applicable, then unified resolver
        st_et = None
        try:
            wno = int(getattr(cls, "wing_id", None) or 0) or (_infer_wing_no(cls) or 0)
        except Exception:
            wno = 0
        st_et = resolve_lesson_time(cls=cls, day=int(d), period_number=int(e.period_number))
        if not st_et:
            # last resort keep previous generic fallback
            st_et = period_times.get(int(e.period_number))
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
    return {
        "days": days,
        "meta": {
            "term_id": term.id,
            "period_times": period_times,
            "columns_by_day": columns_by_day,
            "slot_meta_by_day": slot_meta_by_day,
        },
    }