from __future__ import annotations

from datetime import date, timedelta
from typing import Optional, Tuple


def parse_ui_or_iso_date(s: Optional[str]) -> Optional[date]:
    """Parse a date string in either UI format (DD/MM/YYYY) or ISO (YYYY-MM-DD).

    Returns a datetime.date on success, or None on failure/empty.
    """
    if not s:
        return None
    s = s.strip()
    if not s:
        return None

    # Try UI format DD/MM/YYYY
    try:
        if "/" in s:
            parts = s.split("/")
            if len(parts) == 3:
                d, m, y = parts
                if len(y) == 4:
                    dd = int(d)
                    mm = int(m)
                    yy = int(y)
                    return date(yy, mm, dd)
    except Exception:
        pass

    # Try ISO YYYY-MM-DD
    try:
        if "-" in s and len(s) >= 10:
            return date.fromisoformat(s[:10])
    except Exception:
        pass

    return None


def parse_date_or_error(s: Optional[str]) -> Tuple[Optional[date], Optional[str]]:
    """Parse using parse_ui_or_iso_date and return (date, error_message).

    error_message is None on success; otherwise a human-friendly message
    listing acceptable formats.
    """
    dt = parse_ui_or_iso_date(s)
    if dt is None:
        return None, "date must be in 'DD/MM/YYYY' or 'YYYY-MM-DD' format"
    return dt, None


# ============ Business days utilities ============
_WK_MAP = {
    "MON": 0,
    "TUE": 1,
    "WED": 2,
    "THU": 3,
    "FRI": 4,
    "SAT": 5,
    "SUN": 6,
}


def _parse_workweek(spec: str | None) -> set[int]:
    """Parse a workweek spec like 'SUN-THU' or 'MON-FRI' into a set of weekday indexes.
    Defaults to SUN-THU if spec is invalid.
    """
    if not spec:
        return {6, 0, 1, 2, 3}  # SUN-THU
    spec = spec.strip().upper()
    if "-" in spec and len(spec) >= 7:
        a, b = [x.strip() for x in spec.split("-", 1)]
        if a in _WK_MAP and b in _WK_MAP:
            start = _WK_MAP[a]
            end = _WK_MAP[b]
            days = set()
            i = start
            while True:
                days.add(i)
                if i == end:
                    break
                i = (i + 1) % 7
            return days
    # Fallback: accept comma-separated days, e.g., 'SUN,MON,TUE,WED,THU'
    if "," in spec:
        days: set[int] = set()
        for part in spec.split(","):
            part = part.strip()
            if part in _WK_MAP:
                days.add(_WK_MAP[part])
        if days:
            return days
    return {6, 0, 1, 2, 3}


def add_business_days(start: date, days: int, *, workweek: str | None = None) -> date:
    """Add N business days to a date using a configurable workweek.

    - start: starting date (the count starts from the next day).
    - days: number of business days to add (>=0).
    - workweek: like 'SUN-THU' (default) or 'MON-FRI'.

    Returns the resulting date after skipping non-working days.
    """
    if days <= 0:
        return start
    working = _parse_workweek(workweek)
    d = start
    added = 0
    while added < days:
        d = d + timedelta(days=1)
        if d.weekday() in working:
            added += 1
    return d
