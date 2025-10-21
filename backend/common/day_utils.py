from datetime import date as _date
from typing import Optional


def iso_to_school_dow(dt: _date) -> int:
    """Convert ISO weekday (Mon=1..Sun=7) to school day (Sun=1..Sat=7)."""
    return (dt.isoweekday() % 7) + 1


def iso_to_school_dow_from_iso(iso: int) -> Optional[int]:
    """Convert ISO weekday number (1=Mon ... 7=Sun) to school day (Sun=1 ... Sat=7).
    Returns None for non-working days (Fri=6, Sat=7 in school format)."""
    school_day = (iso % 7) + 1
    return school_day if 1 <= school_day <= 5 else None
