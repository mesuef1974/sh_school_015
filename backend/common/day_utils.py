from datetime import date as _date


def iso_to_school_dow(dt: _date) -> int:
    """Convert ISO weekday (Mon=1..Sun=7) to school day (Sun=1..Sat=7)."""
    return (dt.isoweekday() % 7) + 1