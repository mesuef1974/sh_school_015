from __future__ import annotations

import datetime as _dt
import pytest

from django.contrib.auth.models import Group, User


@pytest.fixture()
def minimal_school_data(db):
    """
    Create a tiny but coherent set of school data to exercise non-empty endpoints
    without slowing tests.

    Returns a dict with keys: term, wing, classroom, teacher_staff, teacher_user,
    subject, students(list), date
    """
    from school.models import (
        AcademicYear,
        Term,
        Wing,
        Class as Classroom,
        Staff,
        Subject,
        TeachingAssignment,
        Student,
        AttendanceRecord,
    )  # type: ignore

    # Academic year and current term
    ay = AcademicYear.objects.create(name="1446/1447", start_date=_dt.date(2024, 8, 1), end_date=_dt.date(2025, 7, 31), is_current=True)
    term = Term.objects.create(
        name="Term 1",
        start_date=_dt.date(2024, 8, 18),
        end_date=_dt.date(2024, 12, 31),
        is_current=True,
        academic_year=ay,
    )

    # Wing and class
    wing = Wing.objects.create(name="A", number=1)
    classroom = Classroom.objects.create(name="10-1", wing=wing)

    # Teacher user + staff
    teacher_user = User.objects.create_user(username="t_min", email="t_min@example.com", password="pass1234")
    # Put user in teacher group if it exists (tolerant)
    try:
        grp, _ = Group.objects.get_or_create(name="teacher")
        teacher_user.groups.add(grp)
    except Exception:
        pass
    staff = Staff.objects.create(user=teacher_user, full_name="Teacher Minimal")

    # Subject and teaching assignment
    subject = Subject.objects.create(name_ar="رياضيات", name_en="Math")
    TeachingAssignment.objects.create(teacher=staff, classroom=classroom, subject=subject)

    # Students
    s1 = Student.objects.create(full_name="طالب 1", class_fk=classroom)
    s2 = Student.objects.create(full_name="طالب 2", class_fk=classroom)

    # One attendance record on a fixed date
    dt = _dt.date(2024, 1, 1)
    dow = dt.isoweekday() % 7 + 1 if dt.isoweekday() == 7 else dt.isoweekday()  # map Mon=1..Sun=7 → keep 1..7
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