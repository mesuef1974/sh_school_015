from __future__ import annotations

from typing import Optional

from ..models import AttendancePolicy, AttendanceRecord


def period_minutes_for_term(term) -> int:
    """Return the equivalent period minutes from policy or 45 as a safe default."""
    try:
        if term is None:
            return 45
        policy = AttendancePolicy.objects.filter(term=term).order_by("id").first()
        if policy and getattr(policy, "late_to_equivalent_period_minutes", None):
            return int(policy.late_to_equivalent_period_minutes)
    except Exception:
        pass
    return 45


def compute_late_seconds(record: AttendanceRecord) -> int:
    """Compute late seconds for a given AttendanceRecord applying business rules.
    - For status 'runaway' treat as a full period according to policy.
    - Otherwise use stored late_minutes.
    """
    if getattr(record, "status", None) == "runaway":
        return period_minutes_for_term(getattr(record, "term", None)) * 60
    try:
        return int(record.late_minutes or 0) * 60
    except Exception:
        return 0


def format_mmss(total_seconds: Optional[int]) -> str:
    try:
        s = int(total_seconds)
    except (TypeError, ValueError):
        return "00:00"
    if s < 0:
        s = 0
    m, sec = divmod(s, 60)
    return f"{m:02d}:{sec:02d}"


def format_hhmmss(total_seconds: Optional[int]) -> str:
    try:
        s = int(total_seconds)
    except (TypeError, ValueError):
        return "00:00:00"
    if s < 0:
        s = 0
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"
