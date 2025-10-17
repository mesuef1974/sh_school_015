import pytest


@pytest.mark.django_db
def test_attendance_students_requires_auth(client):
    # Now the endpoint requires authentication; unauthenticated should be 401
    resp = client.get("/api/v1/attendance/students/")
    assert resp.status_code == 401
