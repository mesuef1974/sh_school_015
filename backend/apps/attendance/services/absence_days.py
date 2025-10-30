from __future__ import annotations
import datetime as dt
from collections import defaultdict
from typing import Tuple


from school.models import AttendanceRecord, AttendancePolicy, Term, SchoolHoliday  # type: ignore

# Policy mappings
UNEXCUSED = {"absent", "runaway"}
EXCUSED = {"excused"}
NEUTRAL = {"present", "late", "left_early"}


def _policy_for_date(d: dt.date) -> AttendancePolicy | None:
    term = Term.objects.filter(start_date__lte=d, end_date__gte=d).order_by("-start_date").first()
    if not term:
        return None
    return AttendancePolicy.objects.filter(term=term).order_by("-id").first()


def _holidays_between(start: dt.date, end: dt.date) -> set[dt.date]:
    return set(SchoolHoliday.objects.filter(date__range=[start, end]).values_list("date", flat=True))


def compute_absence_days(student_id: int, start_date: dt.date, end_date: dt.date) -> Tuple[int, int]:
    """Compute full-day absences within [start_date, end_date] based on first-two-periods rule.

    Rules:
    - Count a full day only if both first two periods have status within {excused, unexcused} (not neutral/none).
    - If any of the two is unexcused => day counts as unexcused.
    - If both are excused => day counts as excused.
    - Ignore holidays and non-working days (if day_of_week available in rows and not in working_days).
    """
    if not start_date or not end_date or start_date > end_date:
        return 0, 0

    # Determine policy reference (use start or end date whichever available)
    pol = _policy_for_date(start_date) or _policy_for_date(end_date)
    first_two = set((pol.first_two_periods_numbers or [1, 2])) if pol else {1, 2}
    working_days = set(pol.working_days or [1, 2, 3, 4, 5]) if pol else {1, 2, 3, 4, 5}

    holidays = _holidays_between(start_date, end_date)

    rows = AttendanceRecord.objects.filter(
        student_id=student_id, date__range=[start_date, end_date], period_number__in=list(first_two)
    ).values("date", "period_number", "status", "day_of_week")

    per_day: dict[dt.date, dict[int, str | None]] = defaultdict(lambda: {n: None for n in first_two})
    day_of_week_map: dict[dt.date, int] = {}
    for r in rows:
        per_day[r["date"]][r["period_number"]] = r["status"]
        day_of_week_map[r["date"]] = r["day_of_week"]

    excused_days = 0
    unexcused_days = 0

    cur = start_date
    one_day = dt.timedelta(days=1)
    while cur <= end_date:
        if cur in holidays:
            cur += one_day
            continue
        dow = day_of_week_map.get(cur)
        if dow is not None and dow not in working_days:
            cur += one_day
            continue
        p = per_day.get(cur)
        if p:
            statuses = [p.get(n) for n in first_two]
            # Ensure both are from {excused, unexcused}
            if any(s is None or s in NEUTRAL for s in statuses):
                cur += one_day
                continue
            if any(s in UNEXCUSED for s in statuses):
                unexcused_days += 1
            elif all(s in EXCUSED for s in statuses):
                excused_days += 1
        cur += one_day

    return excused_days, unexcused_days
