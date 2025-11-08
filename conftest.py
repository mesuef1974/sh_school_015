import os

# Respect existing DJANGO_SETTINGS_MODULE (e.g., CI sets core.settings_test). Default to lightweight test settings.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings_test")

# Ensure backend package is importable regardless of CWD
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
backend = root / "backend"
if str(backend) not in sys.path:
    sys.path.insert(0, str(backend))

# Defer django.setup() to pytest-django; it calls setup itself when needed
# However, ensure apps are loaded early to support tests that import models at module scope
try:
    import django  # type: ignore
    django.setup()
except Exception:
    pass
# Existing root conftest keeps DJANGO_SETTINGS_MODULE and adds backend to sys.path
# The following fixture provides a tiny coherent dataset for non-empty tests.

import datetime as _dt
import pytest


@pytest.fixture()
def minimal_school_data(db):
    """
    Tiny coherent dataset for non-empty bounded-queries tests.
    Returns: { term, wing, classroom, teacher_staff, teacher_user, subject, students[list], date }
    """
    from django.contrib.auth.models import Group, User  # type: ignore
    from school.models import (
        AcademicYear,
        Term,
        Wing,
        Class as Classroom,
        Staff,
        Subject,
        ClassSubject,
        TeachingAssignment,
        Student,
        AttendanceRecord,
    )  # type: ignore

    # Academic year and current term
    ay = AcademicYear.objects.create(
        name="1446/1447",
        start_date=_dt.date(2024, 8, 1),
        end_date=_dt.date(2025, 7, 31),
        is_current=True,
    )
    term = Term.objects.create(
        name="Term 1",
        start_date=_dt.date(2024, 8, 18),
        end_date=_dt.date(2024, 12, 31),
        is_current=True,
        academic_year=ay,
    )

    # Wing and class
    wing = Wing.objects.create(name="A")
    classroom = Classroom.objects.create(name="10-1", wing=wing)

    # Teacher user + staff
    teacher_user = User.objects.create_user(
        username="t_min", email="t_min@example.com", password="pass1234"
    )
    # Put user in teacher group if it exists (tolerant)
    try:
        grp, _ = Group.objects.get_or_create(name="teacher")
        teacher_user.groups.add(grp)
    except Exception:
        pass
    staff = Staff.objects.create(user=teacher_user, full_name="Teacher Minimal")

    # Subject and teaching assignment
    subject = Subject.objects.create(name_ar="رياضيات")
    # Ensure subject is available for the classroom to satisfy TeachingAssignment.clean()
    ClassSubject.objects.create(classroom=classroom, subject=subject, weekly_default=5)
    TeachingAssignment.objects.create(teacher=staff, classroom=classroom, subject=subject, no_classes_weekly=5)

    # Students
    s1 = Student.objects.create(full_name="طالب 1", class_fk=classroom, sid="1001")
    s2 = Student.objects.create(full_name="طالب 2", class_fk=classroom, sid="1002")

    # One attendance record on a fixed date within the term
    dt = term.start_date + _dt.timedelta(days=1)
    dow = dt.isoweekday()  # 1..7
    AttendanceRecord.objects.create(
        student=s1,
        classroom=classroom,
        subject=subject,
        teacher=staff,
        term=term,
        date=dt,
        day_of_week=dow,
        period_number=1,
        start_time=_dt.time(8, 0),
        end_time=_dt.time(8, 45),
        status="present",
        note="",
        source="teacher",
        locked=False,
    )

    return {
        "term": term,
        "wing": wing,
        "classroom": classroom,
        "teacher_staff": staff,
        "teacher_user": teacher_user,
        "subject": subject,
        "students": [s1, s2],
        "date": dt,
    }