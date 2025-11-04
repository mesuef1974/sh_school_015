from __future__ import annotations

from datetime import date
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
