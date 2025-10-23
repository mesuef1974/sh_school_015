from __future__ import annotations

from typing import Iterable, Set

# Centralized role normalization and routing
# Maps various Arabic/English names to canonical role codes used by Frontend and guards
NORMALIZE_MAP: dict[str, str] = {
    # Teacher
    'teacher': 'teacher',
    'subject teacher': 'teacher',
    'معلم': 'teacher',
    'معلّم': 'teacher',
    # Wing Supervisor
    'wing_supervisor': 'wing_supervisor',
    'wing supervisor': 'wing_supervisor',
    'مشرف الجناح': 'wing_supervisor',
    'supervisor': 'wing_supervisor',  # legacy generic name
    # Subject Coordinator
    'subject_coordinator': 'subject_coordinator',
    'subject coordinator': 'subject_coordinator',
    'منسق المواد': 'subject_coordinator',
    'منسّق المواد': 'subject_coordinator',
    # Principal
    'principal': 'principal',
    'المدير': 'principal',
    'مدير': 'principal',
    # Academic Deputy / Vice Principal
    'academic_deputy': 'academic_deputy',
    'vice principal': 'academic_deputy',
    'النائب الأكاديمي': 'academic_deputy',
    'نائب أكاديمي': 'academic_deputy',
    # Timetable Manager
    'timetable_manager': 'timetable_manager',
    'timetable manager': 'timetable_manager',
    'مسؤول الجداول': 'timetable_manager',
}

# Role priority for choosing primary dashboard
PRIORITY_ORDER: list[str] = [
    'principal', 'academic_deputy', 'timetable_manager',
    'subject_coordinator', 'wing_supervisor', 'teacher'
]

# Route mapping per role
ROUTE_BY_ROLE: dict[str, str] = {
    'principal': '/principal/dashboard',
    'academic_deputy': '/academic/dashboard',
    'timetable_manager': '/timetable',
    'subject_coordinator': '/subject/dashboard',
    'wing_supervisor': '/wing/dashboard',
    'teacher': '/attendance/teacher',
}


def normalize_roles(raw_roles: Iterable[str] | None) -> Set[str]:
    out: Set[str] = set()
    for r in (raw_roles or []):
        k = str(r or '').strip().lower()
        if not k:
            continue
        out.add(NORMALIZE_MAP.get(k, k))  # leave unknowns as-is (non-breaking)
    return out


def pick_primary_route(roles: Set[str]) -> str:
    for r in PRIORITY_ORDER:
        if r in roles:
            return ROUTE_BY_ROLE[r]
    return '/'