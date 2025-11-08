from __future__ import annotations
from datetime import time as _time
from typing import Dict, Optional, Tuple

# Centralized timetable timing resolution utilities
# Used by teacher selectors and wing supervisor API to avoid duplication.


def _norm_scope(val: Optional[str]) -> Optional[str]:
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


def _infer_wing_no(cls) -> Optional[int]:
    try:
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


def _wing_floor_from_no(wing_no: Optional[int]) -> Optional[str]:
    if wing_no is None:
        return None
    return "ground" if wing_no in (1, 2) else ("upper" if wing_no in (3, 4, 5) else None)


# Caches shared per-process
_times_cache: Dict[tuple[int, Optional[str]], Dict[int, tuple]] = {}
_times_cache_wing: Dict[tuple[int, int], Dict[int, tuple]] = {}
_times_cache_class: Dict[tuple[int, int], Dict[int, tuple]] = {}


def times_for(day: int, scope: Optional[str]) -> Dict[int, tuple]:
    """Return lesson times for a given day from PeriodTemplate/TemplateSlot.
    If scope is provided (e.g., 'secondary' or 'grade9'), attempt a scoped match first,
    then fall back to any template for that day.
    """
    key = (int(day), scope or None)
    if key in _times_cache:
        return _times_cache[key]
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
        _times_cache[key] = slots_map
        return slots_map
    except Exception:
        _times_cache[key] = {}
        return {}


def times_for_by_wing(day: int, wing_id: int) -> Dict[int, tuple]:
    key = (int(day), int(wing_id))
    if key in _times_cache_wing:
        return _times_cache_wing[key]
    try:
        from school.models import PeriodTemplate, TemplateSlot  # type: ignore

        tpl_ids = list(PeriodTemplate.objects.filter(day_of_week=day, wings__id=wing_id).values_list("id", flat=True))
        slots_map: Dict[int, tuple] = {}
        if tpl_ids:
            slots = (
                TemplateSlot.objects.filter(template_id__in=tpl_ids, kind="lesson")
                .exclude(number__isnull=True)
                .order_by("number", "start_time")
            )
            for s in slots:
                slots_map[int(s.number)] = (s.start_time, s.end_time)
        _times_cache_wing[key] = slots_map
        return slots_map
    except Exception:
        _times_cache_wing[key] = {}
        return {}


def times_for_by_class(day: int, class_id: int) -> Dict[int, tuple]:
    key = (int(day), int(class_id))
    if key in _times_cache_class:
        return _times_cache_class[key]
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
        _times_cache_class[key] = slots_map
        return slots_map
    except Exception:
        _times_cache_class[key] = {}
        return {}


def parse_grade_section(cls) -> tuple[int, Optional[int]]:
    try:
        grade_val = int(getattr(cls, "grade", 0) or 0)
    except Exception:
        grade_val = 0
    sec_val: Optional[int] = None
    try:
        import re

        sec_raw = str(getattr(cls, "section", "") or "").strip()
        m = re.match(r"^(\d+)", sec_raw)
        if m:
            sec_val = int(m.group(1))
        else:
            name = str(getattr(cls, "name", "") or "")
            m2 = re.search(r"^(\d+)[\-\./](\d+)", name.strip())
            if m2:
                if not grade_val:
                    grade_val = int(m2.group(1))
                sec_val = int(m2.group(2))
    except Exception:
        pass
    return grade_val, sec_val


def resolve_lesson_time(*, cls, day: int, period_number: int) -> Optional[Tuple[_time, _time]]:
    """Resolve start/end time with precedence:
    1) Class-bound template (PeriodTemplate.classes)
    2) Thursday Wing 3 special-case by grade (secondary | grade9) when day=5
    3) Generic template for the day (any PeriodTemplate with matching day_of_week)
    """
    # 1) Class binding
    st_et: Optional[Tuple[_time, _time]] = None
    try:
        if getattr(cls, "id", None):
            st_et = times_for_by_class(int(day), int(cls.id)).get(int(period_number))
    except Exception:
        st_et = None

    # 2) Thursday Wing 3 by grade (kept per requirement)
    if not st_et and int(day) == 5:
        try:
            wno_raw = getattr(cls, "wing_id", None)
            wno = int(wno_raw) if wno_raw is not None else (_infer_wing_no(cls) or 0)
        except Exception:
            wno = _infer_wing_no(cls) or 0
        if int(wno) == 3:
            g, sec = parse_grade_section(cls)
            scope: Optional[str] = None
            if g >= 10:
                scope = "secondary"
            elif g == 9 and (sec is not None) and 2 <= int(sec) <= 4:
                scope = "grade9"
            if scope:
                scoped = times_for(5, scope)
                st_et = scoped.get(int(period_number))
                if st_et:
                    return st_et

    # 3) Generic fallback for that day
    if not st_et:
        st_et = times_for(int(day), None).get(int(period_number))

    return st_et


def resolve_thursday_wing3_time(*, cls, period_number: int) -> Optional[Tuple[_time, _time]]:
    """Explicit resolver for Thursday Wing 3 timing.
    Applies grade-based selection (secondary | grade9 2..4) consistent with resolve_lesson_time.
    """
    return resolve_lesson_time(cls=cls, day=5, period_number=int(period_number))
