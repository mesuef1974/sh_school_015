from __future__ import annotations
from datetime import time as _time
from typing import Any, Dict, Optional, Tuple

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
    """Resolve a lesson's start/end time for a given class, day (1..7), and period number.
    Precedence:
      1) class-bound template
      2) Thursday grade-based (secondary for grade>=10, grade9 for 9-2..9-4)
      3) wing-bound templates (M2M)
      4) legacy scope wing-N
      5) floor scope (ground/upper)
      6) generic for the day
    Applies upper-floor special case for Sun–Wed period 7: 12:25–13:10.
    """
    # 1) Class binding
    st_et = None
    try:
        if getattr(cls, "id", None):
            st_et = times_for_by_class(day, int(cls.id)).get(int(period_number))
    except Exception:
        st_et = None

    # 2) Thursday grade-based
    if not st_et and int(day) == 5:
        g, sec = parse_grade_section(cls)
        if g >= 10:
            st_et = times_for(day, "secondary").get(int(period_number))
        if (not st_et) and g == 9 and sec is not None and 2 <= int(sec) <= 4:
            st_et = times_for(day, "grade9").get(int(period_number))

    # 3) Wing-bound (M2M)
    if not st_et:
        try:
            wing_id_val = int(getattr(cls, "wing_id", None) or 0)
        except Exception:
            wing_id_val = 0
        if wing_id_val:
            st_et = times_for_by_wing(day, wing_id_val).get(int(period_number))

    # 4) Legacy wing-N scope
    if not st_et:
        wno = _infer_wing_no(cls)
        if wno:
            st_et = times_for(day, f"wing-{wno}").get(int(period_number))

    # 5) Floor scope
    if not st_et:
        wno2 = _infer_wing_no(cls)
        floor_scope = _wing_floor_from_no(wno2)
        if floor_scope:
            st_et = times_for(day, floor_scope).get(int(period_number))

    # 6) Generic fallback for that day
    if not st_et:
        st_et = times_for(day, None).get(int(period_number))

    # Upper-floor special case: Sun–Wed P7
    try:
        is_upper = False
        w = getattr(cls, "wing", None)
        if w is not None:
            is_upper = (_norm_scope(getattr(w, "floor", None)) == "upper")
        else:
            wno = _infer_wing_no(cls)
            is_upper = (_wing_floor_from_no(wno) == "upper")
    except Exception:
        is_upper = False
    if is_upper and int(day) in (1, 2, 3, 4) and int(period_number) == 7:
        st_et = (_time(12, 25), _time(13, 10))

    return st_et


def resolve_thursday_wing3_time(*, cls, period_number: int) -> Optional[Tuple[_time, _time]]:
    """Dedicated resolver for Wing 3 on Thursday (الخميس – جناح 3).
    Uses DB-backed templates with strict precedence tailored for Wing 3 composition:
      - Classes grade >= 10 → Thursday secondary template (thu_secondary)
      - Classes grade 9 sections 2..4 → Thursday grade9 template (thu_grade9_2_3_4)
      - Otherwise fallback to generic Thursday resolution for the class.
    This function exists to provide an explicit, professional and safe entry point for
    Wing 3 Thursday timing, while delegating to resolve_lesson_time for all fallbacks.
    """
    # Prefer explicit class bindings if any
    try:
        if getattr(cls, "id", None):
            v = times_for_by_class(5, int(cls.id)).get(int(period_number))
            if v:
                return v
    except Exception:
        pass
    # Grade-based for Wing 3 composition
    g, sec = parse_grade_section(cls)
    if g >= 10:
        v = times_for(5, "secondary").get(int(period_number))
        if v:
            return v
    if g == 9 and sec is not None and 2 <= int(sec) <= 4:
        v = times_for(5, "grade9").get(int(period_number))
        if v:
            return v
    # Fall back to the generic resolver for Thursday
    return resolve_lesson_time(cls=cls, day=5, period_number=int(period_number))