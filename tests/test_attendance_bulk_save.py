import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from school.models import Class, Student, AttendanceRecord
from datetime import date as _date


@pytest.mark.django_db
def test_bulk_save_sets_day_of_week_and_returns_200():
    # Create a superuser to bypass teacher assignment checks
    User = get_user_model()
    User.objects.create_superuser(username="admin", password="Pass!234", email="admin@example.com")

    # Minimal data: one class and one student
    c = Class.objects.create(name="12/1")
    s = Student.objects.create(sid="S1", full_name="طالب اختبار", class_fk=c)

    client = APIClient()
    token_resp = client.post(
        "/api/token/", {"username": "admin", "password": "Pass!234"}, format="json"
    )
    assert token_resp.status_code == 200, token_resp.content
    access = token_resp.json()["access"]

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    dt = _date(2025, 10, 17)
    payload = {
        "class_id": c.id,
        "date": dt.isoformat(),
        "records": [{"student_id": s.id, "status": "present", "note": "ok"}],
    }
    resp = client.post("/api/v1/attendance/bulk_save/", payload, format="json")
    assert resp.status_code == 200, resp.content
    # Verify record exists and day_of_week populated (1..7)
    # FK could be classroom_id or class_id depending on model; filter by date+student
    rec = AttendanceRecord.objects.get(date=dt, student_id=s.id)
    assert getattr(rec, "day_of_week", None) in (1, 2, 3, 4, 5, 6, 7)
